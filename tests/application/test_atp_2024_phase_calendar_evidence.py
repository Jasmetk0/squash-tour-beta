"""Source-only ATP 2024 phase evidence; no sporting schedule is installed."""
import json
from datetime import date

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar, RunCalendarPosition
from scripts.audit_atp_earth_week_mapping_v1 import SOURCE_FILE, build_projection

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def phase_evidence():
    return json.loads((SOURCE_FILE.parent / "phase_calendar_evidence" / "2024.json").read_text(encoding="utf-8"))


def test_phase_evidence_binds_to_canonical_2024_memberships_and_main_dates(phase_evidence):
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    by_identity = {r["source_identity"]: r for r in build_projection(source)["mappings"]}
    seasons = json.loads((SOURCE_FILE.parent / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]
    membership = next(s for s in seasons if s["year"] == 2024)
    rows = phase_evidence["occurrences"]
    assert phase_evidence["atp_season_year"] == 2024
    assert phase_evidence["sporting_schedule_installed"] is False
    assert len({r["occurrence_id"] for r in rows}) == len(rows)
    assert rows == sorted(rows, key=lambda r: (r["main_start_date"], r["series_id"]))
    for row in rows:
        canonical = by_identity[row["occurrence_id"]]
        assert (canonical["atp_season_year"], canonical["series_id"]) == (2024, row["series_id"])
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
        ("brisbane", ["2023-12-30","2023-12-31"], [[2023,52]], 1, "atp_250"),
        ("hong_kong", ["2023-12-31","2024-01-01"], [[2023,52],[2024,1]], 1, "atp_250"),
        ("adelaide", ["2024-01-07","2024-01-08"], [[2024,1],[2024,2]], 2, "atp_250"),
        ("auckland", ["2024-01-06","2024-01-07"], [[2024,1]], 2, "atp_250"),
        ("montpellier", ["2024-01-28","2024-01-29"], [[2024,4],[2024,5]], 5, "atp_250"),
        ("cordoba", ["2024-02-03","2024-02-04"], [[2024,5]], 6, "atp_250"),
        ("dallas", ["2024-02-04","2024-02-05"], [[2024,5],[2024,6]], 6, "atp_250"),
        ("lyon", ["2024-02-04","2024-02-05"], [[2024,5],[2024,6]], 6, "atp_250"),
    ],
)
def test_initial_2024_phase_positions(phase_evidence, series, q_dates, q_weeks, main_week, category):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["category_id"] == category
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == [[2024, main_week]]
    january = RunCalendar.earth_default(start_year=2024, season_count=2)
    shifted = RunCalendar(52, 37, 2023, 2)
    for year, week in q_weeks + [[2024, main_week]]:
        expected = None if year == 2023 else RunCalendarPosition(0, week, year, week)
        assert january.calendar_to_season(year, week) == expected
        shifted_week = week - 36 if year == 2023 else week + 16
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, shifted_week, year, week)


def test_brisbane_and_hong_kong_cross_year_opening_not_clamped(phase_evidence):
    rows = {r["series_id"]: r for r in phase_evidence["occurrences"]}
    assert rows["brisbane"]["main_opening_play_evidence"]["observed_iso_week"] == [2023, 52]
    assert rows["hong_kong"]["main_opening_play_evidence"]["observed_iso_week"] == [2024, 1]
    assert rows["lyon"]["historical_identity_evidence"]["actual_host"] == "Marseille, France"
    assert rows["dallas"]["category_id"] == "atp_250"
