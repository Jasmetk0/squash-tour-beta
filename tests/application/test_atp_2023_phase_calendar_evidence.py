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
            assert opening["date"] == row["main_start_date"]
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
