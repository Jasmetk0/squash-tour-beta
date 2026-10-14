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
    knockout_rounds: int = 1,
) -> dict:
    from playwright.sync_api import expect
    from admin_first_tournament_smoke import browser_click, browser_settle

    assert len(original_match_ids) == 2
    simulation = root_scope + "/authoritative-simulation"
    frozen = request("GET", event_scope + "/format")
    assert frozen["format_kind"] == "groups_knockout"
    assert knockout_rounds in (1, 2)
    first_round_count = 1 << (knockout_rounds - 1)
    assert frozen["group_configuration"]["advancing_per_group"] == first_round_count
    assert len(frozen["group_configuration"]["knockout_crossings"]) == first_round_count
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
    first_round = entrants["first_round_matches"]
    assert len(first_round) == first_round_count
    expected_sources = (
        ((1, 1), (2, 1)),
        *((((1, 2), (2, 2)),) if knockout_rounds == 2 else ()),
    )
    actual_players = set()
    for match, (top, bottom) in zip(first_round, expected_sources, strict=True):
        assert (match["top_source"], match["bottom_source"]) == (
            {"group_index": top[0], "finishing_position": top[1]},
            {"group_index": bottom[0], "finishing_position": bottom[1]},
        )
        top_id = standing["groups"][top[0] - 1]["rows"][top[1] - 1]["player_id"]
        bottom_id = standing["groups"][bottom[0] - 1]["rows"][bottom[1] - 1]["player_id"]
        assert (match["top_player_id"], match["bottom_player_id"]) == (top_id, bottom_id)
        actual_players.update((top_id, bottom_id))
    assert len(actual_players) == first_round_count * 2

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
    assert bracket["entrant_count"] == first_round_count * 2
    assert bracket["round_count"] == knockout_rounds
    assert len(bracket["matches"]) == first_round_count * 2 - 1
    for match, first in zip(bracket["matches"][:first_round_count], first_round, strict=True):
        assert match["match_id"] == first["match_id"]
        assert match["participant_sources"] == [
            "player:" + first["top_player_id"],
            "player:" + first["bottom_player_id"],
        ]
    if knockout_rounds == 2:
        assert bracket["matches"][-1]["participant_sources"] == [
            "winner:" + first_round[0]["match_id"],
            "winner:" + first_round[1]["match_id"],
        ]
        assert bracket["terminal_match_id"] not in {
            match["match_id"] for match in first_round
        }
    else:
        assert bracket["terminal_match_id"] == first_round[0]["match_id"]
    page.screenshot(path=str(artifacts / "hybrid-04-reviewed-actual-entrants-bracket.png"),
                    full_page=True)

    # A frozen bracket is an immutable plan. The canonical simulation extends
    # its Week Schedule by *one real Match Day per knockout round*; no final
    # is eligible until both semi-final winner receipts have been committed.
    before_replay = request("GET", simulation + "/match-replays?limit=50")
    assert len(before_replay["matches"]) == 2
    knockout_results = {}
    contexts = {}
    for round_number in range(1, knockout_rounds + 1):
        round_matches = [
            match for match in bracket["matches"]
            if match["round_number"] == round_number
        ]
        assert len(round_matches) == first_round_count // (2 ** (round_number - 1))
        pending_position = request("GET", simulation + "/position")
        assert pending_position["current_slot_kind"] == "match", pending_position
        assert round_matches[0]["match_id"] in pending_position["eligible_match_ids"]
        knockout_preview = request("GET", simulation + "/next-match-day/preview")
        assert knockout_preview["match_day_ordinal"] == round_number + 1, knockout_preview
        assert len(knockout_preview["target_slot_ordinals"]) == len(round_matches)
        assert pending_position["slot_ordinal"] in knockout_preview["target_slot_ordinals"]
        before_round = request("GET", simulation + "/match-replays?limit=50")
        assert not any(
            item["match_id"] in {match["match_id"] for match in round_matches}
            for item in before_round["matches"]
        ), "Future knockout receipts must not exist until their real Match Day"
        page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
        page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
        expect(page.get_by_role(
            "button", name="Review authoritative Next Match Day"
        )).to_be_enabled(timeout=30000)
        page.get_by_role("button", name="Review authoritative Next Match Day").click()
        expect(page.get_by_role(
            "heading", name=f"Reviewed canonical Match Day {round_number + 1}"
        )).to_be_visible(timeout=30000)
        page.get_by_label("Confirm authoritative simulation").check()
        page.get_by_role("button", name="Simulate reviewed authoritative Match Day").click()
        expect(page.get_by_role(
            "button", name="Simulate reviewed authoritative Match Day"
        )).to_have_count(0, timeout=30000)
        after_round = request("GET", simulation + "/match-replays?limit=50")
        assert after_round["read_only"] is True
        assert len(after_round["matches"]) == 2 + sum(
            first_round_count // (2 ** r) for r in range(round_number)
        )
        for match in round_matches:
            found = [item for item in after_round["matches"]
                     if item["match_id"] == match["match_id"]]
            assert len(found) == 1, ("Knockout Match ID must execute once", match)
            result = found[0]
            if round_number == 1:
                expected_participants = {
                    source.removeprefix("player:")
                    for source in match["participant_sources"]
                }
            else:
                expected_participants = {
                    knockout_results[source.removeprefix("winner:")]["winner_player_id"]
                    for source in match["participant_sources"]
                }
            assert {result["winner_player_id"], result["loser_player_id"]} == (
                expected_participants
            ), "Knockout winner feeders must resolve only from actual stored results"
            assert len(result["result_fingerprint"]) == 64
            assert result["replay_available"] and result["total_rallies"] > 0
            knockout_results[match["match_id"]] = result
            context = request(
                "GET", simulation + "/match-replay/context?group_id="
                + quote(match["match_id"], safe=""),
            )
            assert context["verified"] is True and context["rng_rerun"] is False
            assert context["replay_source"] == "stored_authoritative_events"
            assert context["result_fingerprint"] == result["result_fingerprint"]
            assert context["event_id"] == event_id
            contexts[match["match_id"]] = context
        # No dependent match may appear in replay before its own real slot.
        if round_number < knockout_rounds:
            assert bracket["terminal_match_id"] not in {
                replay["match_id"] for replay in after_round["matches"]
            }

    final = knockout_results[bracket["terminal_match_id"]]
    final_context = contexts[bracket["terminal_match_id"]]
    remaining = request("GET", simulation + "/position")
    assert not ({match["match_id"] for match in bracket["matches"]} & set(
        remaining["eligible_match_ids"]
    )), "No completed knockout slot may become replay-eligible"
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
    if knockout_rounds == 2:
        policy_panel.get_by_label("Hybrid points for semifinal").fill("30")
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
    assert policy["knockout_stage_points"] == (
        [["champion", 100], ["finalist", 60], ["semifinal", 30]]
        if knockout_rounds == 2
        else [["champion", 100], ["finalist", 60]]
    )
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
    assert closure["total_ranking_points"] == (240 if knockout_rounds == 2 else 180), closure
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
    assert len(saved_matches) == 2 + (first_round_count * 2 - 1)
    assert len({m["match_id"] for m in saved_matches}) == len(saved_matches)
    assert {m["match_id"] for m in saved_matches if m["draw_type"] == "knockout"} == set(knockout_results)
    for match in bracket["matches"]:
        record = next(m for m in saved_matches if m["match_id"] == match["match_id"])
        replay = knockout_results[match["match_id"]]
        assert record["winner_player_id"] == replay["winner_player_id"]
        assert record["loser_player_id"] == replay["loser_player_id"]
        assert record["round_number"] == match["round_number"]
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
        "real_knockout_matches":len(knockout_results),
        "real_match_days":knockout_rounds + 1,
        "frozen_final_replay":final,
        "frozen_final_context":final_context,
        "all_knockout_replays":knockout_results,
        "all_knockout_contexts":contexts,
        "ranking_policy_authority":policy,
        "ranking_closure":closure,
        "result_published":True,
    }
