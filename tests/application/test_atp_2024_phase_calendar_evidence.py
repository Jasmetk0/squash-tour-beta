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
        ("buenos_aires", ["2024-02-10","2024-02-11"], [[2024,6]], 7, "atp_250"),
        ("delray_beach", ["2024-02-10","2024-02-11","2024-02-12"], [[2024,6],[2024,7]], 7, "atp_250"),
        ("rotterdam", ["2024-02-10","2024-02-11"], [[2024,6]], 7, "atp_500"),
        ("doha", ["2024-02-17","2024-02-18"], [[2024,7]], 8, "atp_250"),
        ("los_cabos", ["2024-02-17","2024-02-18"], [[2024,7]], 8, "atp_250"),
        ("rio", ["2024-02-17","2024-02-18"], [[2024,7]], 8, "atp_500"),
        ("acapulco", ["2024-02-24","2024-02-25"], [[2024,8]], 9, "atp_500"),
        ("dubai", ["2024-02-24","2024-02-25"], [[2024,8]], 9, "atp_500"),
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


@pytest.mark.parametrize("series", ["dallas", "delray_beach"])
def test_february_2024_q_finals_and_scored_main_opening_overlap(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["status"] == "played"
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert opening["observed_iso_week"] in row["main_year_weeks"]


def test_los_cabos_2024_published_capacity_not_a_sporting_profile(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "los_cabos")
    evidence = row["draw_capacity_evidence"]
    assert (evidence["main_places"], evidence["qualifier_places"]) == (28, 4)
    assert evidence["status"] == "published_event_description_not_full_profile"
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("santiago", ["2024-02-24","2024-02-25"], [8], [9]),
        ("indian_wells", ["2024-03-04","2024-03-05"], [10], [10,11]),
        ("miami", ["2024-03-18","2024-03-19"], [12], [12,13]),
        ("estoril", ["2024-03-30","2024-03-31"], [13], [14]),
        ("houston", ["2024-03-30","2024-03-31"], [13], [14]),
        ("marrakech", ["2024-03-31","2024-04-01"], [13,14], [14]),
        ("monte_carlo", ["2024-04-06","2024-04-07"], [14], [15]),
        ("barcelona", ["2024-04-13","2024-04-14"], [15], [16]),
    ],
)
def test_spring_2024_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2024, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2024, w] for w in main_weeks]
    january = RunCalendar.earth_default(start_year=2024, season_count=2)
    shifted = RunCalendar(52, 37, 2023, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2024, week) == RunCalendarPosition(0, week, 2024, week)
        assert shifted.calendar_to_season(2024, week) == RunCalendarPosition(0, week + 16, 2024, week)


@pytest.mark.parametrize(
    ("series", "opening_week", "mapped_week"),
    [("marrakech", 14, 14), ("monte_carlo", 14, 15)],
)
def test_spring_2024_actual_main_opening_overlap(phase_evidence, series, opening_week, mapped_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] == [2024, opening_week]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert row["main_year_weeks"] == [[2024, mapped_week]]
    assert (opening["observed_iso_week"] in row["main_year_weeks"]) == (series == "marrakech")


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks", "category"),
    [
        ("bucharest", ["2024-04-14","2024-04-15"], [15,16], [16], "atp_250"),
        ("munich", ["2024-04-13","2024-04-14"], [15], [16], "atp_250"),
        ("madrid", ["2024-04-22","2024-04-23"], [17], [17,18], "atp_masters_1000"),
        ("rome", ["2024-05-06","2024-05-07"], [19], [19,20], "atp_masters_1000"),
        ("geneva", ["2024-05-18","2024-05-19"], [20], [21], "atp_250"),
        ("lyon_old", ["2024-05-18","2024-05-19"], [20], [21], "atp_250"),
        ("s_hertogenbosch", ["2024-06-08","2024-06-09"], [23], [24], "atp_250"),
        ("stuttgart", ["2024-06-08","2024-06-09"], [23], [24], "atp_250"),
    ],
)
def test_april_june_2024_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks, category):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["category_id"] == category
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2024, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2024, w] for w in main_weeks]
    january = RunCalendar.earth_default(start_year=2024, season_count=2)
    shifted = RunCalendar(52, 37, 2023, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2024, week) == RunCalendarPosition(0, week, 2024, week)
        assert shifted.calendar_to_season(2024, week) == RunCalendarPosition(0, week + 16, 2024, week)


@pytest.mark.parametrize(
    ("series", "opening_week", "mapped_week"),
    [("bucharest", 16, 16), ("geneva", 20, 21), ("lyon_old", 20, 21)],
)
def test_april_may_2024_actual_main_opening_overlap(phase_evidence, series, opening_week, mapped_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] == [2024, opening_week]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert row["main_year_weeks"] == [[2024, mapped_week]]


def test_2024_lyon_clay_and_marseille_are_distinct_licences(phase_evidence):
    rows = {r["series_id"]: r for r in phase_evidence["occurrences"]}
    assert rows["lyon_old"]["historical_identity_evidence"]["actual_host"] == "Lyon, France"
    assert rows["lyon"]["historical_identity_evidence"]["actual_host"] == "Marseille, France"
    assert rows["lyon_old"]["occurrence_id"] != rows["lyon"]["occurrence_id"]


def test_stuttgart_2024_qualifying_round_dates_not_one_round_per_day(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "stuttgart")
    evidence = row["qualifying_round_date_evidence"]
    assert evidence["basis"] == "dated_scored_result_records_not_start_completion_timestamps"
    assert [(r["date"], r["physical_round"], r["scored_matches"]) for r in evidence["rounds"]] == [
        ("2024-06-08", 1, 6), ("2024-06-09", 1, 2), ("2024-06-09", 2, 4)
    ]
    assert {r["date"] for r in evidence["rounds"]} == {e["date"] for e in row["qualifying_date_evidence"]}
    assert phase_evidence["sporting_schedule_installed"] is False
