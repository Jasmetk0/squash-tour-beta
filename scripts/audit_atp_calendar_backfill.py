"""Audit staged ATP Calendar date candidates before promoting a COMPLETE year.

This is strictly read-only: it never modifies canonical Calendar Package data.
Partial cohorts are useful evidence but must not be silently published as
complete/verified season calendars.

Run:
    python scripts/audit_atp_calendar_backfill.py
    python scripts/audit_atp_calendar_backfill.py --json --year 2002
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


SOURCE_DATE_CONFLICTS = {
    # ATP annual archive: Nov 10–16; ATP Finals heritage: Nov 11–16.
    1997: {
        "atp_finals": (
            "ATP 1997 results archive: 1997-11-10 to 1997-11-16; "
            "ATP Finals heritage: 1997-11-11 to 1997-11-16"
        ),
    },
    # ATP 1998 annual results archive: 23–29 November. ATP Finals
    # historical results: 24–29 November. Keep the event-date convention
    # discrepancy explicit, and block canonical promotion.
    1998: {
        "atp_finals": (
            "ATP 1998 results archive: 1998-11-23 to 1998-11-29; "
            "ATP Finals heritage: 1998-11-24 to 1998-11-29"
        ),
    },
    # ATP 1999 annual results index: 22–28 November.
    # ATP Finals heritage: 23–28 November. Do not silently collapse
    # different official ATP event-date conventions.
    1999: {
        "atp_finals": (
            "ATP 1999 results archive: 1999-11-22 to 1999-11-28; "
            "ATP Finals heritage: 1999-11-23 to 1999-11-28"
        ),
    },
    # The published ATP annual archive labels 10–16 Nov, whereas an ATP
    # historical tournament overview cites 8–16 Nov. Resolve which date
    # convention the calendar represents before a whole-year import.
    2003: {
        "atp_finals": (
            "ATP 2003 year results archive: 2003-11-10 to 2003-11-16; "
            "ATP Tournament History overview: 2003-11-08 to 2003-11-16"
        ),
    },
}

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
        duration_days = (end - start).days + 1
        if duration_days < 1 or duration_days > 35:
            raise ValueError(
                f"Historical ATP event duration must be 1–35 days: "
                f"{year}/{sid}, {row['start_date']}..{row['end_date']}"
            )
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
    evidence_conflicts = SOURCE_DATE_CONFLICTS.get(year, {})
    roster_reconciled = (not remaining and len(seen) == len(active) - len(not_held))
    return {
        "year": year,
        "source_url": candidate["source_url"],
        "source_status": "partial_candidate_not_calendar",
        "candidate_count": len(seen),
        "existing_canonical_count": len(already_dated),
        "expected_played_source_count": len(active) - len(not_held),
        "remaining_series_ids": remaining,
        "canonical_conflicts": conflicts,
        "roster_reconciled": roster_reconciled,
        "unresolved_date_conflicts": evidence_conflicts,
        "ready_for_whole_year_promotion": bool(
            roster_reconciled and not conflicts and not evidence_conflicts
        ),
        "candidate_events": validated,
        "warning": (
            "Even zero missing parent Series IDs do not prove a complete ATP "
            "tournament census or legal licence-lineage certainty."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--year", type=int, choices=(1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003), default=2003)
    args = parser.parse_args()
    candidate = json.loads(
        (SOURCE / f"calendar_backfill_{args.year}_candidates_v1.json").read_text(
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
            f"{len(result['canonical_conflicts'])} canonical conflicts, "
            f"{len(result['unresolved_date_conflicts'])} date-source conflicts. "
            "Canonical source unchanged."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
