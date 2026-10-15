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
from real_hybrid_progression_browser_checks import play_and_freeze_hybrid
from real_hybrid_first_ranking_week_browser_checks import publish_first_hybrid_official_week
from real_group_cyclic_tie_browser_checks import (
    exercise_real_cyclic_browser, install_real_match_engine_cyclic_fixture,
)

EVENT_ID = "EVT-2000-W01-browser_cup"


def acceptance(
    root: Path, *, port: int, base_url: str, chromium: str,
    complete_groups: bool = False,
    reconstruct_one_group_match: bool = False,
    cyclic_tie_browser: bool = False,
    hybrid_preparation: bool = False,
    hybrid_progression: bool = False,
    hybrid_multiround: bool = False,
    hybrid_worker_transition: bool = False,
    hybrid_second_week: bool = False,
    hybrid_same_parent_restart: bool = False,
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
            [sys.executable, __file__, "--serve", str(root), "--port", str(port)]
            + (["--cyclic-tie-fixture"] if cyclic_tie_browser else []),
            stdout=server_log, stderr=server_log,
        )
        # Real 6-match MatchEngine tie input search can take longer than the
        # ordinary browser backend startup, especially on shared CI runners.
        for _ in range(1800 if cyclic_tie_browser else 180):
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
                    return response.json() if status in (200, 201, 202) else None

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
                browser_click(page, "Choose groups + knockout" if hybrid_preparation
                              else "Choose pure round-robin groups")
                group_setup = page.get_by_label("Group Format setup")
                expect(group_setup).to_be_visible()
                expect(group_setup).to_contain_text("Frozen direct entrants: 4")
                expect(group_setup.get_by_role(
                    "button", name=("Configure groups + knockout Format" if hybrid_preparation
                                    else "Configure pure-groups Format")
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
                expect(group_setup.get_by_label("Group count")).to_have_value(
                    "2" if hybrid_preparation else "1"
                )
                expect(group_setup.get_by_label("Players per group")).to_have_value(
                    "2" if hybrid_preparation else "4"
                )
                if hybrid_preparation:
                    if hybrid_multiround:
                        group_setup.get_by_label("Advancers per group").fill("2")
                    group_setup.get_by_label("Hybrid match 1 top source").select_option("1:1")
                    group_setup.get_by_label("Hybrid match 1 bottom source").select_option("2:1")
                    if hybrid_multiround:
                        group_setup.get_by_label("Hybrid match 2 top source").select_option("1:2")
                        group_setup.get_by_label("Hybrid match 2 bottom source").select_option("2:2")
                    group_setup.get_by_label("Confirm exact hybrid Format and crossings").check()
                else:
                    group_setup.get_by_label("Confirm immutable pure-groups Format").check()
                browser_click(page, "Configure groups + knockout Format" if hybrid_preparation
                              else "Configure pure-groups Format")
                expect(page.get_by_role(
                    "button", name="Generate group Topology"
                )).to_be_visible()
                preparation = request("GET", event_scope + "/preparation")
                assert preparation["format_kind"] == (
                    "groups_knockout" if hybrid_preparation else "groups"
                )
                if hybrid_preparation:
                    hybrid_format = request("GET", event_scope + "/format")
                    group_configuration = hybrid_format["group_configuration"]
                    assert hybrid_format["format_kind"] == "groups_knockout"
                    assert group_configuration["advancing_per_group"] == (
                        2 if hybrid_multiround else 1
                    )
                    expected_crossings = [{
                        "match_index": 1,
                        "top": {"group_index": 1, "finishing_position": 1},
                        "bottom": {"group_index": 2, "finishing_position": 1},
                    }]
                    if hybrid_multiround:
                        expected_crossings.append({
                            "match_index": 2,
                            "top": {"group_index": 1, "finishing_position": 2},
                            "bottom": {"group_index": 2, "finishing_position": 2},
                        })
                    assert group_configuration["knockout_crossings"] == expected_crossings
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
                expected_matches = 2 if hybrid_preparation else 6
                expected_days = 1 if hybrid_preparation else 3
                assert preparation["group_match_count"] == expected_matches
                assert preparation["group_match_day_count"] == expected_days
                schedule = request("GET", event_scope + "/format/group-match-schedule")
                assert schedule["group_count"] == (2 if hybrid_preparation else 1)
                assert schedule["group_size"] == (2 if hybrid_preparation else 4)
                assert schedule["match_day_count"] == expected_days
                assert len(schedule["matches"]) == expected_matches
                assert len({m["match_id"] for m in schedule["matches"]}) == expected_matches
                assert all(m["effective_match_format"]["format"]["best_of"] == 3
                           for m in schedule["matches"])
                page.screenshot(
                    path=str(artifacts / "02-real-group-format-browser.png"),
                    full_page=True,
                )
                print("GROUP BROWSER: real Admin UI committed BO3 Rules, pure Format, Topology and six Match Days",
                      flush=True)

                if cyclic_tie_browser:
                    # This test uses six real independently selected MatchEngine
                    # results via isolated fixture input adapters; it does NOT
                    # claim those scores arose from this Run's Match-Day RNG.
                    def restart_cyclic_backend():
                        nonlocal process
                        process.terminate()
                        process.wait(timeout=20)
                        process = start()

                    evidence = exercise_real_cyclic_browser(
                        request=request, page=page,
                        event_url=prepared_event_url, event_scope=event_scope,
                        artifacts=artifacts, root=root, run_id=run_id,
                        branch_id=branch_id, event_id=EVENT_ID,
                        restart_backend=restart_cyclic_backend,
                    )
                    assert browser_errors == [], browser_errors
                    (artifacts / "cyclic-tie-evidence.json").write_text(
                        json.dumps(evidence, indent=2)
                    )
                    print(
                        "REAL CYCLIC MATCHENGINE TIE BROWSER / HTTP / SQLITE PASSED "
                        "(isolated test input adapters, not a Run Match-Day)",
                        flush=True,
                    )
                    return

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
                assert len(group["matches"]) == expected_matches
                assert group["match_day_count"] == expected_days
                assert group["group_size"] == (2 if hybrid_preparation else 4)
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
                    expect(group_table.locator("tbody tr")).to_have_count(expected_matches)
                    expect(page.get_by_text(
                        "Authentic group Match Day schedule",
                    )).to_be_visible()
                    expect(group_table.get_by_text("BO3")).to_have_count(expected_matches)
                    expect(group_table.get_by_text(
                        "Not canonically published",
                    )).to_have_count(expected_matches)
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
                hybrid_result = None
                hybrid_ranking = None
                hybrid_task_handoff = None
                hybrid_task_completion = None
                hybrid_second_week_result = None
                hybrid_same_parent_result = None
                if hybrid_progression or hybrid_multiround or hybrid_worker_transition or hybrid_second_week or hybrid_same_parent_restart:
                    if hybrid_progression or hybrid_worker_transition or hybrid_second_week or hybrid_same_parent_restart:
                        from real_hybrid_full_simulation_task_browser_checks import (
                            start_real_group_handoff_task,
                            assert_handoff_task_still_pending,
                        )

                        def start_hybrid_task(adopted_schedule):
                            nonlocal hybrid_task_handoff
                            hybrid_task_handoff = start_real_group_handoff_task(
                                request=request, page=page, run_url=run_url,
                                run_id=run_id, branch_id=branch_id,
                                simulation_scope=simulation_scope,
                                schedule_fingerprint=adopted_schedule["schedule_fingerprint"],
                                artifacts=artifacts,
                            )
                    else:
                        start_hybrid_task = None
                    hybrid_result = play_and_freeze_hybrid(
                        request=request,page=page,run_id=run_id,branch_id=branch_id,
                        event_id=EVENT_ID,run_url=run_url,
                        event_url=prepared_event_url,root_scope=root_scope,
                        event_scope=event_scope,
                        original_match_ids={m["match_id"] for m in schedule["matches"]},
                        initial_revision=revision,artifacts=artifacts,
                        knockout_rounds=2 if hybrid_multiround else 1,
                        on_group_schedule_adopted=start_hybrid_task,
                    )
                    if hybrid_task_handoff is not None:
                        assert_handoff_task_still_pending(
                            request=request, simulation_scope=simulation_scope,
                            frozen=hybrid_task_handoff, artifacts=artifacts,
                        )
                    assert saved(hybrid_result["completed_saved_revision"]) == (
                        hybrid_result["archived_edition"]
                    )
                    if hybrid_worker_transition or hybrid_second_week or hybrid_same_parent_restart:
                        from real_hybrid_full_simulation_task_browser_checks import (
                            resume_original_full_simulation_to_advance_real_hybrid_week,
                        )

                        def worker_transition(**ranking_evidence):
                            nonlocal hybrid_task_completion
                            hybrid_task_completion = resume_original_full_simulation_to_advance_real_hybrid_week(
                                request=request, page=page, run_url=run_url,
                                simulation_scope=simulation_scope,
                                frozen=hybrid_task_handoff, artifacts=artifacts,
                                **ranking_evidence,
                            )
                    else:
                        worker_transition = None
                    hybrid_ranking = publish_first_hybrid_official_week(
                        request=request,page=page,run_id=run_id,branch_id=branch_id,
                        run_url=run_url,root_scope=root_scope,event_id=EVENT_ID,
                        hybrid=hybrid_result,artifacts=artifacts,
                        on_before_week_transition=worker_transition,
                    )
                    if hybrid_task_handoff is not None and not (hybrid_worker_transition or hybrid_second_week or hybrid_same_parent_restart):
                        from real_hybrid_full_simulation_task_browser_checks import (
                            resume_real_hybrid_task_at_explicit_week_two_target,
                        )
                        hybrid_task_completion = resume_real_hybrid_task_at_explicit_week_two_target(
                            request=request, page=page, run_url=run_url,
                            simulation_scope=simulation_scope,
                            frozen=hybrid_task_handoff, artifacts=artifacts,
                        )
                    assert saved(revision) == expected
                    print("HYBRID BROWSER: two real group games, "
                          + ("two semifinals and final" if hybrid_multiround else "one final")
                          + ", explicit Ranking policy, canonical closure, "
                          + "Week-2 publication, Saved revision/restart", flush=True)

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
                        reconstruct_one_group_match=reconstruct_one_group_match,
                    )
                    assert completed["intermediate_backend_restart"] is True
                    assert bool(completed["reconstructed_group_match"]) == reconstruct_one_group_match
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
                if hybrid_result is not None:
                    assert hybrid_ranking is not None
                    viewer = "/viewer/runs/" + quote(run_id, safe="") + "/rankings"
                    assert request("GET", viewer + "/current") == hybrid_ranking["official_week_2"]
                    assert request("GET", viewer + "/history") == hybrid_ranking["ranking_history"]
                    assert request("GET", viewer + "/history/0") == hybrid_ranking["historical_week_1"]
                    assert request("GET", viewer + "/history/1") == hybrid_ranking["official_week_2"]
                    assert request("GET", root_scope + "/authoritative-simulation/position")["current_week"] == {"season_index": 0, "week": 2}
                    if hybrid_worker_transition or hybrid_second_week or hybrid_same_parent_restart:
                        # Actual process death/restart must preserve the exact
                        # terminal parent/task, not enqueue it for duplicate work.
                        from real_hybrid_full_simulation_task_browser_checks import _task
                        assert hybrid_task_handoff is not None and hybrid_task_completion is not None
                        terminal = _task(request, simulation_scope, hybrid_task_handoff["task_id"])
                        assert terminal["state"] == "target_reached", terminal
                        assert terminal["parent_command_id"] == hybrid_task_handoff["parent_command_id"]
                        assert terminal["original_command"]["command_id"] == hybrid_task_handoff["parent_command_id"]
                        assert terminal["current_week"] == {"season_index": 0, "week": 2}
                        assert terminal["needs_operator_action"] is False
                        assert terminal["error"] is None
                        assert request("GET", simulation_scope + "/position")["current_week"] == {"season_index": 0, "week": 2}
                    after_branches = request("GET", "/run-branches?run_id=" + quote(run_id, safe=""))["run_branches"]
                    assert next(item for item in after_branches if item["branch_id"] == branch_id)["saved_head_revision_id"] == hybrid_ranking["saved_week_2_revision"]
                    assert saved(hybrid_result["completed_saved_revision"]) == (
                        hybrid_result["archived_edition"]
                    ), "Saved hybrid group revision changed after SQLite restart"
                    assert request("GET",event_scope+"/group-standings") == (
                        hybrid_result["group_authority"]
                    )
                    assert request("GET",event_scope+"/hybrid-knockout-entrants") == (
                        hybrid_result["entrants_authority"]
                    )
                    assert request("GET",event_scope+"/hybrid-knockout-bracket") == (
                        hybrid_result["bracket_authority"]
                    )
                    assert request("GET",event_scope+"/hybrid-ranking-policy") == (
                        hybrid_result["ranking_policy_authority"]
                    )
                    assert request("GET",event_scope+"/hybrid-ranking-close") == (
                        hybrid_result["ranking_closure"]
                    )
                    replay = request("GET",root_scope+"/authoritative-simulation/match-replays?limit=50")
                    assert len(replay["matches"]) == 2 + hybrid_result["real_knockout_matches"]
                    for match_id, expected_replay in hybrid_result["all_knockout_replays"].items():
                        assert [m for m in replay["matches"] if m["match_id"] == match_id] == [expected_replay]
                        assert request("GET", root_scope + "/authoritative-simulation/match-replay/context?group_id=" + quote(match_id, safe="")) == hybrid_result["all_knockout_contexts"][match_id]
                    final_matches = [m for m in replay["matches"]
                                     if m["match_id"] == hybrid_result["bracket_authority"]["terminal_match_id"]]
                    assert final_matches == [hybrid_result["frozen_final_replay"]], (
                        "Real played knockout final changed after SQLite backend restart"
                    )
                    assert request(
                        "GET",root_scope+"/authoritative-simulation/match-replay/context?group_id="
                        + quote(hybrid_result["bracket_authority"]["terminal_match_id"],safe="")
                    ) == hybrid_result["frozen_final_context"]
                    page.goto(prepared_event_url)
                    expect(page.get_by_role(
                        "table",name="Canonical hybrid knockout bracket"
                    )).to_be_visible(timeout=30000)
                    page.screenshot(path=str(artifacts/"hybrid-05-after-restart.png"),
                                    full_page=True)
                    if hybrid_second_week or hybrid_same_parent_restart:
                        from real_hybrid_full_simulation_task_browser_checks import (
                            prove_next_real_hybrid_week_from_restarted_saved_run,
                        )
                        hybrid_second_week_result = prove_next_real_hybrid_week_from_restarted_saved_run(
                            request=request, page=page, run_url=run_url,
                            simulation_scope=simulation_scope, frozen=hybrid_task_handoff,
                            official_week_two=hybrid_ranking["official_week_2"],
                            saved_week_two_revision=hybrid_ranking["saved_week_2_revision"],
                            artifacts=artifacts,
                        )
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
                    "real_group_match_reconstruction": (
                        completed["reconstructed_group_match"] if completed else None
                    ),
                    "hybrid_group_full_simulation_task":hybrid_task_handoff,
                    "hybrid_full_simulation_terminal":hybrid_task_completion,
                    "hybrid_second_week_from_restart":hybrid_second_week_result,
                    "hybrid_same_parent_across_second_restart":hybrid_same_parent_result,
                    "hybrid_progression": ({
                        "completed_revision":hybrid_result["completed_saved_revision"],
                        "played_group_match_count":hybrid_result["real_group_matches"],
                        "played_knockout_match_count":hybrid_result["real_knockout_matches"],
                        "played_match_days":hybrid_result["real_match_days"],
                        "knockout_champion":hybrid_result["frozen_final_replay"]["winner_player_id"],
                        "knockout_result_fingerprint":hybrid_result["frozen_final_replay"]["result_fingerprint"],
                        "ranking_policy_fingerprint":hybrid_result["ranking_policy_authority"]["authority_fingerprint"],
                        "ranking_source_fingerprint":hybrid_result["ranking_closure"]["source_fingerprint"],
                        "ranking_award_fingerprint":hybrid_result["ranking_closure"]["award_fingerprint"],
                        "total_ranking_points":hybrid_result["ranking_closure"]["total_ranking_points"],
                        "group_authority_fingerprint":hybrid_result["group_authority"]["authority_fingerprint"],
                        "entrants_authority_fingerprint":hybrid_result["entrants_authority"]["authority_fingerprint"],
                        "bracket_authority_fingerprint":hybrid_result["bracket_authority"]["authority_fingerprint"],
                        "result_published":hybrid_result["result_published"],
                        "official_ranking_week_2_published":hybrid_ranking is not None,
                        "official_week_2_fingerprint":hybrid_ranking["expected_ranking_fingerprint"] if hybrid_ranking else None,
                        "official_week_2_saved_revision":hybrid_ranking["saved_week_2_revision"] if hybrid_ranking else None,
                        "official_week_2_total_delta":sum(hybrid_ranking["composed_ranking_deltas"].values()) if hybrid_ranking else None,
                        "official_week_2_publication_count":hybrid_ranking["ranking_history"]["publication_count"] if hybrid_ranking else None,
                    } if hybrid_result else None),
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
    parser.add_argument("--cyclic-tie-browser", action="store_true",
                        help="Chromium UI decision on six natural cyclic MatchEngine test-input receipts")
    parser.add_argument("--cyclic-tie-fixture", action="store_true",
                        help="Serve ONLY: install exact-scope genuine MatchEngine test inputs")
    parser.add_argument("--hybrid-progression", action="store_true",
                        help="Play two real hybrid group matches and knockout final, freeze authorities, Save and restart")
    parser.add_argument("--hybrid-same-parent-restart", action="store_true",
                        help="Resume the SAME second Full Simulation task after a second real process restart")
    parser.add_argument("--hybrid-second-week", action="store_true",
                        help="After original real hybrid worker Week 2 and SQLite restart, advance following week on same Run")
    parser.add_argument("--hybrid-worker-transition", action="store_true",
                        help="Real group-to-knockout Full Simulation worker owns canonical Week Transition")
    parser.add_argument("--hybrid-multiround", action="store_true",
                        help="Two actual group matches, two semifinal MatchEngine games, winner-fed final, ranked Save/restart")
    parser.add_argument("--hybrid-preparation", action="store_true",
                        help="Browser verifies explicitly configured hybrid plus Saved Edition after SQLite restart")
    parser.add_argument("--complete-groups", action="store_true",
                        help="Actually simulate all six group matches, freeze standings, Save, replay after restart")
    parser.add_argument("--reconstruct-one-group-match", action="store_true",
                        help="Review/commit one natural MatchEngine candidate as a real canonical group Slot before Match Day 3")
    args = parser.parse_args()
    if (args.hybrid_preparation or args.hybrid_progression or args.hybrid_multiround or args.hybrid_worker_transition or args.hybrid_second_week or args.hybrid_same_parent_restart) and (
        args.complete_groups or args.reconstruct_one_group_match or args.cyclic_tie_browser
    ):
        parser.error("--hybrid-preparation is a frozen preparation and Save test, not completed hybrid closure")
    if args.hybrid_same_parent_restart and (args.hybrid_second_week or args.hybrid_worker_transition or args.hybrid_progression or args.hybrid_multiround):
        parser.error('--hybrid-same-parent-restart runs separately from other hybrid modes')
    if args.hybrid_second_week and (args.hybrid_worker_transition or args.hybrid_progression or args.hybrid_multiround):
        parser.error("--hybrid-second-week runs separately from other hybrid modes")
    if args.hybrid_worker_transition and (args.hybrid_progression or args.hybrid_multiround):
        parser.error("--hybrid-worker-transition runs separately from the existing hybrid acceptance")
    if args.hybrid_multiround and (args.hybrid_progression or args.hybrid_preparation):
        parser.error("--hybrid-multiround is a standalone fully verified multi-round scenario")
    if args.cyclic_tie_browser and (args.complete_groups or args.reconstruct_one_group_match):
        parser.error("--cyclic-tie-browser cannot also simulate normal Run Match Days")
    if args.reconstruct_one_group_match and not args.complete_groups:
        parser.error("--reconstruct-one-group-match requires --complete-groups")
    if args.serve:
        if args.cyclic_tie_fixture:
            install_real_match_engine_cyclic_fixture(args.serve.resolve())
        uvicorn.run(
            create_smoke_app(args.serve.resolve()),
            host="127.0.0.1", port=args.port, log_level="warning",
        )
    else:
        acceptance(
            args.acceptance.resolve(), port=args.port,
            base_url=args.base_url, chromium=args.chromium,
            complete_groups=args.complete_groups,
            reconstruct_one_group_match=args.reconstruct_one_group_match,
            cyclic_tie_browser=args.cyclic_tie_browser,
            hybrid_preparation=args.hybrid_preparation or args.hybrid_progression or args.hybrid_multiround or args.hybrid_worker_transition or args.hybrid_second_week or args.hybrid_same_parent_restart,
            hybrid_progression=args.hybrid_progression,
            hybrid_multiround=args.hybrid_multiround,
            hybrid_worker_transition=args.hybrid_worker_transition,
            hybrid_second_week=args.hybrid_second_week,
            hybrid_same_parent_restart=args.hybrid_same_parent_restart,
        )
