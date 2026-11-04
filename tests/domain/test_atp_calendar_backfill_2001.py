"""ATP 2001 archived source data matches its canonical Calendar year."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE

pytestmark = pytest.mark.pr_critical


def test_2001_complete_parent_roster_candidates_reconcile_without_canonical_mutation() -> None:
    candidate = json.loads(
        (SOURCE / "calendar_backfill_2001_candidates_v1.json").read_text(
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
    assert report["year"] == 2001
    assert report["candidate_count"] == 65
    assert report["expected_played_source_count"] == 65
    assert report["remaining_series_ids"] == []
    assert len(report["canonical_conflicts"]) == 65
    assert report["ready_for_whole_year_promotion"] is False
    assert "2001" in canonical["year_sources"]
    assert len(canonical["year_sources"]["2001"]["events"]) == 65
    events = {x["series_id"]: x for x in report["candidate_events"]}
    assert events["doha"]["start_date"] == "2001-01-01"
    assert events["hong_kong"]["start_date"] == "2001-01-01"
    assert events["brisbane"]["start_date"] == "2001-01-01"
    assert events["bogota_colombia_2001"]["historical_host"] == "Bogotá"
    assert events["sofia"]["historical_host"] == "Milan"
    assert events["atlanta_verizon_2001"]["historical_host"] == "Atlanta"
    assert events["belgrade_2012"]["historical_host"] == "Amsterdam"
    assert events["stuttgart_indoor_masters"]["start_date"] == "2001-10-15"
    assert events["miami"]["start_date"] == "2001-03-19"
    assert events["miami"]["end_date"] == "2001-04-01"
    assert events["rome"]["category_id"] == "tennis_masters_series"
    assert events["doha"]["iso_weeks_occupied"] == [
        {"iso_year": 2001, "iso_week": 1}
    ]
