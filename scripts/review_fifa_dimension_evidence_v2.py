"""Review FIFA dimension evidence model V2 against V1 and explicit policy.

This script recomputes both prototype audits from canonical research. It records the
measured V1->V2 improvement and applies only the checked-in review policy. Passing
this review does not authorize canonical country-rating authoring.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.audit_fifa_dimension_scores_against_prototype import build_audit

V1_MODEL = Path(
    "config/earth_research/calibration/fifa_dimension_evidence_model_v1.json"
)
V2_MODEL = Path(
    "config/earth_research/calibration/fifa_dimension_evidence_model_v2.json"
)
DEFAULT_POLICY = Path(
    "config/earth_research/calibration/fifa_dimension_evidence_v2_review_policy.json"
)


def _load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "fifa_dimension_evidence_review_policy.v1":
        raise ValueError("unsupported FIFA dimension evidence review policy schema")
    return payload


def _metrics(audit: dict[str, Any], recipe_id: str) -> dict[str, Any]:
    payload = audit["recipes"][recipe_id]
    return {
        "sample_count": payload["sample_count"],
        "mean_absolute_delta": payload["mean_absolute_delta"],
        "mean_signed_delta": payload["mean_signed_delta"],
        "maximum_absolute_delta": payload["maximum_absolute_delta"],
        "review_count": payload["review_count"],
        "review_country_codes": list(payload["review_country_codes"]),
    }


def build_review(
    *,
    policy_path: Path = DEFAULT_POLICY,
    v1_model_path: Path = V1_MODEL,
    v2_model_path: Path = V2_MODEL,
) -> dict[str, Any]:
    policy = _load_policy(policy_path)
    v1 = build_audit(model_path=v1_model_path)
    v2 = build_audit(model_path=v2_model_path)

    if v1["evidence_model_id"] != policy["baseline_model_id"]:
        raise ValueError("review policy baseline_model_id does not match V1 audit")
    if v2["evidence_model_id"] != policy["candidate_model_id"]:
        raise ValueError("review policy candidate_model_id does not match V2 audit")

    recipe_results: dict[str, Any] = {}
    all_policy_checks_pass = True

    for recipe_id, recipe_policy in policy["recipe_policy"].items():
        if recipe_id not in v2["recipes"]:
            raise ValueError(f"V2 audit lacks policy recipe {recipe_id!r}")

        v2_metrics = _metrics(v2, recipe_id)
        v1_metrics = _metrics(v1, recipe_id) if recipe_id in v1["recipes"] else None
        checks: dict[str, bool] = {}

        if recipe_policy.get("max_mean_absolute_delta") is not None:
            checks["mean_absolute_delta"] = (
                float(v2_metrics["mean_absolute_delta"])
                <= float(recipe_policy["max_mean_absolute_delta"])
            )
        if recipe_policy.get("max_review_count") is not None:
            checks["review_count"] = (
                int(v2_metrics["review_count"])
                <= int(recipe_policy["max_review_count"])
            )
        if recipe_policy.get("max_maximum_absolute_delta") is not None:
            checks["maximum_absolute_delta"] = (
                float(v2_metrics["maximum_absolute_delta"])
                <= float(recipe_policy["max_maximum_absolute_delta"])
            )

        recipe_pass = all(checks.values())
        all_policy_checks_pass = all_policy_checks_pass and recipe_pass

        recipe_results[recipe_id] = {
            "decision": recipe_policy["decision"],
            "policy_checks_pass": recipe_pass,
            "checks": checks,
            "v1_metrics": v1_metrics,
            "v2_metrics": v2_metrics,
            "canonical_authoring_allowed": bool(
                recipe_policy["canonical_authoring_allowed"]
            ),
            "blockers": list(recipe_policy["blockers"]),
        }

    regression = policy["regression_requirements"]
    competition_v1 = _metrics(v1, "competition_quality@2023")
    competition_v2 = _metrics(v2, "competition_quality@2023")
    elite_v1 = _metrics(v1, "elite_support@2023")
    elite_v2 = _metrics(v2, "elite_support@2023")

    competition_improvement = round(
        float(competition_v1["mean_absolute_delta"])
        - float(competition_v2["mean_absolute_delta"]),
        3,
    )
    elite_improvement = round(
        float(elite_v1["mean_absolute_delta"])
        - float(elite_v2["mean_absolute_delta"]),
        3,
    )

    regression_checks = {
        "competition_mad_improvement": competition_improvement
        >= float(
            regression[
                "competition_quality_v2_mad_improvement_vs_v1_minimum"
            ]
        ),
        "elite_mad_improvement": elite_improvement
        >= float(
            regression["elite_support_v2_mad_improvement_vs_v1_minimum"]
        ),
        "competition_review_count": int(competition_v2["review_count"])
        <= int(regression["competition_quality_v2_review_count_maximum"]),
        "elite_review_count": int(elite_v2["review_count"])
        <= int(regression["elite_support_v2_review_count_maximum"]),
    }
    regression_pass = all(regression_checks.values())

    return {
        "schema_version": "fifa_dimension_evidence_v2_review.v1",
        "review_id": policy["review_id"],
        "baseline_model_id": v1["evidence_model_id"],
        "candidate_model_id": v2["evidence_model_id"],
        "rating_ready": False,
        "policy_checks_pass": all_policy_checks_pass,
        "regression_checks_pass": regression_pass,
        "review_pass": all_policy_checks_pass and regression_pass,
        "measured_improvement": {
            "competition_quality_mean_absolute_delta": competition_improvement,
            "elite_support_mean_absolute_delta": elite_improvement,
        },
        "regression_checks": regression_checks,
        "recipes": recipe_results,
        "safeguards": list(policy["safeguards"]),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--v1-model", type=Path, default=V1_MODEL)
    parser.add_argument("--v2-model", type=Path, default=V2_MODEL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    review = build_review(
        policy_path=args.policy,
        v1_model_path=args.v1_model,
        v2_model_path=args.v2_model,
    )
    print(json.dumps(review, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(review, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
