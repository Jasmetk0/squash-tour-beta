"""1994 canonical ATP Calendar dates, original source identities and isolation."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE, build, canonical
from scripts.promote_atp_calendar_candidate import prepare

pytestmark = pytest.mark.pr_critical


def test_1994_original_tour_finals_and_85_date_roster() -> None:
    candidate = json.loads((SOURCE / "calendar_backfill_1994_candidates_v1.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads((SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8"))
    report = audit_candidates(candidate, seasons, dated)
    assert report["year"] == 1994
    assert report["candidate_count"] == 85
    assert report["expected_played_source_count"] == 85
    assert report["remaining_series_ids"] == []
    assert len(report["canonical_conflicts"]) == 85
    assert report["roster_reconciled"] is True
    assert report["ready_for_whole_year_promotion"] is False  # already imported
    assert report["unresolved_date_conflicts"] == {}
    rows = {row["series_id"]: row for row in report["candidate_events"]}
    assert rows["oahu_1994"]["historical_host"] == "Oahu"
    assert rows["sydney_2019"]["historical_host"] == "Sydney-1"
    assert rows["sydney_indoor_1994"]["historical_host"] == "Sydney-2 (indoor)"
    assert rows["sydney_indoor_1994"]["start_date"] == "1994-10-03"
    assert rows["stuttgart_indoor_feb_1995"]["start_date"] == "1994-02-14"
    assert rows["stuttgart"]["start_date"] == "1994-07-18"
    assert rows["tokyo"]["start_date"] == "1994-04-04"
    assert rows["tokyo_indoor_1995"]["start_date"] == "1994-10-10"
    assert rows["atlanta_verizon_2001"]["historical_host"] == "Atlanta"
    assert rows["atlanta"]["historical_host"] == "Indianapolis"
    assert rows["eastbourne"]["historical_host"] == "Manchester"
    assert rows["johannesburg_1995"]["historical_host"] == "Sun City"
    assert rows["belgrade_2012"]["historical_host"] == "Hilversum"
    assert rows["dallas"]["historical_host"] == "San Jose"
    assert rows["rio"]["historical_host"] == "Memphis"
    assert rows["miami"]["start_date"] == "1994-03-07"
    assert rows["miami"]["end_date"] == "1994-03-20"
    assert rows["indian_wells"]["start_date"] == "1994-02-28"
    assert rows["monte_carlo"]["start_date"] == "1994-04-18"
    assert rows["stockholm"]["start_date"] == "1994-10-24"
    assert rows["paris_masters"]["end_date"] == "1994-11-06"
    assert rows["atp_finals"]["start_date"] == "1994-11-15"
    assert rows["atp_finals"]["end_date"] == "1994-11-20"
    assert rows["atp_finals"]["category_id"] == "atp_finals"
    assert rows["atp_finals"]["iso_weeks_occupied"] == [{"iso_year": 1994, "iso_week": 46}]
    assert "australian_open" not in rows


def test_1994_is_canonical_idempotent_and_does_not_mutate_old_events() -> None:
    dated_path = SOURCE / "calendar_dates_v1.json"
    out_path = SOURCE / "calendar.json"
    before = (dated_path.read_bytes(), out_path.read_bytes())
    dated, document, report = prepare(1994)
    assert report["candidate_count"] == 85
    assert len(dated["year_sources"]["1994"]["events"]) == 85
    assert document["provenance"]["dated_occurrences"] == 2407
    assert document["provenance"]["season_coverage_entries"] == 37
    assert document["provenance"]["date_coverage_years"] == (
        list(range(1990, 2027))
    )
    assert len(document["entities"]) == 2444
    assert document["provenance"]["run_consumption"] == "opaque_reference_only_no_sporting_calendar"
    lookup = {row["source_entity_id"]: row for row in document["entities"]}
    assert lookup["season_1994_date_coverage"]["payload"]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert lookup["season_1994_date_coverage"]["payload"]["undated_series_ids"] == []
    assert lookup["atp_1994_atp_finals"]["payload"]["start_year_week"] == {"iso_year": 1994, "iso_week": 46}
    assert all(lookup[f"atp_1994_{sid}"]["payload"]["not_squash_rules"] for sid in (
        "atp_finals", "indian_wells", "miami", "tokyo", "tokyo_indoor_1995",
    ))
    assert canonical(document) == out_path.read_text(encoding="utf-8")
    assert (dated_path.read_bytes(), out_path.read_bytes()) == before


def test_1994_out_of_scope_or_duplicate_event_is_rejected() -> None:
    candidate = json.loads((SOURCE / "calendar_backfill_1994_candidates_v1.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads((SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8"))
    invalid = json.loads(json.dumps(candidate))
    invalid["events"].append({
        "historical_host": "Australian Open", "series_id": "australian_open",
        "start_date": "1994-01-17", "end_date": "1994-01-30",
    })
    with pytest.raises(ValueError, match="not active"):
        audit_candidates(invalid, seasons, dated)
    invalid = json.loads(json.dumps(candidate))
    invalid["events"].append(dict(invalid["events"][0]))
    with pytest.raises(ValueError, match="Duplicate candidate Series"):
        audit_candidates(invalid, seasons, dated)
