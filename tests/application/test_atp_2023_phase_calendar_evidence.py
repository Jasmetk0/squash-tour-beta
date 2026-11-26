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
            assert row["main_start_date"] <= opening["date"] <= row["main_end_date"]
            if opening["date"] != row["main_start_date"]:
                assert row["source_disagreement"]["source_url"]
                assert row["source_disagreement"]["note"]
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
        ("delray_beach", ["2023-02-11","2023-02-12"], [[2023,6]], 7, "atp_250"),
        ("rotterdam", ["2023-02-11","2023-02-12"], [[2023,6]], 7, "atp_500"),
        ("doha", ["2023-02-18","2023-02-19"], [[2023,7]], 8, "atp_250"),
        ("lyon", ["2023-02-19","2023-02-20"], [[2023,7],[2023,8]], 8, "atp_250"),
        ("rio", ["2023-02-18","2023-02-19"], [[2023,7]], 8, "atp_500"),
        ("acapulco", ["2023-02-25","2023-02-26"], [[2023,8]], 9, "atp_500"),
        ("dubai", ["2023-02-25","2023-02-26"], [[2023,8]], 9, "atp_500"),
        ("santiago", ["2023-02-25","2023-02-26"], [[2023,8]], 9, "atp_250"),
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


def test_marseille_2023_actual_main_overlap_and_historical_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "lyon")
    assert row["historical_identity_evidence"]["actual_host"] == "Marseille, France"
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] == [2023, 8]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert opening["observed_iso_week"] in row["main_year_weeks"]
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("indian_wells", ["2023-03-06","2023-03-07"], [10], [10,11]),
        ("miami", ["2023-03-20","2023-03-21"], [12], [12,13]),
        ("estoril", ["2023-04-01","2023-04-02"], [13], [14]),
        ("houston", ["2023-04-01","2023-04-02"], [13], [14]),
        ("marrakech", ["2023-04-02","2023-04-03"], [13,14], [14]),
        ("monte_carlo", ["2023-04-08","2023-04-09"], [14], [15]),
        ("banja_luka", ["2023-04-16","2023-04-17"], [15,16], [16]),
        ("barcelona", ["2023-04-15","2023-04-16"], [15], [16]),
    ],
)
def test_spring_2023_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2023, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2023, w] for w in main_weeks]
    january = RunCalendar.earth_default(start_year=2023, season_count=2)
    shifted = RunCalendar(52, 37, 2022, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2023, week) == RunCalendarPosition(0, week, 2023, week)
        assert shifted.calendar_to_season(2023, week) == RunCalendarPosition(0, week + 16, 2023, week)


@pytest.mark.parametrize(
    ("series", "opening_week", "mapped_week"),
    [("marrakech", 14, 14), ("monte_carlo", 14, 15), ("banja_luka", 16, 16)],
)
def test_spring_2023_actual_main_opening_overlap(phase_evidence, series, opening_week, mapped_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] == [2023, opening_week]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert row["main_year_weeks"] == [[2023, mapped_week]]


def test_houston_2023_rain_compressed_main_not_qualifying(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "houston")
    assert row["observed_qualifying_iso_weeks"] == [[2023, 13]]
    assert row["main_year_weeks"] == [[2023, 14]]
    evidence = row["main_round_date_evidence"]
    assert evidence["basis"] == "official_ATP_report_of_winners_completed_rounds_not_full_draw_schedule"
    assert evidence["winner_rounds"] == [
        {"date": "2023-04-08", "physical_rounds": ["round_of_16", "quarterfinal"]},
        {"date": "2023-04-09", "physical_rounds": ["semifinal", "final"]},
    ]
    assert all(list(date.fromisoformat(r["date"]).isocalendar()[:2]) in row["main_year_weeks"]
               for r in evidence["winner_rounds"])
    assert phase_evidence["sporting_schedule_installed"] is False

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("munich", ["2023-04-15", "2023-04-16"], [15], [16]),
        ("madrid", ["2023-04-24", "2023-04-25"], [17], [17,18]),
        ("rome", ["2023-05-08", "2023-05-09"], [19], [19,20]),
        ("geneva", ["2023-05-20", "2023-05-21"], [20], [21]),
        ("lyon_old", ["2023-05-20", "2023-05-21"], [20], [21]),
        ("s_hertogenbosch", ["2023-06-10", "2023-06-11"], [23], [24]),
        ("stuttgart", ["2023-06-10", "2023-06-11"], [23], [24]),
        ("halle", ["2023-06-17", "2023-06-18"], [24], [25]),
    ],
)
def test_late_spring_2023_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2023, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2023, w] for w in main_weeks]
    january = RunCalendar.earth_default(start_year=2023, season_count=2)
    shifted = RunCalendar(52, 37, 2022, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2023, week) == RunCalendarPosition(0, week, 2023, week)
        assert shifted.calendar_to_season(2023, week) == RunCalendarPosition(0, week + 16, 2023, week)


@pytest.mark.parametrize("series", ["geneva", "lyon_old"])
def test_may_2023_actual_main_opening_precedes_projected_week(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"] == "2023-05-21"
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] == [2023, 20]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert row["main_year_weeks"] == [[2023, 21]]
    assert phase_evidence["sporting_schedule_installed"] is False


def test_2023_lyon_clay_and_marseille_remain_distinct(phase_evidence):
    rows = {r["series_id"]: r for r in phase_evidence["occurrences"]}
    assert rows["lyon_old"]["occurrence_id"] == "atp_2023_lyon_old"
    assert rows["lyon"]["occurrence_id"] == "atp_2023_lyon"
    assert rows["lyon_old"]["main_start_date"] == "2023-05-21"
    assert rows["lyon"]["main_start_date"] == "2023-02-20"

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("queens_club", ["2023-06-17", "2023-06-18"], [24], [25]),
        ("mallorca", ["2023-06-24", "2023-06-25"], [25], [26]),
        ("eastbourne", ["2023-06-24", "2023-06-25"], [25], [26]),
        ("bastad", ["2023-07-16", "2023-07-17"], [28,29], [29]),
        ("gstaad", ["2023-07-15", "2023-07-16"], [28], [29]),
        ("newport", ["2023-07-16", "2023-07-17"], [28,29], [29]),
        ("atlanta", ["2023-07-22", "2023-07-23"], [29], [30]),
        ("hamburg", ["2023-07-22", "2023-07-23"], [29], [30]),
    ],
)
def test_early_summer_2023_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2023, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2023, w] for w in main_weeks]
    january = RunCalendar.earth_default(start_year=2023, season_count=2)
    shifted = RunCalendar(52, 37, 2022, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2023, week) == RunCalendarPosition(0, week, 2023, week)
        assert shifted.calendar_to_season(2023, week) == RunCalendarPosition(0, week + 16, 2023, week)


@pytest.mark.parametrize(
    ("series", "opening_date", "opening_week", "mapped_week"),
    [
        ("mallorca", "2023-06-25", 25, 26),
        ("bastad", "2023-07-17", 29, 29),
        ("newport", "2023-07-17", 29, 29),
    ],
)
def test_early_summer_2023_actual_main_opening_overlap(
    phase_evidence, series, opening_date, opening_week, mapped_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["qualifying_date_evidence"][-1]["date"] == opening_date
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] == [2023, opening_week]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert row["main_year_weeks"] == [[2023, mapped_week]]
    assert phase_evidence["sporting_schedule_installed"] is False


def test_mallorca_2023_source_start_and_actual_main_opening_are_distinct(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "mallorca")
    assert row["main_start_date"] == "2023-06-24"
    assert row["main_opening_play_evidence"]["date"] == "2023-06-25"
    assert row["source_disagreement"]["source_url"]


def test_hamburg_2023_q_date_disagreement_retained_without_extra_play(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "hamburg")
    assert [e["date"] for e in row["qualifying_date_evidence"]] == ["2023-07-22", "2023-07-23"]
    assert row["observed_qualifying_iso_weeks"] == [[2023, 29]]
    assert row["main_year_weeks"] == [[2023, 30]]
    assert row["source_disagreement"]["source_url"] != row["source_confirmation"]["source_url"]
    assert row["additional_qualifying_first_round_source_url"]
    assert row["additional_qualifying_source_url"]

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("umag", ["2023-07-22","2023-07-23"], [29], [30]),
        ("kitzbuhel", ["2023-07-29","2023-07-30"], [30], [31]),
        ("los_cabos", ["2023-07-29","2023-07-30"], [30], [31]),
        ("washington", ["2023-07-29","2023-07-30"], [30], [31]),
        ("canadian_open", ["2023-08-05","2023-08-06"], [31], [32]),
        ("cincinnati", ["2023-08-12","2023-08-13"], [32], [33]),
        ("winston_salem", ["2023-08-19","2023-08-20"], [33], [34]),
        ("chengdu", ["2023-09-19","2023-09-20"], [38], [38]),
    ],
)
def test_late_summer_2023_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2023, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2023, w] for w in main_weeks]
    january = RunCalendar.earth_default(start_year=2023, season_count=2)
    shifted = RunCalendar(52, 37, 2022, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2023, week) == RunCalendarPosition(0, week, 2023, week)
        expected = RunCalendarPosition(0, week + 16, 2023, week) if week < 37 else RunCalendarPosition(1, week - 36, 2023, week)
        assert shifted.calendar_to_season(2023, week) == expected


@pytest.mark.parametrize("series", ["canadian_open", "cincinnati"])
def test_2023_north_american_masters_qualifying_capacity(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    evidence = row["qualifying_capacity_evidence"]
    assert evidence["qualifying_rounds"] == 2
    assert evidence["qualifier_places"] == 7
    assert evidence["source_url"]
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize(
    ("series", "opening_week", "mapped_week"),
    [("cincinnati", 32, 33), ("winston_salem", 33, 34), ("chengdu", 38, 38)],
)
def test_late_summer_2023_opening_overlaps_qualifying(phase_evidence, series, opening_week, mapped_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["main_opening_play_evidence"]["date"] == row["qualifying_date_evidence"][-1]["date"]
    assert row["main_opening_play_evidence"]["observed_iso_week"] == [2023, opening_week]
    assert row["main_year_weeks"] == [[2023, mapped_week]]


def test_chengdu_2023_source_finish_is_not_main_projection(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "chengdu")
    assert row["source_finish_iso_week"] == [2023, 39]
    assert row["source_finish_iso_week"] == list(date.fromisoformat(row["main_end_date"]).isocalendar()[:2])
    assert row["source_finish_iso_week"] not in row["main_year_weeks"]

@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("hangzhou", ["2023-09-19","2023-09-20"], [38], [38]),
        ("almaty", ["2023-09-26","2023-09-27"], [39], [39]),
        ("beijing", ["2023-09-26","2023-09-27"], [39], [39]),
        ("shanghai", ["2023-10-02","2023-10-03"], [40], [40,41]),
        ("brussels", ["2023-10-15","2023-10-16"], [41,42], [42]),
        ("stockholm", ["2023-10-14","2023-10-15"], [41], [42]),
        ("tokyo", ["2023-10-14","2023-10-15"], [41], [42]),
        ("basel", ["2023-10-21","2023-10-22"], [42], [43]),
    ],
)
def test_autumn_2023_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2023, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2023, w] for w in main_weeks]
    january = RunCalendar.earth_default(start_year=2023, season_count=2)
    shifted = RunCalendar(52, 37, 2022, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2023, week) == RunCalendarPosition(0, week, 2023, week)
        assert shifted.calendar_to_season(2023, week) == RunCalendarPosition(1, week - 36, 2023, week)


@pytest.mark.parametrize(
    ("series", "actual_host"),
    [("hangzhou", "Zhuhai, China"), ("almaty", "Astana, Kazakhstan"), ("brussels", "Antwerp, Belgium")],
)
def test_2023_relocated_series_retains_historical_host(phase_evidence, series, actual_host):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["occurrence_id"] == f"atp_2023_{series}"
    assert row["historical_identity_evidence"]["actual_host"] == actual_host
    assert row["historical_identity_evidence"]["source_url"]


@pytest.mark.parametrize(("series", "opening_week"), [("hangzhou", 38), ("brussels", 42)])
def test_autumn_2023_actual_main_opening_overlap(phase_evidence, series, opening_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["main_opening_play_evidence"]["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert row["main_opening_play_evidence"]["observed_iso_week"] == [2023, opening_week]


@pytest.mark.parametrize(("series", "finish_week"), [("hangzhou", 39), ("almaty", 40), ("beijing", 40)])
def test_autumn_2023_finish_outside_majority_projection(phase_evidence, series, finish_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["source_finish_iso_week"] == [2023, finish_week]
    assert row["source_finish_iso_week"] == list(date.fromisoformat(row["main_end_date"]).isocalendar()[:2])
    assert row["source_finish_iso_week"] not in row["main_year_weeks"]
