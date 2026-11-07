"""Deterministic, read-only ATP Earth W52 week projection (candidate V1).

ATP reference dates are retained verbatim. This projection is *not* a sporting
Calendar, Run mutation, Match/Edition schedule, ISO-to-civil-date conversion or
approval to create Simulation Slots. It produces reviewable labels only.

CLI:
    python scripts/audit_atp_earth_week_mapping_v1.py --check
    python scripts/audit_atp_earth_week_mapping_v1.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# Support direct invocation from the repository root without an installed package.
ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))
from scripts.build_atp_historical_calendar import SOURCE

SOURCE_FILE = SOURCE / "calendar_dates_v1.json"
FIRST_YEAR, LAST_YEAR = 1990, 2026
MAPPING_POLICY = "atp_earth_w52_week_projection.v1"
# Approved as an explicit source-only exception: Brisbane 2010 started on
# Sunday 2010-01-03, which belongs to ISO 2009/W53. Its closing week is
# 2010/W01. W53 is retained in original ISO evidence, not put into the W52 Run.
REVIEWED_ISO_53_SOURCE_ONLY = frozenset({(2010, "brisbane")})


def _date(value: Any, *, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an exact ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field}: {value}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"Noncanonical {field}: {value}")
    return parsed


def _iso_weeks(start: date, end: date) -> list[dict[str, int]]:
    monday = start - timedelta(days=start.weekday())
    result: list[dict[str, int]] = []
    while monday <= end:
        year, week, _ = monday.isocalendar()
        result.append({"calendar_year": year, "year_week": week})
        monday += timedelta(days=7)
    return result


def _last_week_end_day(end: date) -> str:
    return ("Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday")[end.weekday()]


def map_one(*, season_year: int, series_id: str,
            start_date: str, end_date: str,
            year_source_status: str) -> dict[str, Any]:
    """Map one independently dated parent Series, never assigning partial weeks.

    At most 8 days -> the single ISO week containing the most source days;
    9+ days covering exactly two ISO weeks -> both; 9+ days covering three -> all three and an explicit review
    flag. Do not silently renumber W53 or infer tournament rounds.
    """
    if type(season_year) is not int or not FIRST_YEAR <= season_year <= LAST_YEAR:
        raise ValueError("Unexpected ATP season year")
    if not isinstance(series_id, str) or not series_id:
        raise ValueError("Missing Series identity")
    start, end = (
        _date(start_date, field="start_date"),
        _date(end_date, field="end_date"),
    )
    days = (end - start).days + 1
    if not 5 <= days <= 14:
        raise ValueError(f"Source event duration requires individual review: {season_year}/{series_id}")
    touched = _iso_weeks(start, end)
    if not 1 <= len(touched) <= 3:
        raise ValueError("Source ISO week span outside reviewed projection")
    # The source's year is the officially indexed ATP results/schedule year,
    # not necessarily the ISO year of the first civil day.
    if end.isocalendar().year != season_year:
        raise ValueError(f"Source end ISO year disagrees with ATP year: {season_year}/{series_id}")

    # The source interval may start on Sunday or end on Tuesday/Monday. A
    # closing-week-only rule can move most of an event into the wrong week.
    # For short events select the ISO week containing the most source days;
    # retain source finish separately. Tied majority weeks are never guessed.
    day_counts = { (week["calendar_year"], week["year_week"]): 0 for week in touched }
    cursor = start
    while cursor <= end:
        y, w, _ = cursor.isocalendar()
        day_counts[(y, w)] += 1
        cursor += timedelta(days=1)
    if days <= 8:
        majority = max(day_counts.values())
        winners = [week for week in touched if day_counts[(week["calendar_year"], week["year_week"])] == majority]
        if len(winners) != 1:
            raise ValueError(f"Ambiguous short-event majority week: {season_year}/{series_id}")
        selected = winners
        rule = "single_majority_week"
    elif len(touched) == 2:
        selected = touched
        rule = "two_source_iso_weeks"
    elif len(touched) == 3:
        selected = touched
        rule = "three_source_iso_weeks_reviewed"
    else:
        raise ValueError(f"Unsupported long ATP event interval: {season_year}/{series_id}")

    key = (season_year, series_id)
    touches_iso53 = any(x["year_week"] == 53 for x in touched)
    if touches_iso53:
        if key not in REVIEWED_ISO_53_SOURCE_ONLY:
            raise ValueError(f"Unreviewed source ISO W53: {season_year}/{series_id}")
        if any(x["year_week"] == 53 for x in selected):
            raise ValueError("ISO W53 cannot silently become an Earth W52 week")
    elif key in REVIEWED_ISO_53_SOURCE_ONLY:
        raise ValueError("Pinned Brisbane ISO W53 exception no longer matches source")

    if any(x["year_week"] > 52 for x in selected):
        raise ValueError("Earth W52 projection cannot contain ISO W53")

    flags: list[str] = []
    if len(touched) > len(selected):
        flags.append("compressed_boundary_iso_week")
    if touched[0]["calendar_year"] != touched[-1]["calendar_year"]:
        flags.append("cross_iso_year")
    if touches_iso53:
        flags.append("reviewed_source_iso_week_53_not_projected")
    if len(selected) == 3:
        flags.append("three_week_interval_manual_sporting_review")
    if days <= 8 and selected[0] != touched[-1]:
        flags.append("single_week_majority_precedes_finish_week")
        if end.weekday() == 0:
            flags.append("monday_finish_majority_in_prior_iso_week")
    if end.weekday() not in (5, 6):
        flags.append("non_weekend_finish")
    if year_source_status == "provisional_published_schedule":
        flags.append("provisional_2026")
    if selected[-1]["calendar_year"] != season_year:
        raise ValueError("End-week assignment must stay within ATP source season")

    return {
        "source_identity": f"atp_{season_year}_{series_id}",
        "atp_season_year": season_year,
        "series_id": series_id,
        "original_start_date": start.isoformat(),
        "original_end_date": end.isoformat(),
        "source_iso_weeks": touched,
        "source_iso_week_day_counts": [
            {**week, "source_days_in_week": day_counts[(week["calendar_year"], week["year_week"])]}
            for week in touched
        ],
        "source_finish_iso_week": touched[-1],
        "source_duration_days_inclusive": days,
        "source_finish_day": _last_week_end_day(end),
        "mapped_year_weeks": selected,
        "mapping_rule": rule,
        "review_flags": flags,
        "source_year_status": year_source_status,
        "sporting_schedule_installed": False,
    }


def build_projection(dated: dict[str, Any]) -> dict[str, Any]:
    if dated.get("schema_version") != "tennis.atp_tour_calendar_dates.v1":
        raise ValueError("Invalid ATP date source version")
    if dated.get("reference_span") != {"from": FIRST_YEAR, "to": LAST_YEAR}:
        raise ValueError("Invalid ATP date source span")
    source_years = dated.get("year_sources")
    if not isinstance(source_years, dict) or set(source_years) != {
        str(y) for y in range(FIRST_YEAR, LAST_YEAR + 1)
    }:
        raise ValueError("Expected all 37 source seasons")

    mappings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        row = source_years[str(year)]
        status = row.get("status")
        if status not in {
            "verified_results_archive",
            "verified_atp_results_archive_with_separate_finals_historical_window",
            "provisional_published_schedule",
        } or (status == "provisional_published_schedule") != (year == 2026):
            raise ValueError("Invalid ATP source-year provenance status")
        if not isinstance(row.get("events"), list):
            raise ValueError("Invalid ATP year events")
        for entry in row["events"]:
            item = map_one(
                season_year=year,
                series_id=entry["series_id"],
                start_date=entry["start_date"],
                end_date=entry["end_date"],
                year_source_status=status,
            )
            key = item["source_identity"]
            if key in seen:
                raise ValueError("Duplicate source occurrence: " + key)
            seen.add(key)
            mappings.append(item)

    # Sorting makes the audit stable even when a source JSON object's order
    # changes; the original dated source remains authoritative.
    mappings.sort(key=lambda x: (x["atp_season_year"], x["series_id"]))
    occupancy = Counter(len(item["mapped_year_weeks"]) for item in mappings)
    touched = Counter(len(item["source_iso_weeks"]) for item in mappings)
    flags = Counter(flag for item in mappings for flag in item["review_flags"])
    week_events: dict[tuple[int, int], list[str]] = {}
    for item in mappings:
        for week in item["mapped_year_weeks"]:
            key = (week["calendar_year"], week["year_week"])
            week_events.setdefault(key, []).append(item["source_identity"])
    overlap_counts = Counter(len(events) for events in week_events.values())
    maximum_overlap = max(overlap_counts, default=0)
    summary = {
        "source_event_count": len(mappings),
        "simulated_week_count_distribution": {
            str(n): occupancy.get(n, 0) for n in (1, 2, 3)
        },
        "source_iso_week_count_distribution": {
            str(n): touched.get(n, 0) for n in (1, 2, 3)
        },
        "review_flag_counts": dict(sorted(flags.items())),
        "source_non_weekend_finishes": sum(
            item["source_finish_day"] not in ("Saturday", "Sunday")
            for item in mappings
        ),
        "source_years": LAST_YEAR - FIRST_YEAR + 1,
        "provisional_years": [2026],
        "distinct_mapped_year_weeks": len(week_events),
        "mapped_week_concurrency_distribution": {
            str(n): overlap_counts.get(n, 0)
            for n in range(1, maximum_overlap + 1)
        },
        "max_parallel_source_tournaments_in_week": maximum_overlap,
        "weekly_occupancy_is_not_player_conflict_evidence": True,
        "sporting_schedule_installed": False,
    }
    if (summary["source_event_count"] != 2407
        or summary["simulated_week_count_distribution"] != {
            "1": 2325, "2": 79, "3": 3
        }):
        raise ValueError(
            "ATP source or projection has changed; review before accepting new counts"
        )
    return {
        "schema_version": MAPPING_POLICY,
        "source_file": "calendar_dates_v1.json",
        "reference_span": {"from": FIRST_YEAR, "to": LAST_YEAR},
        "source_calendar_dates_sha256": hashlib.sha256(
            json.dumps(dated, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "intended_run_weeks_per_year": 52,
        "not_a_gregorian_or_iso_year_conversion": True,
        "requires_explicit_sporting_import_design": True,
        "summary": summary,
        "mappings": mappings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Read-only count and safety audit")
    group.add_argument("--json", action="store_true", help="Print full deterministic audit JSON")
    args = parser.parse_args()
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    report = build_projection(source)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
        print("Reference-only projection; no Run or sporting calendar was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
