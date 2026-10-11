from __future__ import annotations

import pytest

from beta_engine.domain.calendar import (
    calendar_position_to_season_week,
    parse_season_start_year,
    season_week_to_calendar_position,
)


def test_season_week_to_calendar_position_official_fax_mapping() -> None:
    cases = [
        (1, 2000, 37),
        (2, 2000, 38),
        (25, 2000, 61),
        (26, 2001, 1),
        (61, 2001, 36),
    ]
    for season_week, calendar_year, year_week in cases:
        position = season_week_to_calendar_position("2000/2001", season_week)
        assert position.season == "2000/2001"
        assert position.season_week == season_week
        assert position.calendar_year == calendar_year
        assert position.year_week == year_week


def test_calendar_position_to_season_week_official_fax_mapping() -> None:
    assert calendar_position_to_season_week("2000/2001", 2000, 37) == 1
    assert calendar_position_to_season_week("2000/2001", 2000, 61) == 25
    assert calendar_position_to_season_week("2000/2001", 2001, 1) == 26
    assert calendar_position_to_season_week("2000/2001", 2001, 36) == 61
    assert calendar_position_to_season_week("2000/2001", 2000, 36) is None
    assert calendar_position_to_season_week("2000/2001", 2001, 37) is None


def test_invalid_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="season_week"):
        season_week_to_calendar_position("2000/2001", 0)
    with pytest.raises(ValueError, match="season_week"):
        season_week_to_calendar_position("2000/2001", 62)
    with pytest.raises(ValueError, match="year_week"):
        calendar_position_to_season_week("2000/2001", 2000, 0)
    with pytest.raises(ValueError, match="year_week"):
        calendar_position_to_season_week("2000/2001", 2001, 62)
    with pytest.raises(ValueError, match="season_start_year_week"):
        season_week_to_calendar_position("2000/2001", 1, season_start_year_week=0)
    with pytest.raises(ValueError, match="season_start_year_week"):
        season_week_to_calendar_position("2000/2001", 1, season_start_year_week=62)
    with pytest.raises(ValueError, match="weeks_per_calendar_year must be 61"):
        season_week_to_calendar_position("2000/2001", 1, weeks_per_calendar_year=52)
    with pytest.raises(ValueError, match="YYYY/YYYY"):
        parse_season_start_year("2000")
    with pytest.raises(ValueError, match="plus one"):
        parse_season_start_year("2000/2002")
