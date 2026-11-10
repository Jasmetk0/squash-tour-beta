"""Evidence-only historical year 2002 ATP date roster validation."""
from __future__ import annotations

import pytest

from tests.support.atp_calendar_backfill import audit_canonical_backfill

pytestmark = pytest.mark.pr_critical


def test_2002_full_year_candidates_reconcile_to_parent_roster() -> None:
    result = audit_canonical_backfill(2002, 62)
    rows = {x["series_id"]: x for x in result["candidate_events"]}
    for sid in ("doha", "hong_kong", "brisbane"):
        assert rows[sid]["start_date"] == "2001-12-31"
        assert rows[sid]["end_date"] == "2002-01-06"
        assert rows[sid]["iso_weeks_occupied"] == [
            {"iso_year": 2002, "iso_week": 1}
        ]
    assert rows["atp_finals"]["start_date"] == "2002-11-11"
    assert rows["atp_finals"]["end_date"] == "2002-11-17"
    assert rows["hong_kong_salem_2002"]["historical_host"] == "Hong Kong"
    assert rows["bangkok_2013"]["historical_host"] == "Tashkent"
