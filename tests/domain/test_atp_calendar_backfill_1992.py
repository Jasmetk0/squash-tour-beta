"""1992 78 original ATP Tour date candidates, inclusive ISO rollover and Finals conflict."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import SOURCE_DATE_CONFLICTS, audit_candidates

from tests.support.atp_calendar_backfill import (
    audit_canonical_backfill,
    read_backfill_inputs,
    verify_idempotent_promotion,
)

pytestmark = pytest.mark.pr_critical


def test_1992_year_effective_78_early_cross_year_events_and_finals_conflict() -> None:
    report = audit_canonical_backfill(1992, 78)
    assert report["preserved_official_date_window_differences"] == SOURCE_DATE_CONFLICTS[1992]
    rows = {e["series_id"]: e for e in report["candidate_events"]}
    assert rows["brisbane"]["historical_host"] == "Adelaide"
    assert rows["wellington_1992"]["historical_host"] == "Wellington"
    assert rows["brisbane"]["start_date"] == "1991-12-30"
    assert rows["brisbane"]["iso_weeks_occupied"] == [{"iso_year": 1992, "iso_week": 1}]
    assert rows["brisbane_autumn_1992"]["historical_host"] == "Brisbane (autumn)"
    assert rows["brisbane_autumn_1992"]["start_date"] == "1992-09-28"
    assert rows["brussels_championship_1992"]["start_date"] == "1992-02-10"
    assert rows["sydney_2019"]["historical_host"] == "Sydney-1"
    assert rows["sydney_indoor_1994"]["historical_host"] == "Sydney-2 (indoor)"
    assert rows["tokyo"]["historical_host"] == "Tokyo-1 (Japan Open)"
    assert rows["tokyo_indoor_1995"]["historical_host"] == "Tokyo-2 (indoor)"
    assert rows["stuttgart_indoor_feb_1995"]["start_date"] == "1992-02-17"
    assert rows["stuttgart"]["start_date"] == "1992-07-13"
    assert rows["atp_finals"]["start_date"] == "1992-11-16"
    assert rows["atp_finals"]["end_date"] == "1992-11-22"
    assert rows["atp_finals"]["iso_weeks_occupied"] == [{"iso_year": 1992, "iso_week": 47}]
    assert "barcelona_olympics" not in rows


def test_1992_archive_and_alternate_windows_are_idempotent() -> None:
    verify_idempotent_promotion(1992, 78)


def test_1992_wrong_source_year_and_duplicate_are_rejected() -> None:
    candidate, seasons, dated = read_backfill_inputs(1992)
    forged = json.loads(json.dumps(candidate))
    forged["source_url"] = "https://www.atptour.com/en/scores/results-archive?year=1993"
    with pytest.raises(ValueError, match="year must match"):
        audit_candidates(forged, seasons, dated)
    forged = json.loads(json.dumps(candidate))
    forged["events"].append(dict(forged["events"][0]))
    with pytest.raises(ValueError, match="Duplicate candidate Series"):
        audit_candidates(forged, seasons, dated)
