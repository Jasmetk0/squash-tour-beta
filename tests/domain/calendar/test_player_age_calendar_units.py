"""Run-year units: 18 Earth years remain 18 years, never 18*52/61."""

from fractions import Fraction

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    birth_year_for_age_at_calendar_position,
    birthday_15_calendar_position,
    birthday_15_season_position,
    completed_weeks_at_calendar_position,
)
from beta_engine.domain.players.lifecycle import synthesize_birth_year_week

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("weeks,offset", [(1, 1), (7, 3), (52, 1), (52, 35), (61, 37), (80, 80)])
def test_year_units_birthday_boundary_and_run_offset_do_not_scale_age(weeks, offset):
    clock = RunCalendar(weeks, offset, 2030, 2)
    for season_week in range(1, weeks + 1):
        position = clock.season_to_calendar(0, season_week)
        for birth_week in {1, weeks, position.year_week}:
            age = age_at_calendar_position(
                birth_year=2012, birth_year_week=birth_week,
                calendar_year=position.calendar_year, year_week=position.year_week,
                weeks_per_calendar_year=weeks,
            )
            elapsed = completed_weeks_at_calendar_position(
                birth_year=2012, birth_year_week=birth_week,
                calendar_year=position.calendar_year, year_week=position.year_week,
                weeks_per_calendar_year=weeks,
            )
            assert age == elapsed // weeks
            assert birth_year_for_age_at_calendar_position(
                age=age, birth_year_week=birth_week,
                calendar_year=position.calendar_year, year_week=position.year_week,
                weeks_per_calendar_year=weeks,
            ) == 2012
            if birth_week == position.year_week:
                assert Fraction(elapsed, weeks) == position.calendar_year - 2012
    assert completed_weeks_at_calendar_position(
        birth_year=2012, birth_year_week=1, calendar_year=2030, year_week=1,
        weeks_per_calendar_year=weeks,
    ) == 18 * weeks


@pytest.mark.parametrize("weeks,offset", [(52, 1), (52, 35), (61, 37), (80, 80)])
def test_fifteenth_birthday_keeps_birth_identity_and_maps_through_requested_offset(weeks, offset):
    clock = RunCalendar(weeks, offset, 2029, 3)
    for birth_week in {1, weeks, offset}:
        birthday = birthday_15_calendar_position(2015, birth_week, weeks_per_calendar_year=weeks)
        assert (birthday.calendar_year, birthday.year_week) == (2030, birth_week)
        season = birthday_15_season_position(
            2015, birth_week, weeks_per_calendar_year=weeks, season_start_year_week=offset,
        )
        expected = clock.calendar_to_season(2030, birth_week)
        assert season.season_start_year == 2029 + expected.season_index
        assert season.season_week == expected.season_week


def test_explicit_earth_clock_rejects_old_out_of_range_birthday_without_conversion():
    # Week 61 belongs to historical FAX, not automatically Earth week 9 or 52.
    for operation in (age_at_calendar_position, completed_weeks_at_calendar_position):
        with pytest.raises(ValueError, match="year_week must be between 1 and 52"):
            operation(birth_year=2012, birth_year_week=61, calendar_year=2030,
                      year_week=1, weeks_per_calendar_year=52)
    with pytest.raises(ValueError, match="year_week"):
        birth_year_for_age_at_calendar_position(age=18, birth_year_week=61,
            calendar_year=2030, year_week=1, weeks_per_calendar_year=52)
    with pytest.raises(ValueError, match="year_week"):
        birthday_15_calendar_position(2015, 61, weeks_per_calendar_year=52)


@pytest.mark.parametrize("weeks", [0, -1, True, 52.0, "52"])
def test_invalid_year_scale_is_rejected_at_all_age_and_identity_entrypoints(weeks):
    with pytest.raises(ValueError, match="positive integer"):
        age_at_calendar_position(birth_year=2012, birth_year_week=1,
            calendar_year=2030, year_week=1, weeks_per_calendar_year=weeks)
    with pytest.raises(ValueError, match="positive integer"):
        synthesize_birth_year_week(player_id="new", birth_year=2012, weeks_per_calendar_year=weeks)


def test_synthesized_identity_stays_deterministic_and_in_its_original_scale():
    for weeks in (1, 7, 52, 61, 80):
        first = [synthesize_birth_year_week(player_id=f"player-{i}", birth_year=2012,
                    weeks_per_calendar_year=weeks) for i in range(200)]
        assert min(first) >= 1 and max(first) <= weeks
        assert first == [synthesize_birth_year_week(player_id=f"player-{i}", birth_year=2012,
                    weeks_per_calendar_year=weeks) for i in range(200)]
    assert synthesize_birth_year_week(player_id="legacy", birth_year=1980) == 30
    assert synthesize_birth_year_week(player_id="legacy", birth_year=1980, weeks_per_calendar_year=61) == 30


def test_missing_scale_retains_legacy_fax_age_and_week_meaning():
    for birth_week in (1, 36, 37, 61):
        for current_week in (1, 36, 37, 61):
            args = {"birth_year": 1980, "birth_year_week": birth_week,
                    "calendar_year": 2000, "year_week": current_week}
            assert age_at_calendar_position(**args) == 20 - (current_week < birth_week)
            assert completed_weeks_at_calendar_position(**args) == 20 * 61 + current_week - birth_week
