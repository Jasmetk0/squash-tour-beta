"""Pool generations, bounded admission and deadlines of the opt-in spawn workers.

Pool integration scenarios use the real ``ProcessPoolExecutor`` with ``spawn`` and is
synchronized with events (no sleeps decide an outcome). A retired generation
never affects a newer one, this process never has more live match workers
than configured (also while a pool is replaced), and every declined, timed out
or failed batch returns the original sequential bytes.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from concurrent.futures import Future

import pytest

from beta_engine.domain.matches import slot_batch
from beta_engine.infrastructure import match_workers
from tests.domain.test_slot_match_batch import corpus

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def items():
    return corpus(6)


@pytest.fixture(scope="module")
def sequential(items):
    return slot_batch.simulate_batch(items)


def _requests(items, offset=0):
    return [
        slot_batch.encode_request(offset + i, c, seed=s, anchor=a, health=h)
        for i, (c, s, a, h) in enumerate(items)
    ]


def _bytes(results):
    return [r.model_dump_json() for r in results]


def _alive(pids):
    return [pid for pid in pids if os.path.exists(f"/proc/{pid}")] if os.path.isdir("/proc") else []


def crash_worker(_request):
    os._exit(3)


def slow_worker(request):
    time.sleep(30)
    return slot_batch.run_encoded(request)


PARTIAL_MARKER = "BETA_ENGINE_TEST_PARTIAL_RESULT_MARKER"


def partial_result_worker(_request):
    """Write the first bytes of a large result, then stall like a busy sender.

    This is exactly the state of a worker terminated in the middle of
    ``send_bytes`` of a big ``MatchResult``: the length header promises 1 MiB,
    only 1 KiB arrives. The marker file says the partial message is written.
    """
    import gc
    import multiprocessing.queues
    import struct

    (results,) = [o for o in gc.get_objects() if isinstance(o, multiprocessing.queues.SimpleQueue)]
    with results._wlock:
        results._writer._send(struct.pack("!i", 1 << 20) + b"\0" * 1024)
        with open(os.environ[PARTIAL_MARKER], "w") as marker:
            marker.write(str(os.getpid()))
        time.sleep(600)


def _wait(predicate, seconds=30.0):
    end = time.monotonic() + seconds
    while not predicate():
        if time.monotonic() > end:
            raise AssertionError("condition not reached")
        time.sleep(0.01)


def test_a_late_failure_of_an_old_batch_never_retires_the_replacement(items, sequential):
    executor = match_workers.ProcessMatchExecutor(2)
    try:
        old = executor.run(_requests(items[:2]))          # generation 1, still in flight
        failing = executor.run(_requests(items[2:4], 2))  # generation 1
        executor.discard(failing)                         # its failure retires generation 1
        assert executor.current_generation() is None and executor.live_worker_pids() == []
        fresh = executor.run(_requests(items[:4]))        # generation 2
        assert fresh.generation.number == 2
        executor.discard(old)                             # the late failure of the old batch
        assert executor.current_generation() == 2
        stats = executor.stats()
        assert stats["retired"] == 1 and stats["stale_discards"] == 1
        responses = sorted(fresh, key=lambda r: r.index)
        expected = _requests(items[:4])
        decoded = [slot_batch.bind_response(r, q, c) for r, q, (c, *_rest) in zip(responses, expected, items)]
        assert _bytes(decoded) == _bytes(sequential[:4])
        assert len(executor.live_worker_pids()) <= 2
    finally:
        executor.close()


class _GatedBatch(match_workers.ProcessBatch):
    """A real batch whose first response waits for ``gate``, then fails."""

    def __init__(self, batch, submitted, gate):
        super().__init__(batch.generation, batch.futures, batch.deadline)
        self.submitted, self.gate = submitted, gate

    def __iter__(self):
        self.submitted.set()
        assert self.gate.wait(60)
        raise RuntimeError("late failure of a batch on the old generation")


class _Scripted(match_workers.ProcessMatchExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hooks = {}

    def run(self, requests):
        hook = self.hooks.pop(requests[0].match_id, None)
        self.work = crash_worker if hook == "crash" else slot_batch.run_encoded
        batch = super().run(requests)
        return hook(batch) if callable(hook) else batch


def test_concurrent_simulate_batch_late_failure_keeps_the_healthy_pool(items, sequential):
    executor = _Scripted(2)
    submitted, gate = threading.Event(), threading.Event()
    late = {}
    executor.hooks[items[0][0].match_id] = lambda b: _GatedBatch(b, submitted, gate)
    before = slot_batch.batch_counters()

    def old_request():
        late["results"] = slot_batch.simulate_batch(items[:2], executor=executor)

    thread = threading.Thread(target=old_request)
    try:
        thread.start()
        assert submitted.wait(60)                 # the old batch holds generation 1
        executor.hooks[items[2][0].match_id] = "crash"
        assert slot_batch.simulate_batch(items[2:4], executor=executor) == sequential[2:4]
        assert executor.current_generation() is None
        replacement = slot_batch.simulate_batch(items[2:6], executor=executor)  # generation 2
        assert executor.current_generation() == 2
        gate.set()                                # the old batch now fails late
        thread.join(60)
        assert late["results"] == sequential[:2]
        assert executor.current_generation() == 2  # not retired by the old batch
        healthy = slot_batch.simulate_batch(items, executor=executor)
        assert _bytes(healthy) == _bytes(sequential) and replacement == sequential[2:6]
        stats = executor.stats()
        assert stats["pools_started"] == 2 and stats["retired"] == 1 and stats["stale_discards"] == 1
        after = slot_batch.batch_counters()
        assert after["fallback_batches"] - before["fallback_batches"] == 2  # crash + late failure
        assert after["executor_batches"] - before["executor_batches"] == 2  # replacement + healthy
        assert stats["max_live_workers_seen"] <= 2
    finally:
        gate.set()
        thread.join(60)
        executor.close()


def test_replacement_waits_for_the_old_processes_and_never_exceeds_the_worker_limit(
    items, sequential, monkeypatch,
):
    executor = match_workers.ProcessMatchExecutor(2)
    real_shutdown = match_workers._shutdown
    joining, release = threading.Event(), threading.Event()

    def slow_shutdown(pool, processes, join_seconds, **kwargs):
        joining.set()
        assert release.wait(60)
        return real_shutdown(pool, processes, join_seconds, **kwargs)

    try:
        executor.start()
        old_pids = executor.worker_pids()
        assert len(old_pids) == 2
        batch = executor.run(_requests(items[:2]))
        list(batch)
        monkeypatch.setattr(match_workers, "_shutdown", slow_shutdown)
        retiring = threading.Thread(target=executor.discard, args=(batch,))
        retiring.start()
        assert joining.wait(60)
        before = slot_batch.batch_counters()["unavailable_batches"]
        # While the old processes are still alive, no second pool starts.
        assert slot_batch.simulate_batch(items[:3], executor=executor) == sequential[:3]
        assert slot_batch.batch_counters()["unavailable_batches"] == before + 1
        assert executor.pools_started == 1 and executor.stats()["retiring"] == 1
        assert len(executor.live_worker_pids()) <= 2
        release.set()
        retiring.join(60)
        assert _alive(old_pids) == []
        assert slot_batch.simulate_batch(items, executor=executor) == sequential
        assert executor.pools_started == 2
        new_pids = executor.live_worker_pids()
        assert 1 <= len(new_pids) <= 2 and not set(new_pids) & set(old_pids)
    finally:
        release.set()
        executor.close()


def test_admission_is_bounded_and_a_declined_batch_is_sequential(items, sequential):
    executor = match_workers.ProcessMatchExecutor(2, max_in_flight=4)
    try:
        with pytest.raises(slot_batch.ExecutorUnavailable):
            executor.run(_requests(items[:5]))
        assert executor.stats()["in_flight"] == 0
        held = executor.run(_requests(items[:3]))
        assert executor.stats()["in_flight"] == 3
        before = slot_batch.batch_counters()
        # The queue is full for a second batch: it runs in the parent, now.
        assert slot_batch.simulate_batch(items[3:5], executor=executor) == sequential[3:5]
        after = slot_batch.batch_counters()
        assert after["unavailable_batches"] == before["unavailable_batches"] + 1
        assert after["fallback_batches"] == before["fallback_batches"]
        assert len(list(held)) == 3
        _wait(lambda: executor.stats()["in_flight"] == 0)
        assert slot_batch.simulate_batch(items[3:6], executor=executor) == sequential[3:6]
        stats = executor.stats()
        assert stats["rejected_full"] == 2 and stats["max_in_flight_seen"] <= 4
        assert stats["retired"] == 0
    finally:
        executor.close()


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_a_stalled_batch_falls_back_within_its_deadline_and_cools_down(items, sequential):
    clock = _Clock()
    executor = match_workers.ProcessMatchExecutor(
        2, batch_timeout_floor=1.0, batch_timeout_per_match=0.25, batch_timeout_cap=2.0,
        timeout_cooldown_seconds=60.0, clock=clock,
    )
    assert executor.batch_timeout(2) == 1.5 and executor.batch_timeout(32) == 2.0
    try:
        executor.start()  # exclude the cold start from the measured deadline
        executor.work = slow_worker
        started = time.monotonic()
        before = slot_batch.batch_counters()
        assert slot_batch.simulate_batch(items[:2], executor=executor) == sequential[:2]
        elapsed = time.monotonic() - started
        assert elapsed < 1.5 + executor.join_seconds + 10, elapsed  # deadline, cleanup, recompute
        stats = executor.stats()
        assert stats["timeouts"] == 1 and stats["retired"] == 1 and stats["in_flight"] == 0
        assert executor.live_worker_pids() == []
        assert slot_batch.batch_counters()["fallback_batches"] == before["fallback_batches"] + 1
        executor.work = slot_batch.run_encoded
        # Cooling down: declined without starting a pool.
        assert slot_batch.simulate_batch(items[:3], executor=executor) == sequential[:3]
        assert executor.pools_started == 1 and executor.stats()["rejected_cooldown"] == 1
        clock.now += 61
        assert slot_batch.simulate_batch(items, executor=executor) == sequential
        assert executor.pools_started == 2
    finally:
        executor.close()


def test_close_during_an_in_flight_batch_falls_back_and_leaves_no_process(items, sequential):
    executor = match_workers.ProcessMatchExecutor(2)
    executor.start()
    executor.work = slow_worker
    pids = executor.worker_pids()
    outcome = {}

    def request():
        outcome["results"] = slot_batch.simulate_batch(items[:3], executor=executor)

    thread = threading.Thread(target=request)
    thread.start()
    _wait(lambda: executor.stats()["in_flight"] == 3)
    executor.close()
    thread.join(60)
    assert not thread.is_alive()
    assert outcome["results"] == sequential[:3]
    assert executor.live_worker_pids() == [] and _alive(pids) == []
    with pytest.raises(slot_batch.ExecutorUnavailable):
        executor.run(_requests(items[:2]))
    assert slot_batch.simulate_batch(items[:2], executor=executor) == sequential[:2]


def test_install_is_atomic_and_uninstall_removes_only_its_own_executor():
    previous = slot_batch.install_executor(None)
    try:
        first = match_workers.install_from_environment("2")
        assert match_workers.install_from_environment("2") is None
        other = match_workers.ProcessMatchExecutor(2)
        assert not slot_batch.uninstall_executor(other)
        assert slot_batch.installed_executor() is first
        match_workers.uninstall(first)
        assert slot_batch.installed_executor() is None
        match_workers.uninstall(other)  # closing a never-started executor is harmless
    finally:
        slot_batch.install_executor(previous)


def test_ready_results_can_be_drained_after_the_batch_deadline():
    futures = [Future(), Future()]
    for index, future in enumerate(futures):
        future.set_result(index)
    generation = match_workers._Generation(1, None)
    batch = match_workers.ProcessBatch(generation, futures, time.monotonic() - 1)

    assert list(batch) == [0, 1]
    assert not batch.timed_out


def test_a_retired_generation_wakes_every_other_waiting_batch_without_a_timeout(items, sequential):
    """Nov 27 #1936: a healthy batch sharing a pool with a failing one.

    Batch X holds both workers; batch Y waits on the same generation. X fails
    (crash/duplicate/missing/foreign) and retires the pool. Y must fall back
    at once: its futures are cancelled or never completed by the retired pool,
    so waiting for them until Y's own deadline is a spurious timeout with a
    cooldown. Y returns the sequential bytes and no timeout is counted.
    """
    executor = match_workers.ProcessMatchExecutor(2)
    outcome = {}
    try:
        executor.start()
        executor.work = slow_worker
        held = executor.run(_requests(items[:2]))          # both workers busy for 30 s
        executor.work = slot_batch.run_encoded

        def waiting_request():
            started = time.monotonic()
            outcome["results"] = slot_batch.simulate_batch(items[2:5], executor=executor)
            outcome["seconds"] = time.monotonic() - started

        thread = threading.Thread(target=waiting_request)
        thread.start()
        _wait(lambda: executor.stats()["in_flight"] == 5)  # Y admitted on the same generation
        deadline = executor.batch_timeout(3)
        held.close()
        executor.discard(held)                              # X failed: generation 1 retires
        thread.join(60)
        assert not thread.is_alive()
        assert outcome["results"] == sequential[2:5]
        stats = executor.stats()
        assert stats["timeouts"] == 0 and stats["rejected_cooldown"] == 0, stats
        assert stats["retired"] == 1 and stats["stale_discards"] == 1, stats
        assert stats.get("stuck_manager_threads", 0) == 0 and stats["in_flight"] == 0
        assert outcome["seconds"] < deadline, (outcome["seconds"], deadline)
        assert executor.live_worker_pids() == []
        # Not cooling down: the very next batch is served by a new generation.
        assert slot_batch.simulate_batch(items, executor=executor) == sequential
        assert executor.pools_started == 2
    finally:
        executor.close()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX byte-stream result pipe")
def test_a_worker_killed_while_sending_its_result_never_blocks_the_manager_thread(
    items, tmp_path, monkeypatch,
):
    """Nov 27 #1936: the pytest step that never exited after its summary.

    A worker retired in the middle of writing a large result leaves a partial
    message. Without help, the manager thread of the retired pool blocks in
    ``recv`` forever and interpreter exit (``_python_exit``) joins it without
    a limit. Retirement must end that thread too.
    """
    marker = tmp_path / "partial"
    monkeypatch.setenv(PARTIAL_MARKER, str(marker))
    executor = match_workers.ProcessMatchExecutor(1)
    pool = thread = results = None
    try:
        executor.work = partial_result_worker
        batch = executor.run(_requests(items[:1]))
        pool = batch.generation.pool
        thread, results = pool._executor_manager_thread, pool._result_queue
        _wait(marker.exists, 120)                           # the partial message is in the pipe
        _wait(lambda: not results._reader.poll(0), 30)      # and the manager thread is reading it
        batch.close()
        executor.discard(batch)                             # e.g. the batch's deadline expired
        assert executor.stats().get("stuck_manager_threads", 0) == 0
        assert not thread.is_alive()
        assert executor.live_worker_pids() == []
        assert not [t for t in threading.enumerate() if t is thread]
    finally:
        executor.close()
        if thread is not None and thread.is_alive():
            # Regression: unblock it anyway so this test process can still exit.
            results._writer.close()
            thread.join(30)
