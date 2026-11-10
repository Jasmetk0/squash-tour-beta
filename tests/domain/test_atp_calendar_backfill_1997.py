"""1997 exact archived ATP Tour historical dates and safe promotion veto."""
from __future__ import annotations

import pytest

from scripts.promote_atp_calendar_candidate import PENDING_CONFLICTS

from tests.support.atp_calendar_backfill import (
    audit_canonical_backfill,
    verify_idempotent_promotion,
)

pytestmark = pytest.mark.pr_critical


def test_1997_all_75_original_atp_tour_roster_dates_are_canonical_with_alternate_window() -> None:
    report = audit_canonical_backfill(1997, 75)
    assert "atp_finals" in report["preserved_official_date_window_differences"]
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


def test_1997_finals_official_source_windows_are_preserved() -> None:
    note = PENDING_CONFLICTS[1997]["atp_finals"]
    assert "1997-11-10" in note
    assert "1997-11-11" in note
    verify_idempotent_promotion(1997, 75)
