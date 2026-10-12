"""Real Chromium -> production HTTP -> SQLite Add Selected/Save/restart acceptance.

Isolated disposable Run/World. Assert real stored revisions and Week-1 rosters;
never mock API, browser input, fingerprint validation or SQL persistence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright
from admin_first_tournament_smoke import browser_click, browser_settle


def database_snapshot(db: Path) -> dict:
    with sqlite3.connect(db) as connection:
        connection.row_factory = sqlite3.Row
        revisions = [dict(r) for r in connection.execute(
            "SELECT revision_id, sequence, payload_json, content_hash FROM "
            "branch_saved_revisions ORDER BY sequence"
        )]
        worlds = [dict(r) for r in connection.execute(
            "SELECT run_id,branch_id,fingerprint,payload_json FROM initial_world_states"
        )]
        assert len(worlds) == 1, "Test must own precisely one Run initial world"
        run_id, branch_id = worlds[0]["run_id"], worlds[0]["branch_id"]
        week_one = {}
        for table in ("player_lifecycle_week_states", "player_sporting_week_states",
                      "player_health_week_states"):
            rows = list(connection.execute(
                f"SELECT fingerprint,payload_json FROM {table} "
                "WHERE run_id=? AND branch_id=? AND week_ordinal=0",
                (run_id, branch_id)
            ))
            assert len(rows) == 1, f"Missing/duplicate Week-1 {table}"
            week_one[table] = {"fingerprint": rows[0][0],
                               "payload": json.loads(rows[0][1])}
    return {"revisions": revisions, "world": json.loads(worlds[0]["payload_json"]),
            "world_fingerprint": worlds[0]["fingerprint"], "week_one": week_one,
            "run_id": run_id, "branch_id": branch_id}


def full_database_digest(db: Path) -> str:
    """Catch ANY accidental SQL mutation, not just changed InitialWorld bytes.

    Include Saved Revision lineage, ranking, Week-1 projections and audit rows.
    The transient SQLite connection does not mutate the database.
    """
    with sqlite3.connect(db) as connection:
        content = "\n".join(connection.iterdump())
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_week_one(snapshot: dict):
    expected = {p["player_id"] for p in snapshot["world"]["players"]}
    assert len(expected) == len(snapshot["world"]["players"])
    for table, row in snapshot["week_one"].items():
        state = row["payload"]
        assert state["source_initial_world_fingerprint"] == snapshot["world_fingerprint"], table
        observed = {p["player_id"] for p in state["players"]}
        assert observed == expected, (table, len(observed), len(expected))


def acceptance(root: Path, *, port: int, base_url: str, chromium: str):
    root.mkdir(parents=True, exist_ok=True)
    if (root / "browser.sqlite").exists():
        raise ValueError("Selected append acceptance needs a new disposable database")
    artifacts = root / "artifacts"
    artifacts.mkdir()
    server_log = (root / "server.log").open("w")
    errors = []

    def start():
        process = subprocess.Popen(
            [sys.executable, "scripts/admin_first_tournament_smoke.py",
             "--serve", str(root), "--port", str(port)],
            stdout=server_log, stderr=server_log)
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Backend exited before health check")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                    if response.status == 200:
                        return process
            except OSError:
                time.sleep(0.15)
        process.terminate()
        process.wait(timeout=15)
        raise RuntimeError("Backend readiness timeout")

    def open_page(browser):
        context = browser.new_context(viewport={"width": 1440, "height": 900})
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
            f"HTTP {response.status} {response.url}") if response.status >= 500 else None)
        return context, page

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    process = start()
    context = None
    page = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chromium, headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                context, page = open_page(browser)
                page.goto(base_url + "/admin/runs/new")
                page.get_by_label("Unique Run name").fill("Selected Append Browser Acceptance")
                browser_click(page, "Create isolated Run")
                expect(page.get_by_role("heading", name="World and Calendar copies")).to_be_visible()
                page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                run_url = page.url

                # First build an ordinary, genuinely saved World and 32-player InitialWorld.
                page.get_by_label("Source kind").select_option("world")
                page.get_by_label("World source").select_option("official_fax_world")
                browser_click(page, "Preview copy")
                page.get_by_label("Confirm source copy").check()
                browser_click(page, "Confirm copy to Working Draft")
                page.get_by_label("Confirm save revision").check()
                browser_click(page, "Save copied packages")
                expect(page.get_by_text("Current Run copy: Present. Draft: clean.", exact=False)).to_be_visible()
                page.get_by_role("link", name="Generate players →").click()
                generate_url = page.url
                expect(page.get_by_role("heading", name="Generate players")).to_be_visible()
                page.get_by_label("Number of generated players").fill("32")
                page.get_by_label("Player generation seed").fill("4207")
                with page.expect_response(lambda r:
                    r.url.endswith("/world-package/preview")
                    and r.request.method == "POST" and r.status == 200) as response:
                    browser_click(page, "Preview generated players")
                original_review = response.value.json()
                assert len(original_review["state"]["players"]) == 32
                page.get_by_label("Approve InitialWorld adoption").check()
                browser_click(page, "Adopt generated players")
                page.get_by_label("Approve InitialWorld revision save").check()
                browser_click(page, "Save InitialWorld revision")
                expect(page.get_by_text("InitialWorld exists: 32 players", exact=False)).to_be_visible()
                before = database_snapshot(root / "browser.sqlite")
                validate_week_one(before)
                assert len(before["world"]["players"]) == 32
                incumbent = {p["player_id"]: p for p in before["world"]["players"]}
                assert not before["world"].get("selected_appends")
                original_revisions = [(r["revision_id"], r["payload_json"], r["content_hash"])
                                      for r in before["revisions"]]
                original_head = before["revisions"][-1]["revision_id"]

                # Generate a separate REAL 200-source cohort. No Add occurs on Preview.
                page.reload()
                browser_settle(page)
                page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                panel = page.get_by_role("region", name="Add selected generated players")
                expect(panel.get_by_role("heading", name="Add selected players to saved InitialWorld")).to_be_visible()
                panel.get_by_label("Selected append source size").fill("200")
                panel.get_by_label("Selected append source seed").fill("45601")
                with page.expect_response(lambda r:
                    r.url.endswith("/world-package/preview")
                    and r.request.method == "POST" and r.status == 200) as response:
                    browser_click(page, "Preview source players (read-only)")
                source = response.value.json()
                assert len(source["state"]["players"]) == 200
                source_ids = {p["player_id"] for p in source["state"]["players"]}
                collisions = sorted(set(incumbent) & source_ids)
                novel = sorted(source_ids - set(incumbent))
                assert collisions and len(novel) >= 2, (
                    "Country-serial generation should expose both collisions and new identities")
                assert database_snapshot(root / "browser.sqlite")["world_fingerprint"] == before["world_fingerprint"]
                assert page.get_by_text("Candidate source: 200 players.", exact=False).is_visible()

                # A visible search-based action selection must reject existing IDs
                # locally without sending an append proposal to the server.
                search = panel.get_by_label("Search generated player preview")
                search.fill(collisions[0])
                existing_box = panel.get_by_role("checkbox", name="Select for bulk action " + collisions[0])
                expect(existing_box).to_be_visible()
                existing_box.check()
                expect(panel.get_by_role("button", name="Verify selected addition on server (no write)")).to_be_disabled()
                expect(panel.get_by_text("These IDs already exist", exact=False)).to_be_visible()
                existing_box.uncheck()

                # Selection survives a search/filter change and does NOT become Keep.
                selected = novel[:2]
                for player_id in selected:
                    search.fill(player_id)
                    box = panel.get_by_role("checkbox", name="Select for bulk action " + player_id)
                    expect(box).to_be_visible()
                    box.check()
                search.fill("")
                expect(panel.get_by_text("Selected: 2. Conflicting IDs: 0.")).to_be_visible()
                with page.expect_response(lambda r:
                    r.url.endswith("/selected-append/preview") and
                    r.request.method == "POST" and r.status == 200) as response:
                    browser_click(page, "Verify selected addition on server (no write)")
                reviewed = response.value.json()
                assert reviewed["preview_only"] is True
                assert reviewed["added_count"] == 2
                assert len(reviewed["state"]["players"]) == 34
                assert set(reviewed["state"]["selected_appends"][-1]["selected_player_ids"]) == set(selected)
                assert all(p == incumbent[p["player_id"]] for p in reviewed["state"]["players"]
                           if p["player_id"] in incumbent), "Append preview changed an old player"
                assert database_snapshot(root / "browser.sqlite")["world_fingerprint"] == before["world_fingerprint"]
                assert len(database_snapshot(root / "browser.sqlite")["revisions"]) == len(before["revisions"])

                # Explicit approved write to the live InitialWorld but NOT a Saved Revision.
                panel.get_by_label("Approve selected InitialWorld append").check()
                with page.expect_response(lambda r:
                    r.url.endswith("/selected-append") and
                    r.request.method == "POST" and r.status == 201) as response:
                    browser_click(page, "Commit selected players (Save separately)")
                committed = response.value.json()
                assert len(committed["players"]) == 34
                assert committed["selected_appends"][-1]["selected_player_ids"] == selected
                live = database_snapshot(root / "browser.sqlite")
                validate_week_one(live)
                assert len(live["world"]["players"]) == 34
                assert live["world_fingerprint"] == reviewed["fingerprint"]
                assert [(r["revision_id"], r["payload_json"], r["content_hash"])
                        for r in live["revisions"]] == original_revisions

                # New branch HEAD is created ONLY by existing manual Save.
                expect(page.get_by_role("button", name="Review existing InitialWorld save")).to_be_visible()
                browser_click(page, "Review existing InitialWorld save")
                page.get_by_label("Approve InitialWorld revision save").check()
                browser_click(page, "Save InitialWorld revision")
                saved = database_snapshot(root / "browser.sqlite")
                validate_week_one(saved)
                assert len(saved["revisions"]) == len(before["revisions"]) + 1
                assert saved["revisions"][-1]["revision_id"] != original_head
                assert [(r["revision_id"], r["payload_json"], r["content_hash"])
                        for r in saved["revisions"][:-1]] == original_revisions
                newest_state = json.loads(saved["revisions"][-1]["payload_json"])["content"]["initial_world"]["state"]
                assert len(newest_state["players"]) == 34
                assert newest_state["selected_appends"][-1]["selected_player_ids"] == selected
                assert saved["world"] == live["world"]
                page.screenshot(path=str(artifacts / "selected-add-saved.png"), full_page=True)
                context.tracing.stop(path=str(artifacts / "before-restart.zip"))
                context.close()
                context = None

                process.terminate()
                process.wait(timeout=25)
                process = start()
                context, page = open_page(browser)
                page.goto(generate_url)
                browser_settle(page)
                page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                expect(page.get_by_text("InitialWorld exists: 34 players", exact=False)).to_be_visible()
                after = database_snapshot(root / "browser.sqlite")
                validate_week_one(after)
                assert after["revisions"] == saved["revisions"]
                assert after["world"] == saved["world"]
                assert after["week_one"] == saved["week_one"]

                # POST-RANKING SAFETY — publish the INITIAL official ranking
                # through real Admin UI, explicitly save the published head.
                # Selected Add must now fail before any existing SQL row changes.
                page.goto(run_url)
                browser_settle(page)
                page.get_by_label("Initial ranking audit reason").fill(
                    "F79-09 post-ranking Add Selected must be denied"
                )
                browser_click(page, "Preview initial ranking")
                page.get_by_label("Approve initial ranking preparation").check()
                browser_click(page, "Confirm initial ranking")
                page.get_by_label("Approve initial ranking save").check()
                browser_click(page, "Save initial ranking revision")
                browser_click(page, "Review initial publication")
                page.get_by_label("Approve initial publication").check()
                browser_click(page, "Publish initial ranking")
                browser_click(page, "Review unsaved published ranking state")
                page.get_by_label("Approve published ranking revision save").check()
                browser_click(page, "Save published ranking revision")
                expect(page.get_by_text(
                    "Viewer readback verified:", exact=False
                )).to_be_visible()
                with sqlite3.connect(root / "browser.sqlite") as db:
                    published = db.execute(
                        "SELECT COUNT(*) FROM published_official_rankings "
                        "WHERE run_id=? AND branch_id=?",
                        (after["run_id"], after["branch_id"]),
                    ).fetchone()[0]
                    assert published > 0, "A real published Official Ranking is required"

                ranked = database_snapshot(root / "browser.sqlite")
                validate_week_one(ranked)
                before_denied_digest = full_database_digest(root / "browser.sqlite")
                assert len(ranked["world"]["players"]) == 34

                # The UI can still inspect a new read-only cohort, but it MUST
                # not persist a third additional player once ranking exists.
                page.goto(generate_url)
                browser_settle(page)
                page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                expect(page.get_by_text(
                    "InitialWorld exists: 34 players", exact=False
                )).to_be_visible()
                panel = page.get_by_role(
                    "region", name="Add selected generated players"
                )
                panel.get_by_label("Selected append source size").fill("200")
                panel.get_by_label("Selected append source seed").fill("45601")
                with page.expect_response(lambda r:
                    r.url.endswith("/world-package/preview")
                    and r.request.method == "POST" and r.status == 200) as resp:
                    browser_click(page, "Preview source players (read-only)")
                assert len(resp.value.json()["state"]["players"]) == 200
                assert full_database_digest(root / "browser.sqlite") == before_denied_digest

                third = next(pid for pid in novel if pid not in selected)
                panel.get_by_label("Search generated player preview").fill(third)
                panel.get_by_role(
                    "checkbox", name="Select for bulk action " + third
                ).check()
                expect(panel.get_by_text(
                    "Selected: 1. Conflicting IDs: 0."
                )).to_be_visible()
                # A source cohort is still inspectable, but Add Selected itself
                # must now fail during read-only preflight, BEFORE approval.
                with page.expect_response(lambda r:
                    r.url.endswith("/selected-append/preview") and
                    r.request.method == "POST" and r.status == 409) as resp:
                    browser_click(page, "Verify selected addition on server (no write)")
                denied = resp.value.json()
                assert denied["detail"]["code"] == "selected_initial_world_append_preview_conflict"
                assert "ranking or sporting activity" in denied["detail"]["message"]
                expect(panel.get_by_text(
                    "Selected append preview failed:", exact=False
                )).to_be_visible()
                expect(panel.get_by_label("Approve selected InitialWorld append")).to_have_count(0)
                expect(panel.get_by_role(
                    "button", name="Commit selected players (Save separately)"
                )).to_have_count(0)
                assert full_database_digest(root / "browser.sqlite") == before_denied_digest, (
                    "409 after published ranking mutated persisted SQL history"
                )
                assert database_snapshot(root / "browser.sqlite") == ranked, (
                    "409 after published ranking changed original players / Week-1"
                )
                page.screenshot(
                    path=str(artifacts / "post-ranking-append-denied.png"),
                    full_page=True,
                )

                assert not errors, errors
                (artifacts / "evidence.json").write_text(json.dumps({
                    "initial_count": 32, "selected_added_count": 2, "saved_count": 34,
                    "historical_head_unchanged": True, "new_saved_revision": True,
                    "all_three_week_one_rosters_match": True,
                    "source_review_did_not_mutate": True,
                    "append_review_did_not_mutate": True,
                    "append_commit_staged_before_save": True,
                    "collision_blocked_before_request": True,
                    "saved_after_backend_restart": True,
                    "saved_revision_history_unchanged": True,
                    "published_ranking_exists": published > 0,
                    "post_ranking_preflight_conflict_409": True,
                    "post_ranking_source_and_preview_read_only": True,
                    "post_ranking_sql_digest_unchanged": True,
                    "selected_player_ids": selected,
                    "run_url": run_url, "browser_errors": errors
                }, indent=2))
                print("SELECTED-APPEND BROWSER/SQLITE RESTART AND POST-RANKING DENIAL PASSED", flush=True)
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
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    acceptance(args.acceptance.resolve(), port=args.port,
               base_url=args.base_url, chromium=args.chromium)
