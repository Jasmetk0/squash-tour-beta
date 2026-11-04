"""Audit staged ATP Calendar date candidates before promoting a COMPLETE year.

This is strictly read-only: it never modifies canonical Calendar Package data.
Partial cohorts are useful evidence but must not be silently published as
complete/verified season calendars.

Run:
    python scripts/audit_atp_calendar_backfill.py
    python scripts/audit_atp_calendar_backfill.py --json
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from scripts.build_atp_historical_calendar import (
    SOURCE, ensure_archive_year_matches, iso_weeks_touched, official_url,
    parse_exact_date,
)


def audit_candidates(
    candidate: dict, seasons: dict, existing_dates: dict,
) -> dict:
    if candidate.get("schema_version") != (
        "tennis.atp_tour_calendar_backfill_candidates.v1"
    ):
        raise ValueError("Unknown candidate ledger schema")
    year = candidate.get("year")
    if type(year) is not int or not 1990 <= year <= 2026:
        raise ValueError("Invalid ATP year")
    official_url(candidate.get("source_url"), identity=str(year))
    ensure_archive_year_matches(candidate["source_url"], year=year)
    if candidate.get("status") != (
        "partial_official_archive_transcription_requires_full_year_reconciliation"
    ):
        raise ValueError("Candidate ledger must explicitly state partial status")
    parse_exact_date(candidate.get("as_of"), identity="candidate as_of")
    season = next((x for x in seasons["seasons"] if x["year"] == year), None)
    if season is None:
        raise ValueError("Missing historical source year")
    active = season["series_category_ids"]
    not_held = set(season["known_not_held_series_ids"])
    raw_events = candidate.get("events")
    if not isinstance(raw_events, list):
        raise ValueError("Missing candidate events")
    seen = set()
    validated = []
    for row in raw_events:
        if not isinstance(row, dict) or set(row) != {
            "historical_host", "series_id", "start_date", "end_date"
        }:
            raise ValueError("Invalid candidate shape")
        sid = row["series_id"]
        if not isinstance(sid, str) or sid not in active:
            raise ValueError("Candidate Series not active in historical year")
        if sid in not_held:
            raise ValueError("Known unheld Series cannot have event dates")
        if sid in seen:
            raise ValueError("Duplicate candidate Series")
        if not isinstance(row["historical_host"], str) or not row["historical_host"].strip():
            raise ValueError("Missing historical host")
        seen.add(sid)
        start = parse_exact_date(row["start_date"], identity=sid)
        end = parse_exact_date(row["end_date"], identity=sid)
        if start.year not in {year - 1, year} or end.year != year:
            raise ValueError("Invalid ATP event year")
        if start.year == year - 1 and start.month != 12:
            raise ValueError("Prior year event must start in December")
        weeks = iso_weeks_touched(start, end)
        validated.append({
            "series_id": sid,
            "historical_host": row["historical_host"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "category_id": active[sid],
            "iso_weeks_occupied": weeks,
            "source_url": candidate["source_url"],
        })
    current = existing_dates.get("year_sources", {}).get(str(year))
    already_dated = {x["series_id"] for x in current["events"]} if current else set()
    conflicts = sorted(already_dated & seen)
    remaining = sorted(set(active) - not_held - seen - already_dated)
    return {
        "year": year,
        "source_url": candidate["source_url"],
        "source_status": "partial_candidate_not_calendar",
        "candidate_count": len(seen),
        "existing_canonical_count": len(already_dated),
        "expected_played_source_count": len(active) - len(not_held),
        "remaining_series_ids": remaining,
        "canonical_conflicts": conflicts,
        "ready_for_whole_year_promotion": not remaining and not conflicts,
        "candidate_events": validated,
        "warning": (
            "Even zero missing parent Series IDs do not prove a complete ATP "
            "tournament census or legal licence-lineage certainty."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    candidate = json.loads(
        (SOURCE / "calendar_backfill_2003_candidates_v1.json").read_text(
            encoding="utf-8"
        )
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    existing = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    result = audit_candidates(candidate, seasons, existing)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            f"ATP {result['year']}: {result['candidate_count']} candidates, "
            f"{len(result['remaining_series_ids'])} missing Series, "
            f"{len(result['canonical_conflicts'])} conflicts. "
            "Canonical source unchanged."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
