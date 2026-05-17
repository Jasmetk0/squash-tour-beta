"""Deterministic mapping between simulation Season Weeks and calendar Year Weeks.

FAX seasons use Season Week as the internal simulation index and Year Week as the
calendar-facing position. This module is the single source of truth for that
mapping so calendars, rankings, history, and future age logic stay aligned.
"""

from __future__ import annotations

from dataclasses import dataclass

TOTAL_SEASON_WEEKS = 61
DEFAULT_SEASON_START_YEAR_WEEK = 37
DEFAULT_WEEKS_PER_CALENDAR_YEAR = 52


@dataclass(frozen=True, slots=True)
class SeasonWeekPosition:
    """Calendar position for one season week."""

    season: str
    season_week: int
    calendar_year: int
    year_week: int


def parse_season_start_year(season: str) -> int:
    """Return the starting calendar year from a season label like ``2000/2001``."""

    if not isinstance(season, str):
        raise ValueError("season must be a string in YYYY/YYYY format")
    parts = season.split("/")
    if len(parts) != 2 or not all(part.isdigit() and len(part) == 4 for part in parts):
        raise ValueError("season must use YYYY/YYYY format")
    start_year = int(parts[0])
    end_year = int(parts[1])
    if end_year != start_year + 1:
        raise ValueError("season end year must be the start year plus one")
    return start_year


def _validate_mapping_inputs(*, season_week: int | None = None, season_start_year_week: int, weeks_per_calendar_year: int) -> None:
    if weeks_per_calendar_year != DEFAULT_WEEKS_PER_CALENDAR_YEAR:
        raise ValueError("weeks_per_calendar_year must be 52 for the current FAX calendar mapping")
    if not 1 <= season_start_year_week <= weeks_per_calendar_year:
        raise ValueError("season_start_year_week must be between 1 and 52")
    if season_week is not None and not 1 <= season_week <= TOTAL_SEASON_WEEKS:
        raise ValueError("season_week must be between 1 and 61")


def season_week_to_calendar_position(
    season: str,
    season_week: int,
    season_start_year_week: int = DEFAULT_SEASON_START_YEAR_WEEK,
    weeks_per_calendar_year: int = DEFAULT_WEEKS_PER_CALENDAR_YEAR,
) -> SeasonWeekPosition:
    """Map a season week to its deterministic calendar year/week position."""

    season_start_year = parse_season_start_year(season)
    _validate_mapping_inputs(
        season_week=season_week,
        season_start_year_week=season_start_year_week,
        weeks_per_calendar_year=weeks_per_calendar_year,
    )
    offset = season_start_year_week + season_week - 1
    calendar_year = season_start_year + ((offset - 1) // weeks_per_calendar_year)
    year_week = ((offset - 1) % weeks_per_calendar_year) + 1
    return SeasonWeekPosition(season=season, season_week=season_week, calendar_year=calendar_year, year_week=year_week)


def calendar_position_to_season_week(
    season: str,
    calendar_year: int,
    year_week: int,
    season_start_year_week: int = DEFAULT_SEASON_START_YEAR_WEEK,
    weeks_per_calendar_year: int = DEFAULT_WEEKS_PER_CALENDAR_YEAR,
) -> int | None:
    """Return the season week for a calendar position, or ``None`` if outside the season."""

    season_start_year = parse_season_start_year(season)
    _validate_mapping_inputs(
        season_start_year_week=season_start_year_week,
        weeks_per_calendar_year=weeks_per_calendar_year,
    )
    if not 1 <= year_week <= weeks_per_calendar_year:
        raise ValueError("year_week must be between 1 and 52")
    calendar_offset = (calendar_year - season_start_year) * weeks_per_calendar_year + year_week
    season_week = calendar_offset - season_start_year_week + 1
    if 1 <= season_week <= TOTAL_SEASON_WEEKS:
        return season_week
    return None
