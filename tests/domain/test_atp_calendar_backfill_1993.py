"""1993 historical ATP Tour date candidates and fail-closed Finals source conflict."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import (
    SOURCE_DATE_CONFLICTS,
    audit_candidates,
)

from tests.support.atp_calendar_backfill import (
    audit_canonical_backfill,
    read_backfill_inputs,
    verify_idempotent_promotion,
)

pytestmark = pytest.mark.pr_critical


def test_1993_archive_source_roster_84_and_disputed_finals_date() -> None:
    report = audit_canonical_backfill(1993, 84)
    assert report["preserved_official_date_window_differences"] == SOURCE_DATE_CONFLICTS[1993]
    assert "atp_finals" in report["preserved_official_date_window_differences"]
    assert "1993-11-15" in report["preserved_official_date_window_differences"]["atp_finals"]
    assert "1993-11-16" in report["preserved_official_date_window_differences"]["atp_finals"]
    rows = {r["series_id"]: r for r in report["candidate_events"]}
    assert rows["kuala_lumpur_jan_1993"]["historical_host"] == "Kuala Lumpur-1"
    assert rows["singapore_1999"]["historical_host"] == "Kuala Lumpur-2"
    assert rows["sydney_2019"]["historical_host"] == "Sydney-1"
    assert rows["sydney_indoor_1994"]["historical_host"] == "Sydney-2 (indoor)"
    assert rows["tokyo"]["historical_host"] == "Tokyo-1 (Japan Open)"
    assert rows["tokyo_indoor_1995"]["historical_host"] == "Tokyo-2 (indoor)"
    assert rows["stuttgart_indoor_feb_1995"]["start_date"] == "1993-02-15"
    assert rows["stuttgart"]["start_date"] == "1993-07-19"
    assert rows["dallas"]["historical_host"] == "San Francisco"
    assert rows["birmingham_1994"]["historical_host"] == "Charlotte"
    assert rows["houston"]["historical_host"] == "Tampa"
    assert rows["johannesburg_1995"]["historical_host"] == "Durban"
    assert rows["poertschach_2008"]["historical_host"] == "Genoa"
    assert rows["atp_finals"]["start_date"] == "1993-11-15"
    assert rows["atp_finals"]["end_date"] == "1993-11-21"
    assert rows["atp_finals"]["category_id"] == "atp_finals"
    assert rows["atp_finals"]["iso_weeks_occupied"] == [{"iso_year": 1993, "iso_week": 46}]


def test_1993_archive_and_alternate_windows_are_idempotent() -> None:
    verify_idempotent_promotion(1993, 84)


def test_1993_duplicate_and_wrong_parent_series_fail_closed() -> None:
    candidate, seasons, dated = read_backfill_inputs(1993)
    forged = json.loads(json.dumps(candidate))
    forged["events"].append(dict(forged["events"][0]))
    with pytest.raises(ValueError, match="Duplicate candidate Series"):
        audit_candidates(forged, seasons, dated)
    forged = json.loads(json.dumps(candidate))
    forged["events"][0]["series_id"] = "australian_open"
    with pytest.raises(ValueError, match="not active"):
        audit_candidates(forged, seasons, dated)
