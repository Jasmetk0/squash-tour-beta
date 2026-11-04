"""1997 exact archived ATP Tour historical dates and safe promotion veto."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import PENDING_CONFLICTS, prepare

pytestmark = pytest.mark.pr_critical


def test_1997_all_75_original_atp_tour_roster_dates_remain_evidence_only() -> None:
    candidate = json.loads(
        (SOURCE / "calendar_backfill_1997_candidates_v1.json").read_text(
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
    assert report["year"] == 1997
    assert report["candidate_count"] == 75
    assert report["expected_played_source_count"] == 75
    assert report["remaining_series_ids"] == []
    assert report["canonical_conflicts"] == []
    assert report["ready_for_whole_year_promotion"] is True
    assert "1997" not in dated["year_sources"]
    events = {x["series_id"]: x for x in report["candidate_events"]}
    assert events["doha"]["start_date"] == "1996-12-30"
    assert events["brisbane"]["start_date"] == "1996-12-30"
    assert events["doha"]["iso_weeks_occupied"] == [
        {"iso_year": 1997, "iso_week": 1}
    ]
    assert events["split_1998"]["historical_host"] == "Zagreb"
    assert events["bangalore_2008"]["historical_host"] == "Shanghai"
    assert events["s_hertogenbosch"]["historical_host"] == "Rosmalen"
    assert events["brussels"]["historical_host"] == "Marbella"
    assert events["beijing_1997"]["historical_host"] == "Beijing"
    assert events["st_petersburg"]["start_date"] == "1997-03-17"
    assert events["st_petersburg"]["end_date"] == "1997-03-30"
    assert events["belgrade_clay_2021"]["end_date"] == "1997-10-05"
    assert events["toulouse_2000"]["end_date"] == "1997-10-05"
    assert events["atp_finals"]["start_date"] == "1997-11-10"


def test_1997_atp_finals_official_source_disagreement_is_blocking() -> None:
    note = PENDING_CONFLICTS[1997]["atp_finals"]
    assert "1997-11-10" in note
    assert "1997-11-11" in note
    with pytest.raises(ValueError, match="Unresolved official ATP dates"):
        prepare(1997)
