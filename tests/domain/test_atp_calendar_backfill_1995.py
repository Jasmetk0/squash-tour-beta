"""1995 original ATP Tour dates, two Tokyos/Stuttgarts and Finals 14–19 Nov."""
from __future__ import annotations

import pytest

from scripts.promote_atp_calendar_candidate import prepare

from tests.support.atp_calendar_backfill import (
    audit_canonical_backfill,
    verify_idempotent_promotion,
)

pytestmark = pytest.mark.pr_critical


def test_1995_original_tour_and_finals_80_date_roster() -> None:
    report = audit_canonical_backfill(1995, 80)
    rows = {e["series_id"]: e for e in report["candidate_events"]}
    assert rows["stuttgart_indoor_feb_1995"]["start_date"] == "1995-02-20"
    assert rows["stuttgart"]["start_date"] == "1995-07-17"
    assert rows["stuttgart_indoor_feb_1995"]["category_id"] == (
        "atp_championship_series"
    )
    assert rows["tokyo"]["start_date"] == "1995-04-10"
    assert rows["tokyo_indoor_1995"]["start_date"] == "1995-10-09"
    assert rows["essen_masters"]["start_date"] == "1995-10-23"
    assert rows["essen_masters"]["category_id"] == (
        "atp_championship_single_week"
    )
    assert rows["hong_kong"]["historical_host"] == "Nice"
    assert rows["hong_kong_salem_2002"]["historical_host"] == "Hong Kong"
    assert rows["johannesburg_1995"]["historical_host"] == "Johannesburg"
    assert rows["bordeaux_1995"]["historical_host"] == "Bordeaux"
    assert rows["montevideo_1995"]["historical_host"] == "Montevideo"
    assert rows["buenos_aires_1995"]["historical_host"] == "Buenos Aires"
    assert rows["atp_finals"]["start_date"] == "1995-11-14"
    assert rows["atp_finals"]["end_date"] == "1995-11-19"
    assert rows["atp_finals"]["iso_weeks_occupied"] == [
        {"iso_year": 1995, "iso_week": 46}
    ]


def test_1995_is_canonical_and_rebuild_is_idempotent() -> None:
    doc = verify_idempotent_promotion(1995, 80)
    lookup = {entity["source_entity_id"]: entity for entity in doc["entities"]}
    assert lookup["atp_1995_atp_finals"]["payload"]["start_year_week"] == {
        "iso_year": 1995,
        "iso_week": 46,
    }
    assert lookup["season_1995_date_coverage"]["payload"][
        "date_coverage_state"
    ] == "verified_complete_known_series_dates"


def test_1995_out_of_scope_events_never_become_playable_athletic_matches() -> None:
    _, doc, _ = prepare(1995)
    occurrences = [
        e for e in doc["entities"]
        if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"
        and e["payload"]["atp_season_year"] == 1995
    ]
    assert len(occurrences) == 80
    assert all(e["payload"]["not_squash_rules"] is True for e in occurrences)
    assert all(e["payload"]["run_week_projection"] ==
               "not_applied_source_only" for e in occurrences)
