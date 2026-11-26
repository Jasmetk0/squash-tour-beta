"""Check recorded phase dates against the canonical ATP calendar and W52 clock."""
import json
from datetime import date

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar, RunCalendarPosition
from scripts.audit_atp_earth_week_mapping_v1 import SOURCE_FILE, build_projection

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def phase_evidence():
    path = SOURCE_FILE.parent / "phase_calendar_evidence" / "2025.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_phase_evidence_binds_to_canonical_2025_memberships_and_main_dates(phase_evidence):
    projection = build_projection(json.loads(SOURCE_FILE.read_text(encoding="utf-8")))
    by_identity = {row["source_identity"]: row for row in projection["mappings"]}
    membership_path = SOURCE_FILE.parent / "seasons_1990_2026.json"
    seasons = json.loads(membership_path.read_text(encoding="utf-8"))["seasons"]
    membership = next(season for season in seasons if season["year"] == 2025)
    occurrences = phase_evidence["occurrences"]

    assert phase_evidence["atp_season_year"] == 2025
    assert phase_evidence["sporting_schedule_installed"] is False
    assert len({row["occurrence_id"] for row in occurrences}) == len(occurrences)
    for row in occurrences:
        canonical = by_identity[row["occurrence_id"]]
        assert (canonical["atp_season_year"], canonical["series_id"]) == (2025, row["series_id"])
        assert membership["series_category_ids"][row["series_id"]] == row["category_id"]
        assert canonical["original_start_date"] == row["main_start_date"]
        assert canonical["original_end_date"] == row["main_end_date"]
        assert row["main_year_weeks"] == [
            [week["calendar_year"], week["year_week"]] for week in canonical["mapped_year_weeks"]
        ]
        observed_weeks = {
            date.fromisoformat(evidence["date"]).isocalendar()[:2]
            for evidence in row["qualifying_date_evidence"]
            if evidence["status"] == "played"
        }
        assert [list(key) for key in sorted(observed_weeks)] == row["observed_qualifying_iso_weeks"]


def test_w52_run_positions_preserve_year_boundary_and_same_week_play(phase_evidence):
    by_series = {row["series_id"]: row for row in phase_evidence["occurrences"]}
    brisbane, adelaide = by_series["brisbane"], by_series["adelaide"]
    assert brisbane["observed_qualifying_iso_weeks"] == [[2024, 52]]
    assert brisbane["main_year_weeks"] == [[2025, 1]]
    assert adelaide["observed_qualifying_iso_weeks"] == adelaide["main_year_weeks"] == [[2025, 2]]

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    assert january.calendar_to_season(2024, 52) is None
    assert january.calendar_to_season(2025, 1) == RunCalendarPosition(0, 1, 2025, 1)
    assert shifted.calendar_to_season(2024, 52) == RunCalendarPosition(0, 16, 2024, 52)
    assert shifted.calendar_to_season(2025, 1) == RunCalendarPosition(0, 17, 2025, 1)
    assert shifted.calendar_to_season(2025, 2) == RunCalendarPosition(0, 18, 2025, 2)


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_week", "january_q", "shifted_q", "shifted_main"),
    [
        ("hong_kong", ["2024-12-29", "2024-12-30"], [[2024, 52], [2025, 1]],
         1, [None, 1], [16, 17], 17),
        ("auckland", ["2025-01-04", "2025-01-05"], [[2025, 1]],
         2, [1], [17], 18),
        ("montpellier", ["2025-01-26", "2025-01-27"], [[2025, 4], [2025, 5]],
         5, [4, 5], [20, 21], 21),
        ("lyon", ["2025-02-09", "2025-02-10"], [[2025, 6], [2025, 7]],
         7, [6, 7], [22, 23], 23),
    ],
)
def test_modern_phase_dates_and_native_positions(
    phase_evidence, series, q_dates, q_weeks, main_week, january_q, shifted_q, shifted_main
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == [[2025, main_week]]
    assert (row["main_start_date"] in q_dates) == (series != "auckland")

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for (year, week), jan_week, shifted_week in zip(q_weeks, january_q, shifted_q):
        jan_expected = (
            None if jan_week is None else RunCalendarPosition(0, jan_week, year, week)
        )
        assert january.calendar_to_season(year, week) == jan_expected
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(
            0, shifted_week, year, week
        )
    assert january.calendar_to_season(2025, main_week) == RunCalendarPosition(
        0, main_week, 2025, main_week
    )
    assert shifted.calendar_to_season(2025, main_week) == RunCalendarPosition(
        0, shifted_main, 2025, main_week
    )


@pytest.mark.parametrize(
    ("series", "q_dates", "q_week", "main_week"),
    [
        ("dallas", ["2025-02-01", "2025-02-02"], 5, 6),
        ("rotterdam", ["2025-02-01", "2025-02-02"], 5, 6),
        ("buenos_aires", ["2025-02-08", "2025-02-09"], 6, 7),
        ("delray_beach", ["2025-02-08", "2025-02-09"], 6, 7),
        ("doha", ["2025-02-15", "2025-02-16"], 7, 8),
        ("rio", ["2025-02-15", "2025-02-16"], 7, 8),
        ("acapulco", ["2025-02-22", "2025-02-23"], 8, 9),
        ("dubai", ["2025-02-22", "2025-02-23"], 8, 9),
        ("santiago", ["2025-02-22", "2025-02-23"], 8, 9),
    ],
)
def test_adjacent_week_phase_dates_and_native_positions(
    phase_evidence, series, q_dates, q_week, main_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert q_dates[-1] < row["main_start_date"]
    assert row["observed_qualifying_iso_weeks"] == [[2025, q_week]]
    assert row["main_year_weeks"] == [[2025, main_week]]
    assert main_week == q_week + 1

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in (q_week, main_week):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(
            0, week, 2025, week
        )
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(
            0, week + 16, 2025, week
        )


@pytest.mark.parametrize(
    ("series", "q_dates", "first_main_week"),
    [
        ("indian_wells", ["2025-03-03", "2025-03-04"], 10),
        ("miami", ["2025-03-17", "2025-03-18"], 12),
    ],
)
def test_masters_two_week_main_preserves_same_week_qualifying(
    phase_evidence, series, q_dates, first_main_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["category_id"] == "atp_masters_1000"
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert q_dates[-1] < row["main_start_date"]
    assert row["observed_qualifying_iso_weeks"] == [[2025, first_main_week]]
    assert row["main_year_weeks"] == [[2025, first_main_week], [2025, first_main_week + 1]]
    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in (first_main_week, first_main_week + 1):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(0, week, 2025, week)
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(0, week + 16, 2025, week)


def test_marseille_2025_retains_relocated_licence_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "lyon")
    assert row["occurrence_id"] == "atp_2025_lyon"
    assert row["historical_identity_evidence"]["actual_host"] == "Marseille, France"
    assert row["historical_identity_evidence"]["source_event_id"] == 496
    assert not any(r["series_id"] == "lyon_old" for r in phase_evidence["occurrences"])
