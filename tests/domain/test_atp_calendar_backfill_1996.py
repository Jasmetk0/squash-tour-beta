"""1996 ATP original Tour/Finals historical dates and canonical integration."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical


def test_1996_original_78_event_source_venue_and_tier_coverage() -> None:
    candidate = json.loads(
        (SOURCE / "calendar_backfill_1996_candidates_v1.json").read_text(
            encoding="utf-8"
        )
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    dated = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    audit = audit_candidates(candidate, seasons, dated)
    assert audit["year"] == 1996
    assert audit["candidate_count"] == 78
    assert audit["expected_played_source_count"] == 78
    assert audit["remaining_series_ids"] == []
    assert audit["roster_reconciled"] is True
    assert audit["unresolved_date_conflicts"] == {}
    assert len(audit["canonical_conflicts"]) == 78  # already canonical
    assert audit["ready_for_whole_year_promotion"] is False
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
    source_path = SOURCE / "calendar_dates_v1.json"
    calendar_path = SOURCE / "calendar.json"
    original_source = source_path.read_bytes()
    original_calendar = calendar_path.read_bytes()
    dated, document, report = prepare(1996)
    assert report["candidate_count"] == 78
    assert len(dated["year_sources"]["1996"]["events"]) == 78
    assert document["provenance"]["dated_occurrences"] == 1731
    assert document["provenance"]["season_coverage_entries"] == 37
    assert document["provenance"]["date_coverage_years"] == (
        [1995, 1996, 2000, 2001, 2002] + list(range(2004, 2027))
    )
    by_id = {row["source_entity_id"]: row for row in document["entities"]}
    assert by_id["atp_1996_atp_finals"]["payload"]["start_year_week"] == {
        "iso_year": 1996,
        "iso_week": 47,
    }
    assert by_id["season_1996_date_coverage"]["payload"][
        "date_coverage_state"
    ] == "verified_complete_known_series_dates"
    assert source_path.read_bytes() == original_source
    assert calendar_path.read_bytes() == original_calendar


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
