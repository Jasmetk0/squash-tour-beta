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
discards the pool and the batch is recomputed in the parent (see
``beta_engine.domain.matches.slot_batch``).
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed

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


class ProcessMatchExecutor(slot_batch.MatchBatchExecutor):
    def __init__(self, workers, *, start_method="spawn", timeout_seconds=600.0, min_batch=2):
        if workers < 1:
            raise ValueError("A process executor needs at least one worker")
        self.workers = workers
        self.start_method = start_method
        self.timeout_seconds = timeout_seconds
        self.min_batch = min_batch
        self._lock = threading.Lock()
        self._pool = None
        self._closed = False
        self.pools_started = 0

    def _ensure_pool(self):
        with self._lock:
            if self._closed:
                raise RuntimeError("Match worker pool is closed")
            if self._pool is None:
                self._pool = ProcessPoolExecutor(
                    max_workers=self.workers,
                    mp_context=multiprocessing.get_context(self.start_method),
                    initializer=_warm_worker,
                )
                self.pools_started += 1
            return self._pool

    def start(self):
        """Start and warm every worker now (optional; otherwise on first batch)."""
        pool = self._ensure_pool()
        for future in [pool.submit(_warm_worker) for _ in range(self.workers)]:
            future.result(timeout=self.timeout_seconds)

    def run(self, requests):
        """Yield responses as workers finish, so the parent decodes meanwhile.

        Completion order is irrelevant: the caller rebinds every response by
        its request index. Stopping early (a rejected result) cancels the rest.
        """
        pool = self._ensure_pool()
        futures = [pool.submit(slot_batch.run_encoded, request) for request in requests]
        try:
            for future in as_completed(futures, timeout=self.timeout_seconds):
                yield future.result()
        finally:
            for future in futures:
                future.cancel()

    def worker_pids(self):
        pool = self._pool
        processes = getattr(pool, "_processes", None) or {}
        return sorted(processes)

    def discard(self):
        with self._lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            _shutdown(pool)

    def close(self):
        with self._lock:
            self._closed = True
            pool, self._pool = self._pool, None
        if pool is not None:
            _shutdown(pool)


def _shutdown(pool):
    processes = list((getattr(pool, "_processes", None) or {}).values())
    try:
        pool.shutdown(wait=False, cancel_futures=True)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join(timeout=10)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)


def install_from_environment(value: str | None = None):
    """Install a pool when opted in; returns the installed executor or None.

    Does not replace an executor somebody else installed in this process.
    """
    workers = resolve_worker_count(value)
    if workers == 0 or slot_batch.installed_executor() is not None:
        return None
    executor = ProcessMatchExecutor(workers)
    slot_batch.install_executor(executor)
    _log.info("Independent slot matches use %d spawn workers", workers)
    return executor


def uninstall(executor):
    if executor is None:
        return
    if slot_batch.installed_executor() is executor:
        slot_batch.install_executor(None)
    executor.close()
