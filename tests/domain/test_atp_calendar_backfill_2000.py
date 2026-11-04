"""ATP original 2000 Tour dates and canonical source-preserving boundaries."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical


def test_2000_archived_original_tiers_reconcile_to_parent_roster() -> None:
    candidate = json.loads(
        (SOURCE / "calendar_backfill_2000_candidates_v1.json").read_text(
            encoding="utf-8"
        )
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    canonical = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    report = audit_candidates(candidate, seasons, canonical)
    assert report["year"] == 2000
    assert report["candidate_count"] == 65
    assert report["expected_played_source_count"] == 65
    assert report["remaining_series_ids"] == []
    assert len(report["canonical_conflicts"]) == 65
    assert report["ready_for_whole_year_promotion"] is False
    assert len(canonical["year_sources"]["2000"]["events"]) == 65
    rows = {x["series_id"]: x for x in report["candidate_events"]}
    assert rows["sofia"]["historical_host"] == "London-1"
    assert rows["acapulco"]["historical_host"] == "Mexico City"
    assert rows["houston"]["historical_host"] == "Orlando"
    assert rows["brussels"]["historical_host"] == "Mallorca"
    assert rows["san_marino_2000"]["historical_host"] == "San Marino"
    assert rows["stuttgart"]["start_date"] == "2000-07-17"
    assert rows["stuttgart_indoor_masters"]["start_date"] == "2000-10-30"
    assert rows["atp_finals"]["start_date"] == "2000-11-27"
    assert rows["atp_finals"]["end_date"] == "2000-12-03"
    assert rows["doha"]["iso_weeks_occupied"] == [
        {"iso_year": 2000, "iso_week": 1}
    ]
    assert not any(
        "olympic" in row["historical_host"].lower()
        or "grand slam" in row["historical_host"].lower()
        for row in report["candidate_events"]
    )


def test_2000_canonical_promotion_is_idempotently_verified() -> None:
    dated, built, audit = prepare(2000)
    assert audit["candidate_count"] == 65
    assert len(dated["year_sources"]["2000"]["events"]) == 65
    assert built["provenance"]["dated_occurrences"] == 2407
    assert built["provenance"]["season_coverage_entries"] == 37
    assert built["provenance"]["date_coverage_years"] == (
        list(range(1990, 2027))
    )
    by_id = {row["source_entity_id"]: row for row in built["entities"]}
    assert by_id["atp_2000_atp_finals"]["payload"][
        "end_year_week"
    ] == {"iso_year": 2000, "iso_week": 48}
    assert by_id["season_2000_date_coverage"]["payload"][
        "date_coverage_state"
    ] == "verified_complete_known_series_dates"
