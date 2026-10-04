from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.application.earth_research_observations import (
    EarthObservationDataset,
    observation_dataset_sha256,
)
from scripts.normalize_fifa_structural_events import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RESEARCH,
    DEFAULT_SEED,
    build_datasets,
    build_manifests,
)


HELDOUT_SEED = Path(
    "config/earth_research/observations/structural/"
    "fifa_structural_events_heldout_v1.json"
)


def test_structural_event_datasets_are_reproducible_and_registered() -> None:
    datasets = build_datasets()
    manifests = build_manifests(datasets)
    research = json.loads(DEFAULT_RESEARCH.read_text(encoding="utf-8"))

    assert len(datasets) == 25
    assert sum(len(dataset.observations) for dataset in datasets.values()) == 43

    for dataset_id, dataset in datasets.items():
        manifest = manifests[dataset_id]
        assert research["observation_datasets"][dataset_id] == manifest.model_dump(
            mode="json"
        )

        checked_in = EarthObservationDataset.model_validate_json(
            (Path("config/earth_research") / manifest.relative_path).read_text(
                encoding="utf-8"
            )
        )
        assert checked_in == dataset
        assert observation_dataset_sha256(checked_in) == manifest.sha256
        assert all(
            observation.collection_method == "official_narrative"
            for observation in checked_in.observations
        )
        assert all(
            observation.measurement_type == "football_structural_event"
            for observation in checked_in.observations
        )
        assert all(
            observation.numeric_value is None
            and observation.text_value
            and observation.unit == "event"
            for observation in checked_in.observations
        )


def test_structural_seed_preserves_pre_1955_history_without_rewriting_event_years() -> None:
    datasets = build_datasets()
    observations = [
        observation
        for dataset in datasets.values()
        for observation in dataset.observations
    ]

    pre_game = [
        observation
        for observation in observations
        if "pre_game_start_history" in observation.quality_flags
    ]
    assert pre_game
    assert all(observation.observation_year < 1955 for observation in pre_game)

    by_id = {observation.observation_id: observation for observation in observations}
    assert any(
        observation.source_entity == "Japan Football Association"
        and observation.observation_year == 1921
        for observation in observations
    )
    assert any(
        observation.source_entity == "Faroe Islands football"
        and observation.observation_year == 1892
        for observation in observations
    )
    assert not any(
        observation.observation_year == 1955
        and "pre_game_start_history" in observation.quality_flags
        for observation in observations
    )
    assert len(by_id) == 43


def test_morocco_academy_timing_conflict_remains_two_independent_observations() -> None:
    datasets = build_datasets()
    conflict = [
        observation
        for dataset in datasets.values()
        for observation in dataset.observations
        if "conflict_group:mar-mohammed-vi-academy-timing"
        in observation.quality_flags
    ]

    assert len(conflict) == 2
    assert {observation.observation_year for observation in conflict} == {2009, 2019}
    assert {
        observation.source_id for observation in conflict
    } == {
        "fifa-morocco-academy-2009",
        "fifa-morocco-development",
    }
    assert all(
        "source_timing_conflict" in observation.quality_flags
        for observation in conflict
    )


def test_structural_dimension_tags_are_relevance_only_not_rating_values() -> None:
    datasets = build_datasets()
    observations = [
        observation
        for dataset in datasets.values()
        for observation in dataset.observations
    ]

    assert any(
        "supports_development_quality" in observation.quality_flags
        for observation in observations
    )
    assert any(
        "supports_squash_tradition" in observation.quality_flags
        for observation in observations
    )
    assert all(
        observation.numeric_value is None for observation in observations
    )
    assert all(
        "rating" not in observation.comparability_group
        for observation in observations
    )


def test_fifa_research_bundle_includes_structural_events_with_existing_sources() -> None:
    bundle = load_earth_research_bundle(DEFAULT_RESEARCH)

    assert len(bundle.datasets) == 40
    assert len(bundle.observations) == 1355

    structural = [
        observation
        for observation in bundle.observations.values()
        if observation.measurement_type == "football_structural_event"
    ]
    assert len(structural) == 57
    assert all(
        observation.source_id in bundle.research.sources
        for observation in structural
    )
    assert all(
        observation.earth_country_code is not None
        and observation.territory_mapping_method
        == "explicit_reviewed_event_to_earth"
        for observation in structural
    )



def test_heldout_structural_event_datasets_are_reproducible_and_separate() -> None:
    datasets = build_datasets(seed_path=HELDOUT_SEED)
    manifests = build_manifests(datasets)
    research = json.loads(DEFAULT_RESEARCH.read_text(encoding="utf-8"))

    assert len(datasets) == 7
    assert sum(len(dataset.observations) for dataset in datasets.values()) == 14

    for dataset_id, dataset in datasets.items():
        manifest = manifests[dataset_id]
        assert research["observation_datasets"][dataset_id] == manifest.model_dump(
            mode="json"
        )
        checked_in = EarthObservationDataset.model_validate_json(
            (Path("config/earth_research") / manifest.relative_path).read_text(
                encoding="utf-8"
            )
        )
        assert checked_in == dataset
        assert observation_dataset_sha256(checked_in) == manifest.sha256
        assert "held-out validation set" in checked_in.scope
        assert all(
            "held_out_validation_country" in observation.quality_flags
            for observation in checked_in.observations
        )


def test_review_and_heldout_structural_seeds_have_independent_input_hashes() -> None:
    review = build_datasets(seed_path=DEFAULT_SEED)
    heldout = build_datasets(seed_path=HELDOUT_SEED)

    review_hashes = {dataset.input_artifact_sha256 for dataset in review.values()}
    heldout_hashes = {dataset.input_artifact_sha256 for dataset in heldout.values()}

    assert len(review_hashes) == 1
    assert len(heldout_hashes) == 1
    assert review_hashes.isdisjoint(heldout_hashes)
