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


def test_canonical_snapshot_contains_only_113_dated_events_and_37_year_ledgers():
    doc = build(*sources())
    stored = (SOURCE / "calendar.json").read_text(encoding="utf-8")
    assert stored == canonical(doc), "Generated source is stale; run --write"
    parsed = CanonicalPackageDocument.model_validate(doc)
    assert parsed.package_type is PackageType.CALENDAR
    assert parsed.package_id == "atp_tour_1990_2026_calendar"
    assert len(parsed.entities) == 150
    assert sum(e.entity_kind == "tennis.calendar.coverage.reference.v1"
               for e in parsed.entities) == 37
    dated = [e for e in parsed.entities
             if e.entity_kind == "tennis.calendar.occurrence.reference.v1"]
    assert len(dated) == 113
    assert all(e.payload["not_squash_rules"] is True
               and e.payload["run_week_projection"] == "not_applied_source_only"
               and len(e.references) == 2 for e in dated)
    assert doc["provenance"]["date_coverage_years"] == [2025, 2026]


def test_2025_2026_full_named_roster_and_prior_35_years_not_fabricated():
    doc = build(*sources())
    cover = {e["payload"]["atp_season_year"]: e["payload"]
             for e in doc["entities"]
             if e["entity_kind"] == "tennis.calendar.coverage.reference.v1"}
    assert sorted(cover) == list(range(1990, 2027))
    for y in range(1990, 2025):
        assert cover[y]["date_coverage_state"] == "undated"
        assert cover[y]["dated_series_count"] == 0
        assert cover[y]["undated_series_ids"]
        assert cover[y]["no_fabricated_dates"] is True
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
