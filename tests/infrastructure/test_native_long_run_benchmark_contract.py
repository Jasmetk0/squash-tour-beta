"""Benchmark-driver completeness contract with a simulated transport (not HTTP)."""

import json
import shutil
from types import SimpleNamespace

import pytest

from scripts import profile_native_season_archive as benchmark

pytestmark = pytest.mark.pr_critical


def run(tmp_path, monkeypatch, timeouts):
    source = tmp_path / "input.db"
    source.write_bytes(b"benchmark-driver-test-only")
    monkeypatch.setattr(benchmark, "require_committed_source", lambda: None)
    monkeypatch.setattr(benchmark, "environment", lambda: {})
    monkeypatch.setattr(benchmark, "backup", shutil.copyfile)
    monkeypatch.setattr(benchmark, "data_size", lambda _path: {})
    starts = []

    class Server:
        base = "http://benchmark-driver.invalid"

        def __init__(self, *_args):
            starts.append(1)

        def memory(self):
            return {}

        def stop(self):
            pass

    def http(_method, url, _payload=None):
        restart = len(starts) > 1
        name = next(n for n, p in benchmark.READS if url.endswith(benchmark.TOUR + p))
        if (name, restart) in timeouts:
            return {"status": None, "error": "TimeoutError", "seconds": 120.0, "timeout": True}, None
        return {"status": 200, "seconds": 0.01, "bytes": 2}, json.dumps({"read": name}).encode()

    monkeypatch.setattr(benchmark, "Server", Server)
    monkeypatch.setattr(benchmark, "http", http)
    root = tmp_path / "result"
    arguments = SimpleNamespace(root=root, input=source, profile=False, seasons=1,
                                repeats=1, read_only=True, keep_database=True)
    raised = None
    try:
        benchmark.read(arguments)
    except SystemExit as exc:
        raised = exc
    return json.loads((root / "result.json").read_text()), raised


def test_complete_reads_claim_restart_equality(tmp_path, monkeypatch):
    report, raised = run(tmp_path, monkeypatch, set())
    assert raised is None
    assert report["restart_complete"] is True and report["restart_missing"] == []
    assert set(report["restart_equal"]) == {"tour", "archive", "season0"}


def test_one_censored_restart_read_is_reported_and_fails_the_invocation(tmp_path, monkeypatch):
    report, raised = run(tmp_path, monkeypatch, {("archive", True)})
    assert raised is not None
    assert report["restart_complete"] is False
    assert report["restart_missing"] == ["archive"]
    assert "archive" not in report["restart_equal"]
    assert report["completeness"]["restart_cold"] == {"complete": False, "missing": ["archive"]}
    censored = [r for r in report["records"] if r.get("timeout")]
    assert [(r["phase"], r["read"]) for r in censored] == [("restart_cold", "archive")]
