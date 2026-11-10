"""1999 original ATP Tour candidate evidence, source-tier and conflict safety."""
from __future__ import annotations

import pytest

from scripts.promote_atp_calendar_candidate import PENDING_CONFLICTS

from tests.support.atp_calendar_backfill import (
    audit_canonical_backfill,
    verify_idempotent_promotion,
)

pytestmark = pytest.mark.pr_critical


def test_1999_parent_series_coverage_complete_with_distinct_window_evidence() -> None:
    audited = audit_canonical_backfill(1999, 66)
    assert "atp_finals" in audited["preserved_official_date_window_differences"]
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
    verify_idempotent_promotion(1999, 66)
