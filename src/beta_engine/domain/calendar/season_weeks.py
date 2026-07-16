"""Deterministic mapping between simulation Season Weeks and calendar Year Weeks.

FAX seasons use Season Week as the internal simulation index and Year Week as the
calendar-facing position. This module is the single source of truth for that
mapping so calendars, rankings, history, and future age logic stay aligned.
"""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.domain.calendar.season_labels import long_season_label_from_start_year

TOTAL_SEASON_WEEKS = 61
DEFAULT_WEEKS_PER_SEASON = TOTAL_SEASON_WEEKS
DEFAULT_SEASON_START_YEAR_WEEK = 37
SEASON_WEEK_1_YEAR_WEEK = DEFAULT_SEASON_START_YEAR_WEEK
DEFAULT_WEEKS_PER_CALENDAR_YEAR = 61
PLAYER_15TH_BIRTHDAY_AGE = 15


@dataclass(frozen=True, slots=True)
class SeasonWeekPosition:
    """Calendar position for one season week."""

    season: str
    season_week: int
    calendar_year: int
    year_week: int
    season_start_year: int | None = None
    season_label: str | None = None


@dataclass(frozen=True, slots=True)
class CalendarSeasonPosition:
    """Bidirectional FAX calendar/season position."""

    season_start_year: int
    season_label: str
    season_week: int
    calendar_year: int
    year_week: int


@dataclass(frozen=True, slots=True)
class Birthday15CalendarPosition:
    """Calendar position for a player's 15th birthday."""

    birth_year: int
    calendar_year: int
    year_week: int


def parse_season_start_year(season: str) -> int:
    """Return the starting calendar year from a season label like ``2000/2001``."""

    if not isinstance(season, str):
        raise ValueError("season must be a string in YYYY/YYYY format")
    parts = season.split("/")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError("season must use YYYY/YYYY or YYYY/YY format")
    start_year = int(parts[0])
    if len(parts[1]) == 4:
        end_year = int(parts[1])
        if end_year != start_year + 1:
            raise ValueError("season end year must be the start year plus one")
    elif len(parts[1]) == 2:
        if int(parts[1]) != (start_year + 1) % 100:
            raise ValueError("season end year must be the start year plus one")
    else:
        raise ValueError("season must use YYYY/YYYY or YYYY/YY format")
    return start_year


def _validate_mapping_inputs(
    *,
    season_week: int | None = None,
    season_start_year_week: int,
    weeks_per_calendar_year: int,
) -> None:
    if weeks_per_calendar_year != DEFAULT_WEEKS_PER_CALENDAR_YEAR:
        raise ValueError(
            "weeks_per_calendar_year must be 61 for the current FAX calendar mapping"
        )
    if not 1 <= season_start_year_week <= weeks_per_calendar_year:
        raise ValueError("season_start_year_week must be between 1 and 61")
    if season_week is not None and not 1 <= season_week <= TOTAL_SEASON_WEEKS:
        raise ValueError("season_week must be between 1 and 61")


def _validate_year_week(
    year_week: int, *, weeks_per_calendar_year: int = DEFAULT_WEEKS_PER_CALENDAR_YEAR
) -> None:
    if weeks_per_calendar_year != DEFAULT_WEEKS_PER_CALENDAR_YEAR:
        raise ValueError(
            "weeks_per_calendar_year must be 61 for the current FAX calendar mapping"
        )
    if not 1 <= year_week <= weeks_per_calendar_year:
        raise ValueError("year_week must be between 1 and 61")


def season_week_to_year_week(season_week: int) -> int:
    """Map a 1-based Season Week to its 1-based FAX Year Week."""

    _validate_mapping_inputs(
        season_week=season_week,
        season_start_year_week=SEASON_WEEK_1_YEAR_WEEK,
        weeks_per_calendar_year=DEFAULT_WEEKS_PER_CALENDAR_YEAR,
    )
    return (
        (SEASON_WEEK_1_YEAR_WEEK - 1 + (season_week - 1))
        % DEFAULT_WEEKS_PER_CALENDAR_YEAR
    ) + 1


def year_week_to_season_week(year_week: int) -> int:
    """Map a 1-based FAX Year Week to its 1-based Season Week."""

    _validate_year_week(year_week)
    return ((year_week - SEASON_WEEK_1_YEAR_WEEK) % DEFAULT_WEEKS_PER_CALENDAR_YEAR) + 1


def season_week_to_calendar_year_offset(season_week: int) -> int:
    """Return 0 for the season start calendar year and 1 for the next calendar year."""

    _validate_mapping_inputs(
        season_week=season_week,
        season_start_year_week=SEASON_WEEK_1_YEAR_WEEK,
        weeks_per_calendar_year=DEFAULT_WEEKS_PER_CALENDAR_YEAR,
    )
    return (
        0
        if season_week
        <= (DEFAULT_WEEKS_PER_CALENDAR_YEAR - SEASON_WEEK_1_YEAR_WEEK + 1)
        else 1
    )


def season_week_to_calendar_position(
    season: str | int,
    season_week: int,
    season_start_year_week: int = DEFAULT_SEASON_START_YEAR_WEEK,
    weeks_per_calendar_year: int = DEFAULT_WEEKS_PER_CALENDAR_YEAR,
) -> SeasonWeekPosition:
    """Map a season week to its deterministic calendar year/week position.

    ``season`` may be a legacy season label (``2000/2001`` or ``2000/01``) or a
    season start year. New code should pass the start year directly when it does
    not otherwise need to parse a label.
    """

    season_start_year = (
        parse_season_start_year(season) if isinstance(season, str) else season
    )
    if not isinstance(season_start_year, int):
        raise ValueError("season_start_year must be an integer")
    _validate_mapping_inputs(
        season_week=season_week,
        season_start_year_week=season_start_year_week,
        weeks_per_calendar_year=weeks_per_calendar_year,
    )
    offset = season_start_year_week + season_week - 1
    calendar_year = season_start_year + ((offset - 1) // weeks_per_calendar_year)
    year_week = ((offset - 1) % weeks_per_calendar_year) + 1
    season_label = long_season_label_from_start_year(season_start_year)
    season_text = season if isinstance(season, str) else season_label
    return SeasonWeekPosition(
        season=season_text,
        season_week=season_week,
        calendar_year=calendar_year,
        year_week=year_week,
        season_start_year=season_start_year,
        season_label=season_label,
    )


def calendar_position_to_season_week(
    *args: object,
    calendar_year: int | None = None,
    year_week: int | None = None,
    season: str | None = None,
    season_start_year_week: int = DEFAULT_SEASON_START_YEAR_WEEK,
    weeks_per_calendar_year: int = DEFAULT_WEEKS_PER_CALENDAR_YEAR,
) -> CalendarSeasonPosition | int | None:
    """Map a calendar year/week to a season position.

    With ``season=...`` this preserves the legacy behavior by returning the
    season week within that specific season, or ``None`` if outside it. Without a
    season, it returns the inferred FAX season position dataclass. The legacy
    positional form ``(season, calendar_year, year_week)`` is also supported.
    """

    if args:
        if len(args) == 3 and isinstance(args[0], str):
            season = args[0]
            calendar_year = args[1]  # type: ignore[assignment]
            year_week = args[2]  # type: ignore[assignment]
        elif len(args) == 2:
            calendar_year = args[0]  # type: ignore[assignment]
            year_week = args[1]  # type: ignore[assignment]
        else:
            raise TypeError(
                "calendar_position_to_season_week expects (calendar_year, year_week) or (season, calendar_year, year_week)"
            )
    if calendar_year is None or year_week is None:
        raise ValueError("calendar_year and year_week are required")
    if not isinstance(calendar_year, int):
        raise ValueError("calendar_year must be an integer")
    if not isinstance(year_week, int):
        raise ValueError("year_week must be an integer")
    _validate_mapping_inputs(
        season_start_year_week=season_start_year_week,
        weeks_per_calendar_year=weeks_per_calendar_year,
    )
    _validate_year_week(year_week, weeks_per_calendar_year=weeks_per_calendar_year)
    season_week = year_week_to_season_week(year_week)
    inferred_start_year = (
        calendar_year if year_week >= season_start_year_week else calendar_year - 1
    )

    if season is not None:
        legacy_start_year = parse_season_start_year(season)
        calendar_offset = (
            calendar_year - legacy_start_year
        ) * weeks_per_calendar_year + year_week
        legacy_season_week = calendar_offset - season_start_year_week + 1
        if 1 <= legacy_season_week <= TOTAL_SEASON_WEEKS:
            return legacy_season_week
        return None

    return CalendarSeasonPosition(
        season_start_year=inferred_start_year,
        season_label=long_season_label_from_start_year(inferred_start_year),
        season_week=season_week,
        calendar_year=calendar_year,
        year_week=year_week,
    )


def birthday_15_calendar_position(
    birth_year: int, birth_year_week: int
) -> Birthday15CalendarPosition:
    """Return the pure calendar position where a player turns 15."""

    if not isinstance(birth_year, int):
        raise ValueError("birth_year must be an integer")
    _validate_year_week(birth_year_week)
    return Birthday15CalendarPosition(
        birth_year=birth_year,
        calendar_year=birth_year + PLAYER_15TH_BIRTHDAY_AGE,
        year_week=birth_year_week,
    )


def birthday_15_season_position(
    birth_year: int, birth_year_week: int
) -> CalendarSeasonPosition:
    """Return the pure season position where a player turns 15."""

    birthday = birthday_15_calendar_position(birth_year, birth_year_week)
    position = calendar_position_to_season_week(
        birthday.calendar_year, birthday.year_week
    )
    assert isinstance(position, CalendarSeasonPosition)
    return position
