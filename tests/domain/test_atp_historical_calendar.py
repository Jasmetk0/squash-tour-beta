"""Deterministic, source-only 1990–2026 ATP reference date/ISO week contract."""
from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import CanonicalPackageDocument, PackageType
from scripts.build_atp_historical_calendar import (
    SOURCE, build, canonical, iso_weeks_touched, project_iso_week_to_run_w52,
)

pytestmark = pytest.mark.pr_critical


def sources():
    return tuple(json.loads((SOURCE / name).read_text(encoding="utf-8"))
                 for name in (
                     "category.json", "series.json", "seasons_1990_2026.json",
                     "calendar_dates_v1.json",
                 ))


def test_canonical_snapshot_contains_516_dated_events_and_37_year_ledgers():
    doc = build(*sources())
    stored = (SOURCE / "calendar.json").read_text(encoding="utf-8")
    assert stored == canonical(doc), "Generated source is stale; run --write"
    parsed = CanonicalPackageDocument.model_validate(doc)
    assert parsed.package_type is PackageType.CALENDAR
    assert parsed.package_id == "atp_tour_1990_2026_calendar"
    assert len(parsed.entities) == 553
    assert sum(e.entity_kind == "tennis.calendar.coverage.reference.v1"
               for e in parsed.entities) == 37
    dated = [e for e in parsed.entities
             if e.entity_kind == "tennis.calendar.occurrence.reference.v1"]
    assert len(dated) == 516
    assert all(e.payload["not_squash_rules"] is True
               and e.payload["run_week_projection"] == "not_applied_source_only"
               and len(e.references) == 2 for e in dated)
    assert doc["provenance"]["date_coverage_years"] == [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]


def test_2018_2026_full_named_roster_and_prior_28_years_not_fabricated():
    doc = build(*sources())
    cover = {e["payload"]["atp_season_year"]: e["payload"]
             for e in doc["entities"]
             if e["entity_kind"] == "tennis.calendar.coverage.reference.v1"}
    assert sorted(cover) == list(range(1990, 2027))
    for y in range(1990, 2018):
        assert cover[y]["date_coverage_state"] == "undated"
        assert cover[y]["dated_series_count"] == 0
        assert cover[y]["undated_series_ids"]
        assert cover[y]["no_fabricated_dates"] is True
    assert cover[2018]["dated_series_count"] == 64
    assert cover[2018]["undated_series_ids"] == []
    assert cover[2018]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert cover[2019]["dated_series_count"] == 63
    assert cover[2019]["undated_series_ids"] == []
    assert cover[2019]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert cover[2019]["year_source_status"] == "verified_results_archive"
    assert cover[2020]["dated_series_count"] == 29
    assert cover[2020]["roster_series_count"] == 41
    assert len(cover[2020]["known_not_held_series_ids"]) == 12
    assert cover[2020]["undated_series_ids"] == []
    assert cover[2020]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert cover[2021]["dated_series_count"] == 58
    assert cover[2021]["roster_series_count"] == 65
    assert len(cover[2021]["known_not_held_series_ids"]) == 7
    assert cover[2021]["undated_series_ids"] == []
    assert cover[2021]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert cover[2022]["dated_series_count"] == 65
    assert cover[2022]["roster_series_count"] == 69
    assert len(cover[2022]["known_not_held_series_ids"]) == 4
    assert cover[2022]["undated_series_ids"] == []
    assert cover[2022]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert cover[2023]["dated_series_count"] == 62
    assert cover[2023]["undated_series_ids"] == []
    assert cover[2023]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert cover[2023]["year_source_status"] == "verified_results_archive"
    assert cover[2024]["dated_series_count"] == 62
    assert cover[2024]["undated_series_ids"] == []
    assert cover[2024]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert cover[2024]["year_source_status"] == "verified_results_archive"
    assert cover[2025]["dated_series_count"] == 57
    assert cover[2025]["undated_series_ids"] == []
    assert cover[2025]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert cover[2026]["dated_series_count"] == 56
    assert cover[2026]["undated_series_ids"] == []
    assert cover[2026]["date_coverage_state"] == "provisional_complete_named_schedule"
    assert cover[2026]["year_source_status"] == "provisional_published_schedule"


def test_2025_2026_precise_dates_two_week_masters_and_host_licence_continuity():
    doc = build(*sources())
    events = {e["source_entity_id"]: e["payload"]
              for e in doc["entities"]
              if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"}
    assert events["atp_2025_brisbane"]["start_year_week"] == {
        "iso_year": 2024, "iso_week": 52,
    }
    assert events["atp_2025_brisbane"]["end_year_week"] == {
        "iso_year": 2025, "iso_week": 1,
    }
    assert events["atp_2025_indian_wells"]["iso_weeks_occupied"] == [
        {"iso_year": 2025, "iso_week": 10},
        {"iso_year": 2025, "iso_week": 11},
    ]
    # 'lyon' persistent Series is 2025 Marseille; old Lyon clay is separate.
    assert events["atp_2025_lyon"]["start_date"] == "2025-02-10"
    assert events["atp_2025_lyon"]["end_date"] == "2025-02-16"
    assert events["atp_2026_brisbane"]["start_date"] == "2026-01-04"
    assert events["atp_2026_brisbane"]["iso_weeks_occupied"] == [
        {"iso_year": 2026, "iso_week": 1},
        {"iso_year": 2026, "iso_week": 2},
    ]
    assert events["atp_2026_doha"]["end_date"] == "2026-02-21"
    assert events["atp_2026_dubai"]["end_date"] == "2026-02-28"
    assert events["atp_2026_umag"]["end_date"] == "2026-07-18"
    assert events["atp_2026_kitzbuhel"]["end_date"] == "2026-07-25"
    assert events["atp_2026_los_cabos"]["end_date"] == "2026-08-01"
    assert events["atp_2026_canadian_open"]["end_date"] == "2026-08-13"
    assert events["atp_2026_lyon"]["start_date"] == "2026-10-19"
    assert events["atp_2026_next_gen_atp_finals"]["start_date"] == "2026-12-09"
    assert events["atp_2026_next_gen_atp_finals"]["end_date"] == "2026-12-13"


def test_week53_and_unequal_length_run_clocks_are_never_silently_reinterpreted():
    assert iso_weeks_touched(date(2024, 12, 29), date(2025, 1, 5)) == [
        {"iso_year": 2024, "iso_week": 52},
        {"iso_year": 2025, "iso_week": 1},
    ]
    assert iso_weeks_touched(date(2026, 12, 28), date(2027, 1, 3)) == [
        {"iso_year": 2026, "iso_week": 53},
    ]
    clock = RunCalendar(weeks_per_year=52,
                        season_start_year_week=52,
                        start_year=2024, season_count=4)
    start = project_iso_week_to_run_w52(date(2024, 12, 29), run_calendar=clock)
    end = project_iso_week_to_run_w52(date(2025, 1, 5), run_calendar=clock)
    assert (start["season_index"], start["season_week"]) == (0, 1)
    assert (end["season_index"], end["season_week"]) == (0, 2)
    assert start["mapping_policy"] == "iso_week_label_to_W52_not_date_authority.v1"
    with pytest.raises(ValueError, match="week 53"):
        project_iso_week_to_run_w52(date(2026, 12, 31), run_calendar=clock)
    with pytest.raises(ValueError, match="requires W52"):
        project_iso_week_to_run_w52(
            date(2026, 3, 4), run_calendar=RunCalendar.fax_default()
        )
    with pytest.raises(ValueError, match="outside"):
        project_iso_week_to_run_w52(
            date(1990, 4, 1),
            run_calendar=RunCalendar.earth_default(start_year=2025),
        )


@pytest.mark.parametrize("mutate,error", [
    (lambda d: d["year_sources"]["2025"]["events"].append(
        copy.deepcopy(d["year_sources"]["2025"]["events"][0])
    ), "Unknown or duplicate"),
    (lambda d: d["year_sources"]["2026"]["events"][0].update(
        {"start_date": "2026-02-30"}
    ), "Invalid exact ISO date"),
    (lambda d: d["year_sources"]["2026"]["events"][0].update(
        {"source_url": "https://atptour.com.evil.test/schedule"}
    ), "Non-official ATP source"),
    (lambda d: d["year_sources"]["2026"]["events"][0].update(
        {"series_id": "fake_250"}
    ), "Unknown or duplicate"),
    (lambda d: d["year_sources"]["2026"]["events"][0].update(
        {"end_date": "2027-01-01"}
    ), "Impossible ATP season-year"),
    (lambda d: d["year_sources"]["2026"]["events"][0].update(
        {"end_date": "2026-12-31"}
    ), "Invalid tournament date interval"),
])
def test_source_curation_fails_closed(mutate, error):
    cats, ser, seasons, dated = sources()
    altered = copy.deepcopy(dated)
    mutate(altered)
    with pytest.raises(ValueError, match=error):
        build(cats, ser, seasons, altered)


def test_calendar_does_not_treat_known_cancelled_tournament_as_played():
    cats, ser, seasons, dated = sources()
    extra = copy.deepcopy(dated)
    extra["year_sources"]["2020"] = {
        "status": "verified_results_archive",
        "source_url": "https://www.atptour.com/en/scores/results-archive?year=2020",
        "as_of": "2026-11-03",
        "events": [{
            "series_id": "indian_wells",
            "start_date": "2020-03-02",
            "end_date": "2020-03-15",
            "source_url": "https://www.atptour.com/en/scores/results-archive?year=2020",
            "source_basis": "official_published_event_dates",
        }],
    }
    with pytest.raises(ValueError, match="Known not-held"):
        build(cats, ser, seasons, extra)

def test_2024_official_archive_dates_and_historical_series_identity():
    doc = build(*sources())
    events = {e["source_entity_id"]: e["payload"]
              for e in doc["entities"]
              if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"}
    assert sum(k.startswith("atp_2024_") for k in events) == 62
    assert events["atp_2024_brisbane"]["start_date"] == "2023-12-31"
    assert events["atp_2024_brisbane"]["iso_weeks_occupied"] == [
        {"iso_year": 2023, "iso_week": 52},
        {"iso_year": 2024, "iso_week": 1},
    ]
    assert events["atp_2024_lyon"]["start_date"] == "2024-02-05"
    assert events["atp_2024_lyon_old"]["start_date"] == "2024-05-19"
    assert events["atp_2024_brussels"]["start_date"] == "2024-10-14"
    assert events["atp_2024_next_gen_atp_finals"]["end_date"] == "2024-12-22"
    assert events["atp_2024_indian_wells"]["iso_weeks_occupied"] == [
        {"iso_year": 2024, "iso_week": 10},
        {"iso_year": 2024, "iso_week": 11},
    ]

def test_2023_official_archive_dates_and_historical_source_aliases():
    doc = build(*sources())
    events = {e["source_entity_id"]: e["payload"]
              for e in doc["entities"]
              if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"}
    assert sum(k.startswith("atp_2023_") for k in events) == 62
    assert events["atp_2023_adelaide"]["start_date"] == "2023-01-01"
    assert events["atp_2023_adelaide_2"]["start_date"] == "2023-01-09"
    # Historical source licences: 2023 Pune, Zhuhai and Astana respectively.
    assert events["atp_2023_hong_kong"]["start_date"] == "2023-01-02"
    assert events["atp_2023_hangzhou"]["start_date"] == "2023-09-20"
    assert events["atp_2023_almaty"]["start_date"] == "2023-09-27"
    assert events["atp_2023_lyon"]["start_date"] == "2023-02-20"
    assert events["atp_2023_lyon_old"]["start_date"] == "2023-05-21"
    assert events["atp_2023_next_gen_atp_finals"]["end_date"] == "2023-12-02"
    assert events["atp_2023_miami"]["iso_weeks_occupied"] == [
        {"iso_year": 2023, "iso_week": 12},
        {"iso_year": 2023, "iso_week": 13},
    ]

def test_2022_played_dates_and_official_non_held_exclusions():
    doc = build(*sources())
    events = {e["source_entity_id"]: e["payload"]
              for e in doc["entities"]
              if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"}
    assert sum(k.startswith("atp_2022_") for k in events) == 65
    for absent in ("beijing", "chengdu", "hangzhou", "shanghai"):
        assert f"atp_2022_{absent}" not in events
    # 2022 original identities rather than later-city display names.
    assert events["atp_2022_hong_kong"]["start_date"] == "2022-01-31"
    assert events["atp_2022_banja_luka"]["start_date"] == "2022-04-18"
    assert events["atp_2022_almaty"]["start_date"] == "2022-10-03"
    assert events["atp_2022_melbourne_2022"]["start_date"] == "2022-01-04"
    assert events["atp_2022_next_gen_atp_finals"]["end_date"] == "2022-11-12"

def test_2021_archived_dates_and_pandemic_cancelled_events():
    doc = build(*sources())
    events = {e["source_entity_id"]: e["payload"]
              for e in doc["entities"]
              if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"}
    assert sum(k.startswith("atp_2021_") for k in events) == 58
    for absent in ("basel", "beijing", "chengdu", "hangzhou", "houston",
                   "rio", "shanghai"):
        assert f"atp_2021_{absent}" not in events
    assert events["atp_2021_indian_wells"]["start_date"] == "2021-10-07"
    assert events["atp_2021_delray_beach"]["start_date"] == "2021-01-07"
    assert events["atp_2021_belgrade_clay_2021"]["start_date"] == "2021-04-19"
    assert events["atp_2021_belgrade_2_2021"]["start_date"] == "2021-05-23"
    assert events["atp_2021_melbourne_1_2021"]["start_date"] == "2021-02-01"
    assert events["atp_2021_melbourne_2_2021"]["start_date"] == "2021-02-01"

def test_2020_pandemic_tour_played_dates_vs_twelve_not_held():
    doc = build(*sources())
    events = {e["source_entity_id"]: e["payload"]
              for e in doc["entities"]
              if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"}
    assert sum(k.startswith("atp_2020_") for k in events) == 29
    for absent in ("beijing", "canadian_open", "chengdu", "halle",
                   "hangzhou", "indian_wells", "madrid", "miami",
                   "monte_carlo", "next_gen_atp_finals", "queens_club", "shanghai"):
        assert f"atp_2020_{absent}" not in events
    assert events["atp_2020_cincinnati"]["start_date"] == "2020-08-22"
    assert events["atp_2020_rome"]["start_date"] == "2020-09-14"
    assert events["atp_2020_cologne_1_2020"]["start_date"] == "2020-10-12"
    assert events["atp_2020_cologne_2_2020"]["start_date"] == "2020-10-19"
    assert events["atp_2020_sardinia_2020"]["start_date"] == "2020-10-12"
    assert events["atp_2020_atp_finals"]["end_date"] == "2020-11-22"

def test_2019_pre_pandemic_dates_and_iso_week_year_rollover():
    doc = build(*sources())
    events = {e["source_entity_id"]: e["payload"]
              for e in doc["entities"]
              if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"}
    assert sum(k.startswith("atp_2019_") for k in events) == 63
    assert events["atp_2019_doha"]["start_date"] == "2018-12-31"
    assert events["atp_2019_doha"]["start_year_week"] == {
        "iso_year": 2019, "iso_week": 1,
    }
    assert events["atp_2019_hong_kong"]["start_date"] == "2018-12-31"
    assert events["atp_2019_belgrade_clay_2021"]["start_date"] == "2019-04-22"
    assert events["atp_2019_hangzhou"]["start_date"] == "2019-09-23"
    assert events["atp_2019_antalya_2019"]["start_date"] == "2019-06-23"
    assert events["atp_2019_sydney_2019"]["end_date"] == "2019-01-12"
    assert events["atp_2019_atp_finals"]["end_date"] == "2019-11-17"

def test_2018_official_archive_complete_named_edition_roster_and_cross_year():
    doc = build(*sources())
    events = {e["source_entity_id"]: e["payload"] for e in doc["entities"]
              if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"}
    assert sum(e.startswith("atp_2018_") for e in events) == 64
    assert events["atp_2018_brisbane"]["start_date"] == "2017-12-31"
    assert events["atp_2018_brisbane"]["iso_weeks_occupied"] == [
        {"iso_year": 2017, "iso_week": 52},
        {"iso_year": 2018, "iso_week": 1},
    ]
    # Venue identities: Quito, Pune, Budapest, Marseille, Lyon, Shenzhen
    assert events["atp_2018_cordoba"]["start_date"] == "2018-02-05"
    assert events["atp_2018_hong_kong"]["start_date"] == "2018-01-01"
    assert events["atp_2018_belgrade_clay_2021"]["start_date"] == "2018-04-23"
    assert events["atp_2018_lyon"]["start_date"] == "2018-02-19"
    assert events["atp_2018_lyon_old"]["start_date"] == "2018-05-20"
    assert events["atp_2018_shenzhen_2018"]["end_date"] == "2018-09-30"
    assert events["atp_2018_atp_finals"]["end_date"] == "2018-11-18"
