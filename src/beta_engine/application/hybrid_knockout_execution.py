"""Project frozen hybrid knockout authorities into canonical Simulation Slot execution."""

from __future__ import annotations

from beta_engine.domain.simulation_slots import (
    SimulationMatchEventPlan,
    WeekSimulationSchedule,
    WeekSimulationScheduleSlot,
)
from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthority,
)


def project_hybrid_knockout_bracket_to_plans(
    authority: TournamentHybridKnockoutBracketAuthority,
) -> tuple[SimulationMatchEventPlan, ...]:
    """Reuse the canonical match-plan contract for every hybrid knockout match."""

    return tuple(
        SimulationMatchEventPlan(
            group_id=match.match_id,
            event_id=authority.event_id,
            match_id=match.match_id,
            participant_sources=match.participant_sources,
        )
        for match in sorted(
            authority.matches,
            key=lambda value: (value.round_number, value.match_index),
        )
    )


def extend_week_schedule_with_hybrid_knockout(
    *,
    base_schedule: WeekSimulationSchedule,
    brackets: tuple[TournamentHybridKnockoutBracketAuthority, ...],
    reserved_nonmatch_ordinals: tuple[int, ...] = (),
) -> WeekSimulationSchedule:
    """Derive append-only post-group chronology without mutating the saved base schedule.

    Hybrid rounds begin after every already-frozen base Match Day. One elimination
    round occupies one new Match Day, guaranteeing a next-day minimum between
    feeder and dependent matches. Multiple hybrid events are deterministically
    ordered by event id within the same derived round day.
    """

    if not brackets:
        return base_schedule
    if base_schedule.schema_version != "week_simulation_schedule.v2":
        raise ValueError(
            "Hybrid knockout execution requires Week Simulation Schedule v2"
        )

    canonical_brackets = tuple(sorted(brackets, key=lambda value: value.event_id))
    if len({value.event_id for value in canonical_brackets}) != len(
        canonical_brackets
    ):
        raise ValueError("Hybrid knockout schedule contains duplicate event authority")
    if any(
        (value.run_id, value.branch_id)
        != (base_schedule.run_id, base_schedule.branch_id)
        for value in canonical_brackets
    ):
        raise ValueError("Hybrid knockout bracket scope differs from Week Schedule")

    base_group_ids = {
        group_id
        for slot in base_schedule.slots
        for group_id in slot.group_ids
    }
    hybrid_group_ids = {
        match.match_id
        for authority in canonical_brackets
        for match in authority.matches
    }
    overlap = base_group_ids & hybrid_group_ids
    if overlap:
        raise ValueError(
            "Hybrid knockout match identity overlaps frozen base Week Schedule"
        )

    max_base_day = max(
        slot.match_day_ordinal or 0 for slot in base_schedule.slots
    )
    next_global_ordinal = max(slot.ordinal for slot in base_schedule.slots) + 1
    reserved = set(reserved_nonmatch_ordinals)

    extension_slots: list[WeekSimulationScheduleSlot] = []
    max_round = max(authority.round_count for authority in canonical_brackets)
    for round_number in range(1, max_round + 1):
        round_matches = [
            (authority, match)
            for authority in canonical_brackets
            for match in authority.matches
            if match.round_number == round_number
        ]
        round_matches.sort(
            key=lambda item: (item[0].event_id, item[1].match_index, item[1].match_id)
        )
        for match_order, (authority, match) in enumerate(round_matches, start=1):
            while next_global_ordinal in reserved:
                next_global_ordinal += 1
            extension_slots.append(
                WeekSimulationScheduleSlot(
                    ordinal=next_global_ordinal,
                    group_ids=(match.match_id,),
                    match_day_ordinal=max_base_day + round_number,
                    match_order=match_order,
                    event_id=authority.event_id,
                    draw_phase="main",
                    round_number=round_number,
                )
            )
            next_global_ordinal += 1

    return WeekSimulationSchedule(
        schema_version="week_simulation_schedule.v2",
        run_id=base_schedule.run_id,
        branch_id=base_schedule.branch_id,
        week=base_schedule.week,
        slots=tuple((*base_schedule.slots, *extension_slots)),
    )
