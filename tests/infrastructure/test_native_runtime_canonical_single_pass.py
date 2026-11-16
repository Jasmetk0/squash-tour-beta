"""Exact canonical runtime proof plus real W52 server-side paired A/B."""
import hashlib
import json
import sqlite3
import statistics
import time
from threading import Lock

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.native_fork_runtime import NativeForkRuntime
from beta_engine.domain.run_revisions import canonical_json
from beta_engine.infrastructure.db import native_fork_runtime_state as storage
from tests.api.test_native_full_simulation_tasks import test_native_task_actual_match_points_all_weeks_and_real_season_rollover
from tests.infrastructure.test_native_fork_runtime_format import runtime_root

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("state,fp", [
    ({"czech": "žluťoučký kůň", "values": [1, -0.0, None]}, "f" * 64),
    ({"emoji": "🎾", "nested": {"x": 1.2e-10}}, "a" * 64),
    ({"obj": {"2": "b", "1": "a"}}, None),
])
def test_canonical_component_identity_bytes_exact(state, fp):
    raw = {"state": state, "fingerprint": fp}
    original = canonical_json(raw).encode("utf-8")
    signature, size, state_json = storage._canonical_runtime_identity(raw)
    assert signature == hashlib.sha256(original).digest()
    assert size == len(original)
    assert state_json == canonical_json(state).encode("utf-8")


def test_runtime_cache_and_corruption_unchanged():
    runtime, revision = runtime_root()
    with storage.native_read_proof_scope() as memo:
        assert storage.load_runtime(revision.payload) == runtime
        assert len(memo["parsed_native_runtimes"]) == 1
        revision.payload["content"]["native_fork_runtime"]["fingerprint"] = "0" * 64
        with pytest.raises(ValueError, match="fingerprint differs"):
            storage.load_runtime(revision.payload)


def _baseline(payload):
    raw = payload["content"]["native_fork_runtime"]
    serialized = canonical_json(raw).encode("utf-8")
    digest = hashlib.sha256(serialized).digest()
    runtime = NativeForkRuntime.model_validate_json(canonical_json(raw["state"]))
    if runtime.fingerprint != raw["fingerprint"]:
        raise ValueError("Native fork runtime fingerprint differs")
    return digest, len(serialized), runtime


def test_actual_native_w52_server_and_paired_runtime_parser(tmp_path, monkeypatch, capsys):
    from beta_engine.application import native_fork_runtime_service as service
    stats = {"calls": 0, "cpu_ns": 0}
    lock = Lock()
    original = service.load_runtime
    def observed(payload):
        t = time.thread_time_ns()
        try:
            return original(payload)
        finally:
            with lock:
                stats["calls"] += 1
                stats["cpu_ns"] += time.thread_time_ns() - t
    monkeypatch.setattr(service, "load_runtime", observed)
    test_native_task_actual_match_points_all_weeks_and_real_season_rollover(
        tmp_path, RunCalendar(52, 51, 2030, 2)
    )
    assert stats["calls"] >= 100

    with sqlite3.connect(f"file:{tmp_path / 'matrix.db'}?mode=ro", uri=True) as sql:
        row = sql.execute(
            "SELECT payload_json FROM branch_saved_revisions "
            "WHERE payload_schema_version='native_fork_saved_root.v2' "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        assert row is not None
    payload = json.loads(row[0])
    reference = _baseline(payload)
    assert storage.load_runtime(payload) == reference[2]
    samples = {"baseline": [], "candidate": []}
    for i in range(9):
        methods = [("baseline", _baseline), ("candidate", storage.load_runtime)]
        if i % 2:
            methods.reverse()
        for name, fn in methods:
            t = time.thread_time_ns()
            result = fn(payload)
            samples[name].append((time.thread_time_ns() - t) / 1e6)
            assert (result[2] if name == "baseline" else result) == reference[2]
    a = statistics.median(samples["baseline"])
    b = statistics.median(samples["candidate"])
    with capsys.disabled():
        print("W52_NATIVE_RUNTIME_SINGLE_PASS " + json.dumps({
            "baseline_median_ms": round(a, 3),
            "candidate_median_ms": round(b, 3),
            "ratio": round(b / a, 4),
            "server_calls": stats["calls"],
            "server_thread_cpu_s": round(stats["cpu_ns"] / 1e9, 3),
            "baseline_samples_ms": [round(x, 3) for x in samples["baseline"]],
            "candidate_samples_ms": [round(x, 3) for x in samples["candidate"]],
            "result_equal": True,
        }, sort_keys=True), flush=True)
