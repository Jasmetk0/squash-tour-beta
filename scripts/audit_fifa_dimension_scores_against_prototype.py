"""Audit provisional FIFA dimension evidence scores against the nine-country prototype.

This is diagnostic research tooling. It compares values on the same 1–10 scale but
never mutates the prototype, calibration model, canonical research, or country ratings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_fifa_dimension_evidence_scores import (
    DEFAULT_MODEL,
    build_dimension_evidence_scores,
)
from scripts.materialize_fifa_earth_prototype import (
    DEFAULT_COUNTRY_INDEX,
    _load_earth_country_codes,
    materialise,
)

DEFAULT_PROTOTYPE = Path(
    "config/earth_research/fifa_earth_prototype_anchors_v2.json"
)
REVIEW_ABSOLUTE_DELTA = 1.5


def _round(value: float) -> float:
    return round(float(value) + 1e-12, 3)


def build_audit(
    *,
    prototype_path: Path = DEFAULT_PROTOTYPE,
    country_index_path: Path = DEFAULT_COUNTRY_INDEX,
    model_path: Path = DEFAULT_MODEL,
) -> dict[str, Any]:
    raw = json.loads(prototype_path.read_text(encoding="utf-8"))
    prototype = materialise(
        raw,
        earth_country_codes=_load_earth_country_codes(country_index_path),
    )
    evidence = build_dimension_evidence_scores(model_path=model_path)

    prototype_codes = sorted(prototype["countries"])
    recipes: dict[str, Any] = {}

    for recipe_id, recipe in evidence["recipes"].items():
        attribute = str(recipe["attribute"])
        year = int(recipe["year"])
        rows: list[dict[str, Any]] = []

        for code in prototype_codes:
            score_payload = evidence["countries"][code][recipe_id]
            score = score_payload["evidence_score"]
            if score is None:
                continue

            rating_payload = prototype["countries"][code]["years"][year]["ratings"][
                attribute
            ]
            prototype_rating = float(rating_payload["value"])
            delta = float(score) - prototype_rating
            rows.append(
                {
                    "country_code": code,
                    "attribute": attribute,
                    "year": year,
                    "evidence_score": float(score),
                    "prototype_rating": prototype_rating,
                    "signed_delta": _round(delta),
                    "absolute_delta": _round(abs(delta)),
                    "review_required": abs(delta) >= REVIEW_ABSOLUTE_DELTA,
                    "prototype_method": rating_payload["method"],
                    "prototype_confidence": rating_payload["confidence"],
                    "prototype_anchor_years": list(rating_payload["anchor_years"]),
                    "evidence_confidence": score_payload["confidence"],
                    "missing_signal_ids": list(score_payload["missing_signal_ids"]),
                    "components": [
                        {
                            "signal_id": component["signal_id"],
                            "weight": component["weight"],
                            "signal_percentile": component["signal_percentile"],
                            "transferred_score": component["transferred_score"],
                            "source_observation_ids": list(
                                component["source_observation_ids"]
                            ),
                        }
                        for component in score_payload["components"]
                    ],
                }
            )

        absolute = [float(row["absolute_delta"]) for row in rows]
        signed = [float(row["signed_delta"]) for row in rows]
        review_rows = [row for row in rows if row["review_required"]]

        recipes[recipe_id] = {
            "attribute": attribute,
            "year": year,
            "sample_count": len(rows),
            "mean_absolute_delta": None
            if not absolute
            else _round(sum(absolute) / len(absolute)),
            "mean_signed_delta": None
            if not signed
            else _round(sum(signed) / len(signed)),
            "maximum_absolute_delta": None
            if not absolute
            else _round(max(absolute)),
            "review_count": len(review_rows),
            "review_country_codes": [
                row["country_code"]
                for row in sorted(
                    review_rows,
                    key=lambda item: (
                        -float(item["absolute_delta"]),
                        item["country_code"],
                    ),
                )
            ],
            "countries": sorted(
                rows,
                key=lambda item: (
                    -float(item["absolute_delta"]),
                    item["country_code"],
                ),
            ),
        }

    return {
        "schema_version": "fifa_dimension_score_prototype_audit.v1",
        "prototype_schema_version": prototype["schema_version"],
        "evidence_score_schema_version": evidence["schema_version"],
        "evidence_model_id": evidence["model_id"],
        "prototype_country_count": len(prototype_codes),
        "prototype_countries": prototype_codes,
        "rating_ready": False,
        "review_absolute_delta_threshold": REVIEW_ABSOLUTE_DELTA,
        "recipes": recipes,
        "limitations": [
            "The nine-country prototype is a review set, not a statistically independent gold standard.",
            "A large delta can be legitimate because prototype ratings include historical/context evidence beyond the quantitative source slice.",
            "A small delta does not validate the transfer curve or make an evidence score canonical.",
            "No audit result automatically changes a rating, model weight, or transfer-curve point.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prototype", type=Path, default=DEFAULT_PROTOTYPE)
    parser.add_argument("--country-index", type=Path, default=DEFAULT_COUNTRY_INDEX)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    audit = build_audit(
        prototype_path=args.prototype,
        country_index_path=args.country_index,
        model_path=args.model,
    )
    summary = {
        recipe_id: {
            "sample_count": payload["sample_count"],
            "mean_absolute_delta": payload["mean_absolute_delta"],
            "mean_signed_delta": payload["mean_signed_delta"],
            "maximum_absolute_delta": payload["maximum_absolute_delta"],
            "review_count": payload["review_count"],
            "review_country_codes": payload["review_country_codes"],
        }
        for recipe_id, payload in audit["recipes"].items()
    }
    print(json.dumps(summary, indent=2))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
