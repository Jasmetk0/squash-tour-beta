"""Real HTTP/SQLite Saved v2 parity while the shared pool crashes, stalls and lies.

The complete ``scripts/verify_slot_worker_parity.py`` scenario (two Runs, a
forked second Branch, a barrier-synchronized concurrent write/read step,
Save, restarts, Restore and an exact retry) runs once sequentially and once
with a pool that, batch after batch, crashes its workers, returns duplicate,
missing and foreign responses and stalls past its deadline, then recovers.
Every receipt, view, full sporting checkpoint, Saved history and audit must be
identical, and a sequential replay in a new process of the stored inputs must
verify both final databases identically.
"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from beta_engine.domain.matches import slot_batch
from beta_engine.infrastructure import match_workers
from scripts import verify_slot_worker_parity as parity
from tests.domain.test_match_worker_generations import crash_worker, slow_worker

pytestmark = pytest.mark.smoke

ROOT = Path(__file__).resolve().parents[2]


class _Mutated(match_workers.ProcessBatch):
    def __init__(self, batch, mutate):
        super().__init__(batch.generation, batch.futures, batch.deadline)
        self.mutate = mutate

    def __iter__(self):
        responses = list(super().__iter__())
        responses.sort(key=lambda r: -r.index)  # reversed completion order
        return iter(self.mutate(responses))


FAULTS = {
    "duplicate": lambda rs: [*rs, rs[0]],
    "missing": lambda rs: rs[1:],
    "foreign": lambda rs: [dataclasses.replace(rs[0], index=rs[1].index), *rs[1:]],
    "shuffled": lambda rs: rs,  # valid, merely out of order: must be accepted
}


class FaultScript(match_workers.ProcessMatchExecutor):
    """Applies one scripted fault per admitted batch, in arrival order.

    The injected timeout has its own trigger, independent of runner speed: its
    workers sleep 30 s while its deadline is 1 s. Every admitted batch is kept,
    so each counted timeout is attributed to exactly one batch; a timeout of
    any other (healthy or differently faulted) batch is an unexpected
    production timeout and fails the test with its generation and size.
    """

    def __init__(self, workers, script):
        super().__init__(workers, timeout_cooldown_seconds=3.0)
        self.script = list(script)
        self.applied = []
        self.batches = []  # (fault, the batch object the request thread iterated)
        self._script_lock = threading.Lock()

    def run(self, requests):
        with self._script_lock:  # ``work`` is shared: submit under the script lock
            fault = self.script[0] if self.script else None
            self.work = {"crash": crash_worker, "timeout": slow_worker}.get(fault, slot_batch.run_encoded)
            batch = super().run(requests)  # a declined batch keeps its fault for the next one
            if self.script:
                self.script.pop(0)
            self.applied.append(fault)
            if fault == "timeout":
                batch.deadline = time.monotonic() + 1.0
            elif fault in FAULTS:
                batch = _Mutated(batch, FAULTS[fault])
            self.batches.append((fault, batch))
        return batch

    def timed_out_batches(self):
        return [(fault, batch.generation.number, len(batch.futures))
                for fault, batch in self.batches if batch.timed_out]


@pytest.fixture(scope="module")
def parity_input(tmp_path_factory):
    path = tmp_path_factory.mktemp("slot-worker-parity") / "parity.db"
    previous = {k: os.environ.get(k) for k in (parity.SAVED_STORAGE, parity.WORKERS)}
    try:
        parity.prepare(path)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return path


def _run(tmp_path, source, label, monkeypatch, executor=None):
    monkeypatch.setenv(parity.SAVED_STORAGE, "saved_v2")
    monkeypatch.delenv(parity.WORKERS, raising=False)
    db_a, db_b = tmp_path / f"{label}-a.db", tmp_path / f"{label}-b.db"
    parity.copy_database(source, db_a)
    parity.copy_database(source, db_b)
    previous = slot_batch.install_executor(executor)
    try:
        evidence = parity.scenario(db_a, db_b)
    finally:
        slot_batch.install_executor(previous)
    return evidence, db_a


def _replay(database, branches, tmp_path, label):
    out = tmp_path / f"{label}-replay.json"
    env = {k: v for k, v in os.environ.items() if k != parity.WORKERS}
    env["PYTHONHASHSEED"] = "97"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_slot_worker_parity.py"), "replay",
         "--root", str(ROOT), "--input", str(database), "--branches", ",".join(branches),
         "--out", str(out)],
        check=True, env=env, timeout=1800,
    )
    return json.loads(out.read_text())


def test_faulty_shared_pool_equals_sequential_over_http_saved_v2(tmp_path, parity_input, monkeypatch):
    sequential, sequential_db = _run(tmp_path, parity_input, "sequential", monkeypatch)
    script = ["crash", "duplicate", "missing", "foreign", "shuffled", "timeout"]
    executor = FaultScript(2, script)
    before = slot_batch.batch_counters()
    try:
        faulty, faulty_db = _run(tmp_path, parity_input, "faulty", monkeypatch, executor)
        stats = executor.stats()
    finally:
        executor.close()
    after = slot_batch.batch_counters()
    expected_summary, expected = parity.summarize(sequential)
    actual_summary, actual = parity.summarize(faulty)
    for part in expected:
        assert actual[part] == expected[part], part
    assert actual_summary == expected_summary
    assert executor.applied[: len(script)] == script, executor.applied
    assert after["fallback_batches"] - before["fallback_batches"] >= 5  # every fault but "shuffled"
    assert after["executor_batches"] - before["executor_batches"] >= 2  # healthy after recovery
    timed_out = executor.timed_out_batches()
    assert [fault for fault, *_ in timed_out] == ["timeout"], f"unexpected worker timeouts: {timed_out}"
    assert stats["timeouts"] == 1 and stats["max_live_workers_seen"] <= 2, stats
    assert stats["stuck_manager_threads"] == 0, stats
    assert executor.live_worker_pids() == []
    # Nothing left that interpreter exit would join without a limit.
    managers = [t for t in threading.enumerate() if type(t).__name__ == "_ExecutorManagerThread"]
    assert managers == [], managers
    # A new sequential process re-verifies both stored results identically.
    branches = ["branch", sequential["fork_id"]]
    replay_sequential = _replay(sequential_db, branches, tmp_path, "sequential")
    replay_faulty = _replay(faulty_db, ["branch", faulty["fork_id"]], tmp_path, "faulty")
    assert replay_sequential["digest"] == replay_faulty["digest"]
