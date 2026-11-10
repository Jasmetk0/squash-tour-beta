"""1994 canonical ATP Calendar dates, original source identities and isolation."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE, canonical

from tests.support.atp_calendar_backfill import (
    audit_canonical_backfill,
    read_backfill_inputs,
    verify_idempotent_promotion,
)

pytestmark = pytest.mark.pr_critical


def test_1994_original_tour_finals_and_85_date_roster() -> None:
    report = audit_canonical_backfill(1994, 85)
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
    out_path = SOURCE / "calendar.json"
    document = verify_idempotent_promotion(1994, 85)
    assert document["provenance"]["run_consumption"] == "opaque_reference_only_no_sporting_calendar"
    lookup = {row["source_entity_id"]: row for row in document["entities"]}
    assert lookup["season_1994_date_coverage"]["payload"]["date_coverage_state"] == "verified_complete_known_series_dates"
    assert lookup["season_1994_date_coverage"]["payload"]["undated_series_ids"] == []
    assert lookup["atp_1994_atp_finals"]["payload"]["start_year_week"] == {"iso_year": 1994, "iso_week": 46}
    assert all(lookup[f"atp_1994_{sid}"]["payload"]["not_squash_rules"] for sid in (
        "atp_finals", "indian_wells", "miami", "tokyo", "tokyo_indoor_1995",
    ))
    assert canonical(document) == out_path.read_text(encoding="utf-8")


def test_1994_out_of_scope_or_duplicate_event_is_rejected() -> None:
    candidate, seasons, dated = read_backfill_inputs(1994)
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
