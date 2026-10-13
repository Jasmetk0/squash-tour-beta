"""Read-only exact Saved Revision simulation schedule for one Tournament Edition.

Only a v2 schedule identifies its own Event and Match Day, so a historical
v1 global schedule is intentionally not reinterpreted as an Edition schedule.
A slot's match_id is exposed only when backed by the saved Simulation Slot plan.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.domain.simulation_slots import SimulationSlotPlan, WeekSimulationSchedule


class RunSavedTourScheduledMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    global_slot_ordinal: int = Field(ge=1)
    match_day_ordinal: int = Field(ge=1)
    match_order: int = Field(ge=1)
    draw_phase: Literal["qualification", "main", "group"]
    round_number: int = Field(ge=1)
    group_id: str = Field(min_length=1)
    match_id: str | None = None


class RunSavedTourMatchSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["run_saved_tour_match_schedule.v1"] = (
        "run_saved_tour_match_schedule.v1"
    )
    source: Literal["saved_week_simulation_schedule.v2"] = (
        "saved_week_simulation_schedule.v2"
    )
    run_id: str
    revision_branch_id: str
    event_id: str
    season_index: int = Field(ge=0, le=49)
    season_week: int = Field(ge=1, le=61)
    week_schedule_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    slots: tuple[RunSavedTourScheduledMatch, ...]


def resolve_saved_tour_match_schedule(
    component: dict | None, *, run_id: str, branch_id: str,
    event_id: str, season_index: int, season_week: int,
) -> RunSavedTourMatchSchedule | None:
    if component is None:
        return None
    ordinal = season_index * 61 + season_week - 1
    rows = [
        row for row in component.get("schedules", ())
        if row.get("week_ordinal") == ordinal
    ]
    if not rows:
        return None
    if len(rows) != 1:
        raise ValueError("Saved Edition week has ambiguous Schedule authority")
    row = rows[0]
    if (row.get("run_id"), row.get("branch_id")) != (run_id, branch_id):
        raise ValueError("Saved Edition Schedule belongs to another Run/Branch")

    schedule = WeekSimulationSchedule.model_validate_json(row["payload_json"])
    if (
        (schedule.run_id, schedule.branch_id) != (run_id, branch_id)
        or (schedule.week.season_index, schedule.week.week)
        != (season_index, season_week)
        or schedule.week.ordinal != row["week_ordinal"]
        or schedule.fingerprint != row.get("schedule_fingerprint")
    ):
        raise ValueError("Saved Edition Schedule provenance or week identity differs")

    # v1 has only global Group slots and no Event/Match Day attribution. It
    # cannot be presented as an Edition-specific Match Day schedule.
    if schedule.schema_version == "week_simulation_schedule.v1":
        return None

    selected = [slot for slot in schedule.slots if slot.event_id == event_id]
    if not selected:
        return None

    # A saved execution plan can attach the real match_id. Never derive one
    # from ordinal, opponent, results, or the presentation order.
    plans = {}
    for plan_row in component.get("slots", ()):
        if plan_row.get("week_ordinal") != ordinal:
            continue
        if (plan_row.get("run_id"), plan_row.get("branch_id")) != (
            run_id, branch_id,
        ):
            raise ValueError("Saved Edition Simulation Slot belongs to another Run/Branch")
        plan = SimulationSlotPlan.model_validate_json(plan_row["payload_json"])
        if (
            (plan.run_id, plan.branch_id, plan.week.ordinal, plan.slot_id, plan.ordinal)
            != (run_id, branch_id, ordinal, plan_row["slot_id"], plan_row["slot_ordinal"])
            or plan.fingerprint != plan_row.get("plan_fingerprint")
        ):
            raise ValueError("Saved Edition Simulation Slot plan provenance differs")
        if plan.ordinal in plans:
            raise ValueError("Saved Edition Simulation Slot ordinal is ambiguous")
        plans[plan.ordinal] = plan

    projected = []
    seen_groups: set[str] = set()
    for slot in selected:
        group_id = slot.group_ids[0]  # canonical v2: exactly one group
        if group_id in seen_groups:
            raise ValueError("Saved Edition Match Day has duplicate group")
        seen_groups.add(group_id)
        plan = plans.get(slot.ordinal)
        match_id = None
        if plan is not None:
            if plan.group_ids != slot.group_ids:
                raise ValueError("Saved Edition Schedule differs from saved Simulation Slot")
            bound = [e for e in plan.match_events if e.group_id == group_id]
            if len(bound) != 1 or bound[0].event_id != event_id:
                raise ValueError("Saved Edition Schedule match event binding differs")
            match_id = bound[0].match_id
        projected.append(RunSavedTourScheduledMatch(
            global_slot_ordinal=slot.ordinal,
            match_day_ordinal=slot.match_day_ordinal,
            match_order=slot.match_order,
            draw_phase=slot.draw_phase,
            round_number=slot.round_number,
            group_id=group_id,
            match_id=match_id,
        ))
    return RunSavedTourMatchSchedule(
        run_id=run_id, revision_branch_id=branch_id, event_id=event_id,
        season_index=season_index, season_week=season_week,
        week_schedule_fingerprint=schedule.fingerprint,
        slots=tuple(sorted(
            projected, key=lambda match: (
                match.match_day_ordinal, match.match_order, match.global_slot_ordinal,
            )
        )),
    )
