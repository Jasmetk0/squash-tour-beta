"""Evidence-only historical year 2002 ATP date roster validation."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE

pytestmark = pytest.mark.pr_critical


def test_2002_full_year_candidates_reconcile_to_parent_roster() -> None:
    candidate = json.loads(
        (SOURCE / "calendar_backfill_2002_candidates_v1.json").read_text(
            encoding="utf-8"
        )
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    canonical = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    result = audit_candidates(candidate, seasons, canonical)
    assert result["year"] == 2002
    assert result["candidate_count"] == 62
    assert result["expected_played_source_count"] == 62
    assert result["remaining_series_ids"] == []
    assert result["canonical_conflicts"] == []
    assert result["ready_for_whole_year_promotion"] is True
    rows = {x["series_id"]: x for x in result["candidate_events"]}
    for sid in ("doha", "hong_kong", "brisbane"):
        assert rows[sid]["start_date"] == "2001-12-31"
        assert rows[sid]["end_date"] == "2002-01-06"
        assert rows[sid]["iso_weeks_occupied"] == [
            {"iso_year": 2002, "iso_week": 1}
        ]
    assert rows["atp_finals"]["start_date"] == "2002-11-11"
    assert rows["atp_finals"]["end_date"] == "2002-11-17"
    assert rows["hong_kong_salem_2002"]["historical_host"] == "Hong Kong"
    assert rows["bangkok_2013"]["historical_host"] == "Tashkent"
    assert "2002" not in canonical["year_sources"]
