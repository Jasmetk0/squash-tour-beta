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
    report_outside_horizon: bool = False,
    occurrence_id: str | None = None,
) -> dict[str, Any]:
    """Project dated source occurrences to real RunCalendarPosition values.

    The caller supplies the Run calendar, including W, offset and horizon.
    A horizon conflict either rejects the request or appears in a separate
    report. This preview leaves Run state untouched.
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
    outside_horizon: list[dict[str, Any]] = []
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
        if occurrence_id is not None and identity != occurrence_id:
            continue
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
        source_ordinals: list[int] = []
        outside_weeks: list[dict[str, int]] = []
        for source_week in source_weeks:
            if not isinstance(source_week, dict):
                raise ValueError("Invalid ATP week record")
            y, w = source_week.get("calendar_year"), source_week.get("year_week")
            if type(y) is not int or type(w) is not int or not 1 <= w <= 52:
                raise ValueError(f"Invalid Earth ISO week for {identity}")
            source_ordinals.append(y * 52 + w)
            position = calendar.calendar_to_season(y, w)
            if position is None:
                if not report_outside_horizon:
                    raise ValueError(f"ATP source week outside Run horizon: {identity} {y}/W{w}")
                outside_weeks.append(source_week)
                continue
            ordinal = calendar.ordinal(position.season_index, position.season_week)
            if calendar.position_at_ordinal(ordinal) != position:
                raise ValueError("Run Calendar forward/reverse mapping disagrees")
            run_positions.append(asdict(position))
            ordinals.append(ordinal)
        if len(set(source_ordinals)) != len(source_ordinals):
            raise ValueError(f"Duplicate native week in ATP occurrence: {identity}")
        if source_ordinals != list(range(source_ordinals[0], source_ordinals[0] + len(source_ordinals))):
            raise ValueError(f"Noncontiguous native ATP weeks: {identity}")
        if source_weeks[-1]["calendar_year"] != year:
            raise ValueError(f"ATP season closure in another calendar year: {identity}")

        # A compressed one-week tournament may finish in the *following*
        # source ISO week. Preserve that finish label on the same native Run
        # clock; it is NOT permission to close matches, rankings or results.
        source_finish = row.get("source_finish_iso_week")
        review_flags = row.get("review_flags")
        if not isinstance(source_finish, dict) or not isinstance(review_flags, list):
            raise ValueError(f"Missing source finish/flags for {identity}")
        if any(not isinstance(flag, str) for flag in review_flags):
            raise ValueError(f"Invalid source review flag for {identity}")
        finish_year, finish_week = (
            source_finish.get("calendar_year"), source_finish.get("year_week")
        )
        if (type(finish_year) is not int or type(finish_week) is not int
                or finish_year != year or not 1 <= finish_week <= 52):
            raise ValueError(f"Invalid source finish week for {identity}")
        finish_offset = finish_year * 52 + finish_week - source_ordinals[-1]
        finish_after_occupancy = finish_offset == 1
        flagged_late_finish = "single_week_majority_precedes_finish_week" in review_flags
        if finish_offset not in (0, 1) or finish_after_occupancy != flagged_late_finish:
            raise ValueError(f"ATP source finish/occupancy mismatch: {identity}")
        event_source = {
            "source_identity": identity,
            "atp_season_year": year,
            "source_series_id": row["series_id"],
            "source_start_date": row["original_start_date"],
            "source_end_date": row["original_end_date"],
            "source_finish_iso_week": source_finish,
            "mapping_rule": row["mapping_rule"],
            "review_flags": list(review_flags),
            "source_status": row["source_year_status"],
        }
        finish_position = calendar.calendar_to_season(finish_year, finish_week)
        if finish_position is None:
            if not report_outside_horizon:
                raise ValueError(f"ATP source finish outside Run horizon: {identity}")
            if source_finish not in outside_weeks:
                outside_weeks.append(source_finish)
        if outside_weeks or finish_position is None:
            outside_horizon.append({
                **event_source,
                "mapped_year_weeks": source_weeks,
                "outside_year_weeks": outside_weeks,
            })
            continue

        finish_ordinal = calendar.ordinal(
            finish_position.season_index, finish_position.season_week
        )
        if calendar.position_at_ordinal(finish_ordinal) != finish_position:
            raise ValueError("Run Calendar source-finish round trip disagrees")
        for ordinal in ordinals:
            by_run_ordinal.setdefault(ordinal, []).append(identity)
        preview.append({
            **event_source,
            "source_finish_run_week": asdict(finish_position),
            "source_finish_run_ordinal": finish_ordinal,
            "source_finish_after_mapped_occupancy": finish_after_occupancy,
            "source_finish_is_not_sporting_result_closure": True,
            "run_weeks": run_positions,
            "run_ordinals": ordinals,
            "requires_sporting_round_and_slot_design": True,
        })
    preview.sort(key=lambda r: (r["atp_season_year"], r["source_identity"]))
    result_count = len(preview) + len(outside_horizon)
    if occurrence_id is not None and result_count == 0:
        raise ValueError(f"ATP source occurrence was not found in selected years: {occurrence_id}")
    if result_count != sum(
        row.get("atp_season_year") in chosen
        and (occurrence_id is None or row.get("source_identity") == occurrence_id)
        for row in raw_events
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
            "native_finish_week_is_reference_only": True,
            "sporting_ready": False,
        },
        "events": preview,
    }
    if report_outside_horizon:
        result["outside_horizon"] = sorted(
            outside_horizon, key=lambda row: (row["atp_season_year"], row["source_identity"])
        )
    result["preview_fingerprint"] = canonical_hash(result)
    return result
