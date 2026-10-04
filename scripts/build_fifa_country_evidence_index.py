"""Build a country-indexed FIFA evidence view from canonical observations/resolutions.

This is a research/calibration input, not a rating generator. It never invents
aggregate values: UK/home-association facts remain explicit aggregate-member
components, and manual/unresolved identity facts stay outside country evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.application.earth_research_identity import identity_resolution_sha256
from scripts.build_fifa_observation_identity_resolutions import (
    RESEARCH,
    build_resolution_sets,
)


def _fact(observation, resolution) -> dict[str, Any]:
    return {
        "observation_id": observation.observation_id,
        "source_id": observation.source_id,
        "source_entity": observation.source_entity,
        "source_page": observation.source_page,
        "observation_year": observation.observation_year,
        "measurement_type": observation.measurement_type,
        "numeric_value": observation.numeric_value,
        "text_value": observation.text_value,
        "unit": observation.unit,
        "identity_status": resolution.status,
        "identity_method": resolution.method,
        "identity_confidence": resolution.confidence,
        "earth_country_code": resolution.earth_country_code,
        "candidate_earth_codes": list(resolution.candidate_earth_codes),
        "identity_reason": resolution.reason,
        "quality_flags": list(observation.quality_flags),
    }


def build_index(research_path: Path = RESEARCH) -> dict[str, Any]:
    bundle = load_earth_research_bundle(research_path)
    resolution_sets = build_resolution_sets()

    resolutions = {}
    for resolution_set in resolution_sets.values():
        for resolution in resolution_set.resolutions:
            if resolution.observation_id in resolutions:
                raise ValueError(
                    f"duplicate resolution for {resolution.observation_id!r}"
                )
            resolutions[resolution.observation_id] = resolution

    if set(resolutions) != set(bundle.observations):
        missing = sorted(set(bundle.observations) - set(resolutions))
        extra = sorted(set(resolutions) - set(bundle.observations))
        raise ValueError(
            f"identity/evidence coverage mismatch; missing={missing}, extra={extra}"
        )

    countries: dict[str, list[dict[str, Any]]] = {}
    manual_review: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for observation_id in sorted(bundle.observations):
        observation = bundle.observations[observation_id]
        resolution = resolutions[observation_id]
        fact = _fact(observation, resolution)

        if resolution.status in {"direct", "aggregate_member"}:
            if resolution.earth_country_code is None:
                raise ValueError(
                    f"safe resolution lacks Earth target: {observation_id}"
                )
            countries.setdefault(resolution.earth_country_code, []).append(fact)
        elif resolution.status == "manual_review":
            manual_review.append(fact)
        elif resolution.status == "unresolved":
            unresolved.append(fact)
        else:
            raise ValueError(
                f"unsupported identity status {resolution.status!r}"
            )

    countries = {
        code: sorted(facts, key=lambda item: item["observation_id"])
        for code, facts in sorted(countries.items())
    }
    manual_review.sort(key=lambda item: item["observation_id"])
    unresolved.sort(key=lambda item: item["observation_id"])

    safe_count = sum(len(facts) for facts in countries.values())
    total_count = safe_count + len(manual_review) + len(unresolved)
    if total_count != len(bundle.observations):
        raise ValueError("country evidence partition lost or duplicated observations")

    return {
        "schema_version": "fifa_country_evidence_index.v1",
        "world_id": "fifa_earth",
        "observation_count": len(bundle.observations),
        "safe_country_evidence_count": safe_count,
        "manual_review_count": len(manual_review),
        "unresolved_count": len(unresolved),
        "country_count_with_safe_evidence": len(countries),
        "input_observation_dataset_sha256s": {
            dataset_id: manifest.sha256
            for dataset_id, manifest in sorted(
                bundle.research.observation_datasets.items()
            )
        },
        "input_identity_resolution_sha256s": {
            set_id: identity_resolution_sha256(resolution_set)
            for set_id, resolution_set in sorted(resolution_sets.items())
        },
        "countries": countries,
        "manual_review": manual_review,
        "unresolved": unresolved,
        "rating_ready": False,
        "limitations": [
            "Safe evidence is grouped by Earth identity but is not a country rating.",
            "Aggregate-member facts remain source components; no synthetic aggregate is created here.",
            "Manual-review and unresolved observations are excluded from country evidence.",
            "Cross-country comparability flags and source-definition limitations remain authoritative.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, default=RESEARCH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_index(args.research)
    summary = {
        key: result[key]
        for key in (
            "observation_count",
            "safe_country_evidence_count",
            "manual_review_count",
            "unresolved_count",
            "country_count_with_safe_evidence",
        )
    }
    print(json.dumps(summary, indent=2))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
