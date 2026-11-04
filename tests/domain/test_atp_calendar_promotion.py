"""Acceptance gates for a historical year promotion, including source conflicts."""
from __future__ import annotations

import json

import pytest

from scripts.promote_atp_calendar_candidate import (
    PENDING_CONFLICTS,
    prepare,
)
from scripts.build_atp_historical_calendar import SOURCE

pytestmark = pytest.mark.pr_critical


def test_2003_promotion_blocked_by_conflicting_official_finals_dates() -> None:
    assert "atp_finals" in PENDING_CONFLICTS[2003]
    assert "2003-11-08" in PENDING_CONFLICTS[2003]["atp_finals"]
    assert "2003-11-10" in PENDING_CONFLICTS[2003]["atp_finals"]
    with pytest.raises(ValueError, match="Unresolved official ATP dates"):
        prepare(2003)


def test_source_files_remain_unchanged_when_promotion_vetoes() -> None:
    source = (SOURCE / "calendar_dates_v1.json").read_bytes()
    generated = (SOURCE / "calendar.json").read_bytes()
    with pytest.raises(ValueError, match="Unresolved official ATP dates"):
        prepare(2003)
    assert (SOURCE / "calendar_dates_v1.json").read_bytes() == source
    assert (SOURCE / "calendar.json").read_bytes() == generated


def test_promoter_rejects_unstaged_year() -> None:
    with pytest.raises(ValueError, match="Only staged 1991–2003"):
        prepare(1990)


def test_conflicted_year_is_not_mislabelled_as_canonically_dated() -> None:
    dated = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    assert "2003" not in dated["year_sources"]


def test_2002_is_mechanically_promotable_without_changing_2004_onward() -> None:
    promoted, built, audited = prepare(2002)
    assert audited["candidate_count"] == 62
    assert "2002" in promoted["year_sources"]
    assert len(promoted["year_sources"]["2002"]["events"]) == 62
    assert built["provenance"]["dated_occurrences"] == 1892
    assert built["provenance"]["season_coverage_entries"] == 37
    assert sorted(built["provenance"]["date_coverage_years"]) == (
        [1991, 1994, 1995, 1996, 2000, 2001, 2002] + list(range(2004, 2027))
    )
    by_id = {
        entity["source_entity_id"]: entity
        for entity in built["entities"]
    }
    assert by_id["atp_2002_doha"]["payload"]["start_year_week"] == {
        "iso_year": 2002,
        "iso_week": 1,
    }
    assert by_id["season_2002_date_coverage"]["payload"][
        "date_coverage_state"
    ] == "verified_complete_known_series_dates"


def test_2001_is_mechanically_promotable_without_changing_other_years() -> None:
    promoted, built, audited = prepare(2001)
    assert audited["candidate_count"] == 65
    assert audited["expected_played_source_count"] == 65
    assert audited["remaining_series_ids"] == []
    assert "2001" in promoted["year_sources"]
    assert len(promoted["year_sources"]["2001"]["events"]) == 65
    assert built["provenance"]["dated_occurrences"] == 1892
    assert built["provenance"]["season_coverage_entries"] == 37
    assert built["provenance"]["date_coverage_years"] == (
        [1991, 1994, 1995, 1996, 2000, 2001, 2002] + list(range(2004, 2027))
    )
    by_id = {x["source_entity_id"]: x for x in built["entities"]}
    assert by_id["atp_2001_atlanta_verizon_2001"]["payload"][
        "start_date"
    ] == "2001-04-23"
    assert by_id["atp_2001_stuttgart"]["payload"][
        "start_date"
    ] == "2001-07-16"
    assert by_id["atp_2001_stuttgart_indoor_masters"]["payload"][
        "start_date"
    ] == "2001-10-15"
    assert by_id["season_2001_date_coverage"]["payload"][
        "date_coverage_state"
    ] == "verified_complete_known_series_dates"
