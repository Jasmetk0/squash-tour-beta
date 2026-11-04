"""Read-only census and source-evidence audit for ALL 1990–2026 ATP years.

Nothing in this script promotes staged candidate dates, changes a Package, or
maps historical tennis events into a playable FAX sporting Run.
The two distinct metrics are:
  - year-effective roster coverage (sourced exact event windows);
  - canonically imported Package occurrence coverage (published snapshot).
A staged, source-conflicted year NEVER counts as canonically dated.

Usage:
    python scripts/audit_atp_calendar_full_roster.py --check
    python scripts/audit_atp_calendar_full_roster.py --json
"""
from __future__ import annotations

import argparse
import json

from scripts.audit_atp_calendar_backfill import (
    SOURCE_DATE_CONFLICTS, audit_candidates,
)
from scripts.build_atp_historical_calendar import SOURCE, build, canonical


def _read(name: str) -> dict:
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def audit_full_roster() -> dict:
    categories = _read("category.json")
    series = _read("series.json")
    seasons = _read("seasons_1990_2026.json")
    dated = _read("calendar_dates_v1.json")
    generated = build(categories, series, seasons, dated)
    if canonical(generated) != (SOURCE / "calendar.json").read_text(encoding="utf-8"):
        raise ValueError("Canonical ATP Calendar snapshot disagrees with its inputs")

    historical = {row["year"]: row for row in seasons["seasons"]}
    if set(historical) != set(range(1990, 2027)):
        raise ValueError("Expected exactly the 37 year-effective ATP seasons")
    sources = dated["year_sources"]
    if set(sources) - {str(year) for year in historical}:
        raise ValueError("Unexpected canonical year")
    old_entities = {
        e["source_entity_id"]: e for e in generated["entities"]
        if e["entity_kind"] == "tennis.calendar.occurrence.reference.v1"
    }
    year_rows: list[dict] = []
    staged_conflicts: list[int] = []
    noncanonical_years: list[int] = []
    total_memberships = 0
    total_known_not_held = 0
    total_canonical = 0
    total_staged = 0
    for year in range(1990, 2027):
        season = historical[year]
        active = season["series_category_ids"]
        not_held = set(season["known_not_held_series_ids"])
        if not not_held <= set(active):
            raise ValueError(f"Unknown cancelled Series for ATP {year}")
        expected = set(active) - not_held
        total_memberships += len(active)
        total_known_not_held += len(not_held)
        canonical_year = sources.get(str(year))
        if canonical_year is not None:
            rows = canonical_year["events"]
            seen = {row["series_id"] for row in rows}
            if len(rows) != len(seen) or seen != expected:
                raise ValueError(f"Canonical ATP {year} does not cover original source roster")
            for sid in expected:
                entity = old_entities.get(f"atp_{year}_{sid}")
                if entity is None or entity["payload"]["atp_season_year"] != year:
                    raise ValueError(f"Missing canonical occurrence ATP {year}/{sid}")
            total_canonical += len(rows)
            mode = (
                "canonical_provisional"
                if canonical_year["status"] == "provisional_published_schedule"
                else "canonical_historic"
            )
            conflicts = []
        else:
            noncanonical_years.append(year)
            staged_file = SOURCE / f"calendar_backfill_{year}_candidates_v1.json"
            if not staged_file.is_file():
                raise ValueError(f"Missing original ATP source candidate year: {year}")
            audit = audit_candidates(_read(staged_file.name), seasons, dated)
            if audit["candidate_count"] != len(expected):
                raise ValueError(f"ATP {year} staged dates omit original source Series")
            if audit["remaining_series_ids"] or audit["canonical_conflicts"]:
                raise ValueError(f"ATP {year} staged/parent roster mismatch")
            if not audit["roster_reconciled"]:
                raise ValueError(f"ATP {year} staged roster not completely sourced")
            conflicts = sorted(audit["unresolved_date_conflicts"])
            if audit["unresolved_date_conflicts"] != SOURCE_DATE_CONFLICTS.get(year, {}):
                raise ValueError(f"ATP {year} source conflict registry disagrees")
            if conflicts:
                staged_conflicts.append(year)
                mode = "staged_blocked_official_date_discrepancy"
            else:
                mode = "staged_source_complete_not_imported"
            total_staged += audit["candidate_count"]
        year_rows.append({
            "year": year,
            "mode": mode,
            "parent_series_count": len(active),
            "known_not_held_count": len(not_held),
            "dated_parent_series_count": len(expected),
            "unresolved_conflict_series_ids": conflicts,
        })

    if total_canonical != generated["provenance"]["dated_occurrences"]:
        raise ValueError("Canonical annual occurrence totals do not match Package")
    if total_canonical != len(old_entities):
        raise ValueError("Duplicate or extra historical occurrences in source Package")
    if total_canonical + total_staged + total_known_not_held != total_memberships:
        raise ValueError("ATP parent roster census is not partitioned exactly")
    if len(generated["entities"]) != total_canonical + 37:
        raise ValueError("Unexpected number of ATP Calendar coverage entities")
    if sorted(int(y) for y in sources) != generated["provenance"]["date_coverage_years"]:
        raise ValueError("Canonical dated-year provenance mismatch")
    if sorted(set(noncanonical_years)) != sorted(noncanonical_years):
        raise ValueError("Duplicate staged year")

    return {
        "reference_span": {"from": 1990, "to": 2026},
        "year_count": len(year_rows),
        "source_dated_year_count": len(year_rows),
        "canonical_year_count": len(sources),
        "noncanonical_staged_years": noncanonical_years,
        "staged_conflict_years": staged_conflicts,
        "canonical_dated_occurrences": total_canonical,
        "staged_exact_date_candidates": total_staged,
        "total_dated_original_events": total_canonical + total_staged,
        "known_not_held_parent_memberships": total_known_not_held,
        "total_parent_year_series_memberships": total_memberships,
        "calendar_source_entity_count": len(generated["entities"]),
        "provisional_canonical_years": [
            r["year"] for r in year_rows if r["mode"] == "canonical_provisional"
        ],
        "all_year_effective_parent_ids_have_exact_date_evidence": True,
        "all_years_canonical_and_final": (
            not noncanonical_years
            and not any(r["mode"] == "canonical_provisional" for r in year_rows)
        ),
        "independent_licence_lineage_certified": False,
        "playable_fax_calendar": False,
        "year_rows": year_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true", help="Fail unless all original source parent rosters have exact dates")
    args = parser.parse_args()
    report = audit_full_roster()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"ATP 1990–2026: {report['source_dated_year_count']}/37 year cohorts "
            f"source-dated, {report['canonical_year_count']}/37 canonical; "
            f"{report['canonical_dated_occurrences']} canonical + "
            f"{report['staged_exact_date_candidates']} staged exact-date candidates, "
            f"{report['known_not_held_parent_memberships']} explicitly not-held "
            "parent memberships. No automatic import or FAX sporting change."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
