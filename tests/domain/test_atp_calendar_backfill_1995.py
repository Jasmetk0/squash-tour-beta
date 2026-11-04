"""1995 original ATP Tour dates, two Tokyos/Stuttgarts and Finals 14–19 Nov."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical


def test_1995_original_tour_and_finals_80_date_roster() -> None:
    candidate = json.loads(
        (SOURCE / "calendar_backfill_1995_candidates_v1.json").read_text(
            encoding="utf-8"
        )
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    dated = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    report = audit_candidates(candidate, seasons, dated)
    assert report["year"] == 1995
    assert report["candidate_count"] == 80
    assert report["expected_played_source_count"] == 80
    assert report["roster_reconciled"] is True
    assert report["remaining_series_ids"] == []
    assert report["unresolved_date_conflicts"] == {}
    assert len(report["canonical_conflicts"]) == 80
    assert report["ready_for_whole_year_promotion"] is False
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
    dated_path = SOURCE / "calendar_dates_v1.json"
    output_path = SOURCE / "calendar.json"
    before = (dated_path.read_bytes(), output_path.read_bytes())
    dated, doc, report = prepare(1995)
    assert report["candidate_count"] == 80
    assert len(dated["year_sources"]["1995"]["events"]) == 80
    assert doc["provenance"]["dated_occurrences"] == 1816
    assert doc["provenance"]["season_coverage_entries"] == 37
    assert doc["provenance"]["date_coverage_years"] == (
        [1994, 1995, 1996, 2000, 2001, 2002] + list(range(2004, 2027))
    )
    lookup = {entity["source_entity_id"]: entity for entity in doc["entities"]}
    assert lookup["atp_1995_atp_finals"]["payload"]["start_year_week"] == {
        "iso_year": 1995,
        "iso_week": 46,
    }
    assert lookup["season_1995_date_coverage"]["payload"][
        "date_coverage_state"
    ] == "verified_complete_known_series_dates"
    assert (dated_path.read_bytes(), output_path.read_bytes()) == before


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
