"""ATP 2001 archived source data matches its canonical Calendar year."""
from __future__ import annotations

import pytest

from tests.support.atp_calendar_backfill import audit_canonical_backfill

pytestmark = pytest.mark.pr_critical


def test_2001_complete_parent_roster_candidates_reconcile_without_canonical_mutation() -> None:
    report = audit_canonical_backfill(2001, 65)
    events = {x["series_id"]: x for x in report["candidate_events"]}
    assert events["doha"]["start_date"] == "2001-01-01"
    assert events["hong_kong"]["start_date"] == "2001-01-01"
    assert events["brisbane"]["start_date"] == "2001-01-01"
    assert events["bogota_colombia_2001"]["historical_host"] == "Bogotá"
    assert events["sofia"]["historical_host"] == "Milan"
    assert events["atlanta_verizon_2001"]["historical_host"] == "Atlanta"
    assert events["belgrade_2012"]["historical_host"] == "Amsterdam"
    assert events["stuttgart_indoor_masters"]["start_date"] == "2001-10-15"
    assert events["miami"]["start_date"] == "2001-03-19"
    assert events["miami"]["end_date"] == "2001-04-01"
    assert events["rome"]["category_id"] == "tennis_masters_series"
    assert events["doha"]["iso_weeks_occupied"] == [
        {"iso_year": 2001, "iso_week": 1}
    ]
