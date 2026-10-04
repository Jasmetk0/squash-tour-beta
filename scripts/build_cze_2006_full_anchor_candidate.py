"""Build the first complete six-attribute FIFA Earth anchor candidate: CZE 2006.

The result is a valid CountryRatingHistory.v2 object with one authored year, but it
is deliberately not inserted into canonical fifa_earth research because 1955-2026
coverage remains incomplete. All evidence is pre- or at-2006; future leakage is
rejected.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.domain.countries.rating_history import (
    CountryRatingHistory,
    RatingEvidence,
    RatingYear,
)
from scripts.build_fifa_2006_anchor_candidates import (
    RESEARCH,
    PROTOTYPE,
    build_candidates as build_partial_candidates,
)
from scripts.curate_cze_uefa_2006_observations import (
    DIRECTORY_DATASET_ID,
    HISTORY_DATASET_ID,
)

COUNTRY_CODE = "CZE"
ANCHOR_YEAR = 2006


def _history_observation(local_id: str) -> str:
    return f"{HISTORY_DATASET_ID}#{local_id}"


def _directory_observation(local_id: str) -> str:
    return f"{DIRECTORY_DATASET_ID}#{local_id}"


ATTRIBUTE_EVIDENCE = {
    "development_quality": {
        "confidence": "medium",
        "source_ids": [
            "uefa-czechia-history",
            "uefa-first-division-clubs-2005-06",
        ],
        "observation_ids": [
            _history_observation("2002-u21-european-champion"),
            _directory_observation("youth-players"),
        ],
        "rationale": (
            "Czechia's 2002 UEFA Under-21 title is direct elite-youth output evidence, "
            "while UEFA's 2005 association directory records 229,457 registered youth "
            "players under 18. Together they support the reviewed 2006 development "
            "estimate, but neither directly measures coaching quality across the whole "
            "country; the numeric rating remains a project estimate."
        ),
    },
    "competition_quality": {
        "confidence": "medium",
        "source_ids": [
            "uefa-czechia-history",
            "uefa-first-division-clubs-2005-06",
        ],
        "observation_ids": [
            _history_observation("1996-euro-runner-up"),
            _history_observation("2004-euro-semi-final"),
            _directory_observation("top-division-clubs"),
        ],
        "rationale": (
            "Repeated senior international performance (EURO 1996 runners-up and "
            "EURO 2004 semi-finalists) plus a documented 16-club 2004/05 domestic "
            "top division provide direct competition-structure/outcome context for "
            "the reviewed 2006 competition estimate."
        ),
    },
    "elite_support": {
        "confidence": "low",
        "source_ids": [
            "uefa-first-division-clubs-2005-06",
        ],
        "observation_ids": [
            _directory_observation("professional-non-amateur-players"),
            _directory_observation("clubs"),
            _directory_observation("teams"),
            _directory_observation("top-division-clubs"),
        ],
        "rationale": (
            "UEFA's 2005 association snapshot records 1,576 non-amateur professional "
            "players, 3,955 clubs, 15,378 teams and a 16-club top division. These are "
            "strong system-scale proxies for a professional support environment, but "
            "they do not directly measure funding, travel, medicine, sport science or "
            "high-performance services, so confidence is deliberately low."
        ),
    },
    "squash_tradition": {
        "confidence": "medium",
        "source_ids": [
            "uefa-czechia-history",
        ],
        "observation_ids": [
            _history_observation("1892-first-prague-club"),
            _history_observation("1901-czech-football-association"),
            _history_observation("1954-uefa-founder-member"),
            _history_observation("1993-independent-czech-era"),
        ],
        "rationale": (
            "UEFA's Czech association timeline documents club roots in 1892, the "
            "Czech Football Association in 1901, the 1954 UEFA founder-member "
            "milestone and explicit institutional continuity into the independent "
            "Czech era from 1993. The rating reflects long-run embedded football "
            "tradition while keeping predecessor context explicit."
        ),
    },
}


def _historical_context(prototype_country: dict[str, Any], year: int) -> tuple[str, str]:
    periods = prototype_country.get("historical_periods")
    if periods:
        for period in periods:
            if int(period["from"]) <= year <= int(period["to"]):
                return (
                    str(period["historical_entity"]),
                    str(period["territory_mapping_note"]),
                )
        raise ValueError(f"{COUNTRY_CODE}: no historical context for {year}")
    return (
        str(prototype_country["historical_entity"]),
        str(prototype_country["territory_mapping_note"]),
    )


def build_candidate(
    *,
    research_path: Path = RESEARCH,
    prototype_path: Path = PROTOTYPE,
) -> dict[str, Any]:
    bundle = load_earth_research_bundle(research_path)
    prototype = json.loads(prototype_path.read_text(encoding="utf-8"))
    prototype_country = prototype["countries"][COUNTRY_CODE]
    anchor = prototype_country["anchors"][str(ANCHOR_YEAR)]

    partial = build_partial_candidates(
        research_path=research_path,
        prototype_path=prototype_path,
    )["countries"][COUNTRY_CODE]["candidate_attributes"]

    ratings: dict[str, RatingEvidence] = {
        "squash_popularity": RatingEvidence.model_validate(
            partial["squash_popularity"]["rating_evidence"]
        ),
        "squash_access": RatingEvidence.model_validate(
            partial["squash_access"]["rating_evidence"]
        ),
    }

    for attribute, config in ATTRIBUTE_EVIDENCE.items():
        ratings[attribute] = RatingEvidence(
            value=anchor["ratings"][attribute],
            method="sourced_estimate",
            confidence=config["confidence"],
            source_ids=list(config["source_ids"]),
            observation_ids=list(config["observation_ids"]),
            rationale=config["rationale"],
            anchor_years=[ANCHOR_YEAR],
        )

    for attribute, evidence in ratings.items():
        unknown_sources = sorted(
            source_id
            for source_id in evidence.source_ids
            if source_id not in bundle.research.sources
        )
        if unknown_sources:
            raise ValueError(
                f"{COUNTRY_CODE}/{attribute}: unknown source IDs {unknown_sources}"
            )
        for observation_id in evidence.observation_ids:
            observation = bundle.observations.get(observation_id)
            if observation is None:
                raise ValueError(
                    f"{COUNTRY_CODE}/{attribute}: missing observation {observation_id!r}"
                )
            if observation.source_id not in evidence.source_ids:
                raise ValueError(
                    f"{COUNTRY_CODE}/{attribute}: observation source "
                    f"{observation.source_id!r} not cited by rating"
                )
            if observation.observation_year is not None and observation.observation_year > ANCHOR_YEAR:
                raise ValueError(
                    f"{COUNTRY_CODE}/{attribute}: future-leaking observation "
                    f"{observation_id!r} from {observation.observation_year}"
                )
            if observation.earth_country_code not in {None, COUNTRY_CODE}:
                raise ValueError(
                    f"{COUNTRY_CODE}/{attribute}: observation targets "
                    f"{observation.earth_country_code!r}"
                )

    historical_entity, territory_mapping_note = _historical_context(
        prototype_country,
        ANCHOR_YEAR,
    )
    year = RatingYear(
        historical_entity=historical_entity,
        territory_mapping_note=territory_mapping_note,
        ratings=ratings,
    )
    history = CountryRatingHistory(
        reference_year=ANCHOR_YEAR,
        data_cutoff=bundle.research.data_cutoff,
        years={ANCHOR_YEAR: year},
    )

    return {
        "schema_version": "fifa_complete_anchor_candidate.v1",
        "world_id": "fifa_earth",
        "country_code": COUNTRY_CODE,
        "year": ANCHOR_YEAR,
        "candidate_history": history.model_dump(mode="json"),
        "candidate_attribute_count": len(ratings),
        "full_year_complete": True,
        "history_coverage_complete": False,
        "missing_history_year_count": len(history.missing_earth_years),
        "missing_history_years": history.missing_earth_years,
        "promotion_ready": False,
        "limitations": [
            "The 2006 year is complete across all six attributes, but the 1955-2026 history is not.",
            "Development/competition/elite-support/tradition values remain reviewed project estimates linked to exact factual observations.",
            "Elite-support evidence is indirect system-scale evidence and therefore carries low confidence.",
            "No observation after 2006 is allowed into this candidate.",
            "Canonical fifa_earth country histories remain unchanged.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, default=RESEARCH)
    parser.add_argument("--prototype", type=Path, default=PROTOTYPE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_candidate(
        research_path=args.research,
        prototype_path=args.prototype,
    )
    print(
        json.dumps(
            {
                "country_code": result["country_code"],
                "year": result["year"],
                "candidate_attribute_count": result["candidate_attribute_count"],
                "full_year_complete": result["full_year_complete"],
                "missing_history_year_count": result["missing_history_year_count"],
                "promotion_ready": result["promotion_ready"],
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
