"""The v82 Run calendar is a pure/versioned domain clock, not stored-state migration."""

from __future__ import annotations

import pytest

from beta_engine.domain.calendar.run_calendar import (
    CALENDAR_SCHEMA_VERSION,
    LEGACY_FAX_CALENDAR_SCHEMA_VERSION,
    RunCalendar,
)


@pytest.mark.parametrize(
    ("calendar", "expected_label", "last_year_week", "first_next"),
    [
        (RunCalendar(52, 1, 2035, 3), "2035", (2035, 52), (2036, 1)),
        (RunCalendar(52, 35, 2035, 3), "2035/2036", (2036, 34), (2036, 35)),
        (RunCalendar(61, 37, 2000, 50), "2000/2001", (2001, 36), (2001, 37)),
        (RunCalendar(7, 3, 2080, 2), "2080/2081", (2081, 2), (2081, 3)),
    ],
)
def test_all_week_round_trips_and_season_boundary(
    calendar: RunCalendar,
    expected_label: str,
    last_year_week: tuple[int, int],
    first_next: tuple[int, int],
) -> None:
    assert calendar.label(0) == expected_label
    end = calendar.season_to_calendar(0, calendar.weeks_per_year)
    first = calendar.season_to_calendar(1, 1)
    assert (end.calendar_year, end.year_week) == last_year_week
    assert (first.calendar_year, first.year_week) == first_next
    for season_index in range(calendar.season_count):
        for season_week in range(1, calendar.weeks_per_year + 1):
            actual = calendar.season_to_calendar(season_index, season_week)
            assert calendar.calendar_to_season(actual.calendar_year, actual.year_week) == actual


def test_fax_legacy_read_semantics_without_retagging_historical_payloads() -> None:
    legacy = RunCalendar.from_metadata()
    assert legacy.schema_version == LEGACY_FAX_CALENDAR_SCHEMA_VERSION
    assert legacy.season_to_calendar(0, 1).year_week == 37
    assert legacy.season_to_calendar(0, 25).year_week == 61
    assert legacy.season_to_calendar(0, 26).year_week == 1
    assert legacy.season_to_calendar(0, 61).year_week == 36
    with pytest.raises(ValueError, match="no writable"):
        legacy.to_metadata()
    with pytest.raises(ValueError, match="migration"):
        legacy.extend_to(51)


def test_explicit_defaults_and_metadata_round_trip() -> None:
    assert (RunCalendar.earth_default().weeks_per_year, RunCalendar.earth_default().season_start_year_week) == (52, 1)
    assert (RunCalendar.fax_default().weeks_per_year, RunCalendar.fax_default().season_start_year_week) == (61, 37)
    calendar = RunCalendar(52, 35, 2028, 4)
    payload = calendar.to_metadata()
    assert payload["schema_version"] == CALENDAR_SCHEMA_VERSION
    assert RunCalendar.from_metadata(payload) == calendar
    assert calendar.calendar_to_season(2028, 34) is None
    assert calendar.calendar_to_season(2032, 35) is None


def test_extension_only_changes_the_end_and_old_week_positions() -> None:
    before = RunCalendar(52, 35, 2028, 2)
    after = before.extend_to(5)
    assert before.season_count == 2
    assert after.season_count == 5
    for i in range(before.season_count):
        for w in (1, 18, 19, 52):
            assert before.season_to_calendar(i, w) == after.season_to_calendar(i, w)
    with pytest.raises(ValueError, match="exceed"):
        before.extend_to(2)
    with pytest.raises(ValueError, match="exceed"):
        before.extend_to(1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"weeks_per_year": 0},
        {"weeks_per_year": -1},
        {"weeks_per_year": True},
        {"weeks_per_year": 52.5},
        {"season_start_year_week": 0},
        {"season_start_year_week": 53},
        {"season_start_year_week": True},
        {"start_year": -1},
        {"start_year": "2000"},
        {"season_count": 0},
        {"season_count": True},
        {"schema_version": "run_calendar.v999"},
    ],
)
def test_invalid_calendar_rejected(kwargs: dict[str, object]) -> None:
    base: dict[str, object] = dict(
        weeks_per_year=52, season_start_year_week=35, start_year=2000, season_count=2
    )
    with pytest.raises(ValueError):
        RunCalendar(**(base | kwargs))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {},
        {"schema_version": CALENDAR_SCHEMA_VERSION},
        {"schema_version": "legacy_fax_calendar.v0", "weeks_per_year": 61,
         "season_start_year_week": 37, "start_year": 2000, "season_count": 50},
        {"schema_version": CALENDAR_SCHEMA_VERSION, "weeks_per_year": "52",
         "season_start_year_week": 1, "start_year": 2000, "season_count": 50},
        {"schema_version": CALENDAR_SCHEMA_VERSION, "weeks_per_year": 52,
         "season_start_year_week": 1, "start_year": 2000, "season_count": 50, "extra": True},
    ],
)
def test_explicit_malformed_or_unversioned_metadata_never_defaults(metadata: object) -> None:
    with pytest.raises(ValueError):
        RunCalendar.from_metadata(metadata)


def test_invalid_positions_rejected_instead_of_wrap_or_clamp() -> None:
    cal = RunCalendar(52, 35, 2030, 2)
    for index, week in ((-1, 1), (2, 1), (0, 0), (0, 53), (True, 1)):
        with pytest.raises(ValueError):
            cal.season_to_calendar(index, week)
    for year, week in ((2030, 0), (2031, 53), (2031, True), (-1, 1)):
        with pytest.raises(ValueError):
            cal.calendar_to_season(year, week)
