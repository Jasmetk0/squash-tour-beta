"""Boundary tests for calendar horizon extension planning (no persistence)."""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar


def test_extension_preserves_basis_and_original_clock():
    original = RunCalendar(52, 35, 2030, 3)
    extended = original.extend_to(5)
    assert extended.to_metadata() == {
        "schema_version": "run_calendar.v1",
        "weeks_per_year": 52,
        "season_start_year_week": 35,
        "start_year": 2030,
        "season_count": 5,
    }
    assert original.season_count == 3
    assert extended.position_at_ordinal(4 * 52 + 51).season_index == 4


@pytest.mark.parametrize("count", [3, 2, 0, -1, True, 3.5, "5"])
def test_extension_requires_strictly_larger_integer(count):
    calendar = RunCalendar.earth_default(start_year=2030, season_count=3)
    with pytest.raises(ValueError, match="exceed current horizon"):
        calendar.extend_to(count)


def test_extension_refuses_season_count_over_signed_int_range():
    calendar = RunCalendar(1, 1, 0, 1)
    assert calendar.extend_to(2**31 - 1).season_count == 2**31 - 1
    with pytest.raises(ValueError, match="season_count exceeds"):
        calendar.extend_to(2**31)


def test_extension_refuses_last_season_year_overflow():
    calendar = RunCalendar(52, 1, 2**31 - 2, 1)
    assert calendar.extend_to(2).season_count == 2
    with pytest.raises(ValueError, match="last season exceeds"):
        calendar.extend_to(3)


def test_extension_refuses_inexact_json_week_ordinals():
    calendar = RunCalendar(2**31 - 1, 1, 0, 1)
    assert calendar.extend_to(2**22).season_count == 2**22
    with pytest.raises(ValueError, match="exact JSON week range"):
        calendar.extend_to(2**23)


def test_historical_legacy_calendar_does_not_extend():
    with pytest.raises(ValueError, match="legacy calendar extension"):
        RunCalendar.legacy_fax().extend_to(51)
