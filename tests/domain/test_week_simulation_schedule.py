from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    WeekSimulationSchedule,
    WeekSimulationScheduleSlot,
    fingerprint,
)


@pytest.mark.pr_critical
def test_week_schedule_v1_fingerprint_stays_historically_identical():
    week = RankingWeek(season_index=2, week=17)
    schedule = WeekSimulationSchedule(
        schema_version="week_simulation_schedule.v1",
        run_id="run",
        branch_id="branch",
        week=week,
        slots=(
            WeekSimulationScheduleSlot(
                ordinal=1,
                group_ids=("g1", "g2"),
            ),
            WeekSimulationScheduleSlot(
                ordinal=2,
                group_ids=("g3",),
            ),
        ),
    )

    historical_payload = {
        "schema_version": "week_simulation_schedule.v1",
        "run_id": "run",
        "branch_id": "branch",
        "week": week.model_dump(mode="json"),
        "slots": [
            {"ordinal": 1, "group_ids": ["g1", "g2"]},
            {"ordinal": 2, "group_ids": ["g3"]},
        ],
    }
    assert schedule.fingerprint == fingerprint(historical_payload)


@pytest.mark.pr_critical
def test_week_schedule_v2_requires_sequential_single_match_global_slots():
    week = RankingWeek(season_index=2, week=17)

    with pytest.raises(
        ValueError,
        match="exactly one competitive group",
    ):
        WeekSimulationSchedule(
            schema_version="week_simulation_schedule.v2",
            run_id="run",
            branch_id="branch",
            week=week,
            slots=(
                WeekSimulationScheduleSlot(
                    ordinal=1,
                    group_ids=("g1", "g2"),
                    match_day_ordinal=1,
                    match_order=1,
                    event_id="event",
                    draw_phase="main",
                    round_number=1,
                ),
            ),
        )

    schedule = WeekSimulationSchedule(
        schema_version="week_simulation_schedule.v2",
        run_id="run",
        branch_id="branch",
        week=week,
        slots=(
            WeekSimulationScheduleSlot(
                ordinal=1,
                group_ids=("g1",),
                match_day_ordinal=1,
                match_order=1,
                event_id="event",
                draw_phase="main",
                round_number=1,
            ),
            WeekSimulationScheduleSlot(
                ordinal=2,
                group_ids=("g2",),
                match_day_ordinal=1,
                match_order=2,
                event_id="event",
                draw_phase="main",
                round_number=1,
            ),
            WeekSimulationScheduleSlot(
                ordinal=3,
                group_ids=("g3",),
                match_day_ordinal=2,
                match_order=1,
                event_id="event",
                draw_phase="main",
                round_number=2,
            ),
        ),
    )
    assert schedule.schema_version == "week_simulation_schedule.v2"
    assert [slot.match_day_ordinal for slot in schedule.slots] == [1, 1, 2]
    assert [slot.match_order for slot in schedule.slots] == [1, 2, 1]
