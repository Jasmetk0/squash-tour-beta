"""Calendar-aware ranking/race point expiry, preserving legacy W61 outputs."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.engine import RankingRaceEngine
from beta_engine.domain.rankings.models import (
    CompletedTournamentPointsInput, RankingRaceReport,
    RunCalendarRankingRaceReport,
)

pytestmark = pytest.mark.pr_critical

TABLE = {"champion": 100, "finalist": 60}
ENGINE = RankingRaceEngine(point_distributions_by_ref={})


def event(season: int, week: int, *, name: str = "event", player: str = "p",
          placements: bool = True) -> CompletedTournamentPointsInput:
    return CompletedTournamentPointsInput(
        event_id=name, season=season, week=week, template_id="Test",
        point_distribution=TABLE,
        placements=[{"player_id": player, "finish": "CHAMPION"}] if placements else [],
    )


def report(calendar: RunCalendar, *, as_season: int, as_week: int,
           inputs: list[CompletedTournamentPointsInput],
           window_weeks: int | None = None):
    return ENGINE.build_report(
        completed_tournaments=inputs, as_of_season=as_season,
        as_of_week=as_week, target_season=as_season,
        run_calendar=calendar, window_weeks=window_weeks,
    )


@pytest.mark.parametrize("weeks", [52, 61, 80])
def test_exact_W_window_expiry_and_previous_season_boundary(weeks):
    clock = RunCalendar(weeks, 1, 2030, 4)
    inputs = [event(2030, weeks, name="previous"), event(2031, 1, name="current")]
    immediately_after = report(clock, as_season=2031, as_week=1, inputs=inputs)
    assert isinstance(immediately_after, RunCalendarRankingRaceReport)
    assert immediately_after.run_calendar == clock.to_metadata()
    assert immediately_after.ranking.window_weeks == weeks
    assert {x.event_id for x in immediately_after.ranking.standings[0].contributions} == {
        "previous", "current",
    }
    assert immediately_after.ranking.standings[0].ranking_points == 200

    # At exactly W elapsed weeks, the old result is excluded; W-1 stays valid.
    last_valid = report(clock, as_season=2031, as_week=weeks-1, inputs=inputs)
    assert {x.event_id for x in last_valid.ranking.standings[0].contributions} == {
        "previous", "current",
    }
    expired = report(clock, as_season=2031, as_week=weeks, inputs=inputs)
    assert [x.event_id for x in expired.ranking.standings[0].contributions] == ["current"]
    assert expired.ranking.standings[0].ranking_points == 100
    # Race remains limited to its target season, not a rolling W window.
    assert expired.race.standings[0].race_points == 100


def test_W52_result_from_first_week_expires_at_next_season_week_one():
    clock = RunCalendar.earth_default(start_year=2030, season_count=3)
    inputs = [event(2030, 1)]
    before = report(clock, as_season=2030, as_week=52, inputs=inputs)
    assert before.ranking.standings[0].ranking_points == 100
    after = report(clock, as_season=2031, as_week=1, inputs=inputs)
    assert after.ranking.standings == []
    assert after.point_awards[0].week == 1


def test_W80_supports_week_80_without_silent_modulo_or_61_week_expiry():
    clock = RunCalendar(80, 37, 2030, 3)
    inputs = [event(2030, 80, name="closing"), event(2031, 78, name="late")]
    at_78 = report(clock, as_season=2031, as_week=78, inputs=inputs)
    assert [x.week for x in at_78.point_awards] == [80, 78]
    assert at_78.ranking.standings[0].ranking_points == 200
    at_80 = report(clock, as_season=2031, as_week=80, inputs=inputs)
    assert at_80.ranking.standings[0].ranking_points == 100
    assert [x.event_id for x in at_80.ranking.standings[0].contributions] == ["late"]
    assert at_80.run_calendar["season_start_year_week"] == 37
    restored = RunCalendarRankingRaceReport.model_validate_json(at_80.model_dump_json())
    assert restored == at_80


def test_configured_window_is_not_confused_with_calendar_year_and_is_not_clamped():
    clock = RunCalendar.earth_default(start_year=2030, season_count=2)
    inputs = [event(2030, 50)]
    custom = report(clock, as_season=2031, as_week=50, inputs=inputs, window_weeks=53)
    default = report(clock, as_season=2031, as_week=50, inputs=inputs)
    assert custom.ranking.standings[0].ranking_points == 100
    assert default.ranking.standings == []
    assert custom.ranking.window_weeks == 53


def test_default_legacy_output_exactly_preserves_existing_report_schema():
    inputs = [event(2027, 61, name="old"), event(2028, 1, name="new")]
    baseline = ENGINE.build_report(
        completed_tournaments=inputs, as_of_season=2028, as_of_week=1,
        target_season=2028,
    )
    explicit_window = ENGINE.build_report(
        completed_tournaments=inputs, as_of_season=2028, as_of_week=1,
        target_season=2028, window_weeks=61,
    )
    assert type(baseline) is RankingRaceReport
    assert baseline.model_dump_json() == explicit_window.model_dump_json()
    assert "schema_version" not in baseline.model_dump()
    assert "run_calendar" not in baseline.model_dump()
    clock = RunCalendar.fax_default()
    with_calendar = report(clock, as_season=2028, as_week=1, inputs=inputs)
    assert baseline.ranking == with_calendar.ranking
    assert baseline.race == with_calendar.race
    assert baseline.point_awards == with_calendar.point_awards


@pytest.mark.parametrize("clock,bad_season,bad_week", [
    (RunCalendar(52, 1, 2030, 2), 2031, 53),
    (RunCalendar(80, 37, 2030, 2), 2031, 81),
    (RunCalendar(80, 37, 2030, 2), 2032, 1),
    (RunCalendar(80, 37, 2030, 2), 2029, 40),
])
def test_source_outside_actual_run_horizon_is_rejected(clock, bad_season, bad_week):
    bad = [event(bad_season, bad_week)]
    with pytest.raises(ValueError, match="season_index|season_week"):
        report(clock, as_season=2031, as_week=1, inputs=bad)
    with pytest.raises(ValueError, match="season_index|season_week"):
        ENGINE.resolve_point_awards(completed_tournaments=bad, run_calendar=clock)


def test_future_empty_event_cannot_leak_even_without_point_awards():
    clock = RunCalendar.earth_default(start_year=2030, season_count=2)
    with pytest.raises(ValueError, match="future"):
        report(clock, as_season=2030, as_week=10,
               inputs=[event(2030, 11, placements=False)])
    with pytest.raises(ValueError, match="future"):
        report(clock, as_season=2030, as_week=10,
               inputs=[event(2030, 11)])


@pytest.mark.parametrize("clock", [
    RunCalendar(52, 1, 2030, 2),
    RunCalendar(80, 37, 2030, 2),
])
def test_calendar_report_guards_target_horizon_and_positive_policy(clock):
    with pytest.raises(ValueError):
        ENGINE.build_report(
            completed_tournaments=[], as_of_season=2030, as_of_week=1,
            target_season=2040, run_calendar=clock,
        )
    with pytest.raises(ValueError):
        report(clock, as_season=2030, as_week=1, inputs=[], window_weeks=0)
    with pytest.raises(ValueError):
        ENGINE.build_report(
            completed_tournaments=[], as_of_season=2030, as_of_week=1,
            target_season=2030, run_calendar=clock, best_of_results=0,
        )


def test_unversioned_inputs_stay_fenced_at_W61_and_no_legacy_reinterpretation():
    future = event(2027, 62)
    with pytest.raises(ValueError, match="Legacy"):
        ENGINE.resolve_point_awards(completed_tournaments=[future])
    with pytest.raises(ValueError, match="Legacy"):
        ENGINE.build_report(
            completed_tournaments=[], as_of_season=2027, as_of_week=62,
            target_season=2027,
        )
    with pytest.raises(ValueError, match="versioned Run clock"):
        ENGINE.build_report(
            completed_tournaments=[], as_of_season=2000, as_of_week=1,
            target_season=2000, run_calendar=RunCalendar.legacy_fax(),
        )


def test_report_metadata_tampering_is_detected_by_calendar_validation():
    clock = RunCalendar(80, 37, 2030, 2)
    result = report(clock, as_season=2030, as_week=80, inputs=[event(2030, 80)])
    raw = result.model_dump(mode="json")
    raw["run_calendar"]["weeks_per_year"] = 52
    with pytest.raises(ValidationError):
        RunCalendarRankingRaceReport.model_validate(raw)


def test_extension_does_not_rewrite_historical_ranking_content():
    clock = RunCalendar.earth_default(start_year=2030, season_count=2)
    inputs = [event(2030, 50)]
    original = report(clock, as_season=2030, as_week=52, inputs=inputs)
    extended = report(clock.extend_to(4), as_season=2030, as_week=52, inputs=inputs)
    assert original.point_awards == extended.point_awards
    assert original.ranking == extended.ranking
    assert original.race == extended.race
    assert original.run_calendar["season_count"] == 2
    assert extended.run_calendar["season_count"] == 4


def test_serialized_calendar_report_rejects_future_award_even_if_metadata_is_valid():
    clock = RunCalendar(80, 37, 2030, 2)
    result = report(clock, as_season=2030, as_week=79, inputs=[event(2030, 79)])
    tampered = result.model_dump(mode="json")
    tampered["point_awards"][0]["week"] = 80
    with pytest.raises(ValidationError, match="future"):
        RunCalendarRankingRaceReport.model_validate(tampered)


def test_legacy_race_target_cannot_bypass_minimum_year_bound():
    with pytest.raises(ValueError, match="Legacy"):
        ENGINE.build_report(
            completed_tournaments=[], as_of_season=2027, as_of_week=1,
            target_season=0,
        )
