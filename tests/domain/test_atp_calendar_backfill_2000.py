"""ATP original 2000 Tour dates and canonical source-preserving boundaries."""
from __future__ import annotations

import pytest

from tests.support.atp_calendar_backfill import (
    audit_canonical_backfill,
    verify_idempotent_promotion,
)

pytestmark = pytest.mark.pr_critical


def test_2000_archived_original_tiers_reconcile_to_parent_roster() -> None:
    report = audit_canonical_backfill(2000, 65)
    rows = {x["series_id"]: x for x in report["candidate_events"]}
    assert rows["sofia"]["historical_host"] == "London-1"
    assert rows["acapulco"]["historical_host"] == "Mexico City"
    assert rows["houston"]["historical_host"] == "Orlando"
    assert rows["brussels"]["historical_host"] == "Mallorca"
    assert rows["san_marino_2000"]["historical_host"] == "San Marino"
    assert rows["stuttgart"]["start_date"] == "2000-07-17"
    assert rows["stuttgart_indoor_masters"]["start_date"] == "2000-10-30"
    assert rows["atp_finals"]["start_date"] == "2000-11-27"
    assert rows["atp_finals"]["end_date"] == "2000-12-03"
    assert rows["doha"]["iso_weeks_occupied"] == [
        {"iso_year": 2000, "iso_week": 1}
    ]
    assert not any(
        "olympic" in row["historical_host"].lower()
        or "grand slam" in row["historical_host"].lower()
        for row in report["candidate_events"]
    )


def test_2000_canonical_promotion_is_idempotently_verified() -> None:
    built = verify_idempotent_promotion(2000, 65)
    by_id = {row["source_entity_id"]: row for row in built["entities"]}
    assert by_id["atp_2000_atp_finals"]["payload"][
        "end_year_week"
    ] == {"iso_year": 2000, "iso_week": 48}
    assert by_id["season_2000_date_coverage"]["payload"][
        "date_coverage_state"
    ] == "verified_complete_known_series_dates"
