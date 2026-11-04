"""1994 partial ATP original Tour date ledger: explicit incompleteness and Finals."""
from __future__ import annotations

import json
import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical


def test_1994_sourced_cohort_is_partial_not_canonical() -> None:
    candidate = json.loads((SOURCE / "calendar_backfill_1994_candidates_v1.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads((SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8"))
    report = audit_candidates(candidate, seasons, dated)
    assert report["year"] == 1994
    assert report["candidate_count"] == 16
    assert report["expected_played_source_count"] == 85
    assert len(report["remaining_series_ids"]) == 69
    assert report["canonical_conflicts"] == []
    assert report["roster_reconciled"] is False
    assert report["ready_for_whole_year_promotion"] is False
    assert "1994" not in dated["year_sources"]
    rows = {row["series_id"]: row for row in report["candidate_events"]}
    assert rows["oahu_1994"]["historical_host"] == "Oahu"
    assert rows["sydney_2019"]["historical_host"] == "Sydney-1"
    assert rows["stuttgart_indoor_feb_1995"]["start_date"] == "1994-02-14"
    assert rows["dallas"]["historical_host"] == "San Jose"
    assert rows["rio"]["historical_host"] == "Memphis"
    assert rows["atp_finals"]["start_date"] == "1994-11-15"
    assert rows["atp_finals"]["end_date"] == "1994-11-20"
    assert rows["atp_finals"]["category_id"] == "atp_finals"
    assert rows["atp_finals"]["iso_weeks_occupied"] == [{"iso_year": 1994, "iso_week": 46}]
    assert "australian_open" not in rows


def test_1994_cannot_be_promoted_and_existing_calendar_is_unchanged() -> None:
    dates = SOURCE / "calendar_dates_v1.json"
    calendar = SOURCE / "calendar.json"
    before = (dates.read_bytes(), calendar.read_bytes())
    with pytest.raises(ValueError, match="not fully reconciled"):
        prepare(1994)
    assert (dates.read_bytes(), calendar.read_bytes()) == before
