"""Fail-closed checks for partial ATP historical Calendar backfill."""
from __future__ import annotations

import copy
import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE

pytestmark = pytest.mark.pr_critical


def inputs():
    candidate = json.loads(
        (SOURCE / "calendar_backfill_2003_candidates_v1.json").read_text(
            encoding="utf-8"
        )
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    dated = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    return candidate, seasons, dated


def test_2003_full_parent_roster_candidates_preserve_real_cross_year_iso_week() -> None:
    result = audit_candidates(*inputs())
    assert result["year"] == 2003
    assert result["candidate_count"] == 63
    assert result["existing_canonical_count"] == 0
    assert result["roster_reconciled"] is True
    assert "atp_finals" in result["unresolved_date_conflicts"]
    assert result["ready_for_whole_year_promotion"] is False
    assert result["remaining_series_ids"] == []
    by_id = {x["series_id"]: x for x in result["candidate_events"]}
    for sid in ("doha", "hong_kong", "brisbane"):
        row = by_id[sid]
        assert row["start_date"] == "2002-12-30"
        assert row["end_date"] == "2003-01-05"
        assert row["iso_weeks_occupied"] == [
            {"iso_year": 2003, "iso_week": 1}
        ]
    assert {x["category_id"] for x in result["candidate_events"]} == {
        "atp_international_series",
        "atp_international_series_gold",
        "tennis_masters_series",
        "atp_finals",
    }
    for sid in ("doha", "hong_kong", "brisbane"):
        assert by_id[sid]["category_id"] == "atp_international_series"


def test_unknown_series_rejected() -> None:
    candidate, seasons, dated = inputs()
    candidate["events"][0]["series_id"] = "not_an_atp_series"
    with pytest.raises(ValueError, match="not active"):
        audit_candidates(candidate, seasons, dated)


def test_duplicate_series_rejected() -> None:
    candidate, seasons, dated = inputs()
    candidate["events"].append(copy.deepcopy(candidate["events"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        audit_candidates(candidate, seasons, dated)


def test_invalid_year_archive_rejected() -> None:
    candidate, seasons, dated = inputs()
    candidate["source_url"] = (
        "https://www.atptour.com/en/scores/results-archive?year=2004"
    )
    with pytest.raises(ValueError, match="archive year must match"):
        audit_candidates(candidate, seasons, dated)


def test_candidate_does_not_implicitly_modify_canonical_data() -> None:
    candidate, seasons, dated = inputs()
    before = json.dumps(dated, sort_keys=True)
    audit_candidates(candidate, seasons, dated)
    assert json.dumps(dated, sort_keys=True) == before
    assert "2003" not in dated["year_sources"]
