"""Focused driver integration for post-group hybrid knockout execution."""

from types import SimpleNamespace

import pytest

import beta_engine.application.authoritative_run_simulation_driver as driver_module
from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    SimulationMatchEventPlan,
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


def frozen_bracket():
    entrants = TournamentHybridKnockoutEntrantsAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="entrants",
        topology_authority_fingerprint=fp("a"),
        group_standings_authority_fingerprint=fp("b"),
        first_round_matches=(
            TournamentHybridKnockoutMatchEntrants(
                match_id="event:hybrid:knockout:first:M1",
                match_index=1,
                top_source=TournamentGroupCrossingSource(
                    group_index=1, finishing_position=1
                ),
                top_player_id="A",
                bottom_source=TournamentGroupCrossingSource(
                    group_index=2, finishing_position=2
                ),
                bottom_player_id="D",
            ),
        ),
    )
    return TournamentHybridKnockoutBracketBuilder.build(
        entrants=entrants,
        command_id="bracket",
    )


@pytest.mark.pr_critical
def test_driver_execution_schedule_appends_frozen_hybrid_bracket_without_rewriting_base(
    monkeypatch,
):
    driver = object.__new__(AuthoritativeRunSimulationDriver)
    week = RankingWeek(season_index=0, week=8)
    base = WeekSimulationSchedule(
        schema_version="week_simulation_schedule.v2",
        run_id="run",
        branch_id="branch",
        week=week,
        slots=(
            WeekSimulationScheduleSlot(
                ordinal=1,
                group_ids=("group-match",),
                match_day_ordinal=1,
                match_order=1,
                event_id="event",
                draw_phase="group",
                round_number=1,
            ),
        ),
    )
    bracket = frozen_bracket()

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_hybrid_knockout_brackets_for_week",
        lambda self, session, **kwargs: (
            (SimpleNamespace(event_id="event"), bracket),
        ),
    )
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_entry_slot_ordinals",
        lambda self, session, run_id, branch_id, week: (),
    )
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_wc_slot_ordinals",
        lambda self, session, run_id, branch_id, week: (),
    )

    effective = driver._execution_schedule(
        None,
        run_id="run",
        branch_id="branch",
        week=week,
        base_schedule=base,
    )

    assert effective is not None
    assert base.slots == (
        WeekSimulationScheduleSlot(
            ordinal=1,
            group_ids=("group-match",),
            match_day_ordinal=1,
            match_order=1,
            event_id="event",
            draw_phase="group",
            round_number=1,
        ),
    )
    assert tuple(slot.group_ids[0] for slot in effective.slots) == (
        "group-match",
        bracket.terminal_match_id,
    )
    assert effective.slots[-1].match_day_ordinal == 2


@pytest.mark.pr_critical
def test_driver_hybrid_match_context_uses_bracket_source_and_shared_match_format(
    monkeypatch,
):
    driver = object.__new__(AuthoritativeRunSimulationDriver)
    bracket = frozen_bracket()
    frozen_match = bracket.matches[0]
    event = SimulationMatchEventPlan(
        group_id=frozen_match.match_id,
        event_id="event",
        match_id=frozen_match.match_id,
        participant_sources=frozen_match.participant_sources,
    )
    slot = object()
    stored_plan = SimpleNamespace(match_events=(event,))

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id: SimpleNamespace(
            current_slot_id="slot-2"
        ),
    )
    monkeypatch.setattr(
        driver_module.AuthoritativeSlotMatchExecutor,
        "_load_plan",
        staticmethod(lambda value: stored_plan),
    )

    class FakeGroupScheduleStore:
        def __init__(self, session):
            pass

        def get(self, **kwargs):
            return None

    class FakeBracketStore:
        def __init__(self, session):
            pass

        def get(self, **kwargs):
            return bracket

    monkeypatch.setattr(
        driver_module,
        "TournamentGroupMatchScheduleAuthorityStore",
        FakeGroupScheduleStore,
    )
    monkeypatch.setattr(
        driver_module,
        "TournamentHybridKnockoutBracketAuthorityStore",
        FakeBracketStore,
    )

    class FakeSession:
        def get(self, model, key):
            return slot

    command = SimpleNamespace(
        run_id="run",
        branch_id="branch",
        expected_week=RankingWeek(season_index=0, week=8),
    )
    result = driver._group_execution_context(
        FakeSession(),
        command,
        packages=(),
        group_id=frozen_match.match_id,
    )

    assert result[3] == "event"
    assert result[4] == ("A", "D")
    assert result[5] is None
