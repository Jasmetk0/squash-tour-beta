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


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_week", "category"),
    [
        ("halle", ["2024-06-15","2024-06-16"], [24], 25, "atp_500"),
        ("queens_club", ["2024-06-15","2024-06-16"], [24], 25, "atp_500"),
        ("mallorca", ["2024-06-22","2024-06-23"], [25], 26, "atp_250"),
        ("eastbourne", ["2024-06-22","2024-06-23"], [25], 26, "atp_250"),
        ("bastad", ["2024-07-14","2024-07-15"], [28,29], 29, "atp_250"),
        ("gstaad", ["2024-07-13","2024-07-14"], [28], 29, "atp_250"),
        ("hamburg", ["2024-07-13","2024-07-14"], [28], 29, "atp_500"),
        ("newport", ["2024-07-14","2024-07-15"], [28,29], 29, "atp_250"),
    ],
)
def test_june_july_2024_phase_positions(phase_evidence, series, q_dates, q_weeks, main_week, category):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["category_id"] == category
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2024, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2024, main_week]]
    january = RunCalendar.earth_default(start_year=2024, season_count=2)
    shifted = RunCalendar(52, 37, 2023, 2)
    for week in sorted(set(q_weeks + [main_week])):
        assert january.calendar_to_season(2024, week) == RunCalendarPosition(0, week, 2024, week)
        assert shifted.calendar_to_season(2024, week) == RunCalendarPosition(0, week + 16, 2024, week)


@pytest.mark.parametrize(
    ("series", "opening_week", "main_week"),
    [("mallorca", 25, 26), ("bastad", 29, 29), ("newport", 29, 29)],
)
def test_june_july_2024_actual_main_opening_overlap(phase_evidence, series, opening_week, main_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] == [2024, opening_week]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert row["main_year_weeks"] == [[2024, main_week]]


def test_queens_2024_same_entrant_can_win_two_physical_rounds_same_day(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "queens_club")
    evidence = row["qualifying_round_date_evidence"]
    assert evidence["date"] == "2024-06-16"
    assert evidence["physical_rounds"] == [1, 2]
    assert evidence["same_entrant_two_wins"] is True
    assert evidence["basis"] == "national_federation_report_of_two_wins_same_day_not_exact_match_start_timestamps"
    assert evidence["date"] in [e["date"] for e in row["qualifying_date_evidence"]]
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_week", "category"),
    [
        ("umag", ["2024-07-20","2024-07-21"], [29], 30, "atp_250"),
        ("atlanta", ["2024-07-20","2024-07-21"], [29], 30, "atp_250"),
        ("kitzbuhel", ["2024-07-20","2024-07-21"], [29], 30, "atp_250"),
        ("washington", ["2024-07-27","2024-07-28"], [30], 31, "atp_500"),
        ("canadian_open", ["2024-08-04","2024-08-05","2024-08-06"], [31,32], 32, "atp_masters_1000"),
        ("cincinnati", ["2024-08-11","2024-08-12"], [32,33], 33, "atp_masters_1000"),
        ("winston_salem", ["2024-08-17","2024-08-18"], [33], 34, "atp_250"),
        ("chengdu", ["2024-09-17","2024-09-18"], [38], 38, "atp_250"),
    ],
)
def test_july_september_2024_phase_positions(phase_evidence, series, q_dates, q_weeks, main_week, category):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["category_id"] == category
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2024, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2024, main_week]]
    january = RunCalendar.earth_default(start_year=2024, season_count=2)
    shifted = RunCalendar(52, 37, 2023, 2)
    for week in sorted(set(q_weeks + [main_week])):
        assert january.calendar_to_season(2024, week) == RunCalendarPosition(0, week, 2024, week)
        season_index, season_week = (0, week + 16) if week <= 36 else (1, week - 36)
        assert shifted.calendar_to_season(2024, week) == RunCalendarPosition(
            season_index, season_week, 2024, week
        )


@pytest.mark.parametrize(
    ("series", "opening_week", "main_week"),
    [("umag", 29, 30), ("canadian_open", 32, 32), ("cincinnati", 33, 33), ("winston_salem", 33, 34)],
)
def test_july_august_2024_actual_main_opening_overlap(phase_evidence, series, opening_week, main_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] == [2024, opening_week]
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert row["main_year_weeks"] == [[2024, main_week]]


@pytest.mark.parametrize(
    ("series", "finish_week"),
    [("canadian_open", 33), ("cincinnati", 34), ("chengdu", 39)],
)
def test_2024_source_finish_not_clamped_to_majority_week(phase_evidence, series, finish_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["source_finish_iso_week"] == [2024, finish_week]
    assert list(date.fromisoformat(row["main_end_date"]).isocalendar()[:2]) == row["source_finish_iso_week"]
    assert row["source_finish_iso_week"] not in row["main_year_weeks"]


def test_cincinnati_2024_geometry_not_copied_from_2025(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "cincinnati")
    evidence = row["qualifying_geometry_evidence"]
    assert (evidence["physical_rounds"], evidence["qualifier_places"]) == (2, 7)
    assert evidence["status"] == "published_event_description_not_full_profile"
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks"),
    [
        ("hangzhou", ["2024-09-17","2024-09-18"], [38], [38]),
        ("tokyo", ["2024-09-23","2024-09-24"], [39], [39]),
        ("beijing", ["2024-09-24","2024-09-25"], [39], [39]),
        ("shanghai", ["2024-09-30","2024-10-01"], [40], [40,41]),
        ("almaty", ["2024-10-13","2024-10-14"], [41,42], [42]),
        ("brussels", ["2024-10-13","2024-10-14"], [41,42], [42]),
        ("stockholm", ["2024-10-12","2024-10-13"], [41], [42]),
        ("basel", ["2024-10-19","2024-10-20"], [42], [43]),
    ],
)
def test_autumn_2024_phase_positions(phase_evidence, series, q_dates, q_weeks, main_weeks):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2024, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2024, w] for w in main_weeks]
    january = RunCalendar.earth_default(start_year=2024, season_count=2)
    shifted = RunCalendar(52, 37, 2023, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2024, week) == RunCalendarPosition(0, week, 2024, week)
        assert shifted.calendar_to_season(2024, week) == RunCalendarPosition(1, week - 36, 2024, week)
    assert shifted.calendar_to_season(2024, 36) == RunCalendarPosition(0, 52, 2024, 36)
    assert shifted.calendar_to_season(2024, 37) == RunCalendarPosition(1, 1, 2024, 37)


@pytest.mark.parametrize("series", ["chengdu", "hangzhou", "almaty", "brussels"])
def test_autumn_2024_same_day_scored_main_and_qualifying(phase_evidence, series):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"] == row["qualifying_date_evidence"][-1]["date"]
    assert opening["status"] == "played"
    assert opening["observed_iso_week"] in row["observed_qualifying_iso_weeks"]
    assert opening["observed_iso_week"] in row["main_year_weeks"]


@pytest.mark.parametrize(("series", "finish_week"), [("hangzhou", 39), ("tokyo", 40), ("beijing", 40)])
def test_autumn_2024_finish_outside_majority_week(phase_evidence, series, finish_week):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["source_finish_iso_week"] == [2024, finish_week]
    assert list(date.fromisoformat(row["main_end_date"]).isocalendar()[:2]) == row["source_finish_iso_week"]
    assert row["source_finish_iso_week"] not in row["main_year_weeks"]


def test_antwerp_2024_preserves_brussels_licence_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "brussels")
    assert row["occurrence_id"] == "atp_2024_brussels"
    assert row["historical_identity_evidence"]["actual_host"] == "Antwerp, Belgium"
    assert row["historical_identity_evidence"]["source_event_id"] == 7485
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize(
    ("series", "q_dates", "q_week", "main_week", "opening"),
    [
        ("vienna", ["2024-10-19","2024-10-20"], 42, 43, False),
        ("paris_masters", ["2024-10-26","2024-10-27"], 43, 44, False),
        ("belgrade", ["2024-11-02","2024-11-03"], 44, 45, True),
        ("metz", ["2024-11-02","2024-11-03"], 44, 45, True),
    ],
)
def test_final_knockout_2024_phase_positions(phase_evidence, series, q_dates, q_week, main_week, opening):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2024, q_week]]
    assert row["main_year_weeks"] == [[2024, main_week]]
    if opening:
        assert row["main_opening_play_evidence"]["date"] == row["main_start_date"] == q_dates[-1]
        assert row["main_opening_play_evidence"]["observed_iso_week"] == [2024, q_week]
    else:
        assert q_dates[-1] < row["main_start_date"]
    january = RunCalendar.earth_default(start_year=2024, season_count=2)
    shifted = RunCalendar(52, 37, 2023, 2)
    for week in (q_week, main_week):
        assert january.calendar_to_season(2024, week) == RunCalendarPosition(0, week, 2024, week)
        assert shifted.calendar_to_season(2024, week) == RunCalendarPosition(1, week - 36, 2024, week)


@pytest.mark.parametrize(
    ("series", "main_week", "opening_week", "rule_section"),
    [("atp_finals", 46, 45, "4.01 B"), ("next_gen_atp_finals", 51, 51, "4.04 B")],
)
def test_2024_finals_no_onsite_qualifying(phase_evidence, series, main_week, opening_week, rule_section):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["qualification_status"] == "not_applicable_no_onsite_qualifying"
    assert row["qualifying_date_evidence"] == row["observed_qualifying_iso_weeks"] == []
    assert row["entry_selection_evidence"]["field_size"] == 8
    assert row["entry_selection_evidence"]["rule_section"] == rule_section
    assert row["main_year_weeks"] == [[2024, main_week]]
    assert row["main_opening_play_evidence"]["observed_iso_week"] == [2024, opening_week]
    january = RunCalendar.earth_default(start_year=2024, season_count=2)
    shifted = RunCalendar(52, 37, 2023, 2)
    for week in {main_week, opening_week}:
        assert january.calendar_to_season(2024, week) == RunCalendarPosition(0, week, 2024, week)
        assert shifted.calendar_to_season(2024, week) == RunCalendarPosition(1, week - 36, 2024, week)


def test_2024_finals_written_selection_rule_distinct_from_actual_field(phase_evidence):
    rows = {r["series_id"]: r for r in phase_evidence["occurrences"]}
    senior = rows["atp_finals"]["entry_selection_evidence"]
    young = rows["next_gen_atp_finals"]["entry_selection_evidence"]
    assert senior["selection_priority"] == {
        "top_ranked_players": 7,
        "eligible_current_year_grand_slam_winners_up_to": 2,
        "grand_slam_winner_rank_range": [8, 20],
        "then_ranked_players_from": 8,
        "direct_acceptances": 8,
    }
    assert young["maximum_age_throughout_calendar_year"] == 20
    assert (young["race_direct_acceptances"], young["wild_card_places_in_written_rule"]) == (7, 1)
    assert young["actual_field_source_url"] != young["source_url"]
    assert phase_evidence["sporting_schedule_installed"] is False


def test_2024_inventory_complete_but_not_sporting_certified(phase_evidence):
    rows = phase_evidence["occurrences"]
    canonical = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))["year_sources"]["2024"]["events"]
    assert len(rows) == len(canonical) == 62
    assert {r["series_id"] for r in rows} == {r["series_id"] for r in canonical}
    summary = phase_evidence["coverage_review"]
    assert summary["canonical_occurrences"] == summary["recorded_occurrences"] == len(rows)
    assert summary["occurrences_with_observed_qualifying_play"] == sum(
        any(e["status"] == "played" for e in r["qualifying_date_evidence"]) for r in rows
    ) == 60
    assert summary["no_onsite_qualifying_occurrences"] == sum(
        r.get("qualification_status") == "not_applicable_no_onsite_qualifying" for r in rows
    ) == 2
    assert all(r["observed_qualifying_iso_weeks"] or r.get("qualification_status") ==
               "not_applicable_no_onsite_qualifying" for r in rows)
    assert summary["occurrences_with_scheduled_only_day_evidence"] == sum(
        any(e["status"] == "scheduled" for e in r["qualifying_date_evidence"]) for r in rows
    )
    assert summary["qualifying_overlaps_projected_main_week"] == sum(
        any(w in r["main_year_weeks"] for w in r["observed_qualifying_iso_weeks"]) for r in rows
    )
    assert summary["observed_main_opening_outside_projection"] == sum(
        "main_opening_play_evidence" in r and
        r["main_opening_play_evidence"]["observed_iso_week"] not in r["main_year_weeks"] for r in rows
    )
    assert summary["source_finish_outside_projection"] == sum(
        list(date.fromisoformat(r["main_end_date"]).isocalendar()[:2]) not in r["main_year_weeks"]
        for r in rows
    )
    assert summary["three_week_main_review_only"] == sum(
        r.get("main_projection_review_only", False) for r in rows
    ) == 0
    assert summary["qualifying_before_january_run_start"] == sum(
        any(y < 2024 for y, _ in r["observed_qualifying_iso_weeks"]) for r in rows
    )
    assert summary["remaining_evidence_gaps"]
    assert summary["sporting_schedule_installed"] is phase_evidence["sporting_schedule_installed"] is False
