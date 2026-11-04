"""1998 original ATP Tour date-source audit and Finals conflict protections."""
from __future__ import annotations

import json

import pytest

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import PENDING_CONFLICTS, prepare

pytestmark = pytest.mark.pr_critical


def test_1998_all_74_played_source_memberships_are_canonical_and_auditable() -> None:
    candidate = json.loads(
        (SOURCE / "calendar_backfill_1998_candidates_v1.json").read_text(
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
    assert audit["year"] == 1998
    assert audit["candidate_count"] == 74
    assert audit["expected_played_source_count"] == 74
    assert audit["remaining_series_ids"] == []
    assert len(audit["canonical_conflicts"]) == 74
    assert audit["roster_reconciled"] is True
    assert "atp_finals" in audit["preserved_official_date_window_differences"]
    assert audit["ready_for_whole_year_promotion"] is False
    assert "1998" in dated["year_sources"]
    events = {x["series_id"]: x for x in audit["candidate_events"]}
    assert events["antwerp_1998"]["historical_host"] == "Antwerp"
    assert events["split_1998"]["historical_host"] == "Split"
    assert events["bologna_1998"]["historical_host"] == "Bologna"
    assert events["new_haven_1998"]["historical_host"] == "New Haven"
    assert events["ostrava_1998"]["historical_host"] == "Ostrava"
    assert events["delray_beach"]["historical_host"] == "Coral Springs"
    assert events["acapulco"]["historical_host"] == "Mexico City"
    assert events["stuttgart"]["category_id"] == "atp_championship_series"
    assert events["stuttgart_indoor_masters"]["category_id"] == (
        "atp_championship_single_week"
    )
    # The ATP archive says Amsterdam ended on Saturday, not Sunday;
    # keep exactly sourced dates, don't fabricate a seven-day interval.
    assert events["belgrade_2012"]["end_date"] == "1998-08-08"
    assert events["belgrade_2012"]["iso_weeks_occupied"] == [
        {"iso_year": 1998, "iso_week": 32}
    ]


def test_1998_finals_archive_and_heritage_dates_are_both_preserved() -> None:
    reason = PENDING_CONFLICTS[1998]["atp_finals"]
    assert "1998-11-23" in reason
    assert "1998-11-24" in reason
    source_years, built, checked = prepare(1998)
    assert checked["unresolved_date_conflicts"] == {}
    assert len(source_years["year_sources"]["1998"]["events"]) == 74
    assert built["provenance"]["dated_occurrences"] == 2407
