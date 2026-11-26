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
