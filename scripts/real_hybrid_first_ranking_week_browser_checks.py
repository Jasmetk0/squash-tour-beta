"""First real hybrid Tournament -> first eligible published Official Ranking.

Production Chromium clicks the actual Admin Review/Confirm/Save surfaces.
No mocked match results, manually inserted ranking awards or direct database writes.
Tests one genuine Run-owned source at the zero-based Week-1 -> Week-2 boundary.
"""
from __future__ import annotations

from urllib.parse import quote


def publish_first_hybrid_official_week(
    *, request, page, run_id: str, branch_id: str, run_url: str,
    root_scope: str, event_id: str, hybrid: dict, artifacts,
) -> dict:
    from playwright.sync_api import expect

    viewer = "/viewer/runs/" + quote(run_id, safe="") + "/rankings"
    simulation = root_scope + "/authoritative-simulation"
    transition = root_scope + "/week-transitions"
    source = hybrid["ranking_closure"]
    champion_id = hybrid["frozen_final_replay"]["winner_player_id"]
    finalist_id = hybrid["frozen_final_replay"]["loser_player_id"]
    group_winners = {
        group["rows"][0]["player_id"]
        for group in hybrid["group_authority"]["groups"]
    }
    result = hybrid["archived_edition"]["published_result"]
    explicit_policy = hybrid["ranking_policy_authority"]
    finish_points = dict(explicit_policy["knockout_stage_points"])
    assert len(result["players"]) == 4
    assert {p["player_id"] for p in result["players"]} == {
        row["player_id"]
        for group in hybrid["group_authority"]["groups"]
        for row in group["rows"]
    }
    expected_points = {
        p["player_id"]:
            p["played_group_wins"] * explicit_policy["played_group_win_points"]
            + finish_points[p["knockout_reached_stage"]]
        for p in result["players"]
    }
    assert result["champion_player_id"] == champion_id
    assert result["finalist_player_id"] == finalist_id
    assert sum(expected_points.values()) == source["total_ranking_points"]
    assert source["total_ranking_points"] in (180, 240)
    if hybrid["bracket_authority"]["round_count"] == 1:
        assert group_winners == {champion_id, finalist_id}
        assert expected_points[champion_id] == 110
        assert expected_points[finalist_id] == 70
    else:
        assert hybrid["bracket_authority"]["round_count"] == 2
        assert sorted(p["knockout_reached_stage"] for p in result["players"]) == [
            "champion", "finalist", "semifinal", "semifinal"
        ]

    # Closing a real tournament at zero-based ordinal 0 cannot publish an
    # Official Ranking immediately: the result's first eligible ordinal is 1.
    initial = request("GET", viewer + "/current")
    original_history = request("GET", viewer + "/history")
    assert initial["week_ordinal"] == original_history["public_head_ordinal"] == 0
    assert initial["week"] == 1 and initial["season_index"] == 0
    assert original_history["publication_count"] == 1
    assert all(row["points"] == 0 for row in initial["rows"])
    request("GET", viewer + "/history/1", status=409)
    request("POST", transition + "/derived/preview", {
        "command_id": "hybrid-must-not-publish-before-authority",
    }, status=409)

    position = request("GET", simulation + "/position")
    assert position["current_week"] == {"season_index": 0, "week": 1}
    assert not position["week_ready_for_transition"]

    # The operator explicitly reviews, confirms and SAVES the canonical
    # ranking authority. This reuses the production Admin UI and source inputs.
    page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    expect(page.get_by_role(
        "button", name="Review derived Ranking Transition Authority",
    )).to_be_visible(timeout=30000)
    page.get_by_label("Operator label", exact=True).fill("Hybrid browser acceptance")
    page.get_by_label("Authority reason", exact=True).fill(
        "First eligible Week-2 ranking from completed Run-owned hybrid source"
    )
    page.get_by_role("button", name="Review derived Ranking Transition Authority", exact=True).click()
    expect(page.get_by_role(
        "button", name="Confirm reviewed Ranking Transition Authority", exact=True,
    )).to_be_visible(timeout=30000)
    expect(page.get_by_text("Target roster")).to_be_visible()
    page.get_by_role("button", name="Confirm reviewed Ranking Transition Authority", exact=True).click()
    expect(page.get_by_role(
        "button", name="Save Ranking Transition Authority",
    )).to_be_enabled(timeout=30000)
    page.get_by_role("button", name="Save Ranking Transition Authority", exact=True).click()
    expect(page.get_by_role(
        "button", name="Save Ranking Transition Authority", exact=True,
    )).to_have_count(0, timeout=30000)

    ready = request("GET", simulation + "/position")
    assert ready["week_ready_for_transition"], ready
    # The exact production preview includes one frozen source binding, not
    # separate points for group wins and the knockout final.
    reviewed = request("POST", transition + "/derived/preview", {
        "command_id": "hybrid-first-eligible-ranking-preview",
    })
    command = reviewed["command"]
    assert command["completed_week"] == {"season_index": 0, "week": 1}
    assert command["target_week"] == {"season_index": 0, "week": 2}
    assert len(command["tournaments"]) == 1, command["tournaments"]
    binding = command["tournaments"][0]
    assert binding["event_id"] == binding["edition_id"] == event_id
    assert binding["completed_week"] == command["completed_week"]
    assert binding["first_publication_week"] == command["target_week"]
    assert binding["expected_result_fingerprint"] == source["result_fingerprint"]
    assert binding["expected_award_fingerprint"] == source["award_fingerprint"]
    expected_fingerprint = reviewed["result"]["official_ranking_fingerprint"]

    # A read-only preview must not publish the next week.
    assert request("GET", viewer + "/history") == original_history
    page.get_by_role("button", name="Review derived Week Transition", exact=True).click()
    expect(page.get_by_role(
        "button", name="Confirm reviewed Week Transition", exact=True,
    )).to_be_visible(timeout=30000)
    expect(page.get_by_text("Tournament bindings")).to_be_visible()
    page.get_by_role("button", name="Confirm reviewed Week Transition", exact=True).click()
    expect(page.get_by_role(
        "button", name="Save transitioned week",
    )).to_be_enabled(timeout=30000)
    page.get_by_role("button", name="Save transitioned week", exact=True).click()
    # On successful Save the component clears its committed/review state;
    # unlike a network-idle heuristic, removal of the review-only Save action
    # establishes that the exact confirmed Save finished.
    expect(page.get_by_role(
        "button", name="Save transitioned week", exact=True,
    )).to_have_count(0, timeout=30000)

    # Read the actual public Saved Revision, not the unpublished candidate
    # or working-draft ranking. One player has one composed Edition result.
    published = request("GET", viewer + "/current")
    historical = request("GET", viewer + "/history")
    week_one = request("GET", viewer + "/history/0")
    week_two = request("GET", viewer + "/history/1")
    assert published == week_two
    assert published["week_ordinal"] == historical["public_head_ordinal"] == 1
    assert (published["season_index"], published["week"]) == (0, 2)
    assert published["snapshot_fingerprint"] == expected_fingerprint
    assert historical["publication_count"] == 2
    assert [entry["week_ordinal"] for entry in historical["publications"]] == [1, 0]
    assert week_one == initial, "Week-1 historical publication was rewritten"
    assert published["best_n"] == initial["best_n"]
    # The initial World generated 64 players, but published ranking membership
    # follows Tour entry/retirement at each week. Never assume row counts stay
    # constant across a genuine Week Transition.
    assert published["row_count"] == len(published["rows"])
    assert initial["row_count"] == len(initial["rows"])
    old_points = {row["player_id"]: row["points"] for row in initial["rows"]}
    new_points = {row["player_id"]: row["points"] for row in published["rows"]}
    assert champion_id in new_points and finalist_id in new_points
    deltas = {
        pid: new_points.get(pid, 0) - old_points.get(pid, 0)
        for pid in old_points.keys() | new_points.keys()
    }
    for player_id, points in expected_points.items():
        assert deltas.get(player_id) == points, (player_id, points, deltas)
    assert all(delta == 0 for pid, delta in deltas.items()
               if pid not in expected_points)
    assert sum(deltas.values()) == source["total_ranking_points"]
    assert len([delta for delta in deltas.values() if delta > 0]) == (
        4 if hybrid["bracket_authority"]["round_count"] == 2 else 2
    )
    page.screenshot(
        path=str(artifacts / "hybrid-07-published-official-week2.png"),
        full_page=True,
    )
    branches = request("GET", "/run-branches?run_id=" + quote(run_id, safe=""))
    branch = next(item for item in branches["run_branches"]
                  if item["branch_id"] == branch_id)
    saved_head = branch["saved_head_revision_id"]
    assert saved_head and saved_head != hybrid["completed_saved_revision"]
    return {
        "official_week_2": published,
        "historical_week_1": week_one,
        "ranking_history": historical,
        "saved_week_2_revision": saved_head,
        "composed_ranking_deltas": deltas,
        "expected_ranking_fingerprint": expected_fingerprint,
    }
