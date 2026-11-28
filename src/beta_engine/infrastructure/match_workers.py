"""Optional bounded spawn pool for independent frozen slot matches.

Off by default. ``BETA_ENGINE_MATCH_WORKERS`` opts in:

* unset, ``""``, ``"0"`` or ``"off"``: the original in-process sequential path;
* ``"auto"``: ``min(4, logical CPUs - 1)`` workers (none on a 1-2 CPU machine);
* a positive integer: exactly that many workers (at most 32).

One pool per server process serves every Run/Branch request; it never grows per
slot. Workers are started with ``spawn`` on every platform (the Windows
behaviour), lazily on the first batch, and receive only encoded pure match
inputs (``FrozenMatchRequest``). They hold no SQLite session, connection,
repository, Signed cache or Save authority. A crash, timeout or rejected result
retires the pool and the batch is recomputed in the parent (see
``beta_engine.domain.matches.slot_batch``).

Concurrency contract (several Run/Branch requests share this executor):

* Every batch is bound to the exact pool *generation* that accepted its
  submissions. Retiring is compare-and-set on that generation only, so a late
  failure of an old batch can never retire a healthy replacement.
* A new generation starts only after every process of a retiring generation
  has been terminated and joined, so this process never has more than
  ``workers`` live match workers, also while a pool is being replaced. A batch
  that arrives meanwhile is computed sequentially in its own request thread.
* Admission is bounded: at most ``max_in_flight`` submitted, unfinished match
  requests per process. A batch that does not fit is computed sequentially.
* Each admitted batch has a deadline proportional to its size (bounded by
  ``batch_timeout_cap``) before the sequential fallback; after a timeout the
  pool is not used for ``timeout_cooldown_seconds``.
* Retiring a generation wakes every other batch still waiting on it at once
  (``GenerationRetired``: an ordinary sequential fallback, not a timeout, no
  cooldown) and ends the generation's processes *and* its manager thread, so
  a retired pool can neither hold a request until its deadline nor block
  interpreter exit.
* No lock is held while a match is simulated or while a result is awaited.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import queue
import threading
import time
from concurrent.futures import ProcessPoolExecutor

from beta_engine.domain.matches import slot_batch

ENVIRONMENT_VARIABLE = "BETA_ENGINE_MATCH_WORKERS"
MAX_WORKERS = 32
_log = logging.getLogger(__name__)


def resolve_worker_count(value: str | None = None, *, cpu_count: int | None = None) -> int:
    if value is None:
        value = os.environ.get(ENVIRONMENT_VARIABLE, "")
    value = value.strip().lower()
    if value in ("", "0", "off", "sequential"):
        return 0
    if value == "auto":
        cpus = cpu_count if cpu_count is not None else (os.cpu_count() or 1)
        workers = min(4, cpus - 1)
        return workers if workers >= 2 else 0
    try:
        workers = int(value)
    except ValueError:
        raise ValueError(f"Invalid {ENVIRONMENT_VARIABLE}: {value!r}") from None
    if not 0 <= workers <= MAX_WORKERS:
        raise ValueError(f"{ENVIRONMENT_VARIABLE} must be between 0 and {MAX_WORKERS}")
    return workers


def _warm_worker():
    # Import the complete engine once per worker, outside any measured batch.
    import beta_engine.domain.matches.match_engine  # noqa: F401
    import beta_engine.domain.matches.slot_batch  # noqa: F401


class GenerationRetired(Exception):
    """The pool generation serving a batch was retired before it completed.

    Raised promptly to every other batch still waiting on that generation (for
    example after a concurrent batch crashed, lied or timed out). It is an
    ordinary fallback, never a timeout of the waiting batch: no cooldown.
    """


_RETIRED = object()  # wake-up sentinel put into the queue of a waiting batch


class _Generation:
    """One concrete ``ProcessPoolExecutor``; retired at most once."""

    __slots__ = ("number", "pool", "lock", "retired", "in_flight", "processes", "waiters",
                 "manager_thread", "result_queue")

    def __init__(self, number, pool):
        self.number = number
        self.pool = pool
        self.lock = threading.Lock()  # submission vs. retirement of this pool only
        self.retired = False
        self.in_flight = 0
        self.processes = ()
        self.waiters = set()  # completion queues of batches iterating this generation
        self.manager_thread = None  # captured at retirement (shutdown drops the reference)
        self.result_queue = None


class ProcessBatch:
    """Futures of one batch, bound to the generation that accepted them."""

    def __init__(self, generation, futures, deadline):
        self.generation = generation
        self.futures = futures
        self.deadline = deadline
        self.timed_out = False
        self.started = time.monotonic()
        self.first_result_seconds = None

    def __iter__(self):
        """Yield responses as workers finish, so the parent decodes meanwhile.

        Completion order is irrelevant: the caller rebinds every response by
        its request index. Completion is observed through done callbacks, not
        ``as_completed``: a future cancelled by the retirement of its pool
        (``shutdown(cancel_futures=True)`` by a concurrent failing batch) is
        never yielded by ``as_completed`` and would otherwise hold this batch
        until its own deadline and be miscounted as a timeout.
        """
        done = queue.SimpleQueue()
        for future in self.futures:
            future.add_done_callback(done.put)  # immediate for finished futures
        generation = self.generation
        with generation.lock:
            if generation.retired:
                done.put(_RETIRED)
            else:
                generation.waiters.add(done)
        pending = len(self.futures)
        try:
            while pending:
                try:
                    # Already delivered completions still count when the
                    # caller spent the rest of the deadline decoding a result.
                    item = done.get(timeout=max(0.0, self.deadline - time.monotonic()))
                except queue.Empty:
                    self.timed_out = True
                    raise TimeoutError(
                        "%d (of %d) futures unfinished" % (pending, len(self.futures))
                    ) from None
                if item is _RETIRED or item.cancelled():
                    raise GenerationRetired(
                        "Match worker pool generation %d was retired with %d of %d results pending"
                        % (generation.number, pending, len(self.futures))
                    )
                pending -= 1
                if self.first_result_seconds is None:
                    self.first_result_seconds = time.monotonic() - self.started
                yield item.result()
        finally:
            with generation.lock:
                generation.waiters.discard(done)

    def close(self):
        for future in self.futures:
            future.cancel()


class ProcessMatchExecutor(slot_batch.MatchBatchExecutor):
    # The pure worker body (tests substitute a crashing or slow one).
    work = staticmethod(slot_batch.run_encoded)

    def __init__(
        self,
        workers,
        *,
        start_method="spawn",
        min_batch=2,
        max_in_flight=None,
        batch_timeout_floor=5.0,
        batch_timeout_per_match=0.5,
        batch_timeout_cap=30.0,
        timeout_cooldown_seconds=30.0,
        join_seconds=5.0,
        clock=time.monotonic,
    ):
        if workers < 1:
            raise ValueError("A process executor needs at least one worker")
        self.workers = workers
        self.start_method = start_method
        self.min_batch = min_batch
        self.max_in_flight = max_in_flight if max_in_flight is not None else max(64, 16 * workers)
        self.batch_timeout_floor = batch_timeout_floor
        self.batch_timeout_per_match = batch_timeout_per_match
        self.batch_timeout_cap = batch_timeout_cap
        self.timeout_cooldown_seconds = timeout_cooldown_seconds
        self.join_seconds = join_seconds
        self._clock = clock
        self._lock = threading.Lock()  # never held while simulating or waiting
        self._current = None
        self._retiring = set()
        self._closed = False
        self._in_flight = 0
        self._unavailable_until = 0.0
        self.pools_started = 0
        self._stats = {
            "admitted_batches": 0, "admitted_matches": 0, "rejected_full": 0,
            "rejected_replacing": 0, "rejected_closed": 0, "rejected_cooldown": 0,
            "retired": 0, "stale_discards": 0, "timeouts": 0, "max_in_flight_seen": 0,
            "max_live_workers_seen": 0, "stuck_manager_threads": 0,
        }

    # -- generation management -------------------------------------------------

    def batch_timeout(self, matches):
        return min(self.batch_timeout_cap, self.batch_timeout_floor + self.batch_timeout_per_match * matches)

    def _generation_for(self, matches):
        """Return the current generation with ``matches`` admitted, or raise."""
        with self._lock:
            if self._closed:
                self._stats["rejected_closed"] += 1
                raise slot_batch.ExecutorUnavailable("Match worker pool is closed")
            if self._clock() < self._unavailable_until:
                self._stats["rejected_cooldown"] += 1
                raise slot_batch.ExecutorUnavailable("Match worker pool cools down after a timeout")
            if self._current is None:
                if self._retiring:
                    # Never more than ``workers`` live processes: wait for the
                    # old pool's processes to be joined (sequential meanwhile).
                    self._stats["rejected_replacing"] += 1
                    raise slot_batch.ExecutorUnavailable("Match worker pool is being replaced")
                self.pools_started += 1
                self._current = _Generation(self.pools_started, ProcessPoolExecutor(
                    max_workers=self.workers,
                    mp_context=multiprocessing.get_context(self.start_method),
                    initializer=_warm_worker,
                ))
            if self._in_flight + matches > self.max_in_flight:
                self._stats["rejected_full"] += 1
                raise slot_batch.ExecutorUnavailable("Match worker queue is full")
            generation = self._current
            self._in_flight += matches
            generation.in_flight += matches
            self._stats["max_in_flight_seen"] = max(self._stats["max_in_flight_seen"], self._in_flight)
            return generation

    def _release(self, generation, count=1):
        with self._lock:
            if not generation.retired:  # a retired generation released everything
                generation.in_flight -= count
                self._in_flight -= count

    def _submit(self, generation, function, arguments):
        """Submit under this generation's lock; refuses a retired generation."""
        futures = []
        with generation.lock:
            if generation.retired:  # its reservation is released by ``_retire``
                raise slot_batch.ExecutorUnavailable("Match worker pool was retired")
            try:
                for argument in arguments:
                    future = generation.pool.submit(function, argument)
                    futures.append(future)
                    future.add_done_callback(lambda _f, g=generation: self._release(g))
            except BaseException:
                self._release(generation, len(arguments) - len(futures))
                for future in futures:
                    future.cancel()
                raise
            live = len(getattr(generation.pool, "_processes", None) or {})
        with self._lock:
            self._stats["max_live_workers_seen"] = max(self._stats["max_live_workers_seen"], live)
        return futures

    def start(self):
        """Start and warm every worker now (optional; otherwise on first batch)."""
        generation = self._generation_for(self.workers)
        futures = self._submit(generation, _run_warm, range(self.workers))
        for future in futures:
            future.result(timeout=self.batch_timeout_cap)

    def run(self, requests):
        requests = list(requests)
        generation = self._generation_for(len(requests))
        try:
            futures = self._submit(generation, self.work, requests)
        except slot_batch.ExecutorUnavailable:
            raise
        except Exception:
            # A broken or shut down pool refused the submission: retire exactly
            # this generation (never a replacement) and let the caller fall back.
            self._retire(generation)
            raise
        with self._lock:
            self._stats["admitted_batches"] += 1
            self._stats["admitted_matches"] += len(requests)
        return ProcessBatch(generation, futures, time.monotonic() + self.batch_timeout(len(requests)))

    def discard(self, batch=None):
        """Retire the generation that served ``batch`` (and only that one)."""
        if not isinstance(batch, ProcessBatch):
            return  # ``run`` raised: it already retired its own generation
        batch.close()
        if batch.timed_out:
            with self._lock:
                self._stats["timeouts"] += 1
                self._unavailable_until = max(
                    self._unavailable_until, self._clock() + self.timeout_cooldown_seconds,
                )
        if not self._retire(batch.generation):
            with self._lock:
                self._stats["stale_discards"] += 1

    def _retire(self, generation):
        """Compare-and-set retirement; returns False if it was already retired."""
        # Lock order is always ``generation.lock`` -> ``self._lock`` (never
        # nested the other way), so retirement cannot deadlock a submission.
        with generation.lock:
            if generation.retired:
                return False
            generation.retired = True  # later submissions to it are refused
            generation.processes = tuple(
                (getattr(generation.pool, "_processes", None) or {}).values()
            )
            # ``shutdown`` drops these references; ``_shutdown`` needs them.
            generation.manager_thread = getattr(generation.pool, "_executor_manager_thread", None)
            generation.result_queue = getattr(generation.pool, "_result_queue", None)
            waiters, generation.waiters = tuple(generation.waiters), set()
        for waiter in waiters:  # every other batch on this pool falls back now
            waiter.put(_RETIRED)
        with self._lock:
            if self._current is generation:
                self._current = None
            # Everything reserved on this generation is released exactly once
            # here; its later completion callbacks are ignored.
            self._in_flight -= generation.in_flight
            generation.in_flight = 0
            self._retiring.add(generation)
            self._stats["retired"] += 1
        stopped = False
        try:
            stopped = _shutdown(
                generation.pool, generation.processes, self.join_seconds,
                manager_thread=generation.manager_thread, result_queue=generation.result_queue,
            )
        finally:
            with self._lock:
                self._retiring.discard(generation)
                if not stopped:
                    self._stats["stuck_manager_threads"] += 1
        if not stopped:
            _log.error("Match worker pool generation %d left its manager thread running",
                       generation.number)
        return True

    # -- observation -----------------------------------------------------------

    def current_generation(self):
        generation = self._current
        return None if generation is None else generation.number

    def worker_pids(self):
        generation = self._current
        processes = getattr(generation.pool, "_processes", None) if generation is not None else None
        return sorted(processes or {})

    def live_worker_pids(self):
        """Every not yet joined worker of this executor, any generation."""
        with self._lock:
            generations = [g for g in (self._current, *self._retiring) if g is not None]
        pids = set()
        for generation in generations:
            processes = generation.processes or tuple(
                (getattr(generation.pool, "_processes", None) or {}).values()
            )
            pids.update(p.pid for p in processes if p.is_alive())
        return sorted(pids)

    def stats(self):
        with self._lock:
            return {**self._stats, "in_flight": self._in_flight,
                    "pools_started": self.pools_started, "retiring": len(self._retiring)}

    def close(self):
        with self._lock:
            self._closed = True
            generation = self._current
        if generation is not None:
            self._retire(generation)


def _run_warm(_index):
    _warm_worker()
    return os.getpid()


def _shutdown(pool, processes, join_seconds, *, manager_thread=None, result_queue=None):
    """Stop one retired pool: its processes and its manager thread.

    Returns whether the pool's manager thread has ended. A worker terminated
    while it was writing a large result leaves a partial message in the
    result pipe. The manager thread then blocks in ``recv`` for bytes that
    never come, because this process itself still holds the pipe's write end
    (CPython 3.11-3.13 close it only in ``shutdown(wait=True)``). Interpreter
    exit joins that thread without a limit (``concurrent.futures.process.
    _python_exit``), so the whole process could never exit. Once every
    worker is joined nothing can write a result any more: closing the parent's
    write end turns the partial read into EOF, the manager thread marks the
    pool broken and ends.
    """
    try:
        pool.shutdown(wait=False, cancel_futures=True)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join(timeout=join_seconds)
            if process.is_alive():
                process.kill()
                process.join(timeout=join_seconds)
        if not any(process.is_alive() for process in processes):
            writer = getattr(result_queue, "_writer", None)
            if writer is not None:
                try:
                    writer.close()
                except OSError:
                    pass
    if manager_thread is None or manager_thread is threading.current_thread():
        return True
    manager_thread.join(timeout=join_seconds)
    return not manager_thread.is_alive()


def install_from_environment(value: str | None = None):
    """Install a pool when opted in; returns the installed executor or None.

    Does not replace an executor somebody else installed in this process.
    """
    workers = resolve_worker_count(value)
    if workers == 0 or slot_batch.installed_executor() is not None:
        return None
    executor = ProcessMatchExecutor(workers)
    if slot_batch.install_executor_if_absent(executor) is not executor:
        return None
    _log.info("Independent slot matches use %d spawn workers", workers)
    return executor


def uninstall(executor):
    if executor is None:
        return
    slot_batch.uninstall_executor(executor)
    executor.close()
