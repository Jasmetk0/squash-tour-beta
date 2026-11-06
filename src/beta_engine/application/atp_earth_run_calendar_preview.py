"""Read-only ATP source-week labels mapped onto an explicit Run Calendar.

The result is a planning PREVIEW, not a playable Tour Edition, Match, Entry,
Ranking, Simulation Slot or persisted Calendar. No implicit civil days exist.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any, Mapping, Sequence

from beta_engine.domain.calendar.run_calendar import CALENDAR_SCHEMA_VERSION, RunCalendar
from beta_engine.domain.run_packages import canonical_hash

ATP_EARTH_RUN_WEEK_PREVIEW_SCHEMA = "atp_earth_run_week_preview.v1"
SOURCE_MAPPING_SCHEMA = "atp_earth_w52_week_projection.v1"
ATP_YEARS = frozenset(range(1990, 2027))


def preview_atp_earth_weeks_on_run(
    *,
    calendar: RunCalendar,
    mapping: Mapping[str, Any],
    years: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Project dated source occurrences to real RunCalendarPosition values.

    The caller supplies a real, explicit Run calendar. Never infer its W, offset,
    horizon or schema from the ATP source, and never silently skip out-of-range
    events. This is deliberately NOT an application or Run-state write API.
    """
    if not isinstance(calendar, RunCalendar):
        raise ValueError("An explicit RunCalendar is required")
    if calendar.schema_version != CALENDAR_SCHEMA_VERSION:
        raise ValueError("Legacy Run calendar cannot be reinterpreted for ATP")
    if calendar.weeks_per_year != 52:
        raise ValueError("ATP Earth V1 mapping requires Run W=52; no FAX/W61 conversion")
    if mapping.get("schema_version") != SOURCE_MAPPING_SCHEMA:
        raise ValueError("ATP source mapping schema mismatch")
    if mapping.get("intended_run_weeks_per_year") != 52:
        raise ValueError("ATP source mapping is not intended for Earth W52")
    if mapping.get("requires_explicit_sporting_import_design") is not True:
        raise ValueError("Expected non-sporting source-only mapping")
    if mapping.get("reference_span") != {"from": 1990, "to": 2026}:
        raise ValueError("Unexpected ATP mapping source span")

    raw_events = mapping.get("mappings")
    if not isinstance(raw_events, list) or len(raw_events) != 2407:
        raise ValueError("ATP mapping input must contain all 2407 source records")
    summary = mapping.get("summary")
    if not isinstance(summary, Mapping) or summary.get("source_event_count") != len(raw_events):
        raise ValueError("ATP mapping count provenance mismatch")

    if years is None:
        requested_years = sorted(ATP_YEARS)
    else:
        if not isinstance(years, (list, tuple)) or not years:
            raise ValueError("Select one or more explicit ATP source years")
        if any(type(y) is not int or y not in ATP_YEARS for y in years):
            raise ValueError("ATP preview year outside 1990–2026")
        if len(years) != len(set(years)):
            raise ValueError("Duplicate selected ATP year")
        requested_years = sorted(years)
    chosen = set(requested_years)

    preview: list[dict[str, Any]] = []
    seen: set[str] = set()
    by_run_ordinal: dict[int, list[str]] = {}
    for row in raw_events:
        if not isinstance(row, dict):
            raise ValueError("Invalid ATP mapping row")
        year = row.get("atp_season_year")
        if type(year) is not int or year not in ATP_YEARS:
            raise ValueError("Invalid ATP mapping year")
        if year not in chosen:
            continue
        identity = row.get("source_identity")
        if not isinstance(identity, str) or not identity.startswith(f"atp_{year}_"):
            raise ValueError("Invalid ATP source occurrence identity")
        if identity in seen:
            raise ValueError("Duplicate ATP mapped occurrence")
        seen.add(identity)
        if row.get("sporting_schedule_installed") is not False:
            raise ValueError("Unexpected sporting authority in source mapping")
        source_weeks = row.get("mapped_year_weeks")
        if not isinstance(source_weeks, list) or not 1 <= len(source_weeks) <= 3:
            raise ValueError("Invalid ATP source week interval")
        run_positions: list[dict[str, int]] = []
        ordinals: list[int] = []
        for source_week in source_weeks:
            if not isinstance(source_week, dict):
                raise ValueError("Invalid ATP week record")
            y, w = source_week.get("calendar_year"), source_week.get("year_week")
            if type(y) is not int or type(w) is not int or not 1 <= w <= 52:
                raise ValueError(f"Invalid Earth ISO week for {identity}")
            position = calendar.calendar_to_season(y, w)
            if position is None:
                raise ValueError(f"ATP source week outside Run horizon: {identity} {y}/W{w}")
            ordinal = calendar.ordinal(position.season_index, position.season_week)
            if calendar.position_at_ordinal(ordinal) != position:
                raise ValueError("Run Calendar forward/reverse mapping disagrees")
            run_positions.append(asdict(position))
            ordinals.append(ordinal)
            by_run_ordinal.setdefault(ordinal, []).append(identity)
        if len(set(ordinals)) != len(ordinals):
            raise ValueError(f"Duplicate native week in ATP occurrence: {identity}")
        if ordinals != list(range(ordinals[0], ordinals[0] + len(ordinals))):
            raise ValueError(f"Noncontiguous native ATP weeks: {identity}")
        if run_positions[-1]["calendar_year"] != year:
            raise ValueError(f"ATP season closure in another calendar year: {identity}")
        preview.append({
            "source_identity": identity,
            "atp_season_year": year,
            "source_series_id": row["series_id"],
            "source_start_date": row["original_start_date"],
            "source_end_date": row["original_end_date"],
            "source_finish_iso_week": row["source_finish_iso_week"],
            "mapping_rule": row["mapping_rule"],
            "review_flags": list(row["review_flags"]),
            "run_weeks": run_positions,
            "run_ordinals": ordinals,
            "requires_sporting_round_and_slot_design": True,
            "source_status": row["source_year_status"],
        })
    preview.sort(key=lambda r: (r["atp_season_year"], r["source_identity"]))
    if len(preview) != sum(
        row.get("atp_season_year") in chosen for row in raw_events
    ):
        raise ValueError("ATP year-selection count mismatch")

    parallel = Counter(len(identities) for identities in by_run_ordinal.values())
    max_parallel = max(parallel, default=0)
    three_week = [row["source_identity"] for row in preview if len(row["run_weeks"]) == 3]
    compressed_finishes = [
        row["source_identity"] for row in preview
        if "single_week_majority_precedes_finish_week" in row["review_flags"]
    ]
    result = {
        "schema_version": ATP_EARTH_RUN_WEEK_PREVIEW_SCHEMA,
        "calendar": calendar.to_metadata(),
        "source_mapping_fingerprint": canonical_hash(dict(mapping)),
        "selected_atp_years": requested_years,
        "source_reference_only": True,
        "no_sporting_install": True,
        "no_simulation_slot_or_match_generation": True,
        "requires_explicit_confirmation_and_save_for_future_import": True,
        "summary": {
            "mapped_occurrences": len(preview),
            "distinct_run_weeks": len(by_run_ordinal),
            "max_parallel_source_tournaments_in_week": max_parallel,
            "concurrent_run_week_distribution": {
                str(n): parallel.get(n, 0) for n in range(1, max_parallel + 1)
            },
            "three_week_sporting_review_required": three_week,
            "short_majority_before_finish_review_required": compressed_finishes,
            "sporting_ready": False,
        },
        "events": preview,
    }
    result["preview_fingerprint"] = canonical_hash(result)
    return result
