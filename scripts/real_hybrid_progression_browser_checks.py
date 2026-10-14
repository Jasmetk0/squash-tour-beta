"""Real Run-owned two-group Match Day -> group standings -> hybrid entrants/bracket.

No result injection, seed reseeding, synthetic HTTP response or invented winner.
Production Chromium clicks actual simulation, group authority and hybrid panels.
"""
from __future__ import annotations

from urllib.parse import quote


def play_and_freeze_hybrid(
    *, request, page, run_id: str, branch_id: str, event_id: str,
    run_url: str, event_url: str, root_scope: str, event_scope: str,
    original_match_ids: set[str], initial_revision: str, artifacts,
) -> dict:
    from playwright.sync_api import expect
    from admin_first_tournament_smoke import browser_click, browser_settle

    assert len(original_match_ids) == 2
    simulation = root_scope + "/authoritative-simulation"
    frozen = request("GET", event_scope + "/format")
    assert frozen["format_kind"] == "groups_knockout"
    assert frozen["group_configuration"]["advancing_per_group"] == 1
    assert len(frozen["group_configuration"]["knockout_crossings"]) == 1
    request("GET", event_scope + "/hybrid-knockout-entrants", status=404)
    request("GET", event_scope + "/hybrid-knockout-bracket", status=404)
    # Must be impossible before any real group match results.
    request("POST", event_scope + "/hybrid-knockout-entrants/generate", {
        "command_id": "premature-entrants",
    }, status=409)

    proposal = request("GET", simulation + "/week-schedule/proposal")
    assert proposal["schedule"]["slots"]
    adopted = request("POST", simulation + "/week-schedule/adopt-proposal", {
        "request_id": "actual-hybrid-two-groups-schedule",
        "expected_week": proposal["schedule"]["week"],
        "expected_schedule_fingerprint": proposal["schedule_fingerprint"],
        "expected_position_fingerprint": proposal["position_fingerprint"],
    }, status=201)
    assert adopted["schedule_fingerprint"] == proposal["schedule_fingerprint"]

    day = request("GET", simulation + "/next-match-day/preview")
    assert day["match_day_ordinal"] == 1
    assert len(day["target_slot_ordinals"]) == 2, day
    page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    browser_click(page, "Review authoritative Next Match Day")
    expect(page.get_by_role("heading", name="Reviewed canonical Match Day 1")).to_be_visible()
    page.get_by_label("Confirm authoritative simulation").check()
    browser_click(page, "Simulate reviewed authoritative Match Day")
    browser_settle(page)
    position = request("GET", simulation + "/position")
    assert position["position_fingerprint"] != day["expected_position_fingerprint"]

    page.goto(event_url)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    tie = request("GET", event_scope + "/group-standings/tie-resolution")
    assert tie["unresolved_case"] is None, tie
    button = page.get_by_role("button", name="Generate canonical group standings")
    expect(button).to_be_disabled()
    page.get_by_label(
        "Confirm generation from all completed canonical group matches"
    ).check()
    expect(button).to_be_enabled()
    button.click()
    first = page.get_by_role("table", name="Canonical group 1 standings")
    second = page.get_by_role("table", name="Canonical group 2 standings")
    expect(first).to_be_visible(timeout=30000)
    expect(second).to_be_visible()
    standing = request("GET", event_scope + "/group-standings")
    assert len(standing["groups"]) == 2
    assert [len(g["rows"]) for g in standing["groups"]] == [2, 2]
    assert len(standing["source_results"]) == 2
    assert {m["match_id"] for m in standing["source_results"]} == original_match_ids
    assert all(m["result_kind"] == "played" for m in standing["source_results"])
    page.screenshot(path=str(artifacts / "hybrid-03-real-two-group-standings.png"),
                    full_page=True)

    region = page.get_by_label("Hybrid knockout progression")
    expect(region).to_be_visible()
    create_entrants = region.get_by_role(
        "button", name="Generate frozen knockout entrants"
    )
    expect(create_entrants).to_be_disabled()
    region.get_by_label("Confirm entrants from exact final group standings").check()
    expect(create_entrants).to_be_enabled()
    create_entrants.click()
    table = page.get_by_role("table", name="Canonical advancing positions")
    expect(table).to_be_visible(timeout=30000)
    entrants = request("GET", event_scope + "/hybrid-knockout-entrants")
    assert entrants["group_standings_authority_fingerprint"] == (
        standing["authority_fingerprint"]
    )
    assert len(entrants["first_round_matches"]) == 1
    only_match = entrants["first_round_matches"][0]
    assert (only_match["top_source"], only_match["bottom_source"]) == (
        {"group_index": 1, "finishing_position": 1},
        {"group_index": 2, "finishing_position": 1},
    )
    assert only_match["top_player_id"] == standing["groups"][0]["rows"][0]["player_id"]
    assert only_match["bottom_player_id"] == standing["groups"][1]["rows"][0]["player_id"]

    create_bracket = region.get_by_role(
        "button", name="Generate frozen knockout bracket"
    )
    expect(create_bracket).to_be_disabled()
    region.get_by_label("Confirm bracket from exact frozen entrants").check()
    expect(create_bracket).to_be_enabled()
    create_bracket.click()
    bracket_table = page.get_by_role("table", name="Canonical hybrid knockout bracket")
    expect(bracket_table).to_be_visible(timeout=30000)
    bracket = request("GET", event_scope + "/hybrid-knockout-bracket")
    assert bracket["entrants_authority_fingerprint"] == entrants["authority_fingerprint"]
    assert bracket["entrant_count"] == 2 and bracket["round_count"] == 1
    assert bracket["terminal_match_id"] == only_match["match_id"]
    assert bracket["matches"][0]["participant_sources"] == [
        "player:" + only_match["top_player_id"],
        "player:" + only_match["bottom_player_id"],
    ]
    page.screenshot(path=str(artifacts / "hybrid-04-reviewed-actual-entrants-bracket.png"),
                    full_page=True)

    # An immutable first-round bracket is a *plan*, not the finished sporting
    # result. The existing Run driver must now dynamically extend the canonical
    # Week Schedule, preserving the group Match Day and its result receipts.
    pending_position = request("GET", simulation + "/position")
    assert pending_position["current_slot_kind"] == "match", pending_position
    assert bracket["terminal_match_id"] in pending_position["eligible_match_ids"]
    knockout_preview = request("GET", simulation + "/next-match-day/preview")
    assert knockout_preview["match_day_ordinal"] == 2, knockout_preview
    assert len(knockout_preview["target_slot_ordinals"]) == 1
    assert pending_position["slot_ordinal"] in knockout_preview["target_slot_ordinals"]
    before_replay = request("GET", simulation + "/match-replays?limit=50")
    assert len([m for m in before_replay["matches"]
                if m["match_id"] == bracket["terminal_match_id"]]) == 0, (
        "Knockout result must not exist before an actual MatchEngine execution"
    )
    page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    from playwright.sync_api import expect
    # Cold React mounts can still be requesting canonical Position/branch state
    # after the protected HTTP preview has already succeeded. Synchronize on
    # the actual actionable control rather than an arbitrary network-idle delay.
    expect(page.get_by_role(
        "button", name="Review authoritative Next Match Day"
    )).to_be_enabled(timeout=30000)
    browser_click(page, "Review authoritative Next Match Day")
    expect(page.get_by_role(
        "heading", name="Reviewed canonical Match Day 2"
    )).to_be_visible()
    page.get_by_label("Confirm authoritative simulation").check()
    browser_click(page, "Simulate reviewed authoritative Match Day")
    browser_settle(page)

    replay_list = request("GET", simulation + "/match-replays?limit=50")
    assert replay_list["read_only"] is True
    assert len(replay_list["matches"]) == 3
    finals = [
        item for item in replay_list["matches"]
        if item["match_id"] == bracket["terminal_match_id"]
    ]
    assert len(finals) == 1
    final = finals[0]
    expected_finalists = {only_match["top_player_id"], only_match["bottom_player_id"]}
    assert {final["winner_player_id"], final["loser_player_id"]} == expected_finalists
    assert len(final["result_fingerprint"]) == 64
    assert final["replay_available"] and final["total_rallies"] > 0
    final_context = request(
        "GET",simulation + "/match-replay/context?group_id="
        + quote(bracket["terminal_match_id"],safe=""),
    )
    assert final_context["verified"] is True
    assert final_context["rng_rerun"] is False
    assert final_context["replay_source"] == "stored_authoritative_events"
    assert final_context["result_fingerprint"] == final["result_fingerprint"]
    assert final_context["event_id"] == event_id
    # No second click may silently replay the terminal or fabricate a winner.
    remaining = request("GET", simulation + "/position")
    assert bracket["terminal_match_id"] not in remaining["eligible_match_ids"]
    page.screenshot(path=str(artifacts / "hybrid-05-real-knockout-final-replay.png"),
                    full_page=True)

    # The two played Group games and final do NOT imply any ranking points.
    # An operator must supply independent explicit values for group wins,
    # champion and finalist, with no model or frontend numerical defaults.
    request("GET", event_scope + "/hybrid-ranking-policy", status=404)
    request("GET", event_scope + "/hybrid-ranking-close", status=404)
    request("POST", event_scope + "/hybrid-ranking-close", {
        "command_id": "premature-closure-without-ranking-policy",
    }, status=409)
    page.goto(event_url)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    policy_panel = page.get_by_label("Hybrid tournament ranking closure")
    expect(policy_panel).to_be_visible(timeout=30000)
    configure_policy = policy_panel.get_by_role(
        "button", name="Freeze hybrid ranking points policy"
    )
    expect(configure_policy).to_be_disabled()
    policy_panel.get_by_label("Played group win points").fill("10")
    policy_panel.get_by_label("Hybrid points for champion").fill("100")
    policy_panel.get_by_label("Hybrid points for finalist").fill("60")
    expect(configure_policy).to_be_disabled()
    policy_panel.get_by_label("Confirm exact hybrid ranking point values").check()
    expect(configure_policy).to_be_enabled()
    configure_policy.click()
    policy_table = policy_panel.get_by_role(
        "table", name="Frozen hybrid ranking phase points"
    )
    expect(policy_table).to_be_visible(timeout=30000)
    policy = request("GET", event_scope + "/hybrid-ranking-policy")
    assert policy["played_group_win_points"] == 10
    assert policy["knockout_stage_points"] == [
        ["champion",100],["finalist",60]
    ]
    assert policy["composition_policy_id"] == (
        "single_tournament_sum_group_plus_knockout_no_double_count.v1"
    )
    close_button = policy_panel.get_by_role(
        "button", name="Close real hybrid tournament ranking source"
    )
    expect(close_button).to_be_disabled()
    policy_panel.get_by_label(
        "Confirm close from real hybrid match results"
    ).check()
    expect(close_button).to_be_enabled()
    close_button.click()
    expect(policy_panel.get_by_text(
        "Canonical tournament source is frozen"
    )).to_be_visible(timeout=30000)
    closure = request("GET", event_scope + "/hybrid-ranking-close")
    assert closure["total_ranking_points"] == 180, closure
    assert all(len(closure[key])==64 for key in (
        "source_fingerprint","result_fingerprint",
        "award_fingerprint","prize_award_fingerprint"
    ))
    assert closure["source_fingerprint"] != closure["award_fingerprint"]
    page.screenshot(
        path=str(artifacts / "hybrid-06-reviewed-ranking-closure.png"),
        full_page=True
    )

    # Explicitly persist canonical tournament/result/awards in a Saved Revision.
    preview = request("GET", simulation + "/save/preview")
    assert preview["can_save"] and preview["has_unsaved_changes"]
    assert preview["saved_head_revision_id"] == initial_revision
    page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    save = page.get_by_role("button", name="Save authoritative simulation")
    expect(save).to_be_enabled(timeout=30000)
    save.click()
    expect(page.get_by_text("Saved as revision",exact=False)).to_be_visible(timeout=30000)
    branches = request("GET", "/run-branches?run_id=" + quote(run_id, safe=""))
    branch = next(b for b in branches["run_branches"] if b["branch_id"] == branch_id)
    last_revision = branch["saved_head_revision_id"]
    assert last_revision != initial_revision
    archived = request("GET", root_scope + "/tour/editions/" +
        quote(event_id, safe="") + "?revision_id=" +
        quote(last_revision, safe="") + "&season_index=0")
    assert archived["group_standings"] is not None
    assert len(archived["group_standings"]["groups"]) == 2
    assert archived["group_standings"]["authority_fingerprint"] == standing["authority_fingerprint"]
    # The saved tournament is published *only after* the operator approved
    # the full phase-policy and the backend closed from real receipts.
    assert archived["published_result"] is not None
    assert archived["published_result"]["champion_player_id"] == final["winner_player_id"]
    assert archived["published_result"]["finalist_player_id"] == final["loser_player_id"]
    saved_matches = archived["published_result"]["matches"]
    assert len(saved_matches) == 3
    assert any(m["match_id"] == bracket["terminal_match_id"]
               and m["winner_player_id"] == final["winner_player_id"]
               for m in saved_matches)
    return {
        "first_saved_revision":initial_revision,
        "completed_saved_revision":last_revision,
        "archived_edition":archived,
        "group_authority":standing,
        "entrants_authority":entrants,
        "bracket_authority":bracket,
        "real_group_matches":2,
        "real_knockout_matches":1,
        "real_match_days":2,
        "frozen_final_replay":final,
        "frozen_final_context":final_context,
        "ranking_policy_authority":policy,
        "ranking_closure":closure,
        "result_published":True,
    }
