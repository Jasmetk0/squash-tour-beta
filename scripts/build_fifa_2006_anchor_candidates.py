"""Build provenance-complete 2006 FIFA rating-anchor candidates for the prototype set.

This is the first rating-authoring experiment. It migrates only the prototype
attributes directly supported by the canonical FIFA Big Count 2006 slice:
squash_popularity and squash_access.

The result uses the production RatingEvidence contract but remains a partial
candidate set because CountryRatingHistory requires all six attributes per authored
year. Nothing is written into canonical fifa_earth country histories.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.domain.countries.rating_history import RatingEvidence
from scripts.build_fifa_country_calibration_signals import build_signals
from scripts.build_fifa_dimension_evidence_scores import build_dimension_evidence_scores

RESEARCH = Path("config/earth_research/fifa_earth.json")
PROTOTYPE = Path("config/earth_research/fifa_earth_prototype_anchors_v2.json")
ANCHOR_YEAR = 2006
SUPPORTED_ATTRIBUTES = ("squash_popularity", "squash_access")

ATTRIBUTE_SIGNAL_IDS = {
    "squash_popularity": ("participation_intensity_2006",),
    "squash_access": (
        "registered_intensity_2006",
        "club_footprint_2006",
    ),
}
ATTRIBUTE_RECIPE_IDS = {
    "squash_popularity": "squash_popularity@2006",
    "squash_access": "squash_access@2006",
}


def _candidate_observation_ids(
    country_signals: dict[str, Any],
    attribute: str,
) -> list[str]:
    observation_ids: list[str] = []
    for signal_id in ATTRIBUTE_SIGNAL_IDS[attribute]:
        signal = country_signals[signal_id]
        if signal["rate"] is None:
            raise ValueError(
                f"{attribute}: required signal {signal_id!r} is missing"
            )
        observation_ids.extend(signal["observation_ids"])
    result = list(dict.fromkeys(observation_ids))
    if not result:
        raise ValueError(f"{attribute}: no exact observations support candidate")
    return result


def build_candidates(
    *,
    research_path: Path = RESEARCH,
    prototype_path: Path = PROTOTYPE,
) -> dict[str, Any]:
    bundle = load_earth_research_bundle(research_path)
    prototype = json.loads(prototype_path.read_text(encoding="utf-8"))
    signals = build_signals()
    dimension_scores = build_dimension_evidence_scores()

    countries: dict[str, Any] = {}
    candidate_count = 0

    for code, country in sorted(prototype["countries"].items()):
        anchor = (country.get("anchors") or {}).get(str(ANCHOR_YEAR))
        if anchor is None:
            raise ValueError(f"{code}: prototype lacks {ANCHOR_YEAR} anchor")

        unknown_sources = sorted(
            source_id
            for source_id in anchor["source_ids"]
            if source_id not in bundle.research.sources
        )
        if unknown_sources:
            raise ValueError(
                f"{code}: anchor cites sources absent from canonical FIFA catalogue: "
                f"{unknown_sources}"
            )

        country_signals = signals["countries"][code]
        attribute_candidates: dict[str, Any] = {}

        for attribute in SUPPORTED_ATTRIBUTES:
            observation_ids = _candidate_observation_ids(
                country_signals,
                attribute,
            )
            for observation_id in observation_ids:
                observation = bundle.observations.get(observation_id)
                if observation is None:
                    raise ValueError(
                        f"{code}/{attribute}: unknown observation {observation_id!r}"
                    )
                if observation.source_id != "fifa-big-count-2006":
                    raise ValueError(
                        f"{code}/{attribute}: non-Big-Count observation in 2006 candidate"
                    )

            evidence = RatingEvidence(
                value=anchor["ratings"][attribute],
                method="sourced_estimate",
                confidence=anchor["confidence"],
                source_ids=list(anchor["source_ids"]),
                observation_ids=observation_ids,
                rationale=(
                    anchor["rationale"].strip()
                    + " Candidate provenance migration: the Big Count component is "
                    "now linked to exact normalized observation IDs; contextual "
                    "sources remain separately cited. This does not promote the "
                    "partial 2006 year into canonical CountryRatingHistory."
                ),
                anchor_years=[ANCHOR_YEAR],
            )

            recipe_id = ATTRIBUTE_RECIPE_IDS[attribute]
            evidence_score = dimension_scores["countries"][code][recipe_id][
                "evidence_score"
            ]
            if evidence_score is None:
                raise ValueError(
                    f"{code}/{attribute}: provisional dimension evidence score missing"
                )
            delta = round(float(evidence.value) - float(evidence_score), 1)

            attribute_candidates[attribute] = {
                "rating_evidence": evidence.model_dump(mode="json"),
                "provisional_dimension_evidence_score": evidence_score,
                "prototype_minus_evidence_score_delta": delta,
                "review_required": abs(delta) >= 1.5,
                "promotion_ready": False,
            }
            candidate_count += 1

        countries[code] = {
            "year": ANCHOR_YEAR,
            "candidate_attributes": attribute_candidates,
            "unsupported_attributes_for_this_candidate": [
                "development_quality",
                "competition_quality",
                "elite_support",
                "squash_tradition",
            ],
            "promotion_ready": False,
        }

    return {
        "schema_version": "fifa_partial_rating_anchor_candidates.v1",
        "world_id": "fifa_earth",
        "year": ANCHOR_YEAR,
        "prototype_schema_version": prototype["schema_version"],
        "canonical_research_schema_version": bundle.research.schema_version,
        "country_count": len(countries),
        "candidate_count": candidate_count,
        "supported_attributes": list(SUPPORTED_ATTRIBUTES),
        "promotion_ready": False,
        "countries": countries,
        "limitations": [
            "This is a partial authoring candidate set, not canonical CountryRatingHistory.",
            "Only 2006 popularity/access are migrated because the current normalized Big Count evidence directly calibrates those dimensions in the prototype.",
            "The remaining four attributes are intentionally not copied merely to complete a six-attribute year.",
            "A candidate can be numerically different from the provisional evidence score because the prototype rating also uses contextual evidence.",
            "Promotion requires explicit human review plus a complete six-attribute authored year/history path.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, default=RESEARCH)
    parser.add_argument("--prototype", type=Path, default=PROTOTYPE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_candidates(
        research_path=args.research,
        prototype_path=args.prototype,
    )
    summary = {
        "country_count": result["country_count"],
        "candidate_count": result["candidate_count"],
        "review_required_count": sum(
            candidate["review_required"]
            for country in result["countries"].values()
            for candidate in country["candidate_attributes"].values()
        ),
        "promotion_ready": result["promotion_ready"],
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
