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
    original_match_ids: set[str],
) -> dict:
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

    # Tournament horizon is selected by the engine, never by a synthetic list.
    preview = request("GET", simulation + "/next-tournament/preview")
    assert preview["event_id"] == event_id, preview
    assert preview["horizon_slot_ordinals"], preview
    played = request("POST", simulation + "/simulate-next-tournament", {
        "command_id": "real-browser-completed-group-tournament",
        "expected_week": preview["week"],
        "expected_position_fingerprint": preview["expected_position_fingerprint"],
        "expected_revision_id": preview["expected_revision_id"],
    }, 201)
    assert played["event_id"] == event_id
    assert played["completed_slot_count"] == len(preview["horizon_slot_ordinals"])
    assert request("POST", simulation + "/simulate-next-tournament", {
        "command_id": "real-browser-completed-group-tournament",
        "expected_week": preview["week"],
        "expected_position_fingerprint": preview["expected_position_fingerprint"],
        "expected_revision_id": preview["expected_revision_id"],
    }, 201) == played

    # Group Standings is frozen by the actual receipt builder. If the official
    # rules cannot break a tie, the browser acceptance performs an explicit
    # separately audited Admin decision for the exact unresolved case.
    tie_audit = []
    for attempt in range(5):
        tie_state = request("GET", event_scope + "/group-standings/tie-resolution")
        case = tie_state["unresolved_case"]
        if case is None:
            break
        decision = request("POST", event_scope + "/group-standings/tie-resolution", {
            "command_id": f"real-group-admin-tie-{attempt}",
            "case_fingerprint": case["fingerprint"] if "fingerprint" in case
                else _case_fingerprint(case),
            "ordered_player_ids": case["player_ids"],
            "admin_reason": (
                "Explicit operator acceptance decision: maintain canonical "
                "player ID order for the otherwise unresolved evidence."
            ),
        }, 201)
        tie_audit.append(decision)
    else:
        raise AssertionError("More than five unresolved Admin tie cases")

    completed = request("POST", event_scope + "/group-standings/generate", {
        "command_id": "real-browser-completed-group-standings",
    }, 201)
    assert completed["groups"], completed
    assert len(completed["groups"]) == 1
    ranking = completed["groups"][0]["rows"]
    assert_real_played_group_table(ranking, check_schedule()["matches"])

    save_preview = request("GET", simulation + "/save/preview")
    assert save_preview["can_save"] is True, save_preview
    assert save_preview["has_unsaved_changes"] is True
    assert save_preview["saved_head_revision_id"] == old_revision
    saved_result = request("POST", simulation + "/save", {
        "expected_draft_version": save_preview["draft_version"],
        "expected_simulation_fingerprint": save_preview["simulation_fingerprint"],
    }, 201)
    final_revision = saved_result["saved_revision"]["revision_id"]
    assert final_revision != old_revision

    path = root_scope + "/tour/editions/" + quote(event_id, safe="")
    final = request("GET", path + "?revision_id="
                    + quote(final_revision, safe="") + "&season_index=0")
    final_group = final["group_standings"]
    assert final_group is not None, final
    assert final_group["authority_fingerprint"] == completed["authority_fingerprint"]
    assert len(final_group["groups"]) == 1
    assert final_group["groups"][0]["rows"] == ranking
    assert len(final_group["tie_decisions"]) == len(tie_audit)
    assert final["group_schedule"]["authority_fingerprint"] == (
        check_schedule()["authority_fingerprint"]
    )
    assert final["saved_revision_id"] == final_revision
    assert final["branch_id"] == final["revision_branch_id"] == branch_id
    assert final["run_id"] == run_id
    return {
        "revision": final_revision,
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
