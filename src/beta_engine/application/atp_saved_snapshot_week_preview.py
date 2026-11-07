"""Project ORIGINAL Saved ATP reference Package values, never current server files.

This read-only adapter uses only the hash-verified Run Package state captured
by the immutable Saved Revision. Uncommitted Working Draft changes and
subsequently updated server reference files cannot alter the result.
A reference projection is not an executable Tour calendar or ranking closure.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from beta_engine.application.atp_historical_calendar_adapter import (
    CALENDAR_COVERAGE_KIND,
    CALENDAR_OCCURRENCE_KIND,
)
from beta_engine.domain.run_packages import PackageType, RunPackageState
from scripts.audit_atp_earth_week_mapping_v1 import build_projection
from scripts.build_atp_historical_calendar import CALENDAR_ID


def build_saved_atp_reference_week_mapping(state: RunPackageState) -> dict[str, Any]:
    """Recompute source-week labels strictly from immutable Run-owned entities.

    This expects the reviewed complete original ATP 1990–2026 source inventory
    and rejects missing, manually edited or internally inconsistent records.
    The output is intentionally NOT sourced from calendar_dates_v1.json.
    """
    if not isinstance(state, RunPackageState):
        raise ValueError("A typed Saved Run Package state is required")
    versions = [
        item for item in state.package_versions
        if item.package_id == CALENDAR_ID
    ]
    if len(versions) != 1 or versions[0].package_type != PackageType.CALENDAR or versions[0].source_version != 1:
        raise ValueError("Saved ATP Calendar Package version missing or unsupported")
    version = versions[0]
    entities = [e for e in state.entities if e.source_package_id == CALENDAR_ID]
    if len(entities) != 2444:
        raise ValueError("Incomplete Saved ATP Calendar reference entities")
    coverage: dict[int, dict[str, Any]] = {}
    events: dict[int, list[dict[str, str]]] = {year: [] for year in range(1990, 2027)}
    for entity in entities:
        if (
            entity.source_package_version != version.source_version
            or entity.source_package_fingerprint != version.source_fingerprint
            or entity.provenance != "package"
            or entity.source_baseline_fingerprint != entity.content_fingerprint
        ):
            raise ValueError("Saved ATP Calendar reference was locally edited or source history differs")
        p = entity.payload
        if not isinstance(p, dict) or p.get("not_squash_rules") is not True:
            raise ValueError("Saved ATP entity lost its non-sporting source boundary")
        year = p.get("atp_season_year")
        if type(year) is not int or not 1990 <= year <= 2026:
            raise ValueError("Saved ATP entity source year is invalid")
        if entity.entity_kind == CALENDAR_COVERAGE_KIND:
            if (
                year in coverage
                or entity.source_entity_id != f"season_{year}_date_coverage"
                or p.get("no_fabricated_dates") is not True
                or not isinstance(p.get("known_not_held_series_ids"), list)
                or p.get("undated_series_ids") != []
                or not isinstance(p.get("year_source_status"), str)
            ):
                raise ValueError("Saved ATP coverage row is incomplete or invalid")
            coverage[year] = p
        elif entity.entity_kind == CALENDAR_OCCURRENCE_KIND:
            sid = p.get("series_id")
            if (
                not isinstance(sid, str) or not sid
                or entity.source_entity_id != f"atp_{year}_{sid}"
                or p.get("no_match_or_result_claim") is not True
                or p.get("run_week_projection") != "not_applied_source_only"
            ):
                raise ValueError("Saved ATP source occurrence identity or boundary invalid")
            # These source fields must agree exactly; never infer missing dates.
            try:
                start = date.fromisoformat(p["start_date"])
                end = date.fromisoformat(p["end_date"])
                from scripts.build_atp_historical_calendar import iso_weeks_touched
                occupied = iso_weeks_touched(start, end)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Saved ATP occurrence has invalid original dates") from exc
            if (
                start.isoformat() != p["start_date"]
                or end.isoformat() != p["end_date"]
                or p.get("start_calendar_year") != start.year
                or p.get("start_year_week") != occupied[0]
                or p.get("end_year_week") != occupied[-1]
                or p.get("iso_weeks_occupied") != occupied
                or p.get("duration_days_inclusive") != (end - start).days + 1
            ):
                raise ValueError("Saved ATP occurrence date/ISO evidence mismatch")
            events[year].append({
                "series_id": sid,
                "start_date": p["start_date"],
                "end_date": p["end_date"],
                "source_year_status": p.get("year_source_state"),
            })
        else:
            raise ValueError("Unexpected Saved ATP Calendar entity kind")
    if set(coverage) != set(events):
        raise ValueError("Missing Saved ATP year coverage")
    if sum(len(items) for items in events.values()) != 2407:
        raise ValueError("Saved ATP source event count is not complete")
    if sum(len(row["known_not_held_series_ids"]) for row in coverage.values()) != 24:
        raise ValueError("Saved ATP known-not-held inventory changed")
    source_years: dict[str, dict[str, Any]] = {}
    for year, rows in events.items():
        c = coverage[year]
        known_not_held = c["known_not_held_series_ids"]
        if (
            c.get("dated_series_count") != len(rows)
            or c.get("roster_series_count") != len(rows) + len(known_not_held)
            or len(known_not_held) != len(set(known_not_held))
            or any(e["source_year_status"] != c["year_source_status"] for e in rows)
        ):
            raise ValueError("Saved ATP source-year coverage disagrees with dated occurrences")
        source_years[str(year)] = {
            "status": c["year_source_status"],
            "events": [
                {
                    "series_id": e["series_id"],
                    "start_date": e["start_date"],
                    "end_date": e["end_date"],
                } for e in rows
            ],
        }
    report = build_projection({
        "schema_version": "tennis.atp_tour_calendar_dates.v1",
        "reference_span": {"from": 1990, "to": 2026},
        "year_sources": source_years,
    })
    # build_projection normally describes a server source FILE. Here it was
    # fed reconstructed Saved entity data, not that mutable file.
    report.pop("source_file")
    report.pop("source_calendar_dates_sha256")
    report["source_origin"] = "immutable_saved_run_package_state.v1"
    report["saved_source_state_fingerprint"] = state.fingerprint
    report["saved_calendar_package_fingerprint"] = version.source_fingerprint
    report["source_only_no_sporting_authority"] = True
    return report
