"""Shared assertions for canonical ATP Calendar backfill evidence."""

from __future__ import annotations

import json

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE
from scripts.promote_atp_calendar_candidate import prepare


def read_backfill_inputs(year: int) -> tuple[dict, dict, dict]:
    filenames = (
        f"calendar_backfill_{year}_candidates_v1.json",
        "seasons_1990_2026.json",
        "calendar_dates_v1.json",
    )
    candidate, seasons, dates = (
        json.loads((SOURCE / name).read_text(encoding="utf-8")) for name in filenames
    )
    return candidate, seasons, dates


def audit_canonical_backfill(year: int, event_count: int) -> dict:
    candidate, seasons, dates = read_backfill_inputs(year)
    report = audit_candidates(candidate, seasons, dates)

    assert report["year"] == year
    assert report["candidate_count"] == event_count
    assert report["expected_played_source_count"] == event_count
    assert report["existing_canonical_count"] == event_count
    assert report["remaining_series_ids"] == []
    assert report["roster_reconciled"] is True
    assert len(report["canonical_conflicts"]) == event_count
    assert report["unresolved_date_conflicts"] == {}
    assert report["ready_for_whole_year_promotion"] is False
    assert len(dates["year_sources"][str(year)]["events"]) == event_count
    return report


def verify_idempotent_promotion(year: int, event_count: int) -> dict:
    dates_path = SOURCE / "calendar_dates_v1.json"
    calendar_path = SOURCE / "calendar.json"
    before = (dates_path.read_bytes(), calendar_path.read_bytes())

    dates, calendar, audit = prepare(year)

    assert audit["candidate_count"] == event_count
    assert audit["unresolved_date_conflicts"] == {}
    assert len(dates["year_sources"][str(year)]["events"]) == event_count
    assert calendar["provenance"]["dated_occurrences"] == 2407
    assert calendar["provenance"]["season_coverage_entries"] == 37
    assert calendar["provenance"]["date_coverage_years"] == list(range(1990, 2027))
    assert len(calendar["entities"]) == 2444
    assert (dates_path.read_bytes(), calendar_path.read_bytes()) == before
    return calendar
