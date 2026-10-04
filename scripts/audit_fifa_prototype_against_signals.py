"""Audit the nine-country FIFA prototype against canonical empirical signals.

This is diagnostic tooling only. It does not modify prototype anchors, canonical
research, or game ratings. The audit reports signal/rating rank agreement and
material pairwise inversions that deserve human review.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from scripts.build_fifa_country_calibration_signals import build_signals
from scripts.materialize_fifa_earth_prototype import (
    DEFAULT_COUNTRY_INDEX,
    _load_earth_country_codes,
    materialise,
)

DEFAULT_PROTOTYPE = Path(
    "config/earth_research/fifa_earth_prototype_anchors_v2.json"
)

COMPARISONS = {
    "participation_intensity_2006": ("squash_popularity",),
    "registered_intensity_2006": ("squash_access",),
    "club_footprint_2006": ("squash_access",),
    "professional_player_density_2023": (
        "competition_quality",
        "elite_support",
    ),
    "professional_club_density_2023": (
        "competition_quality",
        "elite_support",
    ),
}

REVIEW_PERCENTILE_GAP = 25.0
REVIEW_RATING_INVERSION = 0.5


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
    signal = [item[0] for item in pairs]
    rating = [item[1] for item in pairs]
    correlation = _pearson(_average_ranks(signal), _average_ranks(rating))
    return None if correlation is None else round(correlation, 4)


def _review_inversions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    ordered = sorted(
        rows,
        key=lambda item: (
            -float(item["signal_percentile"]),
            item["country_code"],
        ),
    )
    for index, stronger_signal in enumerate(ordered):
        for weaker_signal in ordered[index + 1 :]:
            percentile_gap = (
                float(stronger_signal["signal_percentile"])
                - float(weaker_signal["signal_percentile"])
            )
            rating_gap = (
                float(stronger_signal["prototype_rating"])
                - float(weaker_signal["prototype_rating"])
            )
            if (
                percentile_gap >= REVIEW_PERCENTILE_GAP
                and rating_gap <= -REVIEW_RATING_INVERSION
            ):
                flags.append(
                    {
                        "higher_signal_country": stronger_signal["country_code"],
                        "lower_signal_country": weaker_signal["country_code"],
                        "signal_percentile_gap": round(percentile_gap, 2),
                        "prototype_rating_gap": round(rating_gap, 1),
                    }
                )
    return flags


def build_audit(
    *,
    prototype_path: Path = DEFAULT_PROTOTYPE,
    country_index_path: Path = DEFAULT_COUNTRY_INDEX,
) -> dict[str, Any]:
    raw = json.loads(prototype_path.read_text(encoding="utf-8"))
    prototype = materialise(
        raw,
        earth_country_codes=_load_earth_country_codes(country_index_path),
    )
    signals = build_signals()
    prototype_codes = sorted(prototype["countries"])

    comparisons: dict[str, Any] = {}
    for signal_id, attributes in COMPARISONS.items():
        definition = signals["signal_definitions"][signal_id]
        year = int(definition["observation_year"])

        for attribute in attributes:
            rows: list[dict[str, Any]] = []
            for code in prototype_codes:
                signal = signals["countries"][code][signal_id]
                if signal["rate"] is None:
                    continue
                rating = prototype["countries"][code]["years"][year]["ratings"][
                    attribute
                ]
                rows.append(
                    {
                        "country_code": code,
                        "signal_rate": signal["rate"],
                        "signal_unit": signal["unit"],
                        "signal_percentile": signal["percentile"],
                        "signal_rank_desc": signal["rank_desc"],
                        "prototype_rating": rating["value"],
                        "prototype_rating_method": rating["method"],
                        "prototype_confidence": rating["confidence"],
                        "prototype_anchor_years": list(rating["anchor_years"]),
                        "source_observation_ids": list(signal["observation_ids"]),
                    }
                )

            key = f"{signal_id}__{attribute}"
            pairs = [
                (
                    float(row["signal_percentile"]),
                    float(row["prototype_rating"]),
                )
                for row in rows
            ]
            comparisons[key] = {
                "signal_id": signal_id,
                "attribute": attribute,
                "observation_year": year,
                "sample_count": len(rows),
                "spearman_rho": _spearman(pairs),
                "review_inversion_count": 0,
                "review_inversions": [],
                "countries": sorted(
                    rows,
                    key=lambda item: (
                        -float(item["signal_percentile"]),
                        item["country_code"],
                    ),
                ),
            }
            inversions = _review_inversions(rows)
            comparisons[key]["review_inversion_count"] = len(inversions)
            comparisons[key]["review_inversions"] = inversions

    return {
        "schema_version": "fifa_prototype_signal_audit.v1",
        "prototype_schema_version": prototype["schema_version"],
        "prototype_country_count": len(prototype_codes),
        "prototype_countries": prototype_codes,
        "canonical_signal_schema_version": signals["schema_version"],
        "rating_ready": False,
        "comparison_count": len(comparisons),
        "comparisons": comparisons,
        "review_thresholds": {
            "minimum_signal_percentile_gap": REVIEW_PERCENTILE_GAP,
            "minimum_opposite_rating_gap": REVIEW_RATING_INVERSION,
        },
        "limitations": [
            "Spearman correlations use only the nine-country prototype and are diagnostic, not validation thresholds.",
            "A rank inversion may be legitimate because each country rating includes contextual evidence beyond one quantitative signal.",
            "The professional 2023 comparisons have smaller samples because source missing values remain missing.",
            "No audit result automatically changes a rating or declares a transfer function.",
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
    summary = {
        key: {
            "sample_count": value["sample_count"],
            "spearman_rho": value["spearman_rho"],
            "review_inversion_count": value["review_inversion_count"],
        }
        for key, value in result["comparisons"].items()
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
