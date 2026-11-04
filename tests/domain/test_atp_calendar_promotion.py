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


def test_2003_preserves_annual_archive_and_wider_finals_heritage_dates() -> None:
    assert "atp_finals" in PENDING_CONFLICTS[2003]  # recorded difference
    assert "2003-11-08" in PENDING_CONFLICTS[2003]["atp_finals"]
    assert "2003-11-10" in PENDING_CONFLICTS[2003]["atp_finals"]
    source, built, audit = prepare(2003)
    assert audit["unresolved_date_conflicts"] == {}
    assert audit["preserved_official_date_window_differences"]
    assert len(audit["canonical_conflicts"]) == 63
    assert len(source["year_sources"]["2003"]["events"]) == 63
    by_id = {e["source_entity_id"]: e for e in built["entities"]}
    finals = by_id["atp_2003_atp_finals"]["payload"]
    assert finals["start_date"] == "2003-11-10"
    alt = finals["alternate_official_finals_window"]
    assert alt["alternate_start_date"] == "2003-11-08"
    assert alt["alternate_date_concept"] == (
        "atp_finals_heritage_broader_tournament_interval"
    )


def test_already_canonical_promotion_is_read_only_for_2003() -> None:
    before = (
        (SOURCE / "calendar_dates_v1.json").read_bytes(),
        (SOURCE / "calendar.json").read_bytes(),
    )
    prepare(2003)
    assert (
        (SOURCE / "calendar_dates_v1.json").read_bytes(),
        (SOURCE / "calendar.json").read_bytes(),
    ) == before


def test_promoter_rejects_unstaged_year() -> None:
    with pytest.raises(ValueError, match="Only staged 1990–2003"):
        prepare(1989)


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
    assert built["provenance"]["dated_occurrences"] == 2407
    assert built["provenance"]["season_coverage_entries"] == 37
    assert sorted(built["provenance"]["date_coverage_years"]) == (
        list(range(1990, 2027))
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
    assert built["provenance"]["dated_occurrences"] == 2407
    assert built["provenance"]["season_coverage_entries"] == 37
    assert built["provenance"]["date_coverage_years"] == (
        list(range(1990, 2027))
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
