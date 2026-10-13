"""Real Run group-format Save -> immutable Edition -> Chromium -> SQLite restart.

Uses the production FastAPI commands for Group Rules, frozen Entry Field,
Format, Topology and Group Match Schedule. No mocked API or generated sport
results. A *completed* group stage remains a distinct unverified workflow:
this acceptance explicitly asserts that no standings are fabricated before
any real group matches have been simulated.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

import uvicorn
from playwright.sync_api import expect, sync_playwright

from admin_first_tournament_smoke import (
    browser_click, browser_settle, create_smoke_app, setup_run,
)
from saved_completed_group_browser_checks import play_group_and_save

EVENT_ID = "EVT-2000-W01-browser_cup"


def acceptance(
    root: Path, *, port: int, base_url: str, chromium: str,
    complete_groups: bool = False,
) -> None:
    if (root / "browser.sqlite").exists():
        raise ValueError("Saved group browser acceptance requires a fresh SQLite database")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", port))
    root.mkdir(parents=True, exist_ok=True)
    artifacts = root / "artifacts"
    artifacts.mkdir()
    server_log = (root / "server.log").open("w")
    browser_errors: list[str] = []

    def start():
        process = subprocess.Popen(
            [sys.executable, __file__, "--serve", str(root), "--port", str(port)],
            stdout=server_log, stderr=server_log,
        )
        for _ in range(180):
            if process.poll() is not None:
                raise RuntimeError("Group acceptance backend stopped; inspect server.log")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                    if response.status == 200:
                        return process
            except OSError:
                time.sleep(.1)
        process.terminate()
        process.wait(timeout=20)
        raise RuntimeError("Group acceptance backend did not start")

    def new_page(browser):
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.set_default_timeout(30000)
        page.smoke_pending_requests = set()
        page.smoke_dialogs = []
        page.on("request", lambda request: page.smoke_pending_requests.add(request))
        page.on("requestfinished", lambda request: page.smoke_pending_requests.discard(request))
        page.on("requestfailed", lambda request: page.smoke_pending_requests.discard(request))

        def accept_dialog(dialog):
            page.smoke_dialogs.append(dialog.message)
            dialog.accept()
        page.on("dialog", accept_dialog)
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        page.on("response", lambda response: (
            browser_errors.append(f"HTTP {response.status}: {response.url}")
            if response.status >= 500 else None
        ))
        return context, page

    process = start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chromium, headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context, page = new_page(browser)
            try:
                run_url = setup_run(page, base_url, artifacts)
                url_root, run_id = run_url.split("/admin/runs/", 1)
                api = f"http://127.0.0.1:{port}"

                def request(method, path, body=None, status=200):
                    kwargs = {"timeout": 40000}
                    if body is not None:
                        kwargs["data"] = body
                    response = page.request.fetch(
                        api + path, method=method, **kwargs,
                    )
                    assert response.status == status, (
                        method, path, response.status, response.text()[:1600]
                    )
                    return response.json() if status in (200, 201) else None

                branches = request(
                    "GET", "/run-branches?run_id=" + quote(run_id, safe=""),
                )["run_branches"]
                assert len(branches) == 1, branches
                branch_id = branches[0]["branch_id"]
                root_scope = ("/admin/runs/" + quote(run_id, safe="") +
                              "/branches/" + quote(branch_id, safe=""))
                event_scope = root_scope + "/tournaments/" + quote(EVENT_ID, safe="")
                run_scope = ("/run-containers/" + quote(run_id, safe="") +
                             "/branches/" + quote(branch_id, safe=""))
                old_rev = branches[0]["saved_head_revision_id"]
                assert old_rev

                # The initial generated field is reviewed by the real browser.
                browser_click(page, "Preview actual Entry Field")
                page.get_by_label("Approve reviewed Entry Field", exact=True).check()
                browser_click(page, "Commit reviewed Entry Field")
                prepared_event_url = page.url
                assert "/calendar/" in prepared_event_url


                # This is the missing real Admin UI journey: no direct writes
                # for Group Rules, Format, Topology or Group Match Schedule.
                # Default knockout navigation remains available until Admin
                # explicitly opts into pure round-robin groups.
                browser_click(page, "Choose pure round-robin groups")
                group_setup = page.get_by_label("Group Format setup")
                expect(group_setup).to_be_visible()
                expect(group_setup).to_contain_text("Frozen direct entrants: 4")
                expect(group_setup.get_by_role(
                    "button", name="Configure pure-groups Format"
                )).to_be_disabled()

                group_setup.get_by_label("Season group-match format").select_option("3")
                group_setup.get_by_label(
                    "Confirm immutable season Group Rules"
                ).check()
                browser_click(page, "Adopt season Group Rules")
                expect(group_setup).to_contain_text("Frozen season group rules: BO3")
                policy = request(
                    "GET", root_scope + "/tournament-group-rules?target_season_index=0",
                )
                assert policy["effective"]["default_match_best_of"] == 3
                assert policy["run_id"] == run_id
                assert policy["branch_id"] == branch_id

                # Intentional confirmation; no sneaky API setup or fixture player IDs.
                expect(group_setup.get_by_label("Group count")).to_have_value("1")
                expect(group_setup.get_by_label("Players per group")).to_have_value("4")
                group_setup.get_by_label("Confirm immutable pure-groups Format").check()
                browser_click(page, "Configure pure-groups Format")
                expect(page.get_by_role(
                    "button", name="Generate group Topology"
                )).to_be_visible()
                preparation = request("GET", event_scope + "/preparation")
                assert preparation["format_kind"] == "groups"
                assert preparation["next_required_action"] == "generate_tournament_topology"

                expect(page.get_by_label("Group Topology seed")).to_have_value("137")
                page.get_by_label("Confirm immutable group Topology").check()
                browser_click(page, "Generate group Topology")
                expect(page.get_by_role(
                    "button", name="Generate group Match Schedule"
                )).to_be_visible()
                preparation = request("GET", event_scope + "/preparation")
                assert preparation["next_required_action"] == "prepare_group_match_schedule"
                browser_click(page, "Generate group Match Schedule")

                preparation = request("GET", event_scope + "/preparation")
                assert preparation["phase"] == "group_match_execution_ready"
                assert preparation["group_match_count"] == 6
                assert preparation["group_match_day_count"] == 3
                schedule = request("GET", event_scope + "/format/group-match-schedule")
                assert schedule["group_count"] == 1
                assert schedule["group_size"] == 4
                assert schedule["match_day_count"] == 3
                assert len(schedule["matches"]) == 6
                assert len({m["match_id"] for m in schedule["matches"]}) == 6
                assert all(m["effective_match_format"]["format"]["best_of"] == 3
                           for m in schedule["matches"])
                page.screenshot(
                    path=str(artifacts / "02-real-group-format-browser.png"),
                    full_page=True,
                )
                print("GROUP BROWSER: real Admin UI committed BO3 Rules, pure Format, Topology and six Match Days",
                      flush=True)

                def saved(revision):
                    return request(
                        "GET", root_scope + "/tour/editions/" +
                        quote(EVENT_ID, safe="") +
                        "?revision_id=" + quote(revision, safe="") + "&season_index=0",
                    )

                before = saved(old_rev)
                assert before["saved_revision_id"] == old_rev
                assert before["group_schedule"] is None
                assert before["group_standings"] is None

                # Group Format/Topology/Match Days are *Simulation Slot*
                # authorities, not changes to Viewer-Branch selection. Use the
                # existing fingerprint-locked authoritative Simulation Save,
                # never fabricate a dirty Working Draft to force a generic Save.
                simulation_scope = root_scope + "/authoritative-simulation"
                preview = request("GET", simulation_scope + "/save/preview")
                assert preview["can_save"], preview
                assert preview["has_unsaved_changes"] is True
                assert preview["saved_head_revision_id"] == old_rev
                fingerprint = preview["simulation_fingerprint"]
                assert isinstance(fingerprint, str) and len(fingerprint) == 64
                saved_result = request(
                    "POST", simulation_scope + "/save",
                    {"expected_draft_version": preview["draft_version"],
                     "expected_simulation_fingerprint": fingerprint}, 201,
                )
                revision = saved_result["saved_revision"]["revision_id"]
                assert revision != old_rev

                expected = saved(revision)
                assert expected["run_id"] == run_id
                assert expected["branch_id"] == expected["revision_branch_id"] == branch_id
                assert expected["saved_revision_id"] == revision
                assert expected["season_index"] == 0
                group = expected["group_schedule"]
                assert group is not None and group["source"] == (
                    "saved_tournament_group_match_schedule_authority.v1"
                )
                assert group["authority_fingerprint"] == schedule["authority_fingerprint"]
                assert len(group["matches"]) == 6
                assert group["match_day_count"] == 3
                assert group["group_size"] == 4
                assert expected["group_standings"] is None, (
                    "A completed group table must not be invented before any real results"
                )
                assert expected["published_result"] is None
                assert saved(old_rev) == before, "Live group commands rewrote Saved ancestor"
                negative = root_scope + "/tour/editions/" + quote(EVENT_ID, safe="")
                request("GET", negative + "?revision_id=foreign&season_index=0",
                        status=404)
                request("GET", negative + "?revision_id=" + quote(revision, safe="") +
                        "&season_index=1", status=404)

                def browser_read(page, prefix=""):
                    query = (f"?branch={quote(branch_id, safe='')}"
                             f"&revision={quote(revision, safe='')}&season=0")
                    page.goto(run_url + "/tour/calendar/" +
                              quote(EVENT_ID, safe="") + query)
                    page.get_by_role(
                        "combobox", name="Language / Jazyk",
                    ).select_option("en")
                    expect(page.get_by_role(
                        "heading", name="Browser Acceptance Cup",
                    )).to_be_visible()
                    page.get_by_role("button", name="Schedule & matches").click()
                    group_table = page.get_by_role(
                        "table", name="Saved group matches",
                    )
                    expect(group_table).to_be_visible()
                    expect(group_table.locator("tbody tr")).to_have_count(6)
                    expect(page.get_by_text(
                        "Authentic group Match Day schedule",
                    )).to_be_visible()
                    expect(group_table.get_by_text("BO3")).to_have_count(6)
                    expect(group_table.get_by_text(
                        "Not canonically published",
                    )).to_have_count(6)
                    page.get_by_role("button", name="Results").click()
                    assert page.locator(
                        'section[aria-label="Saved group standings"]'
                    ).count() == 0
                    expect(page.get_by_text(
                        "not published in this revision", exact=False,
                    )).to_be_visible()
                    page.screenshot(
                        path=str(artifacts / f"{prefix}group-edition.png"),
                        full_page=True,
                    )
                    assert "revision=" + quote(revision, safe="") in page.url

                browser_read(page)
                completed = None

                def final_browser_read(page, final_revision, prefix=""):
                    query = (f"?branch={quote(branch_id, safe='')}"
                             f"&revision={quote(final_revision, safe='')}&season=0")
                    page.goto(run_url + "/tour/calendar/" +
                              quote(EVENT_ID, safe="") + query)
                    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                    expect(page.get_by_role("heading", name="Browser Acceptance Cup")).to_be_visible()
                    page.get_by_role("button", name="Results").click()
                    section = page.get_by_label("Saved group standings")
                    expect(section).to_be_visible()
                    table = page.get_by_role("table", name="Saved group 1 standings")
                    expect(table.locator("tbody tr")).to_have_count(4)
                    expect(section.get_by_text(
                        "Saved final tables", exact=False,
                    )).to_be_visible()
                    assert "revision=" + quote(final_revision, safe="") in page.url
                    page.screenshot(path=str(artifacts / f"{prefix}completed-group-edition.png"),
                                    full_page=True)

                if complete_groups:
                    print("GROUP BROWSER: playing six real matches; intermediate Save/restart before final standings",
                          flush=True)

                    def restart_intermediate_backend():
                        # Kill the actual service and start a clean process
                        # against its existing file-backed SQLite database.
                        nonlocal process
                        process.terminate()
                        process.wait(timeout=20)
                        process = start()

                    completed = play_group_and_save(
                        request, run_id=run_id, branch_id=branch_id,
                        event_id=EVENT_ID, root_scope=root_scope,
                        event_scope=event_scope, old_revision=revision,
                        original_match_ids={m["match_id"] for m in schedule["matches"]},
                        page=page, run_url=run_url,
                        event_url=prepared_event_url, artifacts=artifacts,
                        restart_backend=restart_intermediate_backend,
                    )
                    assert completed["intermediate_backend_restart"] is True
                    assert saved(completed["intermediate_revision"]) == (
                        completed["intermediate_edition"]
                    ), "Intermediate saved revision mutated after final generation"
                    assert completed["intermediate_edition"]["group_standings"] is None
                    assert saved(old_rev) == before
                    assert saved(revision) == expected, (
                        "Simulating six real matches rewrote pre-result Saved Revision"
                    )
                    # Reopen the real Run-owned tournament in Present mode.
                    # Read its immutable final groups through the new Admin panel,
                    # not a synthetic result, a mock API or today's ranking.
                    page.goto(prepared_event_url)
                    table = page.get_by_role(
                        "table", name="Canonical group 1 standings"
                    )
                    expect(table).to_be_visible()
                    expect(table.locator("tbody tr")).to_have_count(4)
                    expect(page.get_by_label(
                        "Canonical completed group standings"
                    )).to_contain_text("Frozen authority:")
                    assert page.get_by_role(
                        "button", name="Generate canonical group standings"
                    ).count() == 0, "Frozen authority must not offer a duplicate generation"
                    page.screenshot(
                        path=str(artifacts / "04-admin-frozen-group-table.png"),
                        full_page=True,
                    )
                    final_browser_read(page, completed["revision"])
                    print("GROUP BROWSER: six real matches + intermediate Save/restart + final standings saved",
                          flush=True)

                context.tracing.stop(path=str(artifacts / "before-restart.zip"))
                context.close()
                process.terminate()
                process.wait(timeout=20)
                process = start()
                context, page = new_page(browser)
                assert saved(revision) == expected
                assert saved(old_rev) == before
                browser_read(page, prefix="reopened-")
                if completed is not None:
                    assert saved(completed["revision"]) == completed["edition"], (
                        "Final saved group standings changed after SQLite restart"
                    )
                    assert saved(completed["intermediate_revision"]) == (
                        completed["intermediate_edition"]
                    ), "Intermediate saved group history changed after final restart"
                    final_browser_read(page, completed["revision"], prefix="reopened-")
                assert browser_errors == [], browser_errors
                (artifacts / "group-evidence.json").write_text(json.dumps({
                    "run_id": run_id, "branch_id": branch_id,
                    "old_revision_id": old_rev, "saved_revision_id": revision,
                    "group_schedule_fingerprint": group["authority_fingerprint"],
                    "format_kind": preparation["format_kind"],
                    "group_match_count": len(group["matches"]),
                    "match_day_count": group["match_day_count"],
                    "group_standings_status": (
                        "frozen_from_six_real_matches" if completed else "not_yet_authoritative"
                    ),
                    "real_group_results_simulated": completed is not None,
                    "played_group_match_count": (
                        completed["matches_simulated"] if completed else 0
                    ),
                    "group_match_day_execution": (
                        "three_reviewed_browser_UI_clicks" if completed else "not_executed"
                    ),
                    "final_group_table_generation": (
                        "explicit_Admin_UI_confirmation_and_click" if completed else "not_executed"
                    ),
                    "completed_revision_id": (
                        completed["revision"] if completed else None
                    ),
                    "intermediate_pre_standings_revision_id": (
                        completed["intermediate_revision"] if completed else None
                    ),
                    "intermediate_save_restarted_before_standings": (
                        completed["intermediate_backend_restart"] if completed else False
                    ),
                    "admin_tie_decisions": (
                        completed["group_tie_decision_count"] if completed else 0
                    ),
                    "unchanged_after_restart": True,
                    "browser_errors": browser_errors,
                }, indent=2))
                print(
                    "REAL SAVED GROUP COMPLETED BROWSER ACCEPTANCE PASSED"
                    if completed else
                    "REAL SAVED GROUP PRE-RESULT BROWSER ACCEPTANCE PASSED",
                    flush=True,
                )
            except Exception:
                page.screenshot(path=str(artifacts / "failure.png"), full_page=True)
                (artifacts / "failure.txt").write_text(page.locator("body").inner_text())
                raise
            finally:
                context.tracing.stop(path=str(artifacts / "after-restart.zip"))
                context.close()
                browser.close()
    finally:
        process.terminate()
        process.wait(timeout=20)
        server_log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--serve", type=Path)
    mode.add_argument("--acceptance", type=Path)
    parser.add_argument("--port", type=int, default=8014)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    parser.add_argument("--complete-groups", action="store_true",
                        help="Actually simulate all six group matches, freeze standings, Save, replay after restart")
    args = parser.parse_args()
    if args.serve:
        uvicorn.run(
            create_smoke_app(args.serve.resolve()),
            host="127.0.0.1", port=args.port, log_level="warning",
        )
    else:
        acceptance(
            args.acceptance.resolve(), port=args.port,
            base_url=args.base_url, chromium=args.chromium,
            complete_groups=args.complete_groups,
        )
