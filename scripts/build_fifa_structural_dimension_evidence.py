"""Summarise canonical FIFA structural evidence for development and tradition.

This is a read-only evidence view. It does not assign effect sizes, scores or
country ratings. Event counts describe documentation coverage, not football quality.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_fifa_country_evidence_index import build_index
from scripts.reconcile_fifa_big_count_identities import DEFAULT_EARTH_ROOT

TARGET_DIMENSIONS = ("development_quality", "squash_tradition")


def _conflict_groups(flags: list[str]) -> list[str]:
    prefix = "conflict_group:"
    return sorted(
        flag[len(prefix) :]
        for flag in flags
        if flag.startswith(prefix)
    )


def _dimension_summary(events: list[dict[str, Any]], dimension: str) -> dict[str, Any]:
    supporting = [
        event
        for event in events
        if f"supports_{dimension}" in event["quality_flags"]
    ]
    supporting.sort(
        key=lambda item: (
            item["observation_year"] if item["observation_year"] is not None else 9999,
            item["observation_id"],
        )
    )

    years = [
        int(event["observation_year"])
        for event in supporting
        if event["observation_year"] is not None
    ]
    conflicts = sorted(
        {
            group
            for event in supporting
            for group in _conflict_groups(event["quality_flags"])
        }
    )
    pre_game = [
        event
        for event in supporting
        if "pre_game_start_history" in event["quality_flags"]
    ]

    return {
        "evidence_present": bool(supporting),
        "event_count": len(supporting),
        "first_event_year": min(years) if years else None,
        "last_event_year": max(years) if years else None,
        "pre_1955_event_count": len(pre_game),
        "event_types": sorted(
            {
                event["identity_reason"] if False else event.get("event_type", "")
                for event in []
            }
        ),
        "conflict_groups": conflicts,
        "observation_ids": [event["observation_id"] for event in supporting],
        "events": supporting,
        "rating_ready": False,
    }


def build_summary(*, earth_root: Path = DEFAULT_EARTH_ROOT) -> dict[str, Any]:
    evidence = build_index()
    earth_index = json.loads((earth_root / "index.json").read_text(encoding="utf-8"))
    earth_codes = sorted(earth_index["country_codes"])

    countries: dict[str, Any] = {}
    total_structural_events = 0
    dimension_totals = {dimension: 0 for dimension in TARGET_DIMENSIONS}

    for code in earth_codes:
        facts = evidence["countries"].get(code, [])
        structural = [
            fact
            for fact in facts
            if fact["measurement_type"] == "football_structural_event"
        ]
        structural.sort(
            key=lambda item: (
                item["observation_year"] if item["observation_year"] is not None else 9999,
                item["observation_id"],
            )
        )
        total_structural_events += len(structural)

        dimensions = {}
        for dimension in TARGET_DIMENSIONS:
            summary = _dimension_summary(structural, dimension)
            dimension_totals[dimension] += summary["event_count"]
            dimensions[dimension] = summary

        countries[code] = {
            "structural_event_count": len(structural),
            "structural_observation_ids": [
                event["observation_id"] for event in structural
            ],
            "dimensions": dimensions,
            "rating_ready": False,
        }

    conflict_groups = sorted(
        {
            group
            for country in countries.values()
            for dimension in country["dimensions"].values()
            for group in dimension["conflict_groups"]
        }
    )

    return {
        "schema_version": "fifa_structural_dimension_evidence.v1",
        "world_id": "fifa_earth",
        "rating_ready": False,
        "country_count": len(countries),
        "structural_event_count": total_structural_events,
        "target_dimensions": list(TARGET_DIMENSIONS),
        "dimension_event_counts": dimension_totals,
        "conflict_groups": conflict_groups,
        "countries": countries,
        "limitations": [
            "Event count is documentation coverage, not a proxy for country quality.",
            "Structural events indicate dated changes in institutions/pathways but carry no numeric effect size.",
            "Absence of an event means this seed has no canonical event for that country/dimension, not that football structure was absent.",
            "Pre-1955 facts may inform later tradition review but retain their real historical year.",
            "Source conflicts remain explicit and prevent automatic timing assumptions.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--earth-root", type=Path, default=DEFAULT_EARTH_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_summary(earth_root=args.earth_root)
    print(
        json.dumps(
            {
                "country_count": result["country_count"],
                "structural_event_count": result["structural_event_count"],
                "dimension_event_counts": result["dimension_event_counts"],
                "conflict_groups": result["conflict_groups"],
                "rating_ready": result["rating_ready"],
            },
            indent=2,
        )
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
