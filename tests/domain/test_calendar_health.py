"""Calendar Health boundaries are tested without manufacturing sporting progression."""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_health import (
    CalendarHealthEditEvidence,
    CalendarHealthOrigin,
    CalendarHealthProfile,
    CalendarHealthRecord,
    CalendarHealthState,
    carry_calendar_health_forward,
)

pytestmark = pytest.mark.pr_critical


def week(clock, ordinal):
    p = clock.position_at_ordinal(ordinal)
    return RunWeekPosition(
        calendar=clock, season_index=p.season_index, week=p.season_week
    )


def state(clock, ordinal=0, records=None):
    return CalendarHealthState(
        run_id="run",
        branch_id="branch",
        week=week(clock, ordinal),
        players=(CalendarHealthProfile(player_id="p1", records=records or ()),),
        source_initial_world_fingerprint="a" * 64,
        origin=CalendarHealthOrigin(
            baseline_fingerprint="b" * 64,
            command_id="baseline",
            request_fingerprint="c" * 64,
            initialization_policy="fresh_without_history.v1",
            audit_label="Admin",
            audit_reason="Fresh explicit baseline",
        ),
        admin_edits=(
            CalendarHealthEditEvidence(
                command_id="edit",
                request_fingerprint="d" * 64,
                before_state_fingerprint="b" * 64,
                source_run_id="run",
                source_branch_id="branch",
                player_id="p1",
                mode="current_state_correction",
                audit_label="Admin",
                audit_reason="Known facts",
            ),
        ),
        stage_provenance="explicit-test-facts",
    )


def record(**updates):
    return CalendarHealthRecord(
        **dict(
            dict(
                record_id="injury",
                kind="Injury",
                condition_key="ankle",
                lifecycle="Active",
                severity=25,
                affected_domains=("movement",),
                started_before_run=True,
                provenance="Known pre-Run fact",
                recovery_window_min_weeks=2,
                recovery_window_max_weeks=6,
            ),
            **updates,
        )
    )


@pytest.mark.parametrize(
    "clock",
    [
        RunCalendar(52, 35, 2030, 3),
        RunCalendar(80, 80, 2100, 3),
        RunCalendar(1, 1, 0, 3),
    ],
)
def test_fact_carry_across_calendar_year_and_season_keeps_exact_weekly_windows(clock):
    first = state(clock, records=(record(),))
    current = first
    for ordinal in range(1, clock.weeks_per_year + 1):
        after = carry_calendar_health_forward(
            current, target=week(clock, ordinal), target_player_ids=("p1",)
        )
        assert after.predecessor_fingerprint == current.fingerprint
        assert after.players == first.players
        assert after.origin == first.origin and after.admin_edits == first.admin_edits
        assert after.players[0].records[0].recovery_window_max_weeks == 6
        current = after
    assert (current.week.season_index, current.week.week) == (1, 1)
    assert current.week.calendar_position.calendar_year == clock.start_year + 1
    assert current.week.calendar_position.year_week == clock.season_start_year_week
    assert CalendarHealthState.model_validate_json(current.model_dump_json()) == current


def test_w80_dates_after_week61_and_year_boundary_are_actual_facts():
    c = RunCalendar(80, 80, 0, 3)
    rec = record(
        started_before_run=False,
        onset_week=week(c, 61),
        recovered_week=week(c, 80),
        lifecycle="Recovered",
        severity=0,
    )
    s = state(c, 80, (rec,))
    assert s.players[0].records[0].onset_week.week == 62
    assert s.players[0].records[0].recovered_week.season_index == 1
    assert s.week.calendar_position.calendar_year == 1
    assert week(c, 1).calendar_position.calendar_year == 1
    assert week(c, 1).calendar_position.year_week == 1
    assert s.week.ordinal == 80


def test_reject_calendar_alias_future_reversed_time_and_contradictory_severity():
    c = RunCalendar(52, 35, 2030, 3)
    foreign = RunCalendar(80, 35, 2030, 3)
    for rec in [
        record(started_before_run=False, onset_week=week(foreign, 0)),
        record(started_before_run=False, onset_week=week(c, 1)),
    ]:
        with pytest.raises(ValueError, match="foreign calendar|future date"):
            state(c, records=(rec,))
    with pytest.raises(ValueError, match="precede"):
        record(
            started_before_run=False,
            onset_week=week(c, 52),
            recovered_week=week(c, 51),
            lifecycle="Recovered",
            severity=0,
        )
    with pytest.raises(ValueError, match="zero acute"):
        record(lifecycle="Recovered")
    with pytest.raises(ValueError, match="same Run calendar"):
        record(
            started_before_run=False,
            onset_week=week(c, 0),
            recovered_week=week(foreign, 1),
            lifecycle="Recovered",
            severity=0,
        )
    for target in [week(foreign, 1), week(c, 2)]:
        with pytest.raises(ValueError, match="matching calendar"):
            carry_calendar_health_forward(
                state(c), target=target, target_player_ids=("p1",)
            )


def test_recurrence_order_and_horizon_are_not_modulo_61():
    c = RunCalendar(80, 1, 0, 3)
    source = record(
        record_id="a",
        started_before_run=False,
        onset_week=week(c, 61),
        recovered_week=week(c, 79),
        lifecycle="Recovered",
        severity=0,
    )
    recurrence = record(
        record_id="b",
        started_before_run=False,
        onset_week=week(c, 80),
        recurrence_of_record_id="a",
    )
    assert len(state(c, 80, (source, recurrence)).players[0].records) == 2
    for earlier in [
        dict(onset_week=week(c, 60)),
        dict(onset_week=week(c, 78)),
        dict(onset_week=None, started_before_run=True),
    ]:
        with pytest.raises(ValueError, match="precede"):
            CalendarHealthProfile(
                player_id="p1",
                records=(
                    source,
                    record(
                        record_id="b",
                        recurrence_of_record_id="a",
                        started_before_run=False,
                        onset_week=week(c, 80),
                    ).model_copy(update=earlier),
                ),
            )
    for index, w in [(3, 1), (0, 81)]:
        with pytest.raises(ValueError):
            RunWeekPosition(calendar=c, season_index=index, week=w)
    with pytest.raises(ValueError):
        carry_calendar_health_forward(state(c), target=week(c, 1), target_player_ids=())
