"""Source-only ATP 2021 phase evidence; no sporting schedule is installed."""
import json
from datetime import date

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar, RunCalendarPosition
from scripts.audit_atp_earth_week_mapping_v1 import SOURCE_FILE, build_projection

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def phase_evidence():
    return json.loads((SOURCE_FILE.parent / "phase_calendar_evidence" / "2021.json").read_text(encoding="utf-8"))


def test_phase_evidence_binds_to_canonical_2021_memberships_and_main_dates(phase_evidence):
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    by_identity = {r["source_identity"]: r for r in build_projection(source)["mappings"]}
    seasons = json.loads((SOURCE_FILE.parent / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]
    membership = next(s for s in seasons if s["year"] == 2021)
    rows = phase_evidence["occurrences"]
    assert phase_evidence["atp_season_year"] == 2021
    assert phase_evidence["sporting_schedule_installed"] is False
    assert len({r["occurrence_id"] for r in rows}) == len(rows)
    assert rows == sorted(rows, key=lambda r: (r["main_start_date"], r["series_id"]))
    for row in rows:
        canonical = by_identity[row["occurrence_id"]]
        assert (canonical["atp_season_year"], canonical["series_id"]) == (2021, row["series_id"])
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
            assert row["main_start_date"] <= opening["date"] <= row["main_end_date"]
            if opening["date"] != row["main_start_date"]:
                assert row["source_disagreement"]["source_url"]
                assert row["source_disagreement"]["note"]
            assert opening["status"] == "played"
            assert list(date.fromisoformat(opening["date"]).isocalendar()[:2]) == opening["observed_iso_week"]


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("antalya_2021", ["2021-01-06","2021-01-07"], [[2021,1]], [[2021,1]]),
        ("delray_beach", ["2021-01-05","2021-01-06"], [[2021,1]], [[2021,1]]),
        ("melbourne_1_2021", [], [], [[2021,5]]),
        ("melbourne_2_2021", [], [], [[2021,5]]),
        ("cordoba", ["2021-02-20","2021-02-21","2021-02-22"], [[2021,7],[2021,8]], [[2021,8]]),
        ("montpellier", ["2021-02-21","2021-02-22"], [[2021,7],[2021,8]], [[2021,8]]),
        ("singapore_2021", ["2021-02-20","2021-02-21"], [[2021,7]], [[2021,8]]),
        ("buenos_aires", ["2021-02-27","2021-02-28","2021-03-01"], [[2021,8],[2021,9]], [[2021,9]]),
    ],
)
def test_initial_2021_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2021, season_count=2)
    shifted = RunCalendar(52, 37, 2020, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        season_index, season_week = (0, week + 16) if week <= 36 else (1, week - 36)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(season_index, season_week, year, week)


@pytest.mark.parametrize("series", ["melbourne_1_2021", "melbourne_2_2021"])
def test_2021_melbourne_expanded_main_without_qualifying(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["qualification_status"] == "not_applicable_no_onsite_qualifying"
    assert row["qualification_cancellation_evidence"]["main_draw_size"] == 56
    assert row["qualifying_date_evidence"] == row["observed_qualifying_iso_weeks"] == []
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize(("series", "rounds", "places"), [
    ("antalya_2021", 2, 6), ("cordoba", 3, 4), ("buenos_aires", 3, 4),
])
def test_2021_exceptional_qualifying_geometry_evidence(phase_evidence, series, rounds, places):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["qualifying_capacity_evidence"]["qualifying_rounds"] == rounds
    assert row["qualifying_capacity_evidence"]["qualifier_places"] == places
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize("series", ["cordoba", "montpellier", "buenos_aires"])
def test_2021_monday_qualifying_final_and_main_overlap(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["main_opening_play_evidence"]["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert row["main_opening_play_evidence"]["observed_iso_week"] in row["main_year_weeks"]
