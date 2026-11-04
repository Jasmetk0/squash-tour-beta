"""Complete ATP Tour date evidence census and canonical/staged boundary."""
from __future__ import annotations
import copy
import json

import pytest

from scripts.audit_atp_calendar_full_roster import audit_full_roster
from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE

pytestmark = pytest.mark.pr_critical


def test_all_37_year_cohorts_have_complete_original_source_date_evidence():
    report = audit_full_roster()
    assert report["reference_span"] == {"from": 1990, "to": 2026}
    assert report["year_count"] == 37
    assert report["source_dated_year_count"] == 37
    assert report["canonical_year_count"] == 37
    assert report["noncanonical_staged_years"] == []
    assert report["staged_conflict_years"] == []
    assert report["preserved_alternate_official_finals_window_years"] == [
        1990, 1992, 1993, 1997, 1998, 1999, 2003
    ]
    assert report["canonical_dated_occurrences"] == 2407
    assert report["staged_exact_date_candidates"] == 0
    assert report["total_dated_original_events"] == 2407
    assert report["known_not_held_parent_memberships"] == 24
    assert report["total_parent_year_series_memberships"] == 2431
    assert report["calendar_source_entity_count"] == 2444
    assert report["provisional_canonical_years"] == [2026]
    assert report["all_year_effective_parent_ids_have_exact_date_evidence"] is True
    assert report["all_years_canonical_and_final"] is False
    assert report["independent_licence_lineage_certified"] is False
    assert report["playable_fax_calendar"] is False


def test_each_reviewed_finals_year_preserves_both_official_date_concepts():
    report = audit_full_roster()
    by_year = {row["year"]: row for row in report["year_rows"]}
    assert sorted(by_year) == list(range(1990, 2027))
    for y in [1990, 1992, 1993, 1997, 1998, 1999, 2003]:
        assert by_year[y]["mode"] == "canonical_reviewed_finals_window_distinction"
        assert by_year[y]["unresolved_conflict_series_ids"] == []
    assert by_year[1991]["mode"] == "canonical_historic"
    assert by_year[1994]["mode"] == "canonical_historic"
    assert by_year[2026]["mode"] == "canonical_provisional"


def test_one_missing_source_event_does_not_pass_as_complete():
    candidate = json.loads(
        (SOURCE / "calendar_backfill_1990_candidates_v1.json").read_text(encoding="utf-8")
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    dated = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    candidate = copy.deepcopy(candidate)
    candidate["events"] = [
        event for event in candidate["events"] if event["series_id"] != "wembley_1990"
    ]
    report = audit_candidates(candidate, seasons, dated)
    assert report["candidate_count"] == 74
    assert report["remaining_series_ids"] == []
    assert report["roster_reconciled"] is False
    assert report["ready_for_whole_year_promotion"] is False
