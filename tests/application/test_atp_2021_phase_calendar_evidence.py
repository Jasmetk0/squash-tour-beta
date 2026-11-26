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

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("rotterdam", ["2021-02-27","2021-02-28"], [[2021,8]], [[2021,9]]),
        ("doha", ["2021-03-06","2021-03-07"], [[2021,9]], [[2021,10]]),
        ("lyon", ["2021-03-07","2021-03-08"], [[2021,9],[2021,10]], [[2021,10]]),
        ("santiago", ["2021-03-06","2021-03-07","2021-03-08"], [[2021,9],[2021,10]], [[2021,10]]),
        ("dubai", ["2021-03-13","2021-03-14"], [[2021,10]], [[2021,11]]),
        ("acapulco", ["2021-03-13","2021-03-14","2021-03-15"], [[2021,10],[2021,11]], [[2021,11]]),
        ("miami", ["2021-03-22","2021-03-23"], [[2021,12]], [[2021,12],[2021,13]]),
        ("cagliari_2021", ["2021-04-04","2021-04-05"], [[2021,13],[2021,14]], [[2021,14]]),
    ],
)
def test_spring_2021_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2021, season_count=2)
    shifted = RunCalendar(52, 37, 2020, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, week + 16, year, week)


@pytest.mark.parametrize(("series", "rounds", "places"), [
    ("santiago", 3, 4), ("acapulco", 3, 4), ("dubai", 2, 6), ("miami", 2, 12),
])
def test_spring_2021_qualifying_geometry(phase_evidence, series, rounds, places):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["qualifying_capacity_evidence"]["qualifying_rounds"] == rounds
    assert row["qualifying_capacity_evidence"]["qualifier_places"] == places
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize("series", ["santiago", "dubai", "acapulco", "cagliari_2021"])
def test_spring_2021_actual_main_overlap(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]


def test_2021_marseille_retains_lyon_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "lyon")
    assert row["occurrence_id"] == "atp_2021_lyon"
    assert row["historical_identity_evidence"]["actual_host"] == "Marseille, France"

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks", "places"),
    [
        ("marbella_2021", ["2021-04-04","2021-04-05"], [[2021,13],[2021,14]], [[2021,14]], 4),
        ("monte_carlo", ["2021-04-10","2021-04-11"], [[2021,14]], [[2021,15]], 7),
        ("barcelona", ["2021-04-17","2021-04-18"], [[2021,15]], [[2021,16]], 6),
        ("belgrade_clay_2021", ["2021-04-18","2021-04-19"], [[2021,15],[2021,16]], [[2021,16]], 4),
        ("estoril", ["2021-04-24","2021-04-25"], [[2021,16]], [[2021,17]], 4),
        ("munich", ["2021-04-24","2021-04-25"], [[2021,16]], [[2021,17]], 4),
        ("madrid", ["2021-05-01","2021-05-02"], [[2021,17]], [[2021,18]], 7),
        ("rome", ["2021-05-08","2021-05-09"], [[2021,18]], [[2021,19]], 7),
    ],
)
def test_april_may_2021_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks, places):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    assert row["qualifying_capacity_evidence"]["qualifying_rounds"] == 2
    assert row["qualifying_capacity_evidence"]["qualifier_places"] == places
    january = RunCalendar.earth_default(start_year=2021, season_count=2)
    shifted = RunCalendar(52, 37, 2020, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, week + 16, year, week)


@pytest.mark.parametrize("series", ["monte_carlo", "madrid", "rome"])
def test_2021_sunday_masters_opening_precedes_projection(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert opening["observed_iso_week"] not in row["main_year_weeks"]


@pytest.mark.parametrize("series", ["marbella_2021", "belgrade_clay_2021"])
def test_2021_april_monday_actual_overlap(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["main_opening_play_evidence"]["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert row["main_opening_play_evidence"]["observed_iso_week"] in row["main_year_weeks"]

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks", "places"),
    [
        ("geneva", ["2021-05-15","2021-05-16","2021-05-17"], [[2021,19],[2021,20]], [[2021,20]], 4),
        ("lyon_old", ["2021-05-16","2021-05-17"], [[2021,19],[2021,20]], [[2021,20]], 4),
        ("belgrade_2_2021", ["2021-05-22","2021-05-23"], [[2021,20]], [[2021,21]], 4),
        ("parma_2021", ["2021-05-22","2021-05-23"], [[2021,20]], [[2021,21]], 4),
        ("stuttgart", ["2021-06-07","2021-06-08"], [[2021,23]], [[2021,23]], 4),
        ("halle", ["2021-06-12","2021-06-13"], [[2021,23]], [[2021,24]], 6),
        ("queens_club", ["2021-06-12","2021-06-13"], [[2021,23]], [[2021,24]], 4),
        ("mallorca", ["2021-06-19","2021-06-20"], [[2021,24]], [[2021,25]], 4),
    ],
)
def test_may_june_2021_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks, places):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    assert row["qualifying_capacity_evidence"]["qualifying_rounds"] == 2
    assert row["qualifying_capacity_evidence"]["qualifier_places"] == places
    january = RunCalendar.earth_default(start_year=2021, season_count=2)
    shifted = RunCalendar(52, 37, 2020, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, week + 16, year, week)


@pytest.mark.parametrize("series", ["belgrade_2_2021", "parma_2021", "mallorca"])
def test_2021_sunday_opening_precedes_mapped_main(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["observed_iso_week"] not in row["main_year_weeks"]


def test_2021_geneva_delayed_opening_and_qualifying_overlap(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "geneva")
    assert row["main_start_date"] == "2021-05-16"
    assert row["main_opening_play_evidence"]["date"] == "2021-05-17"
    assert row["observed_qualifying_iso_weeks"] == [[2021, 19], [2021, 20]]
    assert row["main_year_weeks"] == [[2021, 20]]
    assert row["source_disagreement"]["source_url"]


def test_2021_separate_belgrade_and_lyon_occurrences(phase_evidence):
    rows = {r["series_id"]: r for r in phase_evidence["occurrences"]}
    for first, second in [("belgrade_clay_2021", "belgrade_2_2021"), ("lyon", "lyon_old")]:
        assert rows[first]["occurrence_id"] != rows[second]["occurrence_id"]
        assert rows[first]["main_end_date"] < rows[second]["main_start_date"]
