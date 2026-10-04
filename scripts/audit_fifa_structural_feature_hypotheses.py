"""Test simple structural-feature hypotheses against the FIFA review prototype.

The audit intentionally tests and may reject simplistic one-factor mappings. Held-out
validation countries never participate in the correlations or decision thresholds.
"""
from __future__ import annotations

import math
import json
from pathlib import Path
from typing import Any

from scripts.build_fifa_structural_features import build_features
from scripts.materialize_fifa_earth_prototype import (
    DEFAULT_COUNTRY_INDEX,
    _load_earth_country_codes,
    materialise,
)

DEFAULT_PROTOTYPE = Path(
    "config/earth_research/fifa_earth_prototype_anchors_v2.json"
)
MIN_ABS_SPEARMAN_FOR_CANDIDATE = 0.60


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
    if denominator == 0:
        return None
    return numerator / denominator


def _spearman(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    x = [item[0] for item in pairs]
    y = [item[1] for item in pairs]
    value = _pearson(_average_ranks(x), _average_ranks(y))
    return None if value is None else round(value, 4)


def build_audit(
    *,
    prototype_path: Path = DEFAULT_PROTOTYPE,
    country_index_path: Path = DEFAULT_COUNTRY_INDEX,
) -> dict[str, Any]:
    features = build_features()
    raw = json.loads(prototype_path.read_text(encoding="utf-8"))
    prototype = materialise(
        raw,
        earth_country_codes=_load_earth_country_codes(country_index_path),
    )

    review_codes = sorted(
        code
        for code, country in features["countries"].items()
        if country["validation_role"] == "review"
    )
    heldout_codes = sorted(
        code
        for code, country in features["countries"].items()
        if country["validation_role"] == "held_out_validation"
    )

    hypotheses = {
        "tradition_span_only": {
            "attribute": "squash_tradition",
            "feature": lambda country: country["tradition"][
                "evidence_span_years_to_2026"
            ],
            "transform": lambda value: float(value),
            "claim": (
                "Longer dated tradition evidence alone can rank country tradition."
            ),
        },
        "pre1955_event_count_only": {
            "attribute": "squash_tradition",
            "feature": lambda country: country["tradition"][
                "pre_1955_event_count"
            ],
            "transform": lambda value: float(value),
            "claim": (
                "The number of pre-1955 tradition events alone can rank tradition."
            ),
        },
        "development_history_span_only": {
            "attribute": "development_quality",
            "feature": lambda country: (
                None
                if country["development"]["first_event_year"] is None
                else 2026 - int(country["development"]["first_event_year"])
            ),
            "transform": lambda value: float(value),
            "claim": (
                "Longer documented development-system history alone can rank development quality."
            ),
        },
        "development_recency_only": {
            "attribute": "development_quality",
            "feature": lambda country: country["development"][
                "years_since_latest_evidence"
            ],
            "transform": lambda value: -float(value),
            "claim": (
                "More recent development evidence alone can rank development quality."
            ),
        },
    }

    results: dict[str, Any] = {}
    for hypothesis_id, hypothesis in hypotheses.items():
        rows: list[dict[str, Any]] = []
        pairs: list[tuple[float, float]] = []

        for code in review_codes:
            country = features["countries"][code]
            raw_feature = hypothesis["feature"](country)
            if raw_feature is None:
                continue
            transformed = hypothesis["transform"](raw_feature)
            rating = float(
                prototype["countries"][code]["years"][2026]["ratings"][
                    hypothesis["attribute"]
                ]["value"]
            )
            rows.append(
                {
                    "country_code": code,
                    "raw_feature_value": raw_feature,
                    "correlation_feature_value": transformed,
                    "prototype_rating_2026": rating,
                }
            )
            pairs.append((transformed, rating))

        rho = _spearman(pairs)
        candidate = (
            rho is not None
            and abs(rho) >= MIN_ABS_SPEARMAN_FOR_CANDIDATE
        )
        results[hypothesis_id] = {
            "attribute": hypothesis["attribute"],
            "claim": hypothesis["claim"],
            "sample_count": len(rows),
            "spearman_rho": rho,
            "minimum_abs_spearman_for_candidate": (
                MIN_ABS_SPEARMAN_FOR_CANDIDATE
            ),
            "decision": (
                "candidate_for_multifactor_review"
                if candidate
                else "rejected_as_single_factor_transfer"
            ),
            "countries": rows,
        }

    return {
        "schema_version": "fifa_structural_feature_hypothesis_audit.v1",
        "world_id": "fifa_earth",
        "rating_ready": False,
        "canonical_authoring_allowed": False,
        "review_country_codes": review_codes,
        "heldout_country_codes": heldout_codes,
        "heldout_used_for_fit": False,
        "hypotheses": results,
        "limitations": [
            "The prototype is a review artefact, not a gold-standard independent label set.",
            "Failure of a single-factor hypothesis does not prove a structural feature is irrelevant in a multifactor model.",
            "Held-out countries are excluded from all correlations and thresholds.",
            "No rejected or surviving hypothesis automatically produces a country rating.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prototype", type=Path, default=DEFAULT_PROTOTYPE)
    parser.add_argument("--country-index", type=Path, default=DEFAULT_COUNTRY_INDEX)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_audit(
        prototype_path=args.prototype,
        country_index_path=args.country_index,
    )
    print(
        json.dumps(
            {
                key: {
                    "sample_count": value["sample_count"],
                    "spearman_rho": value["spearman_rho"],
                    "decision": value["decision"],
                }
                for key, value in result["hypotheses"].items()
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
