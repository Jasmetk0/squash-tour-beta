"""Benchmark-driver contract with simulated timeouts, not an HTTP integration test."""

import json
import shutil
from types import SimpleNamespace

import pytest

from scripts import profile_native_season_archive as benchmark

pytestmark = pytest.mark.pr_critical


def test_all_censored_reads_cannot_claim_complete_restart_equality(tmp_path, monkeypatch):
    source = tmp_path / "input.db"
    source.write_bytes(b"benchmark-driver-test-only")
    monkeypatch.setattr(benchmark, "require_committed_source", lambda: None)
    monkeypatch.setattr(benchmark, "environment", lambda: {})
    monkeypatch.setattr(benchmark, "backup", shutil.copyfile)
    monkeypatch.setattr(benchmark, "data_size", lambda _path: {})

    class Server:
        base = "http://benchmark-driver.invalid"

        def __init__(self, *_args):
            pass

        def memory(self):
            return {}

        def stop(self):
            pass

    monkeypatch.setattr(benchmark, "Server", Server)
    monkeypatch.setattr(benchmark, "http", lambda *_args, **_kwargs: (
        {"status": None, "error": "TimeoutError", "seconds": 120, "timeout": True}, None))
    root = tmp_path / "result"
    arguments = SimpleNamespace(root=root, input=source, profile=False, seasons=1,
                                repeats=1, read_only=True, keep_database=True)
    try:
        benchmark.read(arguments)
    except (RuntimeError, AssertionError, SystemExit):
        return  # A failed/incomplete invocation also correctly fails closed.
    report = json.loads((root / "result.json").read_text())
    assert report.get("restart_complete") is False, (
        "Missing every response must be explicitly incomplete; all({}.values()) is not a proof"
    )
