"""Build a non-playable ATP Calendar reference Package from dated official evidence.

Usage:
  python -m scripts.build_atp_historical_calendar --check
  python -m scripts.build_atp_historical_calendar --write

For every year 1990–2026, publish explicit DATE COVERAGE (including missing
dates); do not infer dates from the Category/Series roster, a neighbouring
season, or a cancelled Series. The Calendar is NOT a runnable SeasonCalendar,
nor an ATP match/results archive. ISO week labels are not interchangeable with
the RunCalendar equal-length week clock.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from scripts.atp_finals_date_window_evidence import (
    VERIFIED_SOURCE_WINDOW_STATE, CALENDAR_DATE_CONCEPT,
    REVIEWED_DATE_WINDOW_YEARS, validate_official_finals_window_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config/reference_packages/atp_tour_1990_2026"
DATES = SOURCE / "calendar_dates_v1.json"
TARGET = SOURCE / "calendar.json"
FIRST, LAST = 1990, 2026
CALENDAR_ID = "atp_tour_1990_2026_calendar"
CALENDAR_SCOPE = "tennis.atp_tour.calendar.reference.1990_2026"
SERIES_ID = "atp_tour_1990_2026_series"
CATEGORY_ID = "atp_tour_1990_2026_category"
ALLOWED_STATUSES = {
    "verified_results_archive", "provisional_published_schedule",
    VERIFIED_SOURCE_WINDOW_STATE,
}


def parse_exact_date(raw: Any, *, identity: str) -> date:
    if not isinstance(raw, str):
        raise ValueError("Missing exact ISO date: " + identity)
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Invalid exact ISO date: " + identity) from exc
    if parsed.isoformat() != raw:
        raise ValueError("Noncanonical exact ISO date: " + identity)
    return parsed


def official_url(raw: Any, *, identity: str) -> str:
    if not isinstance(raw, str) or not raw.startswith("https://"):
        raise ValueError("Missing secure ATP source: " + identity)
    parsed = urlsplit(raw)
    if parsed.username or parsed.password or parsed.port is not None:
        raise ValueError("Invalid ATP source authority: " + identity)
    if (parsed.hostname or "").lower().removeprefix("www.") not in {
        "atptour.com", "nextgenatpfinals.com",
    }:
        raise ValueError("Non-official ATP source: " + identity)
    return raw


def ensure_archive_year_matches(url: str, *, year: int) -> None:
    """Fail closed if a year-scoped official results archive cites another season.

    Tournament-specific ATP pages may have unrelated query parameters and are
    deliberately not interpreted as annual archive citations.
    """
    parsed = urlsplit(url)
    if parsed.path.rstrip("/").lower() != "/en/scores/results-archive":
        return
    values = parse_qs(parsed.query, keep_blank_values=True)
    if values.get("year") != [str(year)]:
        raise ValueError(
            f"ATP results archive year must match season {year}: {url}"
        )


def iso_weeks_touched(start: date, end: date) -> list[dict[str, int]]:
    """The entire inclusive tournament, including both ISO years at rollover."""
    if end < start or (end - start).days > 35:
        raise ValueError("Invalid tournament date interval")
    monday = start - timedelta(days=start.weekday())
    result = []
    while monday <= end:
        y, w, _ = monday.isocalendar()
        result.append({"iso_year": y, "iso_week": w})
        monday += timedelta(days=7)
    return result


def project_iso_week_to_run_w52(
    value: date, *, run_calendar: Any
) -> dict[str, int | str]:
    """Opt-in *week-label* projection, never a conversion of physical dates.

    Only W52 is supported. ISO week 53 cannot be represented without losing
    information. Callers must not silently map it to W52/W1 or to W61/W80.
    A RunCalendar's equal-length year is not a Gregorian year: the returned
    position deliberately carries a warning and is unsuitable as an automatic
    sporting Schedule/Edition mutation.
    """
    if run_calendar.weeks_per_year != 52:
        raise ValueError("ISO-labelled calendar projection requires W52 clock")
    iso_year, iso_week, _ = value.isocalendar()
    if iso_week == 53:
        raise ValueError("ISO week 53 requires explicit alternate clock policy")
    position = run_calendar.calendar_to_season(iso_year, iso_week)
    if position is None:
        raise ValueError("Date ISO label is outside the requested Run horizon")
    return {
        "season_index": position.season_index,
        "season_week": position.season_week,
        "calendar_year": position.calendar_year,
        "year_week": position.year_week,
        "mapping_policy": "iso_week_label_to_W52_not_date_authority.v1",
    }


def build(
    categories: dict[str, Any],
    series: dict[str, Any],
    seasons: dict[str, Any],
    dated: dict[str, Any],
) -> dict[str, Any]:
    if (
        categories.get("package_id") != CATEGORY_ID
        or series.get("package_id") != SERIES_ID
        or seasons.get("category_source_package_id") != CATEGORY_ID
        or seasons.get("series_source_package_id") != SERIES_ID
        or dated.get("schema_version") != "tennis.atp_tour_calendar_dates.v1"
        or dated.get("reference_span") != {"from": FIRST, "to": LAST}
    ):
        raise ValueError("Mismatched immutable ATP source identities")
    cat_ids = {e["source_entity_id"] for e in categories["entities"]}
    ser = {e["source_entity_id"]: e for e in series["entities"]}
    if len(cat_ids) != 11 or len(ser) != 164:
        raise ValueError("ATP parent package identities or count changed")
    season_rows = {row["year"]: row for row in seasons["seasons"]}
    if set(season_rows) != set(range(FIRST, LAST + 1)):
        raise ValueError("Historical season coverage must span 1990–2026")
    source_years = dated.get("year_sources")
    if not isinstance(source_years, dict) or any(
        str(y) not in {str(v) for v in range(FIRST, LAST + 1)}
        for y in source_years
    ):
        raise ValueError("Invalid dated-year inventory")

    events: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for year in range(FIRST, LAST + 1):
        base_row = season_rows[year]
        active = base_row["series_category_ids"]
        if any(x not in ser or cat not in cat_ids for x, cat in active.items()):
            raise ValueError("Calendar source has unknown Series or Category")
        dated_year = source_years.get(str(year))
        known_cancelled = set(base_row["known_not_held_series_ids"])
        found: set[str] = set()
        valid_events = []
        state = "not_dated_no_fabricated_dates"
        finals_evidence = None
        if dated_year is not None:
            if not isinstance(dated_year, dict):
                raise ValueError("Invalid dated-year source shape: " + str(year))
            state = dated_year.get("status")
            if state not in ALLOWED_STATUSES:
                raise ValueError("Unsupported dated-year status: " + str(year))
            expected_keys = {"status", "source_url", "events", "as_of"}
            if state == VERIFIED_SOURCE_WINDOW_STATE:
                expected_keys.add("finals_date_window_evidence")
                finals_evidence = validate_official_finals_window_evidence(
                    year, dated_year.get("finals_date_window_evidence")
                )
            elif year in REVIEWED_DATE_WINDOW_YEARS:
                raise ValueError(
                    "Reviewed Finals-year source must preserve independent date "
                    "concepts: " + str(year)
                )
            if set(dated_year) != expected_keys:
                raise ValueError("Invalid dated-year source shape: " + str(year))
            official_url(dated_year["source_url"], identity=str(year))
            ensure_archive_year_matches(dated_year["source_url"], year=year)
            parse_exact_date(dated_year["as_of"], identity="source as_of")
            if not isinstance(dated_year["events"], list):
                raise ValueError("Missing dated events list: " + str(year))
            for entry in dated_year["events"]:
                if not isinstance(entry, dict) or set(entry) != {
                    "series_id", "start_date", "end_date",
                    "source_url", "source_basis",
                }:
                    raise ValueError("Invalid dated event shape: " + str(year))
                sid = entry["series_id"]
                if not isinstance(sid, str) or sid not in active or sid in found:
                    raise ValueError("Unknown or duplicate dated Series: " + str(sid))
                if sid in known_cancelled:
                    raise ValueError("Known not-held Series must not have an event date: " + sid)
                if entry["source_basis"] != "official_published_event_dates":
                    raise ValueError("Date origin was not independently designated official")
                url = official_url(entry["source_url"], identity=sid)
                ensure_archive_year_matches(url, year=year)
                start = parse_exact_date(entry["start_date"], identity=sid)
                end = parse_exact_date(entry["end_date"], identity=sid)
                if start.year not in (year, year - 1) or end.year != year:
                    raise ValueError("Impossible ATP season-year event interval: " + sid)
                if start.year == year - 1 and start.month != 12:
                    raise ValueError("ATP prior-year events may begin only in December")
                iso = iso_weeks_touched(start, end)
                if active[sid] not in {
                    p["category_id"] for p in ser[sid]["payload"]["history_periods"]
                    if p["from"] <= year <= p["to"]
                }:
                    raise ValueError("Mismatched source Category in edition " + sid)
                if finals_evidence is not None and sid == "atp_finals":
                    if (start.isoformat(), end.isoformat()) != (
                        finals_evidence["archive_start_date"],
                        finals_evidence["archive_end_date"],
                    ):
                        raise ValueError("Finals archive dates differ from reviewed evidence")
                payload = {
                    "atp_season_year": year,
                    "series_id": sid,
                    "category_id": active[sid],
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "start_calendar_year": start.year,
                    "start_year_week": iso[0],
                    "end_year_week": iso[-1],
                    "iso_weeks_occupied": iso,
                    "duration_days_inclusive": (end - start).days + 1,
                    "source_url": url,
                    "source_basis": entry["source_basis"],
                    "year_source_state": state,
                    "source_as_of": dated_year["as_of"],
                    "not_squash_rules": True,
                    "no_match_or_result_claim": True,
                    "run_week_projection": "not_applied_source_only",
                }
                if finals_evidence is not None and sid == "atp_finals":
                    payload["calendar_date_concept"] = CALENDAR_DATE_CONCEPT
                    payload["alternate_official_finals_window"] = finals_evidence
                valid_events.append({
                    "source_entity_id": f"atp_{year}_{sid}",
                    "entity_kind": "tennis.calendar.occurrence.reference.v1",
                    "entity_schema_version": 1,
                    "scope": CALENDAR_SCOPE,
                    "payload": payload,
                    "references": [
                        {
                            "source_package_id": CATEGORY_ID,
                            "source_entity_id": active[sid],
                            "expected_entity_kind": "tennis.category.reference.v1",
                            "minimum_schema_version": 1,
                        },
                        {
                            "source_package_id": SERIES_ID,
                            "source_entity_id": sid,
                            "expected_entity_kind": "tennis.series.reference.v1",
                            "minimum_schema_version": 1,
                        },
                    ],
                    "valid": True,
                })
                found.add(sid)
        coverage_state = (
            "undated" if dated_year is None
            else "provisional_complete_named_schedule"
            if state == "provisional_published_schedule" and len(found) == len(active)
            else "verified_complete_archive_dates_with_alternate_finals_window"
            if state == VERIFIED_SOURCE_WINDOW_STATE
            and len(found) == len(active) - len(known_cancelled)
            else "verified_complete_known_series_dates"
            if len(found) == len(active) - len(known_cancelled)
            else "partial_verified_dates"
        )
        if finals_evidence is not None and "atp_finals" not in found:
            raise ValueError("Expected reviewed ATP Finals source occurrence absent")
        coverage.append({
            "source_entity_id": f"season_{year}_date_coverage",
            "entity_kind": "tennis.calendar.coverage.reference.v1",
            "entity_schema_version": 1,
            "scope": CALENDAR_SCOPE,
            "payload": {
                "atp_season_year": year,
                "roster_series_count": len(active),
                "dated_series_count": len(found),
                "undated_series_ids": sorted(set(active) - found - known_cancelled),
                "known_not_held_series_ids": sorted(known_cancelled),
                "date_coverage_state": coverage_state,
                "year_source_status": state,
                "year_source_url": dated_year["source_url"] if dated_year else None,
                "no_fabricated_dates": True,
                "not_squash_rules": True,
            },
            "references": [],
            "valid": True,
        })
        events.extend(valid_events)
    if len(coverage) != 37:
        raise ValueError("Incomplete year-level date coverage audit")
    return {
        "schema_version": 1,
        "package_type": "Calendar",
        "package_id": CALENDAR_ID,
        "source_version": 1,
        "provenance": {
            "created_for": "Squash Engine independent ATP historical reference",
            "reference_span": {"from": FIRST, "to": LAST},
            "run_consumption": "opaque_reference_only_no_sporting_calendar",
            "coverage_model": "explicit_yearly_undated_series_ids",
            "source": "calendar_dates_v1.json",
            "actual_dates_not_inferred_from_category_series": True,
            "iso_week_not_run_week": True,
            "date_coverage_years": sorted(int(k) for k in source_years),
            "calendar_date_concept": CALENDAR_DATE_CONCEPT,
            "finals_alternate_official_window_years": sorted(
                int(y) for y, value in source_years.items()
                if value["status"] == VERIFIED_SOURCE_WINDOW_STATE
            ),
            "dated_occurrences": len(events),
            "season_coverage_entries": len(coverage),
        },
        "explicit_scope": [CALENDAR_SCOPE],
        "entities": coverage + sorted(events, key=lambda e: e["source_entity_id"]),
        "children": [],
        "parent_source_fingerprint": None,
    }


def canonical(data: dict[str, Any]) -> str:
    # Large immutable Calendar snapshots: deterministic compact JSON avoids
    # transport-size failures without dropping or transforming source evidence.
    return json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ) + "\n"


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    mode = args.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    options = args.parse_args()
    categories = json.loads((SOURCE / "category.json").read_text(encoding="utf-8"))
    series = json.loads((SOURCE / "series.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads(DATES.read_text(encoding="utf-8"))
    document = canonical(build(categories, series, seasons, dated))
    if options.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != document:
            print("ATP Calendar snapshot stale; execute --write")
            return 1
        print("ATP Calendar reference snapshot verified, no invented dates")
        return 0
    TARGET.write_text(document, encoding="utf-8")
    print("Wrote", TARGET, "source-only ATP calendar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
