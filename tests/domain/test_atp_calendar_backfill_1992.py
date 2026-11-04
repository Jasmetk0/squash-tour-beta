"""1992 78 original ATP Tour date candidates, inclusive ISO rollover and Finals conflict."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import SOURCE_DATE_CONFLICTS, audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical


def test_1992_year_effective_78_early_cross_year_events_and_finals_conflict() -> None:
    candidate = json.loads((SOURCE / "calendar_backfill_1992_candidates_v1.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads((SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8"))
    report = audit_candidates(candidate, seasons, dated)
    assert report["year"] == 1992
    assert report["candidate_count"] == 78
    assert report["expected_played_source_count"] == 78
    assert report["remaining_series_ids"] == []
    assert report["roster_reconciled"] is True
    assert report["canonical_conflicts"] == []
    assert report["unresolved_date_conflicts"] == SOURCE_DATE_CONFLICTS[1992]
    assert report["ready_for_whole_year_promotion"] is False
    assert "1992" not in dated["year_sources"]
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


def test_1992_unresolved_dates_fail_closed_and_canonical_files_unchanged() -> None:
    before = (
        (SOURCE / "calendar_dates_v1.json").read_bytes(),
        (SOURCE / "calendar.json").read_bytes(),
    )
    with pytest.raises(ValueError, match="Unresolved official ATP dates"):
        prepare(1992)
    assert (
        (SOURCE / "calendar_dates_v1.json").read_bytes(),
        (SOURCE / "calendar.json").read_bytes(),
    ) == before


def test_1992_wrong_source_year_and_duplicate_are_rejected() -> None:
    candidate = json.loads((SOURCE / "calendar_backfill_1992_candidates_v1.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads((SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8"))
    forged = json.loads(json.dumps(candidate))
    forged["source_url"] = "https://www.atptour.com/en/scores/results-archive?year=1993"
    with pytest.raises(ValueError, match="year must match"):
        audit_candidates(forged, seasons, dated)
    forged = json.loads(json.dumps(candidate))
    forged["events"].append(dict(forged["events"][0]))
    with pytest.raises(ValueError, match="Duplicate candidate Series"):
        audit_candidates(forged, seasons, dated)
