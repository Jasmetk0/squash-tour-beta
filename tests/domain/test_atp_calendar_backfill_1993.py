"""1993 historical ATP Tour date candidates and fail-closed Finals source conflict."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import (
    SOURCE_DATE_CONFLICTS,
    audit_candidates,
)
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical


def test_1993_archive_source_roster_84_and_disputed_finals_date() -> None:
    candidate = json.loads((SOURCE / "calendar_backfill_1993_candidates_v1.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads((SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8"))
    report = audit_candidates(candidate, seasons, dated)
    assert report["year"] == 1993
    assert report["candidate_count"] == 84
    assert report["expected_played_source_count"] == 84
    assert report["remaining_series_ids"] == []
    assert report["roster_reconciled"] is True
    assert report["canonical_conflicts"] == []
    assert report["ready_for_whole_year_promotion"] is False
    assert report["unresolved_date_conflicts"] == SOURCE_DATE_CONFLICTS[1993]
    assert "atp_finals" in report["unresolved_date_conflicts"]
    assert "1993-11-15" in report["unresolved_date_conflicts"]["atp_finals"]
    assert "1993-11-16" in report["unresolved_date_conflicts"]["atp_finals"]
    assert "1993" not in dated["year_sources"]
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


def test_1993_cannot_be_promoted_and_no_other_calendar_changes() -> None:
    before = (
        (SOURCE / "calendar_dates_v1.json").read_bytes(),
        (SOURCE / "calendar.json").read_bytes(),
    )
    with pytest.raises(ValueError, match="Unresolved official ATP dates"):
        prepare(1993)
    assert (
        (SOURCE / "calendar_dates_v1.json").read_bytes(),
        (SOURCE / "calendar.json").read_bytes(),
    ) == before


def test_1993_duplicate_and_wrong_parent_series_fail_closed() -> None:
    candidate = json.loads((SOURCE / "calendar_backfill_1993_candidates_v1.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads((SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8"))
    forged = json.loads(json.dumps(candidate))
    forged["events"].append(dict(forged["events"][0]))
    with pytest.raises(ValueError, match="Duplicate candidate Series"):
        audit_candidates(forged, seasons, dated)
    forged = json.loads(json.dumps(candidate))
    forged["events"][0]["series_id"] = "australian_open"
    with pytest.raises(ValueError, match="not active"):
        audit_candidates(forged, seasons, dated)
