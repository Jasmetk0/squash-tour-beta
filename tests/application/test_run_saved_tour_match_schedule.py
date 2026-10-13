"""Exact immutable saved Week Simulation Schedule -> Edition Match Day evidence."""
import pytest

from beta_engine.application.run_saved_tour_match_schedule import (
    resolve_saved_tour_match_schedule,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    SimulationMatchEventPlan, SimulationSlotPlan,
    WeekSimulationSchedule, WeekSimulationScheduleSlot,
)

pytestmark = pytest.mark.pr_critical

WEEK = RankingWeek(season_index=2, week=17)


def _v2():
    return WeekSimulationSchedule(
        schema_version="week_simulation_schedule.v2",
        run_id="run", branch_id="original", week=WEEK,
        slots=(
            WeekSimulationScheduleSlot(
                ordinal=1, group_ids=("g-main",), match_day_ordinal=1,
                match_order=1, event_id="event", draw_phase="main", round_number=1,
            ),
            WeekSimulationScheduleSlot(
                ordinal=2, group_ids=("g-foreign",), match_day_ordinal=1,
                match_order=2, event_id="other", draw_phase="main", round_number=1,
            ),
            WeekSimulationScheduleSlot(
                ordinal=3, group_ids=("g-qual",), match_day_ordinal=2,
                match_order=1, event_id="event", draw_phase="qualification", round_number=2,
            ),
        ),
    )


def _plan():
    return SimulationSlotPlan(
        run_id="run", branch_id="original", week=WEEK, slot_id="slot-main",
        ordinal=1, group_ids=("g-main",),
        match_events=(SimulationMatchEventPlan(
            group_id="g-main", event_id="event", match_id="actual-match",
            direct_player_ids=("A", "B"),
        ),),
        slot_start_fingerprint="saved-checkpoint",
        provenance="real-immutable-plan",
    )


def _component(schedule=None, plan=None):
    schedule = schedule or _v2()
    return {
        "schedules": [{
            "run_id": "run", "branch_id": "original", "week_ordinal": WEEK.ordinal,
            "payload_json": schedule.model_dump_json(),
            "schedule_fingerprint": schedule.fingerprint,
        }],
        "slots": ([{
            "run_id": "run", "branch_id": "original",
            "week_ordinal": WEEK.ordinal, "slot_id": plan.slot_id,
            "slot_ordinal": plan.ordinal, "payload_json": plan.model_dump_json(),
            "plan_fingerprint": plan.fingerprint,
        }] if plan else []),
    }


def _resolve(component, event="event"):
    return resolve_saved_tour_match_schedule(
        component, run_id="run", branch_id="original", event_id=event,
        season_index=2, season_week=17,
    )


def test_saved_match_day_is_event_scoped_and_keeps_real_match_order():
    model = _resolve(_component(plan=_plan()))
    assert model.source == "saved_week_simulation_schedule.v2"
    assert model.revision_branch_id == "original"
    assert [(x.global_slot_ordinal, x.match_day_ordinal, x.match_order,
             x.draw_phase, x.round_number, x.match_id) for x in model.slots] == [
        (1, 1, 1, "main", 1, "actual-match"),
        (3, 2, 1, "qualification", 2, None),
    ]
    # The foreign event is in the same *global* schedule, but never leaks.
    other = _resolve(_component(plan=_plan()), event="other")
    assert [(x.global_slot_ordinal, x.match_id) for x in other.slots] == [(2, None)]
    assert _resolve(None) is None
    assert _resolve({}) is None
    assert _resolve(_component(), event="missing") is None


def test_historical_v1_schedule_never_invents_event_or_match_day():
    schedule = WeekSimulationSchedule(
        run_id="run", branch_id="original", week=WEEK,
        slots=(WeekSimulationScheduleSlot(ordinal=1, group_ids=("g-main",)),),
    )
    assert _resolve(_component(schedule=schedule)) is None


def test_wrong_owner_week_and_forged_schedule_fingerprint_fail_closed():
    original = _component(plan=_plan())
    foreign = {**original, "schedules": [{
        **original["schedules"][0], "branch_id": "current-selected-branch",
    }]}
    with pytest.raises(ValueError, match="another Run/Branch"):
        _resolve(foreign)
    stale = {**original, "schedules": [{
        **original["schedules"][0], "schedule_fingerprint": "0" * 64,
    }]}
    with pytest.raises(ValueError, match="provenance"):
        _resolve(stale)
    wrong_week = {**original, "schedules": [{
        **original["schedules"][0], "payload_json": _v2().model_copy(
            update={"week": RankingWeek(season_index=2, week=18)},
        ).model_dump_json(),
    }]}
    with pytest.raises(ValueError, match="week identity"):
        _resolve(wrong_week)


def test_saved_plan_never_forges_match_id_or_foreign_group_binding():
    original = _component(plan=_plan())
    wrong = {**original, "slots": [{
        **original["slots"][0], "branch_id": "other-branch",
    }]}
    with pytest.raises(ValueError, match="another Run/Branch"):
        _resolve(wrong)
    bad = {**original, "slots": [{
        **original["slots"][0], "plan_fingerprint": "0" * 64,
    }]}
    with pytest.raises(ValueError, match="provenance"):
        _resolve(bad)

    mismatched = _plan().model_copy(update={
        "match_events": (SimulationMatchEventPlan(
            group_id="g-main", event_id="another-edition", match_id="forged",
            direct_player_ids=("A", "B"),
        ),),
    })
    with pytest.raises(ValueError, match="event binding"):
        _resolve(_component(plan=mismatched))


def test_duplicate_saved_schedule_row_and_unstarted_slot_are_not_fabricated():
    component = _component()
    assert all(slot.match_id is None for slot in _resolve(component).slots)
    with pytest.raises(ValueError, match="ambiguous Schedule"):
        _resolve({**component, "schedules": component["schedules"] * 2})
