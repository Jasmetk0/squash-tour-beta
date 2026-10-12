"""Production Chromium + SQLite initial ranking -> saved Week 2 -> restart integrity.

This complements the existing three-match browser acceptance with an independently
scoped, byte-exact database history and week-projection continuity audit.
"""
from __future__ import annotations

import argparse
import json
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

from admin_first_tournament_smoke import (
    browser_settle, finish_tournament, setup_run, verify_viewer,
)


def inspect_sqlite(db_path: Path) -> dict:
    """Read complete persisted evidence, including raw revision and ranking bytes."""
    with sqlite3.connect(db_path) as db:
        db.row_factory = sqlite3.Row
        runs = [dict(row) for row in db.execute(
            "SELECT run_id, branch_id, fingerprint, payload_json FROM initial_world_states"
        )]
        assert len(runs) == 1, "Acceptance must own exactly one isolated InitialWorld"
        run_id, branch_id = runs[0]["run_id"], runs[0]["branch_id"]
        scope = (run_id, branch_id)
        revisions = [dict(row) for row in db.execute(
            "SELECT revision_id, sequence, parent_revision_id, content_hash, "
            "payload_json FROM branch_saved_revisions "
            "WHERE run_id=? AND branch_id=? ORDER BY sequence", scope,
        )]
        published = {
            row["week_ordinal"]: dict(row) for row in db.execute(
                "SELECT week_ordinal, snapshot_fingerprint, payload_json "
                "FROM published_official_rankings WHERE run_id=? AND branch_id=? "
                "ORDER BY week_ordinal", scope,
            )
        }
        candidates = {
            row["week_ordinal"]: dict(row) for row in db.execute(
                "SELECT week_ordinal, fingerprint, payload_json "
                "FROM official_ranking_candidates WHERE run_id=? AND branch_id=? "
                "ORDER BY week_ordinal", scope,
            )
        }
        clocks = [dict(row) for row in db.execute(
            "SELECT current_ordinal, ranking_fingerprint "
            "FROM authoritative_world_states WHERE run_id=? AND branch_id=?", scope,
        )]
        projected = {}
        for table in ("player_lifecycle_week_states", "player_sporting_week_states",
                      "player_health_week_states"):
            projected[table] = {}
            for row in db.execute(
                f"SELECT week_ordinal, fingerprint, payload_json FROM {table} "
                "WHERE run_id=? AND branch_id=? ORDER BY week_ordinal", scope,
            ):
                projected[table][row["week_ordinal"]] = {
                    "fingerprint": row["fingerprint"],
                    "raw": row["payload_json"],
                    "state": json.loads(row["payload_json"]),
                }
    return {
        "run_id": run_id, "branch_id": branch_id, "revisions": revisions,
        "initial_world_fingerprint": runs[0]["fingerprint"],
        "initial_world_raw": runs[0]["payload_json"],
        "players": json.loads(runs[0]["payload_json"])["players"],
        "published": published, "candidates": candidates, "clock": clocks,
        "projections": projected,
    }


def player_ids(records):
    ids = [item["player_id"] for item in records]
    assert ids == sorted(set(ids)), "Expected canonical ordered unique player IDs"
    return set(ids)


def verify_transition(before: dict, after: dict) -> dict:
    """Fail closed if Saved ancestors or Week-1 public ranking changed in transition."""
    assert before["run_id"] == after["run_id"]
    assert before["branch_id"] == after["branch_id"]
    assert before["initial_world_fingerprint"] == after["initial_world_fingerprint"]
    assert before["initial_world_raw"] == after["initial_world_raw"]
    original_ids = player_ids(before["players"])
    assert len(original_ids) == 64, "Expected 64 actual first-cohort profiles"
    assert player_ids(after["players"]) == original_ids

    assert before["revisions"], "Initial world and Week-1 rank must be Saved"
    assert after["revisions"][:len(before["revisions"])] == before["revisions"], (
        "Transition rewrote an immutable ancestor Saved Revision"
    )
    assert len(after["revisions"]) > len(before["revisions"]), (
        "Week-2 progression must create a NEW Saved Revision"
    )
    for prev, next_item in zip(after["revisions"], after["revisions"][1:]):
        assert next_item["parent_revision_id"] == prev["revision_id"], (
            "Saved Revision chain lost direct ancestry"
        )
    assert before["published"].get(0), "Published opening Week-1 ranking is required"
    assert after["published"].get(0) == before["published"][0], (
        "Week-2 progress edited Week-1 published ranking"
    )
    assert before["candidates"].get(0), "Opening Week-1 ranking candidate is required"
    assert after["candidates"].get(0) == before["candidates"][0], (
        "Week-2 progress edited initial ranking candidate"
    )
    assert after["published"].get(1), "Week-2 published ranking is required"
    assert len(after["clock"]) == 1 and after["clock"][0]["current_ordinal"] == 1

    roster_sizes = {}
    for table, weeks in after["projections"].items():
        assert 0 in weeks and 1 in weeks, (table, "missing Week 1 or 2")
        week_one, week_two = weeks[0], weeks[1]
        assert week_one["state"]["week"]["season_index"] == 0
        assert week_one["state"]["week"]["week"] == 1
        assert week_two["state"]["week"]["season_index"] == 0
        assert week_two["state"]["week"]["week"] == 2
        assert week_one["state"]["source_initial_world_fingerprint"] == before["initial_world_fingerprint"]
        assert week_two["state"]["source_initial_world_fingerprint"] == before["initial_world_fingerprint"]
        old_ids = player_ids(week_one["state"]["players"])
        new_ids = player_ids(week_two["state"]["players"])
        assert old_ids <= original_ids and new_ids <= original_ids, (
            table, "invented player identity"
        )
        assert new_ids == old_ids, (table, "unexpected player identity loss")
        assert week_two["state"]["predecessor_fingerprint"], (
            table, "Week-2 projection has no predecessor evidence"
        )
        roster_sizes[table] = len(new_ids)
    assert roster_sizes["player_lifecycle_week_states"] == 64
    assert roster_sizes["player_health_week_states"] == 64
    # Sporting can legitimately be a subset of lifecycle, not a fabricated
    # 64-player canonical projection when the domain says otherwise.
    assert 0 < roster_sizes["player_sporting_week_states"] <= 64
    return {
        "initial_players": len(original_ids),
        "week2_saved_revision_count": len(after["revisions"]),
        "preserved_initial_saved_revision_count": len(before["revisions"]),
        "initial_ranking_unchanged": True,
        "week2_ranking_published": True,
        "week2_clock_ordinal": after["clock"][0]["current_ordinal"],
        "week2_roster_sizes": roster_sizes,
    }


def acceptance(root: Path, *, port: int, base_url: str, chromium: str):
    if (root / "browser.sqlite").exists():
        raise ValueError("Week-2 integrity acceptance requires fresh disposable SQLite")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    root.mkdir(parents=True, exist_ok=True)
    artifacts = root / "artifacts"
    artifacts.mkdir()
    server_log = (root / "server.log").open("w")
    errors = []

    def start():
        process = subprocess.Popen(
            [sys.executable, "scripts/admin_first_tournament_smoke.py",
             "--serve", str(root), "--port", str(port)],
            stdout=server_log, stderr=server_log,
        )
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Isolated production backend failed to start")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                    if response.status == 200:
                        return process
            except OSError:
                time.sleep(0.15)
        process.terminate()
        process.wait(timeout=10)
        raise RuntimeError("Production backend health timeout")

    def open_page(browser):
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.set_default_timeout(120000)
        page.smoke_pending_requests = set()
        page.on("request", lambda req: page.smoke_pending_requests.add(req))
        page.on("requestfinished", lambda req: page.smoke_pending_requests.discard(req))
        page.on("requestfailed", lambda req: page.smoke_pending_requests.discard(req))
        page.on("dialog", lambda dialog: dialog.accept())
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda response: errors.append(
            f"HTTP {response.status}: {response.url}"
        ) if response.status >= 500 else None)
        return context, page

    process = start()
    context = None
    page = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chromium, headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                context, page = open_page(browser)
                run_url = setup_run(page, base_url, artifacts)
                before = inspect_sqlite(root / "browser.sqlite")
                assert len(before["published"]) == 1 and 0 in before["published"]
                assert len(before["players"]) == 64
                match_options = finish_tournament(page, artifacts)
                after = inspect_sqlite(root / "browser.sqlite")
                evidence = verify_transition(before, after)
                viewer_rows = verify_viewer(page, run_url, artifacts)
                page.screenshot(
                    path=str(artifacts / "week2-before-restart.png"), full_page=True,
                )
                context.tracing.stop(path=str(artifacts / "before-restart.zip"))
                context.close()
                context = None
                process.terminate()
                process.wait(timeout=25)
                process = start()
                context, page = open_page(browser)
                reopened_rows = verify_viewer(page, run_url, artifacts, "reopened-")
                assert reopened_rows == viewer_rows, "Week-2 ranking Viewer changed on restart"
                reopened = inspect_sqlite(root / "browser.sqlite")
                assert reopened == after, "SQLite ranking and player history changed after restart"
                verify_transition(before, reopened)
                assert not errors, errors
                (artifacts / "evidence.json").write_text(json.dumps({
                    **evidence, "real_matches": match_options,
                    "published_rankings": sorted(reopened["published"]),
                    "same_sqlite_bytes_after_restart": True,
                    "week2_viewer_ranking_same_after_restart": True,
                    "browser_errors": errors,
                }, indent=2))
                print("WEEK2 RANKING + PLAYERS BROWSER/SQLITE RESTART INTEGRITY PASSED", flush=True)
            except Exception:
                if page is not None:
                    page.screenshot(path=str(artifacts / "failure.png"), full_page=True)
                    (artifacts / "failure.txt").write_text(page.locator("body").inner_text())
                raise
            finally:
                if context is not None:
                    context.tracing.stop(path=str(artifacts / "after-restart.zip"))
                    context.close()
                browser.close()
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=25)
        server_log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8022)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    acceptance(args.acceptance.resolve(), port=args.port,
               base_url=args.base_url, chromium=args.chromium)
