"""Normalize the curated FIFA men's 2023 year-end ranking validation snapshot.

This source family is outcome validation only. It must not be used to fit the
professional-count evidence model or to stand in for domestic competition quality
by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from beta_engine.application.earth_research_observations import (
    EarthObservation,
    EarthObservationDataset,
    EarthObservationDatasetManifest,
    observation_dataset_sha256,
)

SOURCE_ID = "fifa-mens-ranking-year-end-2023-review-heldout"
DATASET_ID = "fifa-mens-year-end-ranking-2023-review-heldout-v1"
SOURCE_URL = (
    "https://inside.fifa.com/fifa-rankings/world-ranking/news/"
    "argentina-peerless-panama-buoyant"
)
DEFAULT_SEED = Path(
    "config/earth_research/seeds/"
    "fifa_mens_year_end_ranking_2023_review_heldout.json"
)
DEFAULT_OUTPUT = Path(
    "config/earth_research/observations/normalized/"
    "fifa_mens_year_end_ranking_2023_review_heldout_v1.json"
)


def _input_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_dataset(*, seed_path: Path = DEFAULT_SEED) -> EarthObservationDataset:
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    if seed.get("schema_version") != "fifa_mens_year_end_ranking_seed.v1":
        raise ValueError("unsupported FIFA year-end ranking seed schema")
    if seed.get("ranking_year") != 2023 or seed.get("ranking_date") != "2023-12-21":
        raise ValueError("ranking seed must represent the 21 December 2023 year-end ranking")

    observations: list[EarthObservation] = []
    seen_codes: set[str] = set()
    for row in seed["countries"]:
        code = row["earth_country_code"]
        if code in seen_codes:
            raise ValueError(f"duplicate Earth country in ranking seed: {code}")
        seen_codes.add(code)

        role = row["validation_role"]
        if role not in {"review", "held_out_validation"}:
            raise ValueError(f"{code}: invalid validation role {role!r}")

        final_rank = row["final_rank"]
        best_rank = row["best_rank"]
        worst_rank = row["worst_rank"]
        if not (
            isinstance(final_rank, int)
            and isinstance(best_rank, int)
            and isinstance(worst_rank, int)
            and 1 <= best_rank <= final_rank <= worst_rank
        ):
            raise ValueError(f"{code}: invalid 2023 ranking summary")

        flags = [
            "supports_competition_quality",
            "outcome_validation_only",
            "senior_national_team_outcome",
            "fifa_sum_ranking_model",
            "not_domestic_competition_quality_directly",
            (
                "held_out_validation_country"
                if role == "held_out_validation"
                else "review_country"
            ),
        ]
        source_url = row["source_url"]
        observations.append(
            EarthObservation(
                observation_id=f"{DATASET_ID}#{code.lower()}",
                source_id=SOURCE_ID,
                source_entity=row["country_name"],
                earth_country_code=code,
                historical_entity=row["country_name"],
                observation_year=2023,
                measurement_type="fifa_mens_year_end_world_rank",
                sex_scope="male",
                age_scope="senior",
                competition_scope="mens_senior_national_team",
                numeric_value=final_rank,
                unit="rank_1_is_best",
                collection_method="statistically_processed",
                coverage_scope="association",
                comparability_group="fifa-mens-world-ranking-year-end-2023",
                cross_country_comparable=True,
                is_direct_observation=True,
                is_statistically_modelled=True,
                territory_mapping_method="explicit_reviewed_outcome_to_earth",
                source_locator=(
                    f"{source_url}; Year on year summary; 2023 Final rank="
                    f"{final_rank}, Best rank={best_rank}, Worst rank={worst_rank}"
                ),
                definition_notes=(
                    "FIFA/Coca-Cola Men's World Ranking final rank for 2023. "
                    "The SUM model has been used since August 2018. This is "
                    "independent senior national-team outcome evidence for "
                    "competition-quality validation; it is not a direct domestic "
                    "league-quality measure and must not fit the V2 professional "
                    "ecosystem recipe."
                ),
                quality_flags=flags,
            )
        )

    if len(observations) != 13:
        raise ValueError("ranking validation snapshot must contain exactly 13 countries")

    return EarthObservationDataset(
        dataset_id=DATASET_ID,
        source_id=SOURCE_ID,
        source_url=SOURCE_URL,
        source_document_sha256=None,
        input_artifact_sha256=_input_sha256(seed_path),
        generated_by="scripts/normalize_fifa_mens_ranking_2023.py",
        scope=(
            "Official FIFA men's 2023 year-end ranking outcomes for the nine-country "
            "review set and four held-out validation countries."
        ),
        limitations=(
            "Senior national-team ranking is outcome evidence, not a direct measure "
            "of domestic competition depth. The subset is intentionally restricted "
            "to review/held-out calibration countries and must not be used to fit "
            "the professional-count V2 model."
        ),
        observations=sorted(observations, key=lambda item: item.observation_id),
    )


def build_manifest(
    dataset: EarthObservationDataset,
    *,
    relative_path: str,
) -> EarthObservationDatasetManifest:
    return EarthObservationDatasetManifest(
        dataset_id=dataset.dataset_id,
        source_id=dataset.source_id,
        relative_path=relative_path,
        sha256=observation_dataset_sha256(dataset),
        record_count=len(dataset.observations),
        source_document_sha256=dataset.source_document_sha256,
        input_artifact_sha256=dataset.input_artifact_sha256,
        generated_by=dataset.generated_by,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args()

    dataset = build_dataset(seed_path=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dataset.model_dump(mode="json"), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    relative_path = args.output.relative_to(Path("config/earth_research"))
    manifest = build_manifest(dataset, relative_path=relative_path.as_posix())

    print(
        json.dumps(
            {
                "dataset_id": dataset.dataset_id,
                "record_count": len(dataset.observations),
                "sha256": manifest.sha256,
                "input_artifact_sha256": dataset.input_artifact_sha256,
            },
            indent=2,
        )
    )
    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
