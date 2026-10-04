"""Build annual FIFA tradition-age evidence from canonical structural observations.

This signal measures one narrow part of tradition: documented historical depth since
the earliest canonical tradition-relevant structural anchor available by each engine
year. It is not a tradition rating and does not assume that older always means better.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_fifa_structural_dimension_evidence import build_summary
from scripts.reconcile_fifa_big_count_identities import DEFAULT_EARTH_ROOT

FIRST_YEAR = 1955
LAST_YEAR = 2026


def _role(events: list[dict[str, Any]]) -> str:
    if not events:
        return "none"
    held_out = [
        event
        for event in events
        if "held_out_validation_country" in event["quality_flags"]
    ]
    if len(held_out) == len(events):
        return "held_out_validation"
    if held_out:
        return "mixed"
    return "review"


def build_tradition_age_signal(
    *,
    earth_root: Path = DEFAULT_EARTH_ROOT,
) -> dict[str, Any]:
    structural = build_summary(earth_root=earth_root)
    earth_index = json.loads((earth_root / "index.json").read_text(encoding="utf-8"))
    codes = sorted(earth_index["country_codes"])

    countries: dict[str, Any] = {}
    observed_country_count = 0

    for code in codes:
        tradition = structural["countries"][code]["dimensions"]["squash_tradition"]
        events = list(tradition["events"])
        events.sort(
            key=lambda item: (
                item["observation_year"]
                if item["observation_year"] is not None
                else 9999,
                item["observation_id"],
            )
        )
        role = _role(events)

        annual: dict[str, Any] = {}
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            available = [
                event
                for event in events
                if event["observation_year"] is not None
                and int(event["observation_year"]) <= year
            ]
            if not available:
                annual[str(year)] = {
                    "years_since_first_tradition_anchor": None,
                    "first_tradition_anchor_year": None,
                    "available_anchor_count": 0,
                    "observation_ids": [],
                    "evidence_role": role,
                    "rating_ready": False,
                }
                continue

            first_year = min(int(event["observation_year"]) for event in available)
            annual[str(year)] = {
                "years_since_first_tradition_anchor": year - first_year,
                "first_tradition_anchor_year": first_year,
                "available_anchor_count": len(available),
                "observation_ids": [
                    event["observation_id"] for event in available
                ],
                "evidence_role": role,
                "rating_ready": False,
            }

        if any(
            row["years_since_first_tradition_anchor"] is not None
            for row in annual.values()
        ):
            observed_country_count += 1

        countries[code] = {
            "evidence_role": role,
            "tradition_event_count": len(events),
            "earliest_documented_tradition_year": (
                min(
                    int(event["observation_year"])
                    for event in events
                    if event["observation_year"] is not None
                )
                if events
                else None
            ),
            "annual": annual,
            "rating_ready": False,
        }

    return {
        "schema_version": "fifa_tradition_age_signal.v1",
        "world_id": "fifa_earth",
        "years": {"from": FIRST_YEAR, "to": LAST_YEAR},
        "country_count": len(countries),
        "country_count_with_tradition_age_evidence": observed_country_count,
        "rating_ready": False,
        "countries": countries,
        "limitations": [
            "Years since first documented tradition anchor measure historical depth only, not tradition quality.",
            "A missing value means no canonical tradition anchor is available by that year; it is not zero tradition.",
            "Anchor count is provenance coverage and must not be used as a quality score.",
            "Held-out validation countries are labelled and must not be used to fit any future transfer function.",
            "This signal does not encode continuity, cultural reach, fan intensity, historical success or institutional resilience.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--earth-root", type=Path, default=DEFAULT_EARTH_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_tradition_age_signal(earth_root=args.earth_root)
    print(
        json.dumps(
            {
                "country_count": result["country_count"],
                "country_count_with_tradition_age_evidence": result[
                    "country_count_with_tradition_age_evidence"
                ],
                "years": result["years"],
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
