"""Application coverage for projecting hybrid knockout into canonical match execution."""

import pytest

from beta_engine.application.hybrid_knockout_execution import (
    extend_week_schedule_with_hybrid_knockout,
    project_hybrid_knockout_bracket_to_plans,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    WeekSimulationSchedule,
    WeekSimulationScheduleSlot,
)
from beta_engine.domain.tournaments.format_authority import TournamentGroupCrossingSource
from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketBuilder,
)
from beta_engine.domain.tournaments.hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsAuthority,
    TournamentHybridKnockoutMatchEntrants,
)


def fp(char: str) -> str:
    return char * 64


def bracket():
    entrants = TournamentHybridKnockoutEntrantsAuthority(
        run_id="run",
        branch_id="branch",
        event_id="hybrid-event",
        generated_by_command_id="entrants",
        topology_authority_fingerprint=fp("a"),
        group_standings_authority_fingerprint=fp("b"),
        first_round_matches=(
            TournamentHybridKnockoutMatchEntrants(
                match_id="hybrid-event:hybrid:knockout:first:M1",
                match_index=1,
                top_source=TournamentGroupCrossingSource(
                    group_index=1, finishing_position=1
                ),
                top_player_id="A1",
                bottom_source=TournamentGroupCrossingSource(
                    group_index=2, finishing_position=2
                ),
                bottom_player_id="B2",
            ),
            TournamentHybridKnockoutMatchEntrants(
                match_id="hybrid-event:hybrid:knockout:first:M2",
                match_index=2,
                top_source=TournamentGroupCrossingSource(
                    group_index=2, finishing_position=1
                ),
                top_player_id="B1",
                bottom_source=TournamentGroupCrossingSource(
                    group_index=1, finishing_position=2
                ),
                bottom_player_id="A2",
            ),
        ),
    )
    return TournamentHybridKnockoutBracketBuilder.build(
        entrants=entrants,
        command_id="bracket",
    )


def base_schedule() -> WeekSimulationSchedule:
    return WeekSimulationSchedule(
        schema_version="week_simulation_schedule.v2",
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=10),
        slots=(
            WeekSimulationScheduleSlot(
                ordinal=1,
                group_ids=("group:A-B",),
                match_day_ordinal=1,
                match_order=1,
                event_id="hybrid-event",
                draw_phase="group",
                round_number=1,
            ),
            WeekSimulationScheduleSlot(
                ordinal=2,
                group_ids=("group:C-D",),
                match_day_ordinal=1,
                match_order=2,
                event_id="hybrid-event",
                draw_phase="group",
                round_number=1,
            ),
            WeekSimulationScheduleSlot(
                ordinal=3,
                group_ids=("group:E-F",),
                match_day_ordinal=2,
                match_order=1,
                event_id="hybrid-event",
                draw_phase="group",
                round_number=2,
            ),
        ),
    )


@pytest.mark.pr_critical
def test_hybrid_bracket_projects_to_existing_simulation_match_plan_contract():
    authority = bracket()
    plans = project_hybrid_knockout_bracket_to_plans(authority)

    assert tuple(plan.match_id for plan in plans) == tuple(
        match.match_id for match in authority.matches
    )
    assert plans[0].participant_sources == ("player:A1", "player:B2")
    assert plans[1].participant_sources == ("player:B1", "player:A2")
    assert plans[2].participant_sources == (
        "winner:hybrid-event:hybrid:knockout:first:M1",
        "winner:hybrid-event:hybrid:knockout:first:M2",
    )
    assert all(plan.direct_player_ids is None for plan in plans)


@pytest.mark.pr_critical
def test_hybrid_execution_schedule_appends_without_mutating_frozen_base_schedule():
    base = base_schedule()
    base_payload = base.canonical_payload()
    authority = bracket()

    effective = extend_week_schedule_with_hybrid_knockout(
        base_schedule=base,
        brackets=(authority,),
        reserved_nonmatch_ordinals=(4,),
    )

    assert base.canonical_payload() == base_payload
    assert effective.slots[: len(base.slots)] == base.slots

    added = effective.slots[len(base.slots) :]
    assert tuple(slot.ordinal for slot in added) == (5, 6, 7)
    assert tuple(slot.match_day_ordinal for slot in added) == (3, 3, 4)
    assert tuple(slot.match_order for slot in added) == (1, 2, 1)
    assert tuple(slot.round_number for slot in added) == (1, 1, 2)
    assert all(slot.draw_phase == "main" for slot in added)
    assert tuple(slot.group_ids[0] for slot in added) == tuple(
        match.match_id for match in authority.matches
    )


@pytest.mark.pr_critical
def test_hybrid_execution_schedule_rejects_v1_base_chronology():
    base = WeekSimulationSchedule(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=10),
        slots=(WeekSimulationScheduleSlot(ordinal=1, group_ids=("g1",)),),
    )
    with pytest.raises(ValueError, match="Schedule v2"):
        extend_week_schedule_with_hybrid_knockout(
            base_schedule=base,
            brackets=(bracket(),),
        )
