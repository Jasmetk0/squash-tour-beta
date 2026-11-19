"""Fast bounded-load safety, telemetry and Saved v2 history tests.

No 1,000-player HTTP/SQLite stress test may start during ordinary pytest/PR CI.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from urllib import request as urlrequest

import pytest

from beta_engine.infrastructure.db.saved_v2_store import ENVELOPE_PREFIX, FORMAT
from scripts import giant_native_five_season_load as load

pytestmark = pytest.mark.pr_critical


def test_five_seasons_do_not_execute_without_explicit_opt_in(tmp_path, monkeypatch):
    monkeypatch.setattr(load, "run", lambda *_: pytest.fail("Real benchmark ran"))
    destination = tmp_path / "no-run"
    with pytest.raises(SystemExit) as caught:
        load.main(["--profile", "compatible", "--players", "1000",
                   "--seasons", "5", "--output-dir", str(destination)])
    assert caught.value.code == 2
    assert not destination.exists()


@pytest.mark.parametrize("extra", [
    ["--stop-after-week", "9"],
    ["--stop-after-week", "9", "--saved-v2", "--profile", "requested"],
    ["--stop-after-week", "52", "--saved-v2"],
    ["--stop-after-week", "1", "--saved-v2"],
])
def test_bounded_real_mode_fails_closed_without_supported_v2_contract(tmp_path, monkeypatch, extra):
    monkeypatch.setattr(load, "run", lambda *_: pytest.fail("Real benchmark ran"))
    target = tmp_path / "blocked"
    with pytest.raises(SystemExit) as caught:
        load.main(["--profile", "compatible", "--seasons", "5",
                   "--output-dir", str(target), *extra])
    assert caught.value.code == 2
    assert not target.exists()


def test_w9_opt_in_is_bounded_and_summary_is_not_five_season_success(tmp_path, monkeypatch):
    seen = []

    def fake_run(args, evidence):
        seen.append((args.profile, args.players, args.seasons, args.stop_after_week,
                     args.saved_v2, args.allow_five_season_run))
        evidence.total["last_completed_week"] = 9
        evidence.total["last_completed_season"] = 1
        evidence.total["save_count"] = 7
        return "stopped_after_week"

    monkeypatch.setattr(load, "run", fake_run)
    root = tmp_path / "w9"
    assert load.main(["--profile", "compatible", "--players", "1000",
                      "--seasons", "5", "--stop-after-week", "9", "--saved-v2",
                      "--output-dir", str(root)]) == 0
    assert seen == [("compatible", 1000, 5, 9, True, False)]
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "stopped_after_week"
    assert summary["last_completed_week"] == 9
    assert summary["last_completed_season"] == 1
    assert summary["saved_v2"] is True
    assert summary["seasons_completed"] == 0


def test_plan_only_is_safe_without_expensive_authorization(tmp_path, monkeypatch):
    monkeypatch.setattr(load, "run", lambda *_: pytest.fail("Real benchmark ran"))
    plan = tmp_path / "plan.json"
    assert load.main(["--profile", "compatible", "--seasons", "5",
                      "--plan-only", "--plan-json", str(plan)]) == 0
    data = json.loads(plan.read_text(encoding="utf-8"))
    assert data["simulated_seasons"] == 5
    assert data["editions"] == 300


def test_each_http_save_is_timed_without_altering_transport_timeout(tmp_path, monkeypatch):
    calls = []

    def original_urlopen(req, *args, **kwargs):
        calls.append((req.full_url, args, kwargs))
        return SimpleNamespace(status=201)

    monkeypatch.setattr(urlrequest, "urlopen", original_urlopen)
    evidence = load.Evidence(tmp_path, tmp_path / "run.sqlite", 315)
    with load.timed_http_saves(evidence):
        urlrequest.urlopen(urlrequest.Request("http://localhost:4567/health"), timeout=120)
        urlrequest.urlopen(urlrequest.Request("http://localhost:4567/preview"), timeout=120)
        urlrequest.urlopen(urlrequest.Request("http://localhost:4567/calendar-tour/save"), timeout=120)
        urlrequest.urlopen(urlrequest.Request("http://localhost:4567/prospect-source/save"), timeout=120)
    rows = [json.loads(row) for row in
            (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").splitlines()]
    saves = [item for item in rows if item["kind"] == "save"]
    assert len(saves) == evidence.total["save_count"] == 2
    assert [s["save_index"] for s in saves] == [1, 2]
    assert all(s["http_status"] == 201 and s["duration_seconds"] >= 0 for s in saves)
    assert all(s["max_rss_kib"] > 0 for s in saves)
    assert all(s["sqlite_bytes"] == s["sqlite_wal_bytes"] == s["sqlite_total_bytes"] == 0
               for s in saves)
    assert len(calls) == 4
    assert all(kwargs == {"timeout": 120} for _, _, kwargs in calls)


def test_saved_v2_history_validator_checks_real_format_and_parent_chain(tmp_path):
    db = tmp_path / "format.sqlite"
    with sqlite3.connect(db) as connection:
        connection.executescript("""
            CREATE TABLE run_saved_storage_formats (run_id TEXT, storage_format TEXT);
            CREATE TABLE branch_saved_revisions (
                run_id TEXT, revision_id TEXT, parent_revision_id TEXT, payload_json TEXT
            );
            CREATE TABLE run_branches (
                run_id TEXT, branch_id TEXT, saved_head_revision_id TEXT
            );
            CREATE TABLE saved_revision_nodes (run_id TEXT, digest TEXT, body TEXT);
        """)
        connection.execute("INSERT INTO run_saved_storage_formats VALUES (?,?)", ("run", FORMAT))
        connection.execute("INSERT INTO branch_saved_revisions VALUES (?,?,?,?)",
                           ("run", "r1", None, ENVELOPE_PREFIX + "stub"))
        connection.execute("INSERT INTO branch_saved_revisions VALUES (?,?,?,?)",
                           ("run", "r2", "r1", ENVELOPE_PREFIX + "stub"))
        connection.execute("INSERT INTO run_branches VALUES (?,?,?)", ("run", "branch", "r2"))
        connection.execute("INSERT INTO saved_revision_nodes VALUES (?,?,?)",
                           ("run", "digest", "body"))
    assert load.verify_saved_v2_sqlite_history(db, "r2") == 2
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE branch_saved_revisions "
                           "SET parent_revision_id='missing' WHERE revision_id='r2'")
    with pytest.raises(AssertionError, match="Broken Saved ancestry"):
        load.verify_saved_v2_sqlite_history(db, "r2")


def test_workflow_is_manual_w9_only():
    script = Path(".github/workflows/giant-w9-saved-v2.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in script
    assert "pull_request:" not in script and "push:" not in script
    assert "--stop-after-week 9" in script and "--saved-v2" in script
    assert "--allow-five-season-run" not in script
