"""Canonical 1991 original ATP Tour calendar historical and non-playable."""
import json
import pytest
from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.promote_atp_calendar_candidate import prepare
from scripts.build_atp_historical_calendar import SOURCE, canonical

pytestmark=pytest.mark.pr_critical

def test_1991_original_source_reconciled_in_canonical():
    c=json.loads((SOURCE/"calendar_backfill_1991_candidates_v1.json").read_text(encoding="utf-8"))
    ss=json.loads((SOURCE/"seasons_1990_2026.json").read_text(encoding="utf-8"))
    d=json.loads((SOURCE/"calendar_dates_v1.json").read_text(encoding="utf-8"))
    a=audit_candidates(c,ss,d)
    assert a["candidate_count"]==a["expected_played_source_count"]==76
    assert a["remaining_series_ids"]==[]
    assert len(a["canonical_conflicts"])==76
    assert a["roster_reconciled"] is True
    assert a["ready_for_whole_year_promotion"] is False
    assert a["unresolved_date_conflicts"]=={}
    r={e["series_id"]:e for e in a["candidate_events"]}
    assert r["maceio_1992"]["historical_host"]=="Guaruja-1"
    assert r["guaruja_1992"]["historical_host"]=="Guaruja-2"
    assert r["maceio_1992"]["start_date"]=="1991-02-04"
    assert r["guaruja_1992"]["start_date"]=="1991-10-21"
    assert r["brisbane"]["start_date"]=="1990-12-31"
    assert r["brisbane"]["iso_weeks_occupied"]==[{"iso_year":1991,"iso_week":1}]
    assert r["wellington_1992"]["start_date"]=="1990-12-31"
    assert r["brisbane_autumn_1992"]["historical_host"]=="Brisbane (autumn)"
    assert r["sydney_2019"]["start_date"]=="1991-01-07"
    assert r["sydney_indoor_1994"]["start_date"]=="1991-09-30"
    assert r["tokyo"]["start_date"]=="1991-04-08"
    assert r["tokyo_indoor_1995"]["start_date"]=="1991-10-07"
    assert r["stuttgart_indoor_feb_1995"]["start_date"]=="1991-02-18"
    assert r["stuttgart"]["start_date"]=="1991-07-15"
    assert r["cologne_1992_clay"]["historical_host"]=="Geneva"
    assert r["atp_finals"]["start_date"]=="1991-11-12"
    assert r["atp_finals"]["end_date"]=="1991-11-17"
    assert r["atp_finals"]["iso_weeks_occupied"]==[{"iso_year":1991,"iso_week":46}]
    assert "australian_open" not in r

def test_1991_promotion_idempotent_does_not_mutate_source():
    p=SOURCE/"calendar_dates_v1.json"
    q=SOURCE/"calendar.json"
    before=p.read_bytes(),q.read_bytes()
    dates,calendar,audit=prepare(1991)
    assert audit["candidate_count"]==76
    assert len(dates["year_sources"]["1991"]["events"])==76
    assert calendar["provenance"]["dated_occurrences"]==2407
    assert calendar["provenance"]["date_coverage_years"]==(
        list(range(1990, 2027))
    )
    assert len(calendar["entities"])==2444
    assert canonical(calendar)==q.read_text(encoding="utf-8")
    entries={e["source_entity_id"]:e for e in calendar["entities"]}
    assert entries["season_1991_date_coverage"]["payload"]["date_coverage_state"]=="verified_complete_known_series_dates"
    assert entries["atp_1991_brisbane"]["payload"]["start_year_week"]=={"iso_year":1991,"iso_week":1}
    assert entries["atp_1991_atp_finals"]["payload"]["run_week_projection"]=="not_applied_source_only"
    assert (p.read_bytes(),q.read_bytes())==before

def test_1991_excluded_slam_and_duplicate_rejected():
    c=json.loads((SOURCE/"calendar_backfill_1991_candidates_v1.json").read_text(encoding="utf-8"))
    ss=json.loads((SOURCE/"seasons_1990_2026.json").read_text(encoding="utf-8"))
    d=json.loads((SOURCE/"calendar_dates_v1.json").read_text(encoding="utf-8"))
    forgery=json.loads(json.dumps(c))
    forgery["events"].append(dict(forgery["events"][0]))
    with pytest.raises(ValueError,match="Duplicate candidate Series"):
        audit_candidates(forgery,ss,d)
    forgery=json.loads(json.dumps(c))
    forgery["events"][0]["series_id"]="australian_open"
    with pytest.raises(ValueError,match="not active"):
        audit_candidates(forgery,ss,d)
