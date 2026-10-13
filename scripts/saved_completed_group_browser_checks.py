"""Finish *real* Group matches through the production Run Simulation API.

No fabricated result receipts or database fixture insertion. Existing immutable
Format/Topology/Group Schedule and real generated athletes from the Phase-1
browser are used as inputs. A final table is read only AFTER all six actual
matches are persisted, followed by the ordinary authoritative Simulation Save.
"""
from __future__ import annotations

from urllib.parse import quote



def play_group_and_save(
    request, *, run_id: str, branch_id: str, event_id: str,
    root_scope: str, event_scope: str, old_revision: str,
    original_match_ids: set[str], page, run_url: str, event_url: str, artifacts,
    restart_backend,
) -> dict:
    # The fast backend suite imports this module without installing Playwright.
    # Load browser-only dependencies only in the real Chromium execution.
    from playwright.sync_api import expect
    from admin_first_tournament_smoke import browser_click, browser_settle

    simulation = root_scope + "/authoritative-simulation"

    def check_schedule():
        schedule = request("GET", event_scope + "/format/group-match-schedule")
        matches = schedule["matches"]
        assert len(matches) == len(original_match_ids) == 6
        assert {match["match_id"] for match in matches} == original_match_ids
        assert (schedule["group_count"], schedule["group_size"]) == (1, 4)
        return schedule

    check_schedule()

    # The real driver must first adopt one immutable global Week Schedule.
    # This reserves the actual group Match Days and avoids any manually chosen
    # opponent, seed, slot, phase order or fabricated competitive output.
    proposed = request("GET", simulation + "/week-schedule/proposal")
    assert proposed["schedule"]["slots"]
    assert len(proposed["schedule_fingerprint"]) == 64
    adopted = request("POST", simulation + "/week-schedule/adopt-proposal", {
        "request_id": "real-browser-group-schedule",
        "expected_week": proposed["schedule"]["week"],
        "expected_schedule_fingerprint": proposed["schedule_fingerprint"],
        "expected_position_fingerprint": proposed["position_fingerprint"],
    }, 201)
    assert adopted["schedule_fingerprint"] == proposed["schedule_fingerprint"]

    preflight = request("GET", simulation + "/position")
    assert preflight["current_week"] == {"season_index": 0, "week": 1}
    assert preflight["current_slot_kind"] in {"entry", "match"}, preflight

    # The prior acceptance used direct POSTs here. Execute the *actual* Admin
    # Simulation UI instead. No result is inserted, mocked or reconstructed.
    page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    played = []
    day_ordinals = []
    for day in range(1, 4):
        preview = request("GET", simulation + "/next-match-day/preview")
        assert preview["match_day_ordinal"] == day, preview
        assert preview["target_slot_ordinals"], preview
        expect(page.get_by_role(
            "button", name="Review authoritative Next Match Day"
        )).to_be_enabled()
        browser_click(page, "Review authoritative Next Match Day")
        expect(page.get_by_role(
            "heading", name=f"Reviewed canonical Match Day {day}"
        )).to_be_visible()
        expect(page.get_by_label("Reviewed authoritative Match Day").locator("li")).to_have_count(
            len(preview["target_slot_ordinals"])
        )
        page.get_by_label("Confirm authoritative simulation").check()
        browser_click(page, "Simulate reviewed authoritative Match Day")
        # The mutation invalidates the position and Save preview; settle before
        # asking the server for its next authoritative state.
        browser_settle(page)
        following = request("GET", simulation + "/position")
        assert following["position_fingerprint"] != preview["expected_position_fingerprint"], (
            "Browser Match Day click did not advance canonical position", day, following
        )
        played.append(day)
        day_ordinals.extend(preview["target_slot_ordinals"])
        page.screenshot(path=str(artifacts / f"03-simulation-group-day-{day}.png"), full_page=True)
    assert len(day_ordinals) == len(set(day_ordinals)) == 6
    assert played == [1, 2, 3]

    # Complete standings only via the real Planned Event panel. Genuine ties,
    # when encountered, require explicit player ordering and an audited reason.
    # This ordinary group run does NOT deterministically manufacture a tie.
    page.goto(event_url)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    tie_audit = []
    for attempt in range(5):
        tie_state = request("GET", event_scope + "/group-standings/tie-resolution")
        case = tie_state["unresolved_case"]
        if case is None:
            break
        editor = page.get_by_role("group", name="Explicit group tie decision")
        expect(editor).to_be_visible()
        initial_ids = case["player_ids"]
        assert len(initial_ids) >= 2, case
        editor.get_by_role("button", name=f"Move {initial_ids[0]} down").click()
        editor.get_by_label("Admin tie decision reason").fill(
            "Reviewed exact canonical tie evidence in the production Admin; "
            "operator deliberately swapped the top two unresolved players."
        )
        editor.get_by_label(
            "Confirm this exact player order and recorded audit reason"
        ).check()
        browser_click(page, "Commit audited group tie decision")
        browser_settle(page)
        after = request("GET", event_scope + "/group-standings/tie-resolution")
        assert len(after["resolutions"]) == len(tie_state["resolutions"]) + 1, after
        tie_audit.append(after["resolutions"][-1])
    else:
        raise AssertionError("More than five unresolved Admin tie cases")

    # First Save is intentionally *before* final Group Standings. This is the
    # production two-revision history boundary, not a synthetic intermediate
    # component assembled from sporting fixtures.
    intermediate_preview = request("GET", simulation + "/save/preview")
    assert intermediate_preview["can_save"] is True, intermediate_preview
    assert intermediate_preview["has_unsaved_changes"] is True
    assert intermediate_preview["saved_head_revision_id"] == old_revision
    page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    # Some read-only Replay/diagnostics queries can remain in-flight while the
    # production Save action is already ready. Synchronize on the exact real
    # control and confirmed revision, not a global network-idle heuristic.
    save_button = page.get_by_role(
        "button", name="Save authoritative simulation"
    )
    expect(save_button).to_be_enabled(timeout=30000)
    save_button.click()
    expect(page.get_by_text(
        "Saved as revision", exact=False
    )).to_be_visible(timeout=30000)
    current = request("GET", "/run-branches?run_id=" + quote(run_id, safe=""))
    branch = next(item for item in current["run_branches"]
                  if item["branch_id"] == branch_id)
    intermediate_revision = branch["saved_head_revision_id"]
    assert intermediate_revision != old_revision
    expect(page.get_by_text(
        f"Saved as revision {intermediate_revision}."
    )).to_be_visible()

    historical_path = root_scope + "/tour/editions/" + quote(event_id, safe="")
    interim_query = (
        "?revision_id=" + quote(intermediate_revision, safe="")
        + "&season_index=0"
    )
    intermediate = request("GET", historical_path + interim_query)
    assert intermediate["group_standings"] is None, (
        "Six genuinely completed matches do not automatically publish a table"
    )
    assert intermediate["published_result"] is None
    assert intermediate["group_schedule"]["authority_fingerprint"] == (
        check_schedule()["authority_fingerprint"]
    )
    pending = intermediate["pending_group_tie_decisions"]
    assert len(pending) == len(tie_audit)
    for decision, frozen in zip(tie_audit, pending):
        assert frozen["case_fingerprint"] == _case_fingerprint(
            decision["decision"]["case"]
        )
        assert frozen["admin_reason"] == decision["decision"]["admin_reason"]
        assert frozen["ordered_player_ids"] == decision["decision"]["ordered_player_ids"]

    history_url = (
        run_url + "/tour/calendar/" + quote(event_id, safe="")
        + "?branch=" + quote(branch_id, safe="")
        + "&revision=" + quote(intermediate_revision, safe="")
        + "&season=0"
    )
    page.goto(history_url)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    page.get_by_role("button", name="Results").click()
    assert page.get_by_label("Saved group standings").count() == 0
    if pending:
        expect(page.get_by_label(
            "Saved pending group tie decisions"
        )).to_be_visible()
    else:
        assert page.get_by_label("Saved pending group tie decisions").count() == 0
    page.screenshot(
        path=str(artifacts / "04-saved-intermediate-no-final-table.png"),
        full_page=True,
    )

    # Close and *recreate* the live HTTP backend against the same SQLite file,
    # then reopen the original immutable revision from the real Saved Tour API.
    restart_backend()
    restored = request("GET", historical_path + interim_query)
    assert restored == intermediate, (
        "Intermediate saved group history changed after SQLite backend restart"
    )
    page.reload()
    page.get_by_role("button", name="Results").click() if (
        page.get_by_role("button", name="Results").get_attribute("aria-current")
        != "page"
    ) else None
    assert page.get_by_label("Saved group standings").count() == 0
    if pending:
        expect(page.get_by_label(
            "Saved pending group tie decisions"
        )).to_be_visible()
    page.screenshot(
        path=str(artifacts / "04-reopened-intermediate-no-final-table.png"),
        full_page=True,
    )
    page.goto(event_url)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    settled_ties = request("GET", event_scope + "/group-standings/tie-resolution")
    assert settled_ties["unresolved_case"] is None
    assert len(settled_ties["resolutions"]) == len(tie_audit)

    button = page.get_by_role("button", name="Generate canonical group standings")
    expect(button).to_be_disabled()
    page.get_by_label("Confirm generation from all completed canonical group matches").check()
    expect(button).to_be_enabled()
    # The committed standings may invalidate auxiliary long-lived queries.
    # Assert the exact authority table appears instead of global network idle.
    button.click()
    table = page.get_by_role("table", name="Canonical group 1 standings")
    expect(table).to_be_visible(timeout=30000)
    expect(table.locator("tbody tr")).to_have_count(4)
    assert page.get_by_role("button", name="Generate canonical group standings").count() == 0
    completed = request("GET", event_scope + "/group-standings")
    assert len(completed["groups"]) == 1
    ranking = completed["groups"][0]["rows"]
    assert_real_played_group_table(ranking, check_schedule()["matches"])
    page.screenshot(path=str(artifacts / "04-clicked-real-group-standings.png"), full_page=True)

    save_preview = request("GET", simulation + "/save/preview")
    assert save_preview["can_save"] is True, save_preview
    assert save_preview["has_unsaved_changes"] is True
    assert save_preview["saved_head_revision_id"] == intermediate_revision
    page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    # A cold React mount first renders 'Loading authoritative sporting
    # state…'. Wait for the real scoped queries to settle rather than treating
    # that transient loading UI as an absent Save action.
    final_save_button = page.get_by_role(
        "button", name="Save authoritative simulation"
    )
    expect(final_save_button).to_be_enabled(timeout=30000)
    final_save_button.click()
    expect(page.get_by_text(
        "Saved as revision", exact=False
    )).to_be_visible(timeout=30000)
    current_branches = request("GET", "/run-branches?run_id=" + quote(run_id, safe=""))
    current = next(item for item in current_branches["run_branches"]
                   if item["branch_id"] == branch_id)
    final_revision = current["saved_head_revision_id"]
    assert final_revision != intermediate_revision
    expect(page.get_by_text(f"Saved as revision {final_revision}.")).to_be_visible()

    final = request("GET", historical_path + "?revision_id="
                    + quote(final_revision, safe="") + "&season_index=0")
    final_group = final["group_standings"]
    assert final_group is not None, final
    assert final_group["authority_fingerprint"] == completed["authority_fingerprint"]
    assert len(final_group["groups"]) == 1
    # Public Edition v1 intentionally projects sporting columns only; the
    # canonical internal authority carries additional provenance fields.
    frozen_rows = final_group["groups"][0]["rows"]
    assert len(frozen_rows) == len(ranking) == 4
    for source, projected in zip(ranking, frozen_rows):
        assert all(source[name] == value for name, value in projected.items()), (
            "Saved Edition sporting table differs from frozen canonical source",
            source, projected,
        )
    assert len(final_group["tie_decisions"]) == len(tie_audit)
    assert final["group_schedule"]["authority_fingerprint"] == (
        check_schedule()["authority_fingerprint"]
    )
    assert final["saved_revision_id"] == final_revision
    assert request("GET", historical_path + interim_query) == intermediate
    assert final["branch_id"] == final["revision_branch_id"] == branch_id
    assert final["run_id"] == run_id
    return {
        "revision": final_revision,
        "intermediate_revision": intermediate_revision,
        "intermediate_edition": intermediate,
        "intermediate_backend_restart": True,
        "edition": final,
        "standings": ranking,
        "played": played,
        "group_tie_decision_count": len(tie_audit),
        "matches_simulated": 6,
    }


def _case_fingerprint(case: dict) -> str:
    """The domain's canonical fingerprint of the supplied unresolved case."""
    from beta_engine.domain.tournaments.group_standings_authority import (
        TournamentGroupStandingsTieCase,
    )
    return TournamentGroupStandingsTieCase.model_validate(case).fingerprint



def assert_real_played_group_table(ranking: list[dict], scheduled: list[dict]) -> None:
    """All six saved matches must have produced real two-sided played receipts."""
    assert len(scheduled) == 6
    assert len(ranking) == 4
    participants = {
        p for match in scheduled
        for p in (match["top_player_id"], match["bottom_player_id"])
    }
    assert len(participants) == 4
    assert {r["player_id"] for r in ranking} == participants
    assert [r["position"] for r in ranking] == [1, 2, 3, 4]
    assert sum(r["wins"] for r in ranking) == 6, "Six real group wins are required"
    assert sum(r["losses"] for r in ranking) == 6, "Six real group losses are required"
    assert sum(r["played_matches"] for r in ranking) == 12
    assert sum(r["walkovers_received"] for r in ranking) == 0
    assert sum(r["walkovers_conceded"] for r in ranking) == 0
    assert all(r["group_points"] >= 0 for r in ranking)
