"""Audit FIFA competition evidence scores against independent 2023 ranking outcomes.

The FIFA year-end ranking observations are validation-only and never participate in
V2 model fitting. Review and held-out groups are reported separately.
"""
from __future__ import annotations

import json
import math
from typing import Any

from scripts.build_fifa_country_evidence_index import build_index
from scripts.build_fifa_dimension_evidence_scores import build_dimension_evidence_scores

RANKING_MEASUREMENT = "fifa_mens_year_end_world_rank"
COMPETITION_RECIPE = "competition_quality@2023"


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        value = values[order[cursor]]
        while end < len(order) and values[order[end]] == value:
            end += 1
        average = ((cursor + 1) + end) / 2
        for position in range(cursor, end):
            ranks[order[position]] = average
        cursor = end
    return ranks


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean)
        for a, b in zip(left, right)
    )
    left_ss = sum((value - left_mean) ** 2 for value in left)
    right_ss = sum((value - right_mean) ** 2 for value in right)
    denominator = math.sqrt(left_ss * right_ss)
    return None if denominator == 0 else numerator / denominator


def _spearman_score_vs_rank(rows: list[dict[str, Any]]) -> float | None:
    numeric = [row for row in rows if row["competition_evidence_score"] is not None]
    if len(numeric) < 2:
        return None
    score = [float(row["competition_evidence_score"]) for row in numeric]
    # Lower FIFA rank is better, so negate it before rank correlation.
    outcome_strength = [-float(row["fifa_year_end_rank"]) for row in numeric]
    value = _pearson(_average_ranks(score), _average_ranks(outcome_strength))
    return None if value is None else round(value, 4)


def _pairwise_concordance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric = [row for row in rows if row["competition_evidence_score"] is not None]
    concordant = 0
    discordant = 0
    score_ties = 0
    for index, left in enumerate(numeric):
        for right in numeric[index + 1 :]:
            score_delta = float(left["competition_evidence_score"]) - float(
                right["competition_evidence_score"]
            )
            if score_delta == 0:
                score_ties += 1
                continue
            # Positive means left has the better FIFA outcome.
            outcome_delta = float(right["fifa_year_end_rank"]) - float(
                left["fifa_year_end_rank"]
            )
            if score_delta * outcome_delta > 0:
                concordant += 1
            elif score_delta * outcome_delta < 0:
                discordant += 1
            else:
                score_ties += 1

    comparable = concordant + discordant
    return {
        "concordant_pairs": concordant,
        "discordant_pairs": discordant,
        "score_or_outcome_ties": score_ties,
        "comparable_pair_count": comparable,
        "concordance_rate": (
            None if comparable == 0 else round(concordant / comparable, 4)
        ),
    }


def build_audit() -> dict[str, Any]:
    evidence = build_index()
    scores = build_dimension_evidence_scores()

    rows_by_role: dict[str, list[dict[str, Any]]] = {
        "review": [],
        "held_out_validation": [],
    }

    for code, facts in evidence["countries"].items():
        ranking_facts = [
            fact
            for fact in facts
            if fact["measurement_type"] == RANKING_MEASUREMENT
        ]
        if not ranking_facts:
            continue
        if len(ranking_facts) != 1:
            raise ValueError(f"{code}: expected one 2023 FIFA ranking observation")

        fact = ranking_facts[0]
        flags = set(fact["quality_flags"])
        if "outcome_validation_only" not in flags:
            raise ValueError(f"{code}: ranking fact is not validation-only")
        if "held_out_validation_country" in flags:
            role = "held_out_validation"
        elif "review_country" in flags:
            role = "review"
        else:
            raise ValueError(f"{code}: ranking fact lacks validation role")

        score_payload = scores["countries"][code][COMPETITION_RECIPE]
        rows_by_role[role].append(
            {
                "country_code": code,
                "validation_role": role,
                "fifa_year_end_rank": int(fact["numeric_value"]),
                "ranking_observation_id": fact["observation_id"],
                "competition_evidence_score": score_payload["evidence_score"],
                "competition_model_id": score_payload["model_id"],
                "competition_missing_signal_ids": list(
                    score_payload["missing_signal_ids"]
                ),
                "competition_component_observation_ids": sorted(
                    {
                        observation_id
                        for component in score_payload["components"]
                        for observation_id in component["source_observation_ids"]
                    }
                ),
                "fit_allowed": False,
            }
        )

    expected_roles = {"review": 9, "held_out_validation": 4}
    for role, expected_count in expected_roles.items():
        if len(rows_by_role[role]) != expected_count:
            raise ValueError(
                f"{role}: expected {expected_count} ranking outcomes, "
                f"got {len(rows_by_role[role])}"
            )
        rows_by_role[role].sort(
            key=lambda row: (row["fifa_year_end_rank"], row["country_code"])
        )

    groups: dict[str, Any] = {}
    for role, rows in rows_by_role.items():
        numeric = [
            row for row in rows if row["competition_evidence_score"] is not None
        ]
        groups[role] = {
            "ranking_outcome_count": len(rows),
            "numeric_comparison_count": len(numeric),
            "missing_competition_score_country_codes": [
                row["country_code"]
                for row in rows
                if row["competition_evidence_score"] is None
            ],
            "spearman_score_vs_better_rank": _spearman_score_vs_rank(rows),
            "pairwise": _pairwise_concordance(rows),
            "countries": rows,
        }

    return {
        "schema_version": "fifa_competition_outcome_validation.v1",
        "world_id": "fifa_earth",
        "outcome_year": 2023,
        "competition_recipe": COMPETITION_RECIPE,
        "rating_ready": False,
        "fit_allowed": False,
        "groups": groups,
        "limitations": [
            "FIFA senior national-team ranking is independent outcome evidence, not a direct domestic competition-quality measurement.",
            "Ranking outcomes never alter V2 model parameters in this audit.",
            "Held-out sample size is small and is diagnostic rather than a universal validation threshold.",
            "Countries missing professional input evidence remain missing rather than receiving zero scores.",
        ],
    }


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_audit()
    print(
        json.dumps(
            {
                role: {
                    "ranking_outcome_count": payload["ranking_outcome_count"],
                    "numeric_comparison_count": payload["numeric_comparison_count"],
                    "spearman_score_vs_better_rank": payload[
                        "spearman_score_vs_better_rank"
                    ],
                    "pairwise": payload["pairwise"],
                    "missing_competition_score_country_codes": payload[
                        "missing_competition_score_country_codes"
                    ],
                }
                for role, payload in result["groups"].items()
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
