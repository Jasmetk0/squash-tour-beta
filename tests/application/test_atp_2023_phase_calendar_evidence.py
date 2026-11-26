"""Source-only ATP 2023 phase evidence; no sporting schedule is installed."""
import json
from datetime import date

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar, RunCalendarPosition
from scripts.audit_atp_earth_week_mapping_v1 import SOURCE_FILE, build_projection

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def phase_evidence():
    return json.loads((SOURCE_FILE.parent / "phase_calendar_evidence" / "2023.json").read_text(encoding="utf-8"))


def test_phase_evidence_binds_to_canonical_2023_memberships_and_main_dates(phase_evidence):
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    by_identity = {r["source_identity"]: r for r in build_projection(source)["mappings"]}
    seasons = json.loads((SOURCE_FILE.parent / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]
    membership = next(s for s in seasons if s["year"] == 2023)
    rows = phase_evidence["occurrences"]
    assert phase_evidence["atp_season_year"] == 2023
    assert phase_evidence["sporting_schedule_installed"] is False
    assert len({r["occurrence_id"] for r in rows}) == len(rows)
    assert rows == sorted(rows, key=lambda r: (r["main_start_date"], r["series_id"]))
    for row in rows:
        canonical = by_identity[row["occurrence_id"]]
        assert (canonical["atp_season_year"], canonical["series_id"]) == (2023, row["series_id"])
        assert membership["series_category_ids"][row["series_id"]] == row["category_id"]
        assert canonical["original_start_date"] == row["main_start_date"]
        assert canonical["original_end_date"] == row["main_end_date"]
        assert row["main_year_weeks"] == [
            [week["calendar_year"], week["year_week"]] for week in canonical["mapped_year_weeks"]
        ]
        observed = {
            date.fromisoformat(e["date"]).isocalendar()[:2]
            for e in row["qualifying_date_evidence"] if e["status"] == "played"
        }
        assert [list(k) for k in sorted(observed)] == row["observed_qualifying_iso_weeks"]
        if "main_opening_play_evidence" in row:
            opening = row["main_opening_play_evidence"]
            assert opening["date"] == row["main_start_date"]
            assert opening["status"] == "played"
            assert list(date.fromisoformat(opening["date"]).isocalendar()[:2]) == opening["observed_iso_week"]


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_week", "category"),
    [
        ("adelaide", ["2022-12-31","2023-01-01"], [[2022,52]], 1, "atp_250"),
        ("hong_kong", ["2022-12-31","2023-01-01"], [[2022,52]], 1, "atp_250"),
        ("adelaide_2", ["2023-01-08","2023-01-09"], [[2023,1],[2023,2]], 2, "atp_250"),
        ("auckland", ["2023-01-07","2023-01-08"], [[2023,1]], 2, "atp_250"),
        ("cordoba", ["2023-02-04","2023-02-05"], [[2023,5]], 6, "atp_250"),
        ("dallas", ["2023-02-05","2023-02-06"], [[2023,5],[2023,6]], 6, "atp_250"),
        ("montpellier", ["2023-02-05","2023-02-06"], [[2023,5],[2023,6]], 6, "atp_250"),
        ("buenos_aires", ["2023-02-11","2023-02-12"], [[2023,6]], 7, "atp_250"),
    ],
)
def test_initial_2023_phase_positions(phase_evidence, series, q_dates, q_weeks, main_week, category):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["category_id"] == category
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == [[2023, main_week]]
    january = RunCalendar.earth_default(start_year=2023, season_count=2)
    shifted = RunCalendar(52, 37, 2022, 2)
    for year, week in q_weeks + [[2023, main_week]]:
        expected = None if year == 2022 else RunCalendarPosition(0, week, year, week)
        assert january.calendar_to_season(year, week) == expected
        shifted_week = week - 36 if year == 2022 else week + 16
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, shifted_week, year, week)


def test_2023_adelaide_opening_on_jan_1_is_prior_iso_year(phase_evidence):
    rows = {r["series_id"]: r for r in phase_evidence["occurrences"]}
    first, second = rows["adelaide"], rows["adelaide_2"]
    assert first["occurrence_id"] != second["occurrence_id"]
    assert first["main_end_date"] == second["qualifying_date_evidence"][0]["date"] == "2023-01-08"
    assert first["main_opening_play_evidence"]["observed_iso_week"] == [2022, 52]
    assert first["observed_qualifying_iso_weeks"] == [[2022, 52]]
    assert second["main_opening_play_evidence"]["observed_iso_week"] == [2023, 2]


def test_pune_2023_retains_hong_kong_series_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "hong_kong")
    assert row["occurrence_id"] == "atp_2023_hong_kong"
    assert row["historical_identity_evidence"]["actual_host"] == "Pune, India"
    assert row["observed_qualifying_iso_weeks"] == [[2022, 52]]


def test_auckland_source_disagreement_not_silently_installed(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "auckland")
    assert row["main_start_date"] == "2023-01-09"
    assert "source_disagreement" in row
    assert "main_opening_play_evidence" not in row
    assert phase_evidence["sporting_schedule_installed"] is False
