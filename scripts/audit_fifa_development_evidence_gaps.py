"""Audit FIFA development/tradition evidence coverage against a source-backed framework.

This is a research-gap tool only. It reports whether the current canonical structural
corpus contains evidence relevant to each facet. It never assigns effect sizes,
quality scores or country ratings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_fifa_country_evidence_index import build_index
from scripts.build_fifa_structural_features import build_features
from scripts.reconcile_fifa_big_count_identities import DEFAULT_EARTH_ROOT

DEFAULT_FRAMEWORK = Path(
    "config/earth_research/calibration/fifa_development_evidence_framework_v1.json"
)


def _load_framework(path: Path = DEFAULT_FRAMEWORK) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "fifa_development_evidence_framework.v1":
        raise ValueError("unsupported FIFA development evidence framework schema")
    if payload.get("rating_ready") is not False:
        raise ValueError("development evidence framework must not be rating-ready")
    return payload


def _structural_events(index: dict[str, Any], code: str) -> list[dict[str, Any]]:
    return [
        fact
        for fact in index["countries"].get(code, [])
        if fact["measurement_type"] == "football_structural_event"
    ]


def _facet_evidence(
    events: list[dict[str, Any]],
    *,
    event_types: set[str],
    dimension: str,
) -> dict[str, Any]:
    supporting = [
        event
        for event in events
        if event.get("comparability_group") in event_types
        and f"supports_{dimension}" in event["quality_flags"]
    ]
    supporting.sort(
        key=lambda event: (
            event["observation_year"]
            if event["observation_year"] is not None
            else 9999,
            event["observation_id"],
        )
    )
    return {
        "evidence_present": bool(supporting),
        "observation_ids": [event["observation_id"] for event in supporting],
        "source_ids": sorted({event["source_id"] for event in supporting}),
        "event_types": sorted(
            {
                str(event["comparability_group"])
                for event in supporting
            }
        ),
        "first_evidence_year": (
            min(
                int(event["observation_year"])
                for event in supporting
                if event["observation_year"] is not None
            )
            if supporting
            else None
        ),
        "last_evidence_year": (
            max(
                int(event["observation_year"])
                for event in supporting
                if event["observation_year"] is not None
            )
            if supporting
            else None
        ),
    }


def build_gap_audit(
    *,
    framework_path: Path = DEFAULT_FRAMEWORK,
    earth_root: Path = DEFAULT_EARTH_ROOT,
) -> dict[str, Any]:
    framework = _load_framework(framework_path)
    evidence = build_index()
    features = build_features(earth_root=earth_root)
    earth_index = json.loads((earth_root / "index.json").read_text(encoding="utf-8"))
    earth_codes = sorted(earth_index["country_codes"])

    countries: dict[str, Any] = {}
    development_counts = {
        facet: {"review": 0, "held_out_validation": 0, "all_canonical": 0}
        for facet in framework["development_facets"]
    }
    tradition_counts = {
        facet: {"review": 0, "held_out_validation": 0, "all_canonical": 0}
        for facet in framework["tradition_facets"]
    }

    for code in earth_codes:
        role = features["countries"][code]["validation_role"]
        events = _structural_events(evidence, code)

        development: dict[str, Any] = {}
        for facet, definition in framework["development_facets"].items():
            event_types = set(definition["canonical_structural_event_types"])
            facet_payload = _facet_evidence(
                events,
                event_types=event_types,
                dimension="development_quality",
            )
            facet_payload.update(
                {
                    "description": definition["description"],
                    "direct_evidence_required": bool(
                        definition["direct_evidence_required"]
                    ),
                    "canonical_structural_event_types": sorted(event_types),
                    "coverage_interpretation": (
                        "current_structural_proxy_present"
                        if facet_payload["evidence_present"]
                        else "no_canonical_facet_evidence"
                    ),
                }
            )
            development[facet] = facet_payload
            if facet_payload["evidence_present"]:
                development_counts[facet]["all_canonical"] += 1
                if role in {"review", "held_out_validation"}:
                    development_counts[facet][role] += 1

        tradition: dict[str, Any] = {}
        for facet, definition in framework["tradition_facets"].items():
            event_types = set(definition["canonical_structural_event_types"])
            facet_payload = _facet_evidence(
                events,
                event_types=event_types,
                dimension="squash_tradition",
            )
            facet_payload.update(
                {
                    "description": definition["description"],
                    "canonical_structural_event_types": sorted(event_types),
                    "coverage_interpretation": (
                        "current_structural_proxy_present"
                        if facet_payload["evidence_present"]
                        else "no_canonical_facet_evidence"
                    ),
                }
            )
            tradition[facet] = facet_payload
            if facet_payload["evidence_present"]:
                tradition_counts[facet]["all_canonical"] += 1
                if role in {"review", "held_out_validation"}:
                    tradition_counts[facet][role] += 1

        countries[code] = {
            "validation_role": role,
            "fit_allowed": features["countries"][code]["fit_allowed"],
            "development_facets": development,
            "tradition_facets": tradition,
            "rating_ready": False,
        }

    review_codes = [
        code
        for code in earth_codes
        if countries[code]["validation_role"] == "review"
    ]
    heldout_codes = [
        code
        for code in earth_codes
        if countries[code]["validation_role"] == "held_out_validation"
    ]

    return {
        "schema_version": "fifa_development_evidence_gap_audit.v1",
        "world_id": "fifa_earth",
        "framework_id": framework["framework_id"],
        "rating_ready": False,
        "canonical_authoring_allowed": False,
        "country_count": len(countries),
        "review_country_codes": review_codes,
        "heldout_country_codes": heldout_codes,
        "development_facet_coverage": development_counts,
        "tradition_facet_coverage": tradition_counts,
        "countries": countries,
        "source_basis": framework["source_basis"],
        "safeguards": framework["safeguards"],
        "next_source_priorities": [
            "talent_identification",
            "playing_opportunities",
            "youth_to_senior_transition",
            "coaching_capacity",
            "academy_pathway_coverage_depth",
            "cultural_audience_embedding",
        ],
        "limitations": [
            "Current structural proxies record existence of milestones, not nationwide quality or coverage depth.",
            "A facet marked present is not a positive quality judgement.",
            "A facet marked absent means no canonical evidence in the current corpus, not evidence that the capability does not exist.",
            "Held-out validation countries remain excluded from fitting.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", type=Path, default=DEFAULT_FRAMEWORK)
    parser.add_argument("--earth-root", type=Path, default=DEFAULT_EARTH_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_gap_audit(
        framework_path=args.framework,
        earth_root=args.earth_root,
    )
    print(
        json.dumps(
            {
                "development_facet_coverage": result[
                    "development_facet_coverage"
                ],
                "tradition_facet_coverage": result["tradition_facet_coverage"],
                "next_source_priorities": result["next_source_priorities"],
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
