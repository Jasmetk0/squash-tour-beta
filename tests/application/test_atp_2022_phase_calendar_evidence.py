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

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("santiago", ["2022-02-19","2022-02-20"], [[2022,7]], [[2022,8]]),
        ("indian_wells", ["2022-03-08","2022-03-09"], [[2022,10]], [[2022,10],[2022,11]]),
        ("miami", ["2022-03-21","2022-03-22"], [[2022,12]], [[2022,12],[2022,13]]),
        ("houston", ["2022-04-02","2022-04-03"], [[2022,13]], [[2022,14]]),
        ("marrakech", ["2022-04-03","2022-04-04","2022-04-05"], [[2022,13],[2022,14]], [[2022,14]]),
        ("monte_carlo", ["2022-04-09","2022-04-10"], [[2022,14]], [[2022,15]]),
        ("banja_luka", ["2022-04-17","2022-04-18"], [[2022,15],[2022,16]], [[2022,16]]),
        ("barcelona", ["2022-04-16","2022-04-17"], [[2022,15]], [[2022,16]]),
    ],
)
def test_spring_2022_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2022, season_count=2)
    shifted = RunCalendar(52, 37, 2021, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, week + 16, year, week)


def test_2022_marrakech_rain_preserves_played_days_and_opening(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "marrakech")
    assert row["main_start_date"] == "2022-04-04"
    assert row["main_opening_play_evidence"]["date"] == "2022-04-05"
    assert row["main_opening_play_evidence"]["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert row["qualifying_date_evidence"][-2]["date"] == "2022-04-04"
    assert row["qualifying_date_evidence"][-2]["status"] == "played"


def test_2022_monte_carlo_opening_precedes_projected_main(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "monte_carlo")
    assert row["main_opening_play_evidence"]["observed_iso_week"] == [2022, 14]
    assert row["main_year_weeks"] == [[2022, 15]]


def test_2022_belgrade_retains_banja_luka_series(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "banja_luka")
    assert row["historical_identity_evidence"]["actual_host"] == "Belgrade, Serbia"
    assert row["occurrence_id"] == "atp_2022_banja_luka"


def test_2022_miami_qualifier_capacity_is_evidence_only(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "miami")
    assert row["qualifier_capacity_evidence"]["qualifier_places"] == 12
    assert phase_evidence["sporting_schedule_installed"] is False

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("estoril", ["2022-04-23","2022-04-24"], [[2022,16]], [[2022,17]]),
        ("munich", ["2022-04-23","2022-04-24"], [[2022,16]], [[2022,17]]),
        ("madrid", ["2022-04-30","2022-05-01"], [[2022,17]], [[2022,18]]),
        ("rome", ["2022-05-07","2022-05-08"], [[2022,18]], [[2022,19]]),
        ("geneva", ["2022-05-14","2022-05-15"], [[2022,19]], [[2022,20]]),
        ("lyon_old", ["2022-05-14","2022-05-15"], [[2022,19]], [[2022,20]]),
        ("s_hertogenbosch", ["2022-06-04","2022-06-06","2022-06-07"], [[2022,22],[2022,23]], [[2022,23]]),
        ("stuttgart", ["2022-06-04","2022-06-05"], [[2022,22]], [[2022,23]]),
    ],
)
def test_late_spring_2022_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2022, season_count=2)
    shifted = RunCalendar(52, 37, 2021, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, week + 16, year, week)


@pytest.mark.parametrize("series", ["madrid", "rome", "geneva", "lyon_old"])
def test_2022_sunday_main_opening_precedes_projected_main(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    observed = row["main_opening_play_evidence"]
    assert observed["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert observed["observed_iso_week"] not in row["main_year_weeks"]


def test_2022_rosmalen_delayed_qualification_overlaps_main(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "s_hertogenbosch")
    assert [e["date"] for e in row["qualifying_date_evidence"]] == ["2022-06-04", "2022-06-06", "2022-06-07"]
    assert row["observed_qualifying_iso_weeks"] == [[2022, 22], [2022, 23]]
    assert row["main_year_weeks"] == [[2022, 23]]
    assert row["main_opening_play_evidence"]["date"] == "2022-06-06"
    assert row["source_disagreement"]["source_url"]

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("halle", ["2022-06-11","2022-06-12"], [[2022,23]], [[2022,24]]),
        ("queens_club", ["2022-06-11","2022-06-12"], [[2022,23]], [[2022,24]]),
        ("mallorca", ["2022-06-18","2022-06-19"], [[2022,24]], [[2022,25]]),
        ("eastbourne", ["2022-06-18","2022-06-19"], [[2022,24]], [[2022,25]]),
        ("bastad", ["2022-07-10","2022-07-11"], [[2022,27],[2022,28]], [[2022,28]]),
        ("newport", ["2022-07-10","2022-07-11"], [[2022,27],[2022,28]], [[2022,28]]),
        ("gstaad", ["2022-07-17","2022-07-18"], [[2022,28],[2022,29]], [[2022,29]]),
        ("hamburg", ["2022-07-16","2022-07-17"], [[2022,28]], [[2022,29]]),
    ],
)
def test_early_summer_2022_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2022, season_count=2)
    shifted = RunCalendar(52, 37, 2021, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(0, week + 16, year, week)


@pytest.mark.parametrize("series", ["bastad", "newport", "gstaad"])
def test_2022_summer_monday_qualifying_overlaps_main(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert len(row["observed_qualifying_iso_weeks"]) == 2
    assert row["main_opening_play_evidence"]["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert row["main_opening_play_evidence"]["observed_iso_week"] in row["main_year_weeks"]


def test_2022_mallorca_sunday_opening_precedes_projected_main(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "mallorca")
    assert row["main_opening_play_evidence"]["date"] == "2022-06-19"
    assert row["main_opening_play_evidence"]["observed_iso_week"] == [2022, 24]
    assert row["main_year_weeks"] == [[2022, 25]]

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("atlanta", ["2022-07-23","2022-07-24"], [[2022,29]], [[2022,30]]),
        ("kitzbuhel", ["2022-07-23","2022-07-24"], [[2022,29]], [[2022,30]]),
        ("umag", ["2022-07-23","2022-07-24"], [[2022,29]], [[2022,30]]),
        ("los_cabos", ["2022-07-30","2022-07-31"], [[2022,30]], [[2022,31]]),
        ("washington", ["2022-07-30","2022-07-31"], [[2022,30]], [[2022,31]]),
        ("canadian_open", ["2022-08-06","2022-08-07"], [[2022,31]], [[2022,32]]),
        ("cincinnati", ["2022-08-13","2022-08-14"], [[2022,32]], [[2022,33]]),
        ("winston_salem", ["2022-08-20","2022-08-21"], [[2022,33]], [[2022,34]]),
    ],
)
def test_late_summer_2022_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2022, season_count=2)
    shifted = RunCalendar(52, 37, 2021, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        season_index, season_week = (0, week + 16) if week <= 36 else (1, week - 36)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(season_index, season_week, year, week)


@pytest.mark.parametrize("series", ["cincinnati", "winston_salem"])
def test_2022_late_summer_sunday_opening_precedes_projected_main(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["main_opening_play_evidence"]["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert row["main_opening_play_evidence"]["observed_iso_week"] not in row["main_year_weeks"]


@pytest.mark.parametrize(("series", "places"), [("washington", 6), ("canadian_open", 7), ("cincinnati", 7)])
def test_2022_north_america_capacity_evidence(phase_evidence, series, places):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["qualifier_capacity_evidence"]["qualifier_places"] == places
    assert phase_evidence["sporting_schedule_installed"] is False

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("metz", ["2022-09-18","2022-09-19"], [[2022,37],[2022,38]], [[2022,38]]),
        ("san_diego_2022", ["2022-09-17","2022-09-18"], [[2022,37]], [[2022,38]]),
        ("seoul_2022", ["2022-09-24","2022-09-25"], [[2022,38]], [[2022,39]]),
        ("sofia", ["2022-09-25","2022-09-26"], [[2022,38],[2022,39]], [[2022,39]]),
        ("tel_aviv_2022", ["2022-09-25","2022-09-26"], [[2022,38],[2022,39]], [[2022,39]]),
        ("almaty", ["2022-10-01","2022-10-02"], [[2022,39]], [[2022,40]]),
        ("tokyo", ["2022-10-01","2022-10-02"], [[2022,39]], [[2022,40]]),
        ("florence_2022", ["2022-10-08","2022-10-09"], [[2022,40]], [[2022,41]]),
    ],
)
def test_early_autumn_2022_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == main_weeks
    january = RunCalendar.earth_default(start_year=2022, season_count=2)
    shifted = RunCalendar(52, 37, 2021, 2)
    for year, week in q_weeks + main_weeks:
        assert january.calendar_to_season(year, week) == RunCalendarPosition(0, week, year, week)
        season_index, season_week = (0, week + 16) if week <= 36 else (1, week - 36)
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(season_index, season_week, year, week)


@pytest.mark.parametrize("series", ["metz", "sofia", "tel_aviv_2022"])
def test_2022_autumn_monday_qualifying_overlaps_main(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert len(row["observed_qualifying_iso_weeks"]) == 2
    assert row["main_opening_play_evidence"]["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert row["main_opening_play_evidence"]["observed_iso_week"] in row["main_year_weeks"]


def test_2022_astana_historical_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "almaty")
    assert row["historical_identity_evidence"]["actual_host"] == "Astana, Kazakhstan"
    assert row["category_id"] == next(r["category_id"] for r in phase_evidence["occurrences"] if r["series_id"] == "tokyo")
