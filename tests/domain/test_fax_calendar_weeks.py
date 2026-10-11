import pytest

from beta_engine.domain.calendar.season_weeks import (
    birthday_15_calendar_position,
    birthday_15_season_position,
    calendar_position_to_season_week,
    season_week_to_calendar_position,
    season_week_to_calendar_year_offset,
    season_week_to_year_week,
    year_week_to_season_week,
)


def test_season_week_to_year_week_boundaries() -> None:
    assert season_week_to_year_week(1) == 37
    assert season_week_to_year_week(25) == 61
    assert season_week_to_year_week(26) == 1
    assert season_week_to_year_week(61) == 36


def test_year_week_to_season_week_boundaries() -> None:
    assert year_week_to_season_week(37) == 1
    assert year_week_to_season_week(61) == 25
    assert year_week_to_season_week(1) == 26
    assert year_week_to_season_week(36) == 61


def test_all_weeks_round_trip_between_season_week_and_year_week() -> None:
    for week in range(1, 62):
        assert year_week_to_season_week(season_week_to_year_week(week)) == week
        assert season_week_to_year_week(year_week_to_season_week(week)) == week


def test_season_week_to_calendar_year_offset() -> None:
    assert season_week_to_calendar_year_offset(1) == 0
    assert season_week_to_calendar_year_offset(25) == 0
    assert season_week_to_calendar_year_offset(26) == 1
    assert season_week_to_calendar_year_offset(61) == 1


@pytest.mark.parametrize(
    ("season_week", "calendar_year", "year_week"),
    [(1, 2000, 37), (25, 2000, 61), (26, 2001, 1), (61, 2001, 36)],
)
def test_season_week_to_calendar_position_for_2000(
    season_week: int, calendar_year: int, year_week: int
) -> None:
    position = season_week_to_calendar_position(2000, season_week)

    assert position.season_start_year == 2000
    assert position.season_label == "2000/2001"
    assert position.season_week == season_week
    assert position.calendar_year == calendar_year
    assert position.year_week == year_week


@pytest.mark.parametrize(
    ("calendar_year", "year_week", "season_start_year", "season_week", "season_label"),
    [
        (2000, 37, 2000, 1, "2000/2001"),
        (2000, 61, 2000, 25, "2000/2001"),
        (2001, 1, 2000, 26, "2000/2001"),
        (2001, 36, 2000, 61, "2000/2001"),
        (2001, 37, 2001, 1, "2001/2002"),
    ],
)
def test_calendar_position_to_season_week(
    calendar_year: int,
    year_week: int,
    season_start_year: int,
    season_week: int,
    season_label: str,
) -> None:
    position = calendar_position_to_season_week(calendar_year, year_week)

    assert position.season_start_year == season_start_year
    assert position.season_label == season_label
    assert position.season_week == season_week
    assert position.calendar_year == calendar_year
    assert position.year_week == year_week


def test_birthday_15_calendar_position() -> None:
    first = birthday_15_calendar_position(1985, 37)
    second = birthday_15_calendar_position(1986, 1)

    assert first.calendar_year == 2000
    assert first.year_week == 37
    assert second.calendar_year == 2001
    assert second.year_week == 1


@pytest.mark.parametrize(
    (
        "birth_year",
        "birth_year_week",
        "season_label",
        "season_start_year",
        "season_week",
    ),
    [
        (1985, 37, "2000/2001", 2000, 1),
        (1985, 61, "2000/2001", 2000, 25),
        (1985, 1, "1999/2000", 1999, 26),
        (1985, 36, "1999/2000", 1999, 61),
        (1986, 1, "2000/2001", 2000, 26),
    ],
)
def test_birthday_15_season_position(
    birth_year: int,
    birth_year_week: int,
    season_label: str,
    season_start_year: int,
    season_week: int,
) -> None:
    position = birthday_15_season_position(birth_year, birth_year_week)

    assert position.season_label == season_label
    assert position.season_start_year == season_start_year
    assert position.season_week == season_week


@pytest.mark.parametrize("season_week", [0, 62])
def test_invalid_season_week_validation(season_week: int) -> None:
    with pytest.raises(ValueError, match="season_week must be between 1 and 61"):
        season_week_to_year_week(season_week)
    with pytest.raises(ValueError, match="season_week must be between 1 and 61"):
        season_week_to_calendar_year_offset(season_week)


@pytest.mark.parametrize("year_week", [0, 62])
def test_invalid_year_week_validation(year_week: int) -> None:
    with pytest.raises(ValueError, match="year_week must be between 1 and 61"):
        year_week_to_season_week(year_week)
    with pytest.raises(ValueError, match="year_week must be between 1 and 61"):
        calendar_position_to_season_week(2000, year_week)
    with pytest.raises(ValueError, match="year_week must be between 1 and 61"):
        birthday_15_calendar_position(1985, year_week)
    with pytest.raises(ValueError, match="year_week must be between 1 and 61"):
        birthday_15_season_position(1985, year_week)
