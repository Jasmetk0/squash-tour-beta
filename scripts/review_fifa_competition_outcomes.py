"""Apply the fixed FIFA competition-outcome review policy to the independent audit.

This review classifies the existing validation result. It never retunes the V2 model,
changes thresholds, or authorizes canonical rating authorship.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.audit_fifa_competition_against_2023_ranking import build_audit

DEFAULT_POLICY = Path(
    "config/earth_research/calibration/fifa_competition_outcome_review_policy_v1.json"
)


def _load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema_version") != "fifa_competition_outcome_review_policy.v1":
        raise ValueError("unsupported FIFA competition outcome review policy")
    if policy.get("audit_schema_version") != "fifa_competition_outcome_validation.v1":
        raise ValueError("competition outcome policy/audit schema mismatch")
    if policy.get("competition_recipe") != "competition_quality@2023":
        raise ValueError("competition outcome policy must target competition_quality@2023")
    if policy.get("canonical_authoring_allowed") is not False:
        raise ValueError("outcome review policy must not authorize canonical authoring")
    return policy


def _group_pass(payload: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    rho = payload["spearman_score_vs_better_rank"]
    concordance = payload["pairwise"]["concordance_rate"]
    numeric_count = int(payload["numeric_comparison_count"])

    checks = {
        "numeric_country_count": {
            "actual": numeric_count,
            "minimum": int(rule["minimum_numeric_country_count"]),
            "pass": numeric_count >= int(rule["minimum_numeric_country_count"]),
        },
        "spearman_score_vs_better_rank": {
            "actual": rho,
            "minimum": float(rule["minimum_spearman_score_vs_better_rank"]),
            "pass": rho is not None
            and float(rho) >= float(rule["minimum_spearman_score_vs_better_rank"]),
        },
        "pairwise_concordance_rate": {
            "actual": concordance,
            "minimum": float(rule["minimum_pairwise_concordance_rate"]),
            "pass": concordance is not None
            and float(concordance) >= float(rule["minimum_pairwise_concordance_rate"]),
        },
    }
    return {
        "pass": all(check["pass"] for check in checks.values()),
        "checks": checks,
    }


def build_review(
    *,
    policy_path: Path = DEFAULT_POLICY,
) -> dict[str, Any]:
    policy = _load_policy(policy_path)
    audit = build_audit()

    if audit["schema_version"] != policy["audit_schema_version"]:
        raise ValueError("competition outcome audit does not match policy schema")
    if audit["competition_recipe"] != policy["competition_recipe"]:
        raise ValueError("competition outcome audit recipe differs from policy")
    if audit["fit_allowed"] is not False:
        raise ValueError("competition outcome audit must remain fit_allowed=false")

    review_result = _group_pass(audit["groups"]["review"], policy["review"])
    heldout_result = _group_pass(
        audit["groups"]["held_out_validation"],
        policy["held_out_validation"],
    )

    if not review_result["pass"]:
        decision = policy["decisions"]["review_fail"]
    elif not heldout_result["pass"]:
        decision = policy["decisions"]["review_pass_heldout_fail"]
    else:
        decision = policy["decisions"]["both_pass"]

    return {
        "schema_version": "fifa_competition_outcome_review.v1",
        "policy_id": policy["policy_id"],
        "competition_recipe": policy["competition_recipe"],
        "decision": decision,
        "review_pass": review_result["pass"],
        "held_out_validation_pass": heldout_result["pass"],
        "review": review_result,
        "held_out_validation": heldout_result,
        "review_missing_competition_score_country_codes": audit["groups"]["review"][
            "missing_competition_score_country_codes"
        ],
        "heldout_missing_competition_score_country_codes": audit["groups"][
            "held_out_validation"
        ]["missing_competition_score_country_codes"],
        "fit_allowed": False,
        "canonical_authoring_allowed": False,
        "safeguards": policy["safeguards"],
        "interpretation": (
            "Independent senior national-team outcome validation can support or weaken "
            "confidence in the V2 competition recipe, but cannot itself promote a "
            "domestic competition-quality score into canonical country history."
        ),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_review(policy_path=args.policy)
    print(json.dumps(result, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
