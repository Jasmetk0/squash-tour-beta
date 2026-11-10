"""1996 ATP original Tour/Finals historical dates and canonical integration."""
from __future__ import annotations

import pytest

from scripts.promote_atp_calendar_candidate import prepare

from tests.support.atp_calendar_backfill import (
    audit_canonical_backfill,
    verify_idempotent_promotion,
)

pytestmark = pytest.mark.pr_critical


def test_1996_original_78_event_source_venue_and_tier_coverage() -> None:
    audit = audit_canonical_backfill(1996, 78)
    events = {row["series_id"]: row for row in audit["candidate_events"]}
    assert events["jakarta_1996"]["historical_host"] == "Jakarta"
    assert events["bermuda_1996"]["historical_host"] == "Bermuda"
    assert events["seoul_1996"]["historical_host"] == "Seoul"
    assert events["porto_1996"]["historical_host"] == "Porto"
    assert events["tel_aviv_1996"]["historical_host"] == "Tel Aviv"
    assert events["hong_kong"]["historical_host"] == "New Delhi"
    assert events["hong_kong_salem_2002"]["historical_host"] == "Hong Kong"
    assert events["houston"]["historical_host"] == "Pinehurst"
    assert events["delray_beach"]["historical_host"] == "Coral Springs"
    assert events["stuttgart"]["category_id"] == "atp_championship_series"
    assert events["stuttgart_indoor_masters"]["category_id"] == (
        "atp_championship_single_week"
    )
    assert events["atp_finals"]["start_date"] == "1996-11-19"
    assert events["atp_finals"]["end_date"] == "1996-11-24"
    assert events["atp_finals"]["iso_weeks_occupied"] == [
        {"iso_year": 1996, "iso_week": 47}
    ]
    assert events["st_petersburg"]["iso_weeks_occupied"] == [
        {"iso_year": 1996, "iso_week": 12},
        {"iso_year": 1996, "iso_week": 13},
    ]


def test_1996_canonical_snapshot_is_unchanged_on_idempotent_check() -> None:
    document = verify_idempotent_promotion(1996, 78)
    by_id = {row["source_entity_id"]: row for row in document["entities"]}
    assert by_id["atp_1996_atp_finals"]["payload"]["start_year_week"] == {
        "iso_year": 1996,
        "iso_week": 47,
    }
    assert by_id["season_1996_date_coverage"]["payload"][
        "date_coverage_state"
    ] == "verified_complete_known_series_dates"


def test_1996_olympics_and_other_out_of_scope_competitions_not_imported() -> None:
    dated, document, _ = prepare(1996)
    ids = {
        row["source_entity_id"]
        for row in document["entities"]
        if row["entity_kind"] == "tennis.calendar.occurrence.reference.v1"
    }
    assert not any(
        row_id.startswith("atp_1996_") and any(
            marker in row_id for marker in
            ("olympics", "grand_slam", "davis_cup", "world_team_cup")
        )
        for row_id in ids
    )
