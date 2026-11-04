"""1999 original ATP Tour candidate evidence, source-tier and conflict safety."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import PENDING_CONFLICTS, prepare

pytestmark = pytest.mark.pr_critical


def test_1999_parent_series_coverage_complete_with_distinct_window_evidence() -> None:
    candidate = json.loads(
        (SOURCE / "calendar_backfill_1999_candidates_v1.json").read_text(
            encoding="utf-8"
        )
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    canonical = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    audited = audit_candidates(candidate, seasons, canonical)
    assert audited["year"] == 1999
    assert audited["candidate_count"] == 66
    assert audited["expected_played_source_count"] == 66
    assert audited["remaining_series_ids"] == []
    assert len(audited["canonical_conflicts"]) == 66
    assert audited["roster_reconciled"] is True
    assert "atp_finals" in audited["preserved_official_date_window_differences"]
    assert audited["ready_for_whole_year_promotion"] is False
    # Completeness of source IDs does not override conflicting official
    # date definitions for the year-ending ATP World Championship.
    assert "1999" in canonical["year_sources"]
    events = {row["series_id"]: row for row in audited["candidate_events"]}
    assert events["prague_1999"]["historical_host"] == "Prague"
    assert events["merano_1999"]["historical_host"] == "Meran"
    assert events["boston_1999"]["historical_host"] == "Boston"
    assert events["brighton_2000"]["historical_host"] == "Bournemouth"
    assert events["singapore_1999"]["historical_host"] == "Singapore"
    assert events["hong_kong"]["historical_host"] == "Chennai"
    assert events["hong_kong_salem_2002"]["historical_host"] == "Hong Kong"
    assert events["stuttgart"]["category_id"] == "atp_championship_series"
    assert events["stuttgart_indoor_masters"]["category_id"] == (
        "atp_championship_single_week"
    )
    assert events["atp_finals"]["start_date"] == "1999-11-22"
    assert events["atp_finals"]["end_date"] == "1999-11-28"
    assert events["atp_finals"]["iso_weeks_occupied"] == [
        {"iso_year": 1999, "iso_week": 47}
    ]


def test_1999_official_finals_date_disagreement_is_recorded() -> None:
    reason = PENDING_CONFLICTS[1999]["atp_finals"]
    assert "1999-11-22" in reason
    assert "1999-11-23" in reason
    source_years, built, checked = prepare(1999)
    assert checked["unresolved_date_conflicts"] == {}
    assert len(source_years["year_sources"]["1999"]["events"]) == 66
    assert built["provenance"]["dated_occurrences"] == 2407
