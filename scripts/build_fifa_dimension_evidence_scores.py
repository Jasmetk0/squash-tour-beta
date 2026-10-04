"""Convert empirical FIFA signal percentiles into provisional 1–10 dimension evidence scores.

These scores are calibration aids, not canonical country ratings. The transfer curve
and dimension recipes live in a versioned JSON model so the mapping is explicit,
reviewable and replaceable without changing source observations.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beta_engine.domain.countries.rating_history import GAME_ATTRIBUTE_NAMES
from scripts.build_fifa_country_calibration_signals import build_signals

DEFAULT_MODEL = Path(
    "config/earth_research/calibration/fifa_dimension_evidence_model_v1.json"
)


def _load_model(path: Path = DEFAULT_MODEL) -> dict[str, Any]:
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("schema_version") != "fifa_dimension_evidence_model.v1":
        raise ValueError("unsupported FIFA dimension evidence model schema")
    if model.get("rating_scale") != "country_ratings_1_10.v2":
        raise ValueError("dimension evidence model must target the 1–10 rating scale")

    curve = model.get("percentile_transfer_curve")
    if not isinstance(curve, list) or len(curve) < 2:
        raise ValueError("percentile transfer curve requires at least two points")

    previous_percentile = -1.0
    previous_score = 0.0
    for point in curve:
        percentile = point.get("percentile")
        score = point.get("score")
        if (
            isinstance(percentile, bool)
            or not isinstance(percentile, (int, float))
            or not 0 <= float(percentile) <= 100
        ):
            raise ValueError("transfer-curve percentile must be numeric within 0..100")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 1 <= float(score) <= 10
        ):
            raise ValueError("transfer-curve score must be numeric within 1..10")
        if float(percentile) <= previous_percentile:
            raise ValueError("transfer-curve percentiles must be strictly increasing")
        if float(score) < previous_score:
            raise ValueError("transfer-curve scores must be non-decreasing")
        previous_percentile = float(percentile)
        previous_score = float(score)

    if float(curve[0]["percentile"]) != 0 or float(curve[-1]["percentile"]) != 100:
        raise ValueError("transfer curve must cover the full 0..100 percentile range")

    recipes = model.get("recipes")
    if not isinstance(recipes, dict) or not recipes:
        raise ValueError("dimension evidence model requires recipes")
    for recipe_id, recipe in recipes.items():
        attribute = recipe.get("attribute")
        if attribute not in GAME_ATTRIBUTE_NAMES:
            raise ValueError(f"{recipe_id}: unknown country attribute {attribute!r}")
        components = recipe.get("components")
        if not isinstance(components, list) or not components:
            raise ValueError(f"{recipe_id}: components are required")
        weights = []
        for component in components:
            weight = component.get("weight")
            if (
                isinstance(weight, bool)
                or not isinstance(weight, (int, float))
                or float(weight) <= 0
            ):
                raise ValueError(f"{recipe_id}: component weight must be positive")
            weights.append(float(weight))
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError(f"{recipe_id}: component weights must sum to 1.0")
    return model


def percentile_to_score(percentile: float, model: dict[str, Any]) -> float:
    if isinstance(percentile, bool) or not isinstance(percentile, (int, float)):
        raise ValueError("percentile must be numeric")
    value = float(percentile)
    if not 0 <= value <= 100:
        raise ValueError("percentile must be within 0..100")

    curve = model["percentile_transfer_curve"]
    for point in curve:
        if value == float(point["percentile"]):
            return round(float(point["score"]), 4)

    for left, right in zip(curve, curve[1:]):
        x0 = float(left["percentile"])
        x1 = float(right["percentile"])
        if x0 <= value <= x1:
            y0 = float(left["score"])
            y1 = float(right["score"])
            fraction = (value - x0) / (x1 - x0)
            return round(y0 + (y1 - y0) * fraction, 4)

    raise ValueError("percentile falls outside transfer curve")


def build_dimension_evidence_scores(
    *,
    model_path: Path = DEFAULT_MODEL,
) -> dict[str, Any]:
    model = _load_model(model_path)
    signals = build_signals()

    signal_definitions = signals["signal_definitions"]
    recipes = model["recipes"]
    for recipe_id, recipe in recipes.items():
        for component in recipe["components"]:
            signal_id = component["signal_id"]
            if signal_id not in signal_definitions:
                raise ValueError(f"{recipe_id}: unknown signal {signal_id!r}")
            signal_year = int(signal_definitions[signal_id]["observation_year"])
            if signal_year != int(recipe["year"]):
                raise ValueError(
                    f"{recipe_id}: signal year {signal_year} differs from recipe year"
                )
            attribute = recipe["attribute"]
            if attribute not in signal_definitions[signal_id]["primary_dimensions"]:
                raise ValueError(
                    f"{recipe_id}: signal {signal_id!r} does not declare {attribute!r} "
                    "as a primary dimension"
                )

    countries: dict[str, dict[str, Any]] = {}
    recipe_observed_counts = {recipe_id: 0 for recipe_id in recipes}

    for code, country_signals in signals["countries"].items():
        country_scores: dict[str, Any] = {}
        for recipe_id, recipe in recipes.items():
            components: list[dict[str, Any]] = []
            missing_signal_ids: list[str] = []

            for component in recipe["components"]:
                signal_id = component["signal_id"]
                weight = float(component["weight"])
                signal = country_signals[signal_id]
                percentile = signal["percentile"]
                if percentile is None:
                    missing_signal_ids.append(signal_id)
                    components.append(
                        {
                            "signal_id": signal_id,
                            "weight": weight,
                            "signal_percentile": None,
                            "transferred_score": None,
                            "source_observation_ids": list(
                                signal["observation_ids"]
                            ),
                            "completeness": signal["completeness"],
                        }
                    )
                    continue

                transferred = percentile_to_score(float(percentile), model)
                components.append(
                    {
                        "signal_id": signal_id,
                        "weight": weight,
                        "signal_percentile": percentile,
                        "transferred_score": transferred,
                        "source_observation_ids": list(signal["observation_ids"]),
                        "completeness": signal["completeness"],
                    }
                )

            require_all = bool(recipe.get("require_all_components", True))
            score = None
            if not missing_signal_ids or not require_all:
                observed_components = [
                    component
                    for component in components
                    if component["transferred_score"] is not None
                ]
                if observed_components:
                    weight_total = sum(
                        float(component["weight"])
                        for component in observed_components
                    )
                    weighted = sum(
                        float(component["transferred_score"])
                        * float(component["weight"])
                        for component in observed_components
                    ) / weight_total
                    score = round(weighted + 1e-12, 1)
                    recipe_observed_counts[recipe_id] += 1

            country_scores[recipe_id] = {
                "attribute": recipe["attribute"],
                "year": int(recipe["year"]),
                "evidence_score": score,
                "rating_ready": False,
                "confidence": recipe["confidence"],
                "require_all_components": require_all,
                "missing_signal_ids": missing_signal_ids,
                "components": components,
                "rationale": recipe["rationale"],
                "model_id": model["model_id"],
            }

        countries[code] = country_scores

    return {
        "schema_version": "fifa_dimension_evidence_scores.v1",
        "world_id": "fifa_earth",
        "model_id": model["model_id"],
        "model_schema_version": model["schema_version"],
        "rating_scale": model["rating_scale"],
        "rating_ready": False,
        "country_count": len(countries),
        "recipe_observed_counts": recipe_observed_counts,
        "unsupported_attributes": model["unsupported_attributes"],
        "transfer_curve": model["percentile_transfer_curve"],
        "recipes": recipes,
        "countries": countries,
        "limitations": [
            "Evidence scores are provisional 1–10 calibration aids, not canonical game ratings.",
            "The percentile transfer curve expresses relative empirical evidence strength, not universal semantic truth.",
            "Required missing components keep a recipe score missing rather than zero-filled.",
            "Development quality and tradition are intentionally unsupported by the current quantitative source slice.",
            "Future canonical ratings require independent historical/context evidence and exact observation provenance.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_dimension_evidence_scores(model_path=args.model)
    print(
        json.dumps(
            {
                "country_count": result["country_count"],
                "recipe_observed_counts": result["recipe_observed_counts"],
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
