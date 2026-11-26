"""Source-only ATP 2020 phase evidence; no sporting schedule is installed."""
import json
from datetime import date

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar, RunCalendarPosition
from scripts.audit_atp_earth_week_mapping_v1 import SOURCE_FILE, build_projection

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def phase_evidence():
    return json.loads((SOURCE_FILE.parent / "phase_calendar_evidence" / "2020.json").read_text(encoding="utf-8"))


def test_phase_evidence_binds_to_canonical_2020_memberships_and_main_dates(phase_evidence):
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    by_identity = {r["source_identity"]: r for r in build_projection(source)["mappings"]}
    seasons = json.loads((SOURCE_FILE.parent / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]
    membership = next(s for s in seasons if s["year"] == 2020)
    rows = phase_evidence["occurrences"]
    assert phase_evidence["atp_season_year"] == 2020
    assert phase_evidence["sporting_schedule_installed"] is False
    assert len({r["occurrence_id"] for r in rows}) == len(rows)
    assert rows == sorted(rows, key=lambda r: (r["main_start_date"], r["series_id"]))
    for row in rows:
        canonical = by_identity[row["occurrence_id"]]
        assert (canonical["atp_season_year"], canonical["series_id"]) == (2020, row["series_id"])
        assert row["series_id"] not in membership["known_not_held_series_ids"]
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


@pytest.mark.parametrize(("series", "q_dates", "q_weeks", "main_weeks"), [
    ("doha", ["2020-01-04","2020-01-05"], [[2020,1]], [[2020,2]]),
    ("adelaide", ["2020-01-11","2020-01-12"], [[2020,2]], [[2020,3]]),
    ("auckland", ["2020-01-11","2020-01-12"], [[2020,2]], [[2020,3]]),
    ("cordoba", ["2020-02-01","2020-02-02"], [[2020,5]], [[2020,6]]),
    ("hong_kong", ["2020-02-01","2020-02-02"], [[2020,5]], [[2020,6]]),
    ("montpellier", ["2020-02-02","2020-02-03"], [[2020,5],[2020,6]], [[2020,6]]),
    ("buenos_aires", ["2020-02-08","2020-02-09"], [[2020,6]], [[2020,7]]),
    ("dallas", ["2020-02-09","2020-02-10"], [[2020,6],[2020,7]], [[2020,7]]),
])
def test_initial_2020_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    assert row["qualifying_capacity_evidence"]["qualifying_rounds"] == 2
    assert row["qualifying_capacity_evidence"]["qualifier_places"] == 4
    january = RunCalendar.earth_default(start_year=2020, season_count=2)
    shifted = RunCalendar(52, 37, 2019, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, week + 16, year, week)


@pytest.mark.parametrize("series", ["adelaide", "montpellier", "dallas"])
def test_initial_2020_actual_main_overlap(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert (opening["observed_iso_week"] in row["main_year_weeks"]) == (series != "adelaide")


@pytest.mark.parametrize(("series", "host"), [
    ("hong_kong", "Pune, India"), ("dallas", "Long Island, New York, USA"),
])
def test_2020_stable_series_historical_host(phase_evidence, series, host):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["historical_identity_evidence"]["actual_host"] == host
    assert row["occurrence_id"] == f"atp_2020_{series}"
