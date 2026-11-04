"""1990 original Tour source census, separate historical events and Finals date conflict."""
from __future__ import annotations

import json
import pytest

from scripts.audit_atp_calendar_backfill import (
    SOURCE_DATE_CONFLICTS, audit_candidates,
)
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical


def read_inputs():
    source = json.loads((SOURCE / "calendar_backfill_1990_candidates_v1.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads((SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8"))
    return source, seasons, dated


def test_1990_original_75_event_candidates_reconcile_with_original_parent():
    source, seasons, dated = read_inputs()
    report = audit_candidates(source, seasons, dated)
    assert report["year"] == 1990
    assert report["candidate_count"] == 75
    assert report["expected_played_source_count"] == 75
    assert report["remaining_series_ids"] == []
    assert report["roster_reconciled"] is True
    assert report["canonical_conflicts"] == []
    assert report["unresolved_date_conflicts"] == SOURCE_DATE_CONFLICTS[1990]
    assert "1990" not in dated["year_sources"]
    assert report["ready_for_whole_year_promotion"] is False

    by_id = {entry["series_id"]: entry for entry in report["candidate_events"]}
    assert by_id["toronto_indoor_1990"]["historical_host"] == "Toronto-1 (indoor)"
    assert by_id["toronto_indoor_1990"]["start_date"] == "1990-02-12"
    assert by_id["canadian_open"]["historical_host"] == "Toronto (Canadian Open)"
    assert by_id["canadian_open"]["start_date"] == "1990-07-23"
    assert by_id["rio_carpet_1990"]["historical_host"] == "Rio de Janeiro"
    assert by_id["rio"]["historical_host"] == "Memphis"
    assert by_id["san_remo_1990"]["historical_host"] == "San Remo"
    assert by_id["wembley_1990"]["historical_host"] == "Wembley"
    assert by_id["itaparica_1990"]["historical_host"] == "Itaparica"
    assert by_id["sydney_2019"]["start_date"] == "1990-01-08"
    assert by_id["sydney_indoor_1994"]["start_date"] == "1990-10-01"
    assert by_id["tokyo"]["start_date"] == "1990-04-09"
    assert by_id["tokyo_indoor_1995"]["start_date"] == "1990-10-08"
    assert by_id["stuttgart_indoor_feb_1995"]["start_date"] == "1990-02-19"
    assert by_id["stuttgart"]["start_date"] == "1990-07-16"
    assert by_id["atp_finals"]["start_date"] == "1990-11-12"
    assert by_id["atp_finals"]["end_date"] == "1990-11-18"
    assert by_id["atp_finals"]["iso_weeks_occupied"] == [{"iso_year": 1990, "iso_week": 46}]
    assert "australian_open" not in by_id
    assert "grand_slam_cup" not in by_id


def test_1990_ambiguous_finals_cannot_mutate_existing_source_or_calendar():
    dates_path = SOURCE / "calendar_dates_v1.json"
    calendar_path = SOURCE / "calendar.json"
    before = (dates_path.read_bytes(), calendar_path.read_bytes())
    with pytest.raises(ValueError, match="Unresolved official ATP dates"):
        prepare(1990)
    assert (dates_path.read_bytes(), calendar_path.read_bytes()) == before


def test_1990_wrong_archive_finals_date_fails_even_in_staged_evidence():
    source, seasons, dated = read_inputs()
    edited = json.loads(json.dumps(source))
    finals = next(event for event in edited["events"] if event["series_id"] == "atp_finals")
    finals["start_date"] = "1990-11-13"
    with pytest.raises(ValueError, match="no longer matches"):
        audit_candidates(edited, seasons, dated)


def test_1990_wrong_source_year_duplicate_or_slam_are_rejected():
    source, seasons, dated = read_inputs()
    edited = json.loads(json.dumps(source))
    edited["source_url"] = "https://www.atptour.com/en/scores/results-archive?year=1991"
    with pytest.raises(ValueError, match="year must match"):
        audit_candidates(edited, seasons, dated)
    edited = json.loads(json.dumps(source))
    edited["events"].append(dict(edited["events"][0]))
    with pytest.raises(ValueError, match="Duplicate candidate Series"):
        audit_candidates(edited, seasons, dated)
    edited = json.loads(json.dumps(source))
    edited["events"][0]["series_id"] = "australian_open"
    with pytest.raises(ValueError, match="not active"):
        audit_candidates(edited, seasons, dated)
