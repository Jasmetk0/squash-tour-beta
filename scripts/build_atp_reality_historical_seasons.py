"""Build / verify deterministic historical ATP Reality *reference* seasons.

This script reads only the two canonical source Package JSON files in
config/reference_packages/atp_reality_2026. It does NOT create Calendar
Editions, score matches, schedule events, or mutate Runs.

Usage:
    python scripts/build_atp_reality_historical_seasons.py --check
    python scripts/build_atp_reality_historical_seasons.py --write

Partial historical coverage is explicit: a missing Series means "not yet
documented in this dataset", NOT "did not exist".
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "config" / "reference_packages" / "atp_reality_2026"
OUT = PACKAGE_DIR / "seasons_1955_2026.json"
START_YEAR = 1955
END_YEAR = 2026


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _active_periods(periods: list[dict[str, Any]], year: int) -> list[dict[str, Any]]:
    return [p for p in periods if p["from"] <= year <= p["to"]]


def _era(year: int) -> str:
    if year < 1968:
        return "pre_open"
    if year < 1970:
        return "early_open"
    if year < 1990:
        return "grand_prix_wct"
    if year < 2000:
        return "initial_atp_tour"
    if year < 2009:
        return "masters_and_international_series"
    return "modern_atp"


def _ranking_regime(year: int) -> str:
    if year < 1973:
        return "before_atp_computer_rankings"
    if year == 1973:
        return "atp_computer_rankings_launched_august_1973"
    return "atp_rankings_exist_methods_historically_variable"


def build_seasons(
    categories: dict[str, Any], series: dict[str, Any]
) -> dict[str, Any]:
    assert categories["package_type"] == "Category"
    assert series["package_type"] == "Series"
    assert categories["package_id"] != series["package_id"]
    category_entities = {e["source_entity_id"]: e for e in categories["entities"]}
    series_entities = {e["source_entity_id"]: e for e in series["entities"]}
    if len(category_entities) != len(categories["entities"]):
        raise ValueError("duplicate Category ID")
    if len(series_entities) != len(series["entities"]):
        raise ValueError("duplicate Series ID")
    if len(category_entities) < 20 or len(series_entities) < 60:
        raise ValueError("unexpectedly small history source inventory")

    for entity in categories["entities"]:
        if not entity["payload"].get("history_periods"):
            raise ValueError("Category has no history periods: " + entity["source_entity_id"])
    for entity in series["entities"]:
        periods = entity["payload"].get("history_periods")
        if not periods:
            raise ValueError("Series has no history periods: " + entity["source_entity_id"])
        referenced = {r["source_entity_id"] for r in entity["references"]}
        period_categories = {p["category_id"] for p in periods}
        if not period_categories.issubset(referenced):
            raise ValueError("Series missing source Category reference: " + entity["source_entity_id"])
        if any(r["source_package_id"] != categories["package_id"] for r in entity["references"]):
            raise ValueError("Series references wrong source Package")
        if any(p["category_id"] not in category_entities for p in periods):
            raise ValueError("Series references unknown category")
        for p in periods:
            if not p.get("source_url") or p["from"] > p["to"] or p["from"] < START_YEAR or p["to"] > END_YEAR:
                raise ValueError("invalid source-backed Series interval")
            cat_periods = category_entities[p["category_id"]]["payload"]["history_periods"]
            for year in range(p["from"], p["to"] + 1):
                if len(_active_periods(cat_periods, year)) != 1:
                    raise ValueError("Series category not effective in " + str(year))

    seasons: list[dict[str, Any]] = []
    for year in range(START_YEAR, END_YEAR + 1):
        active_categories: list[str] = []
        for entity_id, entity in category_entities.items():
            intervals = _active_periods(entity["payload"]["history_periods"], year)
            if len(intervals) > 1:
                raise ValueError("overlapping Category intervals: " + entity_id)
            if intervals:
                active_categories.append(entity_id)
        active_series: dict[str, str] = {}
        known_not_held: list[str] = []
        for entity_id, entity in series_entities.items():
            intervals = _active_periods(entity["payload"]["history_periods"], year)
            if len(intervals) > 1:
                raise ValueError("overlapping Series intervals: " + entity_id)
            if intervals:
                category_id = intervals[0]["category_id"]
                if category_id not in active_categories:
                    raise ValueError("Series effective without Category: " + entity_id)
                active_series[entity_id] = category_id
                if year in entity["payload"].get("not_held_years_known", []):
                    known_not_held.append(entity_id)
        season = {
            "year": year,
            "era": _era(year),
            "ranking_regime": _ranking_regime(year),
            "category_ids": sorted(active_categories),
            "series_category_ids": {k: active_series[k] for k in sorted(active_series)},
            "known_not_held_series_ids": sorted(known_not_held),
            "source_coverage": "reference_only_not_complete_event_census",
            "edition_assertion": "none; listed Series identity does not imply annual tournament played",
        }
        seasons.append(season)

    return {
        "schema_version": "tennis.historical_reference_seasons.v1",
        "from_year": START_YEAR,
        "to_year": END_YEAR,
        "seasons_count": len(seasons),
        "category_source_package_id": categories["package_id"],
        "series_source_package_id": series["package_id"],
        "coverage": "PARTIAL: verified competition eras, 1990+ top-nine Masters identities, and 2026 reference roster; not all 1955–2026 events or editions",
        "historical_absence_semantics": "Unlisted = unverified in dataset, not proof of nonexistence; listed = source-backed Series identity/category, not proof an Edition was played",
        "seasons": seasons,
    }


def _bytes(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    built = build_seasons(_read(PACKAGE_DIR / "category.json"), _read(PACKAGE_DIR / "series.json"))
    serialized = _bytes(built)
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != serialized:
            print("Historical ATP seasons are stale; run --write.")
            return 1
        print("Historical ATP reference seasons verified: 72 years, no unsupported annual Edition claims.")
        return 0
    OUT.write_text(serialized, encoding="utf-8")
    print("Wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
