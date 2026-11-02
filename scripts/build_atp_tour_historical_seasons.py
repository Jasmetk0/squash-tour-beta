"""Resolve ATP Tour-only historical Category/Series reference seasons, 1990–2026.

The current source registry is intentionally incomplete for some historical years:
an absent tournament means not verified, NEVER proof it did not exist.
No Calendar Editions, played results, Run mutation, ranking or squash logic.
Run: python scripts/build_atp_tour_historical_seasons.py --check | --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "reference_packages" / "atp_tour_1990_2026"
TARGET = SOURCE / "seasons_1990_2026.json"
FIRST, LAST = 1990, 2026

# Source-backed ATP singles main Tour tier rosters. These expected counts
# describe *played events* (never cancelled Series identities), and are
# intentionally NOT backfilled from any present-day calendar to older years.
# Official archive: https://www.atptour.com/en/scores/results-archive?year=YYYY
PLAYED_TIER_COUNTS: dict[int, dict[str, int]] = {
    2015: {"atp_masters_1000": 9, "atp_500": 13, "atp_250": 39},
    2016: {"atp_masters_1000": 9, "atp_500": 13, "atp_250": 39},
    2017: {"atp_masters_1000": 9, "atp_500": 13, "atp_250": 40},
    2018: {"atp_masters_1000": 9, "atp_500": 13, "atp_250": 40},
    2019: {"atp_masters_1000": 9, "atp_500": 13, "atp_250": 39},
    2020: {"atp_masters_1000": 3, "atp_500": 7, "atp_250": 18},
    2021: {"atp_masters_1000": 8, "atp_500": 9, "atp_250": 39},
    2022: {"atp_masters_1000": 8, "atp_500": 13, "atp_250": 42},
    2023: {"atp_masters_1000": 9, "atp_500": 13, "atp_250": 38},
    2024: {"atp_masters_1000": 9, "atp_500": 13, "atp_250": 38},
    2025: {"atp_masters_1000": 9, "atp_500": 16, "atp_250": 30},
}



def _active(periods: list[dict[str, Any]], year: int) -> list[dict[str, Any]]:
    return [p for p in periods if p["from"] <= year <= p["to"]]


def _era(year: int) -> str:
    if year < 2000:
        return "atp_tour_championship_and_world_series"
    if year < 2009:
        return "tennis_masters_and_international_series"
    return "atp_masters_1000_500_250"


def build(
    category_doc: dict[str, Any], series_doc: dict[str, Any]
) -> dict[str, Any]:
    if category_doc["package_type"] != "Category" or series_doc["package_type"] != "Series":
        raise ValueError("Expected one Category and one Series Package")
    if (category_doc["package_id"], series_doc["package_id"]) != (
        "atp_tour_1990_2026_category", "atp_tour_1990_2026_series"
    ):
        raise ValueError("Unexpected source Package identity")
    categories = {x["source_entity_id"]: x for x in category_doc["entities"]}
    series = {x["source_entity_id"]: x for x in series_doc["entities"]}
    if len(categories) != len(category_doc["entities"]) or len(series) != len(series_doc["entities"]):
        raise ValueError("Duplicate source entity identity")

    # Reference scope is *only* ATP Tour main circuit/ATP-operated Finals,
    # not external tennis events or separate Challenger/ITF competitions.
    forbidden = {"grand_slam", "davis_cup", "laver_cup", "united_cup"}
    if forbidden & categories.keys() or forbidden & series.keys():
        raise ValueError("Non-ATP Tour reference leaked into Package")

    for entity in category_doc["entities"]:
        intervals = entity["payload"].get("history_periods") or []
        if not intervals:
            raise ValueError("Category missing history: " + entity["source_entity_id"])
        for year in range(FIRST, LAST + 1):
            if len(_active(intervals, year)) > 1:
                raise ValueError("Overlapping Category intervals: " + entity["source_entity_id"])
        for p in intervals:
            if not p.get("source_url") or p["from"] > p["to"] or p["from"] < FIRST or p["to"] > LAST:
                raise ValueError("Invalid Category evidence interval")

    for entity in series_doc["entities"]:
        intervals = entity["payload"].get("history_periods") or []
        if not intervals:
            raise ValueError("Series missing history: " + entity["source_entity_id"])
        refs = {
            r["source_entity_id"]
            for r in entity["references"]
            if r["source_package_id"] == category_doc["package_id"]
            and r["expected_entity_kind"] == "tennis.category.reference.v1"
        }
        for p in intervals:
            cid = p["category_id"]
            if cid not in categories or cid not in refs or not p.get("source_url"):
                raise ValueError("Invalid Series Category reference / evidence")
            if p["from"] < FIRST or p["to"] > LAST or p["from"] > p["to"]:
                raise ValueError("Series out-of-range history")
            for year in range(p["from"], p["to"] + 1):
                if len(_active(categories[cid]["payload"]["history_periods"], year)) != 1:
                    raise ValueError("Series references category outside effective years")
        for year in range(FIRST, LAST + 1):
            applicable = _active(intervals, year)
            if len(applicable) > 1:
                raise ValueError("Conflicting category for Series in year " + str(year))
            if year in entity["payload"].get("not_held_years_known", []) and not applicable:
                raise ValueError("Cancellation without effective Series category in year " + str(year))

    rows = []
    for year in range(FIRST, LAST + 1):
        active_cats = sorted(
            x["source_entity_id"] for x in category_doc["entities"]
            if _active(x["payload"]["history_periods"], year)
        )
        active_series = {
            x["source_entity_id"]: _active(x["payload"]["history_periods"], year)[0]["category_id"]
            for x in series_doc["entities"]
            if _active(x["payload"]["history_periods"], year)
        }
        active_series = dict(sorted(active_series.items()))
        nonheld = sorted(
            x["source_entity_id"] for x in series_doc["entities"]
            if year in x["payload"].get("not_held_years_known", [])
        )
        if year in PLAYED_TIER_COUNTS:
            expected = PLAYED_TIER_COUNTS[year]
            actual = {
                category: sum(
                    tier == category and series_id not in nonheld
                    for series_id, tier in active_series.items()
                )
                for category in expected
            }
            if actual != expected:
                raise ValueError(
                    f"ATP played-tier roster mismatch in {year}: "
                    f"expected {expected}, observed {actual}"
                )
            played_roster = {
                "status": "played_tour_tiers_reconciled_to_atp_results_archive",
                "source_url": f"https://www.atptour.com/en/scores/results-archive?year={year}",
                "played_counts": expected,
                "scope": "ATP Masters 1000, ATP 500, ATP 250; excludes Finals and team events",
                "not_an_edition_calendar": True,
            }
        else:
            played_roster = {
                "status": (
                    "provisional_calendar_not_final_results"
                    if year == 2026 else "unverified_incomplete"
                ),
                "played_counts": None,
                "scope": "No complete played ATP 1000/500/250 event census established",
                "not_an_edition_calendar": True,
            }
        rows.append({
            "year": year,
            "era": _era(year),
            "category_ids": active_cats,
            "series_category_ids": active_series,
            "known_not_held_series_ids": nonheld,
            "played_tier_roster_validation": played_roster,
            "source_coverage": "partial_historical_reference_not_complete_atp_tour_census",
            "edition_assertion": "none; reference membership does not prove played annual edition",
        })

    return {
        "schema_version": "tennis.atp_tour_reference_seasons.v1",
        "from_year": FIRST,
        "to_year": LAST,
        "seasons_count": len(rows),
        "category_source_package_id": category_doc["package_id"],
        "series_source_package_id": series_doc["package_id"],
        "coverage": "PARTIAL: 1990–2026 ATP-only Category labels, selected historic Tour Series, and 2026 main Tour roster",
        "historical_absence_semantics": "Missing means unverified, NOT nonexistent or cancelled",
        "seasons": rows,
    }


def canonical_output(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--check", action="store_true")
    choice.add_argument("--write", action="store_true")
    args = parser.parse_args()
    c = json.loads((SOURCE / "category.json").read_text(encoding="utf-8"))
    s = json.loads((SOURCE / "series.json").read_text(encoding="utf-8"))
    payload = canonical_output(build(c, s))
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != payload:
            print("Historical seasons stale; run --write")
            return 1
        print("ATP Tour reference 1990–2026: 37 seasons verified (partial historical Series coverage)")
        return 0
    TARGET.write_text(payload, encoding="utf-8")
    print("Created", TARGET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
