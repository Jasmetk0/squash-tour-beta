"""Source-only ATP 2022 phase evidence; no sporting schedule is installed."""
import json
from datetime import date

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar, RunCalendarPosition
from scripts.audit_atp_earth_week_mapping_v1 import SOURCE_FILE, build_projection

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def phase_evidence():
    return json.loads((SOURCE_FILE.parent / "phase_calendar_evidence" / "2022.json").read_text(encoding="utf-8"))


def test_phase_evidence_binds_to_canonical_2022_memberships_and_main_dates(phase_evidence):
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    by_identity = {r["source_identity"]: r for r in build_projection(source)["mappings"]}
    seasons = json.loads((SOURCE_FILE.parent / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]
    membership = next(s for s in seasons if s["year"] == 2022)
    rows = phase_evidence["occurrences"]
    assert phase_evidence["atp_season_year"] == 2022
    assert phase_evidence["sporting_schedule_installed"] is False
    assert len({r["occurrence_id"] for r in rows}) == len(rows)
    assert rows == sorted(rows, key=lambda r: (r["main_start_date"], r["series_id"]))
    for row in rows:
        canonical = by_identity[row["occurrence_id"]]
        assert (canonical["atp_season_year"], canonical["series_id"]) == (2022, row["series_id"])
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
        ("adelaide", ["2022-01-02","2022-01-03"], [[2021,52],[2022,1]], [[2022,1]]),
        ("melbourne_2022", ["2022-01-03","2022-01-04"], [[2022,1]], [[2022,1]]),
        ("adelaide_2", ["2022-01-09","2022-01-10"], [[2022,1],[2022,2]], [[2022,2]]),
        ("sydney_2022", ["2022-01-09","2022-01-10"], [[2022,1],[2022,2]], [[2022,2]]),
        ("cordoba", ["2022-01-29","2022-01-30"], [[2022,4]], [[2022,5]]),
        ("hong_kong", ["2022-01-30","2022-01-31"], [[2022,4],[2022,5]], [[2022,5]]),
        ("montpellier", ["2022-01-30","2022-01-31"], [[2022,4],[2022,5]], [[2022,5]]),
        ("buenos_aires", ["2022-02-05","2022-02-06"], [[2022,5]], [[2022,6]]),
    ],
)
def test_initial_2022_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2022, season_count=2)
    shifted = RunCalendar(52, 37, 2021, 2)
    for year, week in q_weeks + main_weeks:
        expected = None if year == 2021 else RunCalendarPosition(0, week, year, week)
        assert january.calendar_to_season(year, week) == expected
        shifted_week = week - 36 if year == 2021 else week + 16
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, shifted_week, year, week)


@pytest.mark.parametrize("series", ["adelaide", "melbourne_2022", "adelaide_2", "sydney_2022", "hong_kong", "montpellier"])
def test_initial_2022_actual_opening_on_final_qualifying_date(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert opening["status"] == "played"


def test_2022_pune_retains_hong_kong_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "hong_kong")
    assert row["occurrence_id"] == "atp_2022_hong_kong"
    assert row["historical_identity_evidence"]["actual_host"] == "Pune, India"
    assert phase_evidence["sporting_schedule_installed"] is False

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("dallas", ["2022-02-06","2022-02-07"], [[2022,5],[2022,6]], [[2022,6]]),
        ("rotterdam", ["2022-02-05","2022-02-06"], [[2022,5]], [[2022,6]]),
        ("delray_beach", ["2022-02-12","2022-02-13"], [[2022,6]], [[2022,7]]),
        ("doha", ["2022-02-12","2022-02-13"], [[2022,6]], [[2022,7]]),
        ("lyon", ["2022-02-13","2022-02-14"], [[2022,6],[2022,7]], [[2022,7]]),
        ("rio", ["2022-02-12","2022-02-13"], [[2022,6]], [[2022,7]]),
        ("acapulco", ["2022-02-19","2022-02-20"], [[2022,7]], [[2022,8]]),
        ("dubai", ["2022-02-19","2022-02-20"], [[2022,7]], [[2022,8]]),
    ],
)
def test_february_2022_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2022, season_count=2)
    shifted = RunCalendar(52, 37, 2021, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, week + 16, year, week)


@pytest.mark.parametrize("series", ["dallas", "lyon"])
def test_february_2022_actual_opening_on_final_qualifying_date(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert opening["status"] == "played"


def test_2022_marseille_retains_lyon_series_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "lyon")
    assert row["occurrence_id"] == "atp_2022_lyon"
    assert row["historical_identity_evidence"]["actual_host"] == "Marseille, France"
    assert row["historical_identity_evidence"]["source_event_id"] == 496
    assert phase_evidence["sporting_schedule_installed"] is False
