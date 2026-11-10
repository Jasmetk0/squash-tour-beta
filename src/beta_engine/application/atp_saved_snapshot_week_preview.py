"""Project ORIGINAL Saved ATP reference Package values, never current server files.

This read-only adapter uses only the hash-verified Run Package state captured
by the immutable Saved Revision. Uncommitted Working Draft changes and
subsequently updated server reference files cannot alter the result.
A reference projection is not an executable Tour calendar or ranking closure.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from beta_engine.application.atp_historical_calendar_adapter import (
    CALENDAR_COVERAGE_KIND,
    CALENDAR_OCCURRENCE_KIND,
)
from beta_engine.application.atp_reference_package_adapter import (
    CATEGORY_ID, CATEGORY_KIND, CATEGORY_SCOPE, SERIES_ID, SERIES_KIND, SERIES_SCOPE,
)
from beta_engine.domain.run_packages import (
    PackageType, RunPackageEntity, RunPackageState, SourceReference,
)
from beta_engine.application.atp_earth_week_mapping import build_projection
from beta_engine.application.atp_historical_calendar_source import CALENDAR_ID, iso_weeks_touched


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



def _original_source_entities(
    state: RunPackageState, package_id: str, package_type: PackageType, *,
    entity_kind: str, scope: str, expected_count: int,
) -> dict[str, RunPackageEntity]:
    versions = [item for item in state.package_versions if item.package_id == package_id]
    if len(versions) != 1 or versions[0].package_type != package_type or versions[0].source_version != 1:
        raise ValueError(f"Saved ATP source Package is missing or unsupported: {package_id}")
    version = versions[0]
    entities = {e.source_entity_id: e for e in state.entities if e.source_package_id == package_id}
    if len(entities) != expected_count:
        raise ValueError(f"Saved ATP source Package is incomplete: {package_id}")
    for entity in entities.values():
        if (
            entity.source_package_version != version.source_version
            or entity.source_package_fingerprint != version.source_fingerprint
            or entity.entity_kind != entity_kind
            or entity.entity_schema_version != 1
            or entity.scope != scope
            or entity.payload.get("not_squash_rules") is not True
            or entity.provenance != "package"
            or entity.source_baseline_fingerprint != entity.content_fingerprint
        ):
            raise ValueError(f"Saved ATP source was locally edited or is invalid: {entity.source_entity_id}")
    return entities


def _effective_period(entity: RunPackageEntity, year: int) -> dict[str, Any]:
    periods = entity.payload.get("history_periods")
    if not isinstance(periods, list) or any(
        not isinstance(period, dict)
        or type(period.get("from")) is not int or type(period.get("to")) is not int
        or period["from"] > period["to"]
        for period in periods
    ):
        raise ValueError(f"Invalid Saved ATP history: {entity.source_entity_id}")
    effective = [period for period in periods if period["from"] <= year <= period["to"]]
    if len(effective) != 1:
        raise ValueError(f"Ambiguous or missing Saved ATP history: {entity.source_entity_id} in {year}")
    return effective[0]


def audit_saved_atp_tour_bindings(
    state: RunPackageState, *, selected_occurrences: frozenset[str],
) -> dict[str, Any]:
    """Verify Tour links after the Saved Calendar mapping has been validated."""
    categories = _original_source_entities(
        state, CATEGORY_ID, PackageType.CATEGORY,
        entity_kind=CATEGORY_KIND, scope=CATEGORY_SCOPE, expected_count=11,
    )
    series = _original_source_entities(
        state, SERIES_ID, PackageType.SERIES,
        entity_kind=SERIES_KIND, scope=SERIES_SCOPE, expected_count=164,
    )
    counts: Counter[str] = Counter()
    selected: dict[str, dict[str, Any]] = {}
    for event in state.entities:
        if event.source_package_id != CALENDAR_ID or event.entity_kind != CALENDAR_OCCURRENCE_KIND:
            continue
        year = event.payload["atp_season_year"]
        category_id = event.payload.get("category_id")
        series_id = event.payload["series_id"]
        category = categories.get(category_id) if isinstance(category_id, str) else None
        tournament = series.get(series_id)
        if category is None or tournament is None:
            raise ValueError(f"Unresolved Saved ATP Category or Series: {event.source_entity_id}")
        expected_refs = {
            SourceReference(
                source_package_id=CATEGORY_ID, source_entity_id=category_id,
                expected_entity_kind=CATEGORY_KIND,
            ),
            SourceReference(
                source_package_id=SERIES_ID, source_entity_id=series_id,
                expected_entity_kind=SERIES_KIND,
            ),
        }
        if len(event.references) != 2 or set(event.references) != expected_refs:
            raise ValueError(f"Saved ATP Calendar references disagree: {event.source_entity_id}")
        series_period = _effective_period(tournament, year)
        category_period = _effective_period(category, year)
        if series_period.get("category_id") != category_id:
            raise ValueError(f"Saved ATP Category does not match the Series year: {event.source_entity_id}")
        counts[category_id] += 1
        if event.source_entity_id in selected_occurrences:
            selected[event.source_entity_id] = {
                "series_id": series_id,
                "series_name": tournament.payload["name"],
                "category_id": category_id,
                "historical_category_label": category_period["historical_label"],
            }
    if sum(counts.values()) != 2407:
        raise ValueError("Saved ATP Tour bindings do not cover all 2,407 occurrences")
    if set(selected) != selected_occurrences:
        raise ValueError("Selected ATP occurrences do not match the verified Saved source")
    return {
        "verified_occurrences": sum(counts.values()),
        "occurrences_by_category": dict(sorted(counts.items())),
        "selected_occurrences": dict(sorted(selected.items())),
    }
