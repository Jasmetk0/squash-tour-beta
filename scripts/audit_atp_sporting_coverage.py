"""Read-only ATP source inventory; never treats a profile as executable."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "config/reference_packages/atp_tour_1990_2026"
OCCURRENCE = "tennis.calendar.occurrence.reference.v1"
COVERAGE = "tennis.calendar.coverage.reference.v1"


def audit(calendar: dict, sporting: dict, years: list[int] | None = None) -> dict:
    """Cross-check all profile bindings, then report selected years only."""
    occurrences = {}
    coverage = {}
    for entity in calendar["entities"]:
        kind, payload = entity["entity_kind"], entity["payload"]
        year = payload["atp_season_year"]
        if kind == OCCURRENCE:
            key = entity["source_entity_id"]
            if key in occurrences or key != f"atp_{year}_{payload['series_id']}":
                raise ValueError(f"Duplicate or invalid occurrence: {key}")
            occurrences[key] = payload
        elif kind == COVERAGE:
            if year in coverage:
                raise ValueError(f"Duplicate coverage year: {year}")
            coverage[year] = payload
        else:
            raise ValueError(f"Unknown calendar entity kind: {kind}")
    profiles = {}
    for profile in sporting["profiles"]:
        key = profile["occurrence_id"]
        if key in profiles:
            raise ValueError(f"Duplicate profile: {key}")
        if key not in occurrences:
            raise ValueError(f"Orphan profile: {key}")
        event = occurrences[key]
        for field, source_field in (
            ("category_id", "category_id"), ("source_start_date", "start_date"),
            ("source_end_date", "end_date"),
        ):
            if profile[field] != event[source_field]:
                raise ValueError(f"Profile/calendar mismatch: {key} {field}")
        profiles[key] = profile
    selected = sorted(set(coverage if years is None else years))
    if not set(selected) <= set(coverage):
        raise ValueError("Requested year not in calendar coverage")
    if any(p["atp_season_year"] not in coverage for p in occurrences.values()):
        raise ValueError("Dated occurrence without year coverage")
    rows = []
    for year in selected:
        dated = [(key, event) for key, event in sorted(occurrences.items())
                 if event["atp_season_year"] == year]
        metadata = coverage[year]
        if len(dated) != metadata["dated_series_count"]:
            raise ValueError(f"Calendar dated count mismatch: {year}")
        counts = Counter(event["category_id"] for _, event in dated)
        present = Counter(event["category_id"] for key, event in dated if key in profiles)
        events = [
            {"occurrence_id": key, "category_id": event["category_id"],
             "start_date": event["start_date"], "end_date": event["end_date"],
             "profile_status": "profiled" if key in profiles else "missing",
             "profile_schema": profiles[key]["schema_version"] if key in profiles else None}
            for key, event in dated
        ]
        count = sum(present.values())
        rows.append({
            "year": year, "date_coverage_state": metadata["date_coverage_state"],
            "dated": len(dated), "profiled": count, "missing": len(dated) - count,
            "undated_series_ids": sorted(metadata["undated_series_ids"]),
            "known_not_held_series_ids": sorted(metadata["known_not_held_series_ids"]),
            "categories": {category: {"dated": total, "profiled": present[category],
                                       "missing": total - present[category]}
                           for category, total in sorted(counts.items())},
            "occurrences": events,
        })
    return {"schema_version": "atp_sporting_coverage_audit.v1",
            "calendar_source_version": calendar["source_version"],
            "sporting_source_version": sporting["source_version"],
            "execution_readiness_assessed": False, "years": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, action="append", help="Repeat; defaults to all years.")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        calendar = json.loads((args.source_root / "calendar.json").read_text(encoding="utf-8"))
        sporting = json.loads((args.source_root / "squash_sporting_profiles_v1.json").read_text(encoding="utf-8"))
        report = audit(calendar, sporting, args.year)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"ATP coverage audit failed: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
