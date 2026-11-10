"""Calendar retains mutually distinguishable official ATP Finals date concepts."""
from __future__ import annotations

import copy
import json

import pytest

from scripts.atp_finals_date_window_evidence import (
    CALENDAR_DATE_CONCEPT, REVIEWED_DATE_WINDOW_YEARS,
    VERIFIED_SOURCE_WINDOW_STATE, make_official_finals_window_evidence,
    validate_official_finals_window_evidence,
)
from scripts.build_atp_historical_calendar import SOURCE, build, canonical
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical

YEARS = [1990, 1992, 1993, 1997, 1998, 1999, 2003]


def sources():
    return tuple(
        json.loads((SOURCE / filename).read_text(encoding="utf-8"))
        for filename in (
            "category.json", "series.json", "seasons_1990_2026.json",
            "calendar_dates_v1.json",
        )
    )


def test_all_seven_source_window_distinctions_are_canonical_and_idempotent():
    assert sorted(REVIEWED_DATE_WINDOW_YEARS) == YEARS
    cat, ser, seasons, dated = sources()
    canonical_result = build(cat, ser, seasons, dated)
    by_id = {row["source_entity_id"]: row for row in canonical_result["entities"]}
    assert canonical_result["provenance"]["date_coverage_years"] == (
        list(range(1990, 2027))
    )
    assert canonical_result["provenance"]["dated_occurrences"] == 2407
    assert len(canonical_result["entities"]) == 2444
    assert canonical_result["provenance"][
        "finals_alternate_official_window_years"
    ] == YEARS
    assert canonical_result["provenance"]["calendar_date_concept"] == (
        CALENDAR_DATE_CONCEPT
    )
    assert canonical(canonical_result) == (
        SOURCE / "calendar.json"
    ).read_text(encoding="utf-8")
    for year in YEARS:
        raw = dated["year_sources"][str(year)]
        assert raw["status"] == VERIFIED_SOURCE_WINDOW_STATE
        evidence = validate_official_finals_window_evidence(
            year, raw["finals_date_window_evidence"]
        )
        source, prepared, report = prepare(year)
        assert source["year_sources"][str(year)] == raw
        assert prepared["provenance"]["dated_occurrences"] == 2407
        assert report["unresolved_date_conflicts"] == {}
        assert report["preserved_official_date_window_differences"]
        assert report["roster_reconciled"] is True
        assert report["ready_for_whole_year_promotion"] is False  # already canonical
        assert len(report["canonical_conflicts"]) == len(raw["events"])
        finals = by_id[f"atp_{year}_atp_finals"]["payload"]
        assert finals["start_date"] == evidence["archive_start_date"]
        assert finals["end_date"] == evidence["archive_end_date"]
        assert finals["calendar_date_concept"] == CALENDAR_DATE_CONCEPT
        assert finals["alternate_official_finals_window"] == evidence
        assert finals["no_match_or_result_claim"] is True
        assert finals["not_squash_rules"] is True
        assert finals["run_week_projection"] == "not_applied_source_only"
        coverage = by_id[f"season_{year}_date_coverage"]["payload"]
        assert coverage["date_coverage_state"] == (
            "verified_complete_archive_dates_with_alternate_finals_window"
        )
        assert coverage["undated_series_ids"] == []


def test_alternate_official_window_cannot_be_silently_deleted_or_rewritten():
    categories, series, seasons, dated = sources()
    for year in YEARS:
        modified = copy.deepcopy(dated)
        ev = modified["year_sources"][str(year)]["finals_date_window_evidence"]
        ev["alternate_start_date"] = ev["archive_start_date"]
        with pytest.raises(ValueError, match="invalid or tampered"):
            build(categories, series, seasons, modified)
        modified = copy.deepcopy(dated)
        del modified["year_sources"][str(year)]["finals_date_window_evidence"]
        with pytest.raises(ValueError, match="invalid or tampered"):
            build(categories, series, seasons, modified)
        modified = copy.deepcopy(dated)
        modified["year_sources"][str(year)]["status"] = "verified_results_archive"
        with pytest.raises(ValueError, match="must preserve independent date"):
            build(categories, series, seasons, modified)


def test_archive_event_date_and_historical_tournament_range_are_not_interchangeable():
    _, _, _, dated = sources()
    for year in YEARS:
        evidence = make_official_finals_window_evidence(year)
        assert evidence["archive_start_date"] != evidence["alternate_start_date"]
        assert evidence["archive_end_date"] == evidence["alternate_end_date"]
        assert evidence["archive_source_url"] == (
            f"https://www.atptour.com/en/scores/results-archive?year={year}"
        )
        assert evidence["no_match_day_or_playable_calendar_claim"] is True
    assert make_official_finals_window_evidence(2003)[
        "alternate_date_concept"
    ] == "atp_finals_heritage_broader_tournament_interval"
    with pytest.raises(ValueError, match="not reviewed"):
        make_official_finals_window_evidence(2005)


def test_all_37_years_are_source_dated_but_2026_remains_provisional():
    _, _, _, dated = sources()
    assert sorted(int(y) for y in dated["year_sources"]) == list(range(1990, 2027))
    assert dated["year_sources"]["2026"]["status"] == "provisional_published_schedule"
    assert dated["legal_boundary"].startswith("Reference-only")
