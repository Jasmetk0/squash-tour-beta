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

EVENT_ID = "EVT-2000-W01-browser_cup"


def acceptance(root: Path, *, port: int, base_url: str, chromium: str) -> None:
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

                policy = request(
                    "POST", root_scope + "/tournament-group-rules/versions",
                    {"command_id": "browser-group-rules",
                     "effective_from_season_index": 0,
                     "default_match_best_of": 3}, 201,
                )
                assert policy["default_match_best_of"] == 3
                format_ = request(
                    "POST", event_scope + "/format/configure",
                    {"command_id": "browser-group-format",
                     "format_kind": "groups", "group_count": 1,
                     "group_size": 4, "seeded_slots_per_group": 0,
                     "group_seed_placements": [], "advancing_per_group": 0,
                     "knockout_crossings": []}, 201,
                )
                assert format_["format_kind"] == "groups"
                assert format_["group_configuration"]["group_size"] == 4
                topology = request(
                    "POST", event_scope + "/format/topology/generate",
                    {"command_id": "browser-group-topology",
                     "topology_seed": 137}, 201,
                )
                assert len(topology["group_matches"]) == 6
                schedule = request(
                    "POST", event_scope + "/format/group-match-schedule/generate",
                    {"command_id": "browser-group-match-days"}, 201,
                )
                assert schedule["group_count"] == 1
                assert schedule["group_size"] == 4
                assert schedule["match_day_count"] == 3
                assert len(schedule["matches"]) == 6
                assert len({m["match_id"] for m in schedule["matches"]}) == 6
                assert all(m["effective_match_format"]["format"]["best_of"] == 3
                           for m in schedule["matches"])
                print("GROUP BROWSER: real Entry, Format, Topology and Match Days committed",
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
                context.tracing.stop(path=str(artifacts / "before-restart.zip"))
                context.close()
                process.terminate()
                process.wait(timeout=20)
                process = start()
                context, page = new_page(browser)
                assert saved(revision) == expected
                assert saved(old_rev) == before
                browser_read(page, prefix="reopened-")
                assert browser_errors == [], browser_errors
                (artifacts / "group-evidence.json").write_text(json.dumps({
                    "run_id": run_id, "branch_id": branch_id,
                    "old_revision_id": old_rev, "saved_revision_id": revision,
                    "group_schedule_fingerprint": group["authority_fingerprint"],
                    "format_kind": format_["format_kind"],
                    "group_match_count": len(group["matches"]),
                    "match_day_count": group["match_day_count"],
                    "group_standings_status": "not_yet_authoritative",
                    "real_group_results_simulated": False,
                    "unchanged_after_restart": True,
                    "browser_errors": browser_errors,
                }, indent=2))
                print("REAL SAVED GROUP PRE-RESULT BROWSER ACCEPTANCE PASSED", flush=True)
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
        )
