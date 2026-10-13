"""Read-only frozen standings: points, W/O, provenance and audited tie reasons."""
import pytest

from beta_engine.application.run_saved_tour_group_standings import (
    resolve_saved_tour_group_standings,
)
from beta_engine.application.run_saved_tour_group_schedule import RunSavedTourGroupSchedule
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsBuilder, TournamentGroupStandingsUnresolvedTie,
    TournamentGroupTieResolutionDecision,
)
from beta_engine.domain.tournaments.group_tie_resolution_authority import (
    TournamentGroupTieResolutionAuthority,
)
from beta_engine.domain.tournaments.walkover_authority import TournamentWalkoverResult
from tests.domain.test_tournament_group_standings_authority import (
    schedule_three, played, receipt, fp,
)

pytestmark = pytest.mark.pr_critical


def _base(with_tie=False):
    schedule = schedule_three()
    if with_tie:
        results = (
            played("A-B", "A", "B", "A", (2, 1),
                   set_points=((11, 9), (11, 9), (11, 9))),
            played("A-C", "A", "C", "C", (1, 2),
                   set_points=((11, 9), (11, 9), (11, 9))),
            played("B-C", "B", "C", "B", (2, 1),
                   set_points=((11, 9), (11, 9), (11, 9))),
        )
        receipts = tuple(receipt(schedule, r, str(i))
                         for i, r in enumerate(results, 1))
        with pytest.raises(TournamentGroupStandingsUnresolvedTie) as unresolved:
            TournamentGroupStandingsBuilder.build(
                schedule=schedule, receipts=receipts, command_id="standings",
            )
        decision = TournamentGroupTieResolutionDecision(
            case=unresolved.value.case, ordered_player_ids=("C", "A", "B"),
            admin_reason="Exact evidence manually reviewed.",
        )
        authority = TournamentGroupStandingsBuilder.build(
            schedule=schedule, receipts=receipts, command_id="standings",
            admin_tie_resolutions=(decision,),
        )
        tie = TournamentGroupTieResolutionAuthority(
            run_id="run", branch_id="branch", event_id="event",
            resolved_by_command_id="tie-command",
            group_match_schedule_fingerprint=schedule.fingerprint,
            decision=decision,
        )
        ties = [{
            "run_id": "run", "branch_id": "branch", "event_id": "event",
            "command_id": "tie-command",
            "case_fingerprint": tie.case.fingerprint,
            "authority_fingerprint": tie.fingerprint,
            "group_match_schedule_fingerprint": schedule.fingerprint,
            "payload_json": tie.model_dump_json(),
        }]
    else:
        receipts = (
            TournamentGroupStandingsBuilder.receipt_from_result(
                scheduled_match=schedule.matches[0],
                result=TournamentWalkoverResult(
                    match_id="A-B", winner_player_id="A", loser_player_id="B",
                ), result_fingerprint=fp("1"),
            ),
            receipt(schedule, played("A-C", "A", "C", "A", (2, 0)), "2"),
            receipt(schedule, played("B-C", "B", "C", "C", (0, 2)), "3"),
        )
        authority = TournamentGroupStandingsBuilder.build(
            schedule=schedule, receipts=receipts, command_id="standings",
        )
        ties = []
    group_schedule = RunSavedTourGroupSchedule(
        run_id="run", revision_branch_id="branch", event_id="event",
        authority_fingerprint=schedule.fingerprint,
        group_count=1, group_size=3, match_day_count=3, matches=(),
    )
    row = {
        "run_id": "run", "branch_id": "branch", "event_id": "event",
        "command_id": authority.generated_by_command_id,
        "authority_fingerprint": authority.fingerprint,
        "group_match_schedule_fingerprint": schedule.fingerprint,
        "group_rules_policy_fingerprint": schedule.group_rules_policy_fingerprint,
        "payload_json": authority.model_dump_json(),
    }
    return {"group_standings": [row], "group_tie_resolutions": ties}, group_schedule


def _read(component, schedule):
    return resolve_saved_tour_group_standings(
        component, run_id="run", branch_id="branch",
        event_id="event", group_schedule=schedule,
    )


def test_frozen_group_standings_show_true_wins_points_and_walkovers():
    component, schedule = _base()
    result = _read(component, schedule)
    assert result.source == "saved_tournament_group_standings_authority"
    assert result.group_schedule_fingerprint == schedule.authority_fingerprint
    assert len(result.groups) == 1
    players = {row.player_id: row for row in result.groups[0].rows}
    assert [row.player_id for row in result.groups[0].rows] == ["A", "C", "B"]
    assert players["A"].wins == 2 and players["A"].group_points == 8
    assert players["A"].walkovers_received == 1
    assert players["A"].played_matches == 1
    assert players["B"].walkovers_conceded == 1
    assert result.tie_decisions == ()
    assert _read(None, schedule) is None
    assert _read({}, schedule) is None


def test_audited_admin_tie_order_and_reason_are_not_guessed():
    component, schedule = _base(with_tie=True)
    result = _read(component, schedule)
    assert [r.player_id for r in result.groups[0].rows] == ["C", "A", "B"]
    assert len(result.tie_decisions) == 1
    decision = result.tie_decisions[0]
    assert decision.ordered_player_ids == ("C", "A", "B")
    assert decision.admin_reason == "Exact evidence manually reviewed."
    assert decision.case_fingerprint == component["group_tie_resolutions"][0]["case_fingerprint"]
    with pytest.raises(ValueError, match="do not match frozen standings"):
        _read({**component, "group_tie_resolutions": []}, schedule)


def test_stale_foreign_missing_or_duplicate_authority_fails_closed():
    component, schedule = _base(with_tie=True)
    saved = component["group_standings"][0]
    tie = component["group_tie_resolutions"][0]
    with pytest.raises(ValueError, match="another Run/Branch"):
        _read({**component, "group_standings": [{**saved, "branch_id": "fork"}]}, schedule)
    with pytest.raises(ValueError, match="Ambiguous"):
        _read({**component, "group_standings": [saved, saved]}, schedule)
    with pytest.raises(ValueError, match="lack their saved"):
        _read(component, None)
    with pytest.raises(ValueError, match="provenance"):
        _read({**component, "group_standings": [{
            **saved, "authority_fingerprint": "0" * 64,
        }]}, schedule)
    with pytest.raises(ValueError, match="another Run/Branch"):
        _read({**component, "group_tie_resolutions": [{
            **tie, "branch_id": "fork",
        }]}, schedule)
    with pytest.raises(ValueError, match="duplicated"):
        _read({**component, "group_tie_resolutions": [tie, tie]}, schedule)
    with pytest.raises(ValueError, match="lack group standings"):
        _read({"group_tie_resolutions": [tie]}, schedule)
