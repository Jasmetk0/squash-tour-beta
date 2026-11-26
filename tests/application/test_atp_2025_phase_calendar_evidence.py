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


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_week", "january_q", "shifted_q", "shifted_main"),
    [
        ("hong_kong", ["2024-12-29", "2024-12-30"], [[2024, 52], [2025, 1]],
         1, [None, 1], [16, 17], 17),
        ("auckland", ["2025-01-04", "2025-01-05"], [[2025, 1]],
         2, [1], [17], 18),
        ("montpellier", ["2025-01-26", "2025-01-27"], [[2025, 4], [2025, 5]],
         5, [4, 5], [20, 21], 21),
        ("lyon", ["2025-02-09", "2025-02-10"], [[2025, 6], [2025, 7]],
         7, [6, 7], [22, 23], 23),
    ],
)
def test_modern_phase_dates_and_native_positions(
    phase_evidence, series, q_dates, q_weeks, main_week, january_q, shifted_q, shifted_main
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == q_weeks
    assert row["main_year_weeks"] == [[2025, main_week]]
    assert (row["main_start_date"] in q_dates) == (series != "auckland")

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for (year, week), jan_week, shifted_week in zip(q_weeks, january_q, shifted_q):
        jan_expected = (
            None if jan_week is None else RunCalendarPosition(0, jan_week, year, week)
        )
        assert january.calendar_to_season(year, week) == jan_expected
        assert shifted.calendar_to_season(year, week) == RunCalendarPosition(
            0, shifted_week, year, week
        )
    assert january.calendar_to_season(2025, main_week) == RunCalendarPosition(
        0, main_week, 2025, main_week
    )
    assert shifted.calendar_to_season(2025, main_week) == RunCalendarPosition(
        0, shifted_main, 2025, main_week
    )


@pytest.mark.parametrize(
    ("series", "q_dates", "q_week", "main_week"),
    [
        ("dallas", ["2025-02-01", "2025-02-02"], 5, 6),
        ("rotterdam", ["2025-02-01", "2025-02-02"], 5, 6),
        ("buenos_aires", ["2025-02-08", "2025-02-09"], 6, 7),
        ("delray_beach", ["2025-02-08", "2025-02-09"], 6, 7),
        ("doha", ["2025-02-15", "2025-02-16"], 7, 8),
        ("rio", ["2025-02-15", "2025-02-16"], 7, 8),
        ("acapulco", ["2025-02-22", "2025-02-23"], 8, 9),
        ("dubai", ["2025-02-22", "2025-02-23"], 8, 9),
        ("santiago", ["2025-02-22", "2025-02-23"], 8, 9),
    ],
)
def test_adjacent_week_phase_dates_and_native_positions(
    phase_evidence, series, q_dates, q_week, main_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert q_dates[-1] < row["main_start_date"]
    assert row["observed_qualifying_iso_weeks"] == [[2025, q_week]]
    assert row["main_year_weeks"] == [[2025, main_week]]
    assert main_week == q_week + 1

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in (q_week, main_week):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(
            0, week, 2025, week
        )
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(
            0, week + 16, 2025, week
        )


@pytest.mark.parametrize(
    ("series", "q_dates", "first_main_week"),
    [
        ("indian_wells", ["2025-03-03", "2025-03-04"], 10),
        ("miami", ["2025-03-17", "2025-03-18"], 12),
    ],
)
def test_masters_two_week_main_preserves_same_week_qualifying(
    phase_evidence, series, q_dates, first_main_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["category_id"] == "atp_masters_1000"
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert q_dates[-1] < row["main_start_date"]
    assert row["observed_qualifying_iso_weeks"] == [[2025, first_main_week]]
    assert row["main_year_weeks"] == [[2025, first_main_week], [2025, first_main_week + 1]]
    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in (first_main_week, first_main_week + 1):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(0, week, 2025, week)
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(0, week + 16, 2025, week)


def test_marseille_2025_retains_relocated_licence_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "lyon")
    assert row["occurrence_id"] == "atp_2025_lyon"
    assert row["historical_identity_evidence"]["actual_host"] == "Marseille, France"
    assert row["historical_identity_evidence"]["source_event_id"] == 496
    assert not any(r["series_id"] == "lyon_old" for r in phase_evidence["occurrences"])


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks", "opening_iso_week"),
    [
        ("bucharest", ["2025-03-30", "2025-03-31"], [13, 14], [14], 14),
        ("houston", ["2025-03-29", "2025-03-30"], [13], [14], None),
        ("marrakech", ["2025-03-30", "2025-03-31"], [13, 14], [14], 14),
        ("monte_carlo", ["2025-04-05", "2025-04-06"], [14], [15], 14),
        ("barcelona", ["2025-04-12", "2025-04-13"], [15], [16], None),
        ("munich", ["2025-04-12", "2025-04-13"], [15], [16], None),
        ("madrid", ["2025-04-21", "2025-04-22"], [17], [17, 18], None),
        ("rome", ["2025-05-05", "2025-05-06"], [19], [19, 20], None),
    ],
)
def test_spring_phase_positions_preserve_source_overlap(
    phase_evidence, series, q_dates, q_weeks, main_weeks, opening_iso_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2025, week] for week in q_weeks]
    assert row["main_year_weeks"] == [[2025, week] for week in main_weeks]
    assert (q_dates[-1] == row["main_start_date"]) == (opening_iso_week is not None)

    if opening_iso_week is not None:
        opening = row["main_opening_play_evidence"]
        assert opening["status"] == "played"
        assert opening["date"] == row["main_start_date"]
        assert opening["observed_iso_week"] == [2025, opening_iso_week]
        assert date.fromisoformat(opening["date"]).isocalendar()[:2] == (2025, opening_iso_week)
        assert opening_iso_week in q_weeks
        if series == "monte_carlo":
            assert opening_iso_week not in main_weeks

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(0, week, 2025, week)
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(0, week + 16, 2025, week)


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_week", "opening_week"),
    [
        ("geneva", ["2025-05-17", "2025-05-18"], [20], 21, 20),
        ("hamburg", ["2025-05-17", "2025-05-18"], [20], 21, 20),
        ("stuttgart", ["2025-06-07", "2025-06-08"], [23], 24, None),
        ("s_hertogenbosch", ["2025-06-07", "2025-06-08", "2025-06-09"], [23, 24], 24, 24),
        ("halle", ["2025-06-14", "2025-06-15"], [24], 25, None),
        ("queens_club", ["2025-06-14", "2025-06-15"], [24], 25, None),
        ("mallorca", ["2025-06-21", "2025-06-22"], [25], 26, 25),
        ("eastbourne", ["2025-06-21", "2025-06-22"], [25], 26, None),
    ],
)
def test_may_june_phase_positions_and_observed_opening(
    phase_evidence, series, q_dates, q_weeks, main_week, opening_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2025, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2025, main_week]]
    if opening_week is not None:
        opening = row["main_opening_play_evidence"]
        assert opening["status"] == "played"
        assert opening["date"] == q_dates[-1] == row["main_start_date"]
        assert opening["observed_iso_week"] == [2025, opening_week]
        assert date.fromisoformat(opening["date"]).isocalendar()[:2] == (2025, opening_week)
        assert opening_week in q_weeks
        assert (opening_week == main_week) == (series == "s_hertogenbosch")
    else:
        assert q_dates[-1] < row["main_start_date"]
        assert "main_opening_play_evidence" not in row

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in sorted(set(q_weeks + [main_week])):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(0, week, 2025, week)
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(0, week + 16, 2025, week)


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks", "opening_week"),
    [
        ("bastad", ["2025-07-13", "2025-07-14"], [28, 29], [29], 29),
        ("gstaad", ["2025-07-12", "2025-07-13"], [28], [29], None),
        ("los_cabos", ["2025-07-12", "2025-07-13"], [28], [29], None),
        ("kitzbuhel", ["2025-07-19", "2025-07-20"], [29], [30], None),
        ("umag", ["2025-07-19", "2025-07-20"], [29], [30], 29),
        ("washington", ["2025-07-19", "2025-07-20"], [29], [30], None),
        ("canadian_open", ["2025-07-26", "2025-07-27"], [30], [30, 31, 32], 30),
        ("cincinnati", ["2025-08-05", "2025-08-06"], [32], [32, 33, 34], None),
    ],
)
def test_summer_phase_positions_and_review_only_masters(
    phase_evidence, series, q_dates, q_weeks, main_weeks, opening_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2025, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2025, w] for w in main_weeks]
    assert row.get("main_projection_review_only", False) == (len(main_weeks) == 3)
    if opening_week is not None:
        opening = row["main_opening_play_evidence"]
        assert opening["status"] == "played"
        assert opening["date"] == q_dates[-1] == row["main_start_date"]
        assert opening["observed_iso_week"] == [2025, opening_week]
        assert date.fromisoformat(opening["date"]).isocalendar()[:2] == (2025, opening_week)
        assert opening_week in q_weeks
    else:
        assert q_dates[-1] < row["main_start_date"]

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in sorted(set(q_weeks + main_weeks)):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(0, week, 2025, week)
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(0, week + 16, 2025, week)


@pytest.mark.parametrize(
    ("series", "entrants", "rounds", "places"),
    [("canadian_open", 32, 1, 16), ("cincinnati", 48, 2, 12)],
)
def test_summer_masters_qualifying_geometry_not_inferred_from_duration(
    phase_evidence, series, entrants, rounds, places
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    geometry = row["qualifying_geometry_evidence"]
    assert (geometry["entrants"], geometry["physical_rounds"], geometry["qualifier_places"]) == (
        entrants, rounds, places
    )
    assert entrants == places * 2 ** rounds
    assert len(row["qualifying_date_evidence"]) == 2
    assert row["main_projection_review_only"] is True
    assert phase_evidence["sporting_schedule_installed"] is False


@pytest.mark.parametrize(
    ("series", "q_dates", "q_weeks", "main_weeks", "opening_week", "finish_week"),
    [
        ("winston_salem", ["2025-08-16", "2025-08-17"], [33], [34], 33, None),
        ("chengdu", ["2025-09-16", "2025-09-17"], [38], [38], 38, 39),
        ("hangzhou", ["2025-09-16", "2025-09-17"], [38], [38], 38, 39),
        ("tokyo", ["2025-09-22", "2025-09-23"], [39], [39], None, 40),
        ("beijing", ["2025-09-23", "2025-09-24"], [39], [39], None, 40),
        ("shanghai", ["2025-09-29", "2025-09-30"], [40], [40, 41], None, None),
        ("almaty", ["2025-10-11", "2025-10-12"], [41], [42], None, None),
        ("brussels", ["2025-10-12", "2025-10-13"], [41, 42], [42], 42, None),
    ],
)
def test_late_summer_autumn_phase_positions_across_shifted_season_boundary(
    phase_evidence, series, q_dates, q_weeks, main_weeks, opening_week, finish_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2025, w] for w in q_weeks]
    assert row["main_year_weeks"] == [[2025, w] for w in main_weeks]
    assert (q_dates[-1] == row["main_start_date"]) == (opening_week is not None)
    if opening_week is not None:
        opening = row["main_opening_play_evidence"]
        assert opening["status"] == "played"
        assert opening["date"] == row["main_start_date"]
        assert opening["observed_iso_week"] == [2025, opening_week]
        assert date.fromisoformat(opening["date"]).isocalendar()[:2] == (2025, opening_week)
    if finish_week is not None:
        assert row["source_finish_iso_week"] == [2025, finish_week]
        assert date.fromisoformat(row["main_end_date"]).isocalendar()[:2] == (2025, finish_week)
        assert finish_week not in main_weeks

    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in sorted(set(q_weeks + main_weeks + ([finish_week] if finish_week else []))):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(0, week, 2025, week)
        season_index, season_week = (0, week + 16) if week <= 36 else (1, week - 36)
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(
            season_index, season_week, 2025, week
        )

    assert shifted.calendar_to_season(2025, 36) == RunCalendarPosition(0, 52, 2025, 36)
    assert shifted.calendar_to_season(2025, 37) == RunCalendarPosition(1, 1, 2025, 37)


@pytest.mark.parametrize(
    ("series", "q_dates", "q_week", "main_week", "actual_opening"),
    [
        ("stockholm", ["2025-10-11", "2025-10-12"], 41, 42, False),
        ("basel", ["2025-10-18", "2025-10-19"], 42, 43, False),
        ("vienna", ["2025-10-18", "2025-10-19"], 42, 43, False),
        ("paris_masters", ["2025-10-25", "2025-10-26"], 43, 44, False),
        ("belgrade", ["2025-11-01", "2025-11-02"], 44, 45, True),
        ("metz", ["2025-11-01", "2025-11-02"], 44, 45, True),
    ],
)
def test_final_knockout_phase_dates_and_native_positions(
    phase_evidence, series, q_dates, q_week, main_week, actual_opening
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert [e["date"] for e in row["qualifying_date_evidence"] if e["status"] == "played"] == q_dates
    assert row["observed_qualifying_iso_weeks"] == [[2025, q_week]]
    assert row["main_year_weeks"] == [[2025, main_week]]
    if actual_opening:
        opening = row["main_opening_play_evidence"]
        assert opening["status"] == "played"
        assert opening["date"] == q_dates[-1] == row["main_start_date"]
        assert opening["observed_iso_week"] == [2025, q_week]
    else:
        assert q_dates[-1] < row["main_start_date"]
    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in (q_week, main_week):
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(0, week, 2025, week)
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(1, week - 36, 2025, week)


@pytest.mark.parametrize(
    ("series", "category", "method", "main_week", "opening_week"),
    [
        ("atp_finals", "atp_finals", "season_race_with_grand_slam_exception", 46, 45),
        ("next_gen_atp_finals", "next_gen_finals", "age_restricted_season_race", 51, 51),
    ],
)
def test_finals_have_selection_evidence_not_fabricated_qualifying(
    phase_evidence, series, category, method, main_week, opening_week
):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == series)
    assert row["category_id"] == category
    assert row["qualification_status"] == "not_applicable_no_onsite_qualifying"
    assert row["qualifying_date_evidence"] == row["observed_qualifying_iso_weeks"] == []
    assert row["entry_selection_evidence"]["method"] == method
    assert row["entry_selection_evidence"]["field_size"] == 8
    assert row["main_year_weeks"] == [[2025, main_week]]
    opening = row["main_opening_play_evidence"]
    assert opening["date"] == row["main_start_date"]
    assert opening["observed_iso_week"] == [2025, opening_week]
    assert date.fromisoformat(opening["date"]).isocalendar()[:2] == (2025, opening_week)
    january = RunCalendar.earth_default(start_year=2025, season_count=2)
    shifted = RunCalendar(52, 37, 2024, 2)
    for week in {main_week, opening_week}:
        assert january.calendar_to_season(2025, week) == RunCalendarPosition(0, week, 2025, week)
        assert shifted.calendar_to_season(2025, week) == RunCalendarPosition(1, week - 36, 2025, week)


def test_athens_2025_preserves_belgrade_licence_identity(phase_evidence):
    row = next(r for r in phase_evidence["occurrences"] if r["series_id"] == "belgrade")
    assert row["occurrence_id"] == "atp_2025_belgrade"
    assert row["historical_identity_evidence"]["actual_host"] == "Athens, Greece"
    assert row["historical_identity_evidence"]["source_event_id"] == 5100


def test_2025_phase_inventory_is_complete_but_not_sporting_certified(phase_evidence):
    rows = phase_evidence["occurrences"]
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    canonical = source["year_sources"]["2025"]["events"]
    assert len(rows) == len(canonical) == 57
    assert {r["series_id"] for r in rows} == {r["series_id"] for r in canonical}
    assert rows == sorted(rows, key=lambda r: (r["main_start_date"], r["series_id"]))
    summary = phase_evidence["coverage_review"]
    assert summary["canonical_occurrences"] == summary["recorded_occurrences"] == len(rows)
    assert summary["occurrences_with_observed_qualifying_play"] == sum(
        any(e["status"] == "played" for e in r["qualifying_date_evidence"]) for r in rows
    ) == 55
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
    ) == 2
    assert summary["qualifying_before_january_run_start"] == sum(
        any(y < 2025 for y, _ in r["observed_qualifying_iso_weeks"]) for r in rows
    )
    assert summary["remaining_evidence_gaps"]
    assert summary["sporting_schedule_installed"] is phase_evidence["sporting_schedule_installed"] is False
