"""Evaluate the active FIFA quantitative calibration model against review policy.

This gate classifies dimensions for the next research step. It never authorizes
automatic canonical rating creation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beta_engine.domain.countries.rating_history import GAME_ATTRIBUTE_NAMES
from scripts.audit_fifa_dimension_scores_against_prototype import (
    build_audit as build_dimension_score_audit,
)
from scripts.build_fifa_dimension_evidence_scores import (
    build_dimension_evidence_scores,
)

DEFAULT_POLICY = Path(
    "config/earth_research/calibration/fifa_calibration_review_policy_v1.json"
)


def _load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema_version") != "fifa_calibration_review_policy.v1":
        raise ValueError("unsupported FIFA calibration review policy schema")
    if policy.get("canonical_authoring_allowed") is not False:
        raise ValueError("review policy must not authorize canonical authoring")
    thresholds = policy.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("review policy thresholds are required")
    required = {
        "minimum_review_sample_count",
        "maximum_mean_absolute_delta_for_baseline_candidate",
        "maximum_absolute_delta_for_baseline_candidate",
        "maximum_review_count_for_baseline_candidate",
        "maximum_mean_absolute_delta_for_context_gap",
        "maximum_review_count_for_context_gap",
    }
    if set(thresholds) != required:
        raise ValueError("review policy threshold set is incomplete or unexpected")
    return policy


def _classify(metrics: dict[str, Any], thresholds: dict[str, Any]) -> str:
    sample = int(metrics["sample_count"])
    mad = float(metrics["mean_absolute_delta"])
    maximum = float(metrics["maximum_absolute_delta"])
    review_count = int(metrics["review_count"])

    if sample < int(thresholds["minimum_review_sample_count"]):
        return "insufficient_review_sample"

    if (
        mad
        <= float(
            thresholds["maximum_mean_absolute_delta_for_baseline_candidate"]
        )
        and maximum
        <= float(thresholds["maximum_absolute_delta_for_baseline_candidate"])
        and review_count
        <= int(thresholds["maximum_review_count_for_baseline_candidate"])
    ):
        return "quantitative_baseline_candidate"

    if (
        mad
        <= float(thresholds["maximum_mean_absolute_delta_for_context_gap"])
        and review_count <= int(thresholds["maximum_review_count_for_context_gap"])
    ):
        return "quantitative_baseline_with_context_gap"

    return "quantitative_model_rejected"


def evaluate_gate(*, policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    policy = _load_policy(policy_path)
    scores = build_dimension_evidence_scores()
    audit = build_dimension_score_audit()

    if scores["model_id"] != policy["model_id"]:
        raise ValueError(
            f"policy targets {policy['model_id']!r}, active model is "
            f"{scores['model_id']!r}"
        )
    if audit["evidence_model_id"] != scores["model_id"]:
        raise ValueError("score audit and active evidence model disagree")

    recipe_by_attribute = {
        recipe["attribute"]: recipe_id
        for recipe_id, recipe in scores["recipes"].items()
    }
    unsupported = scores["unsupported_attributes"]
    context_requirements = policy["context_requirements"]

    dimensions: dict[str, Any] = {}
    for attribute in GAME_ATTRIBUTE_NAMES:
        if attribute in unsupported:
            dimensions[attribute] = {
                "attribute": attribute,
                "state": "quantitatively_unsupported",
                "canonical_authoring_allowed": False,
                "recipe_id": None,
                "evidence_model_id": scores["model_id"],
                "quantitative_reason": unsupported[attribute],
                "review_metrics": None,
                "review_country_codes": [],
                "context_requirements": list(context_requirements[attribute]),
            }
            continue

        recipe_id = recipe_by_attribute.get(attribute)
        if recipe_id is None:
            raise ValueError(
                f"{attribute}: neither quantitative recipe nor unsupported reason"
            )
        metrics = audit["recipes"].get(recipe_id)
        if metrics is None:
            raise ValueError(f"{attribute}: recipe {recipe_id!r} lacks score audit")

        state = _classify(metrics, policy["thresholds"])
        dimensions[attribute] = {
            "attribute": attribute,
            "state": state,
            "canonical_authoring_allowed": False,
            "recipe_id": recipe_id,
            "evidence_model_id": scores["model_id"],
            "quantitative_reason": scores["recipes"][recipe_id]["rationale"],
            "review_metrics": {
                key: metrics[key]
                for key in (
                    "sample_count",
                    "mean_absolute_delta",
                    "mean_signed_delta",
                    "maximum_absolute_delta",
                    "review_count",
                )
            },
            "review_country_codes": list(metrics["review_country_codes"]),
            "context_requirements": list(context_requirements[attribute]),
        }

    return {
        "schema_version": "fifa_calibration_gate.v1",
        "world_id": "fifa_earth",
        "policy_id": policy["policy_id"],
        "evidence_model_id": scores["model_id"],
        "rating_ready": False,
        "canonical_authoring_allowed": False,
        "thresholds": policy["thresholds"],
        "state_definitions": policy["states"],
        "dimensions": dimensions,
        "safeguards": policy["safeguards"],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = evaluate_gate(policy_path=args.policy)
    summary = {
        attribute: {
            "state": payload["state"],
            "review_country_codes": payload["review_country_codes"],
        }
        for attribute, payload in result["dimensions"].items()
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
