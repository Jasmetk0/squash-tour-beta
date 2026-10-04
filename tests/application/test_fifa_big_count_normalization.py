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
from scripts.normalize_fifa_big_count_2006 import (
    DEFAULT_OUTPUT_DIR,
    FIELD_SPECS,
    build_datasets,
    build_manifests,
)


RESEARCH = Path("config/earth_research/fifa_earth.json")


def test_checked_in_big_count_v2_is_reproducible_and_registered() -> None:
    datasets = build_datasets()
    manifests = build_manifests(datasets, output_dir=DEFAULT_OUTPUT_DIR)
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))

    assert len(datasets) == 5
    assert sum(len(dataset.observations) for dataset in datasets.values()) == 1038
    assert {
        dataset_id: len(dataset.observations)
        for dataset_id, dataset in datasets.items()
    } == {
        "fifa-big-count-2006-all-players-v2": 208,
        "fifa-big-count-2006-registered-v2": 208,
        "fifa-big-count-2006-unregistered-v2": 208,
        "fifa-big-count-2006-clubs-v2": 206,
        "fifa-big-count-2006-officials-v2": 208,
    }

    for dataset_id, manifest in manifests.items():
        assert research["observation_datasets"][dataset_id] == manifest.model_dump(
            mode="json"
        )
        checked_in = EarthObservationDataset.model_validate_json(
            (Path("config/earth_research") / manifest.relative_path).read_text(
                encoding="utf-8"
            )
        )
        assert checked_in == datasets[dataset_id]
        assert observation_dataset_sha256(checked_in) == manifest.sha256


def test_big_count_v2_preserves_missing_cells_and_source_semantics() -> None:
    datasets = build_datasets()

    all_players = {
        observation.source_entity: observation
        for observation in datasets[
            "fifa-big-count-2006-all-players-v2"
        ].observations
    }
    registered = {
        observation.source_entity: observation
        for observation in datasets[
            "fifa-big-count-2006-registered-v2"
        ].observations
    }
    clubs = {
        observation.source_entity: observation
        for observation in datasets[
            "fifa-big-count-2006-clubs-v2"
        ].observations
    }

    assert all_players["USA"].numeric_value == 24_472_778
    assert all_players["USA"].sex_scope == "mixed"
    assert all_players["USA"].earth_country_code is None
    assert all_players["USA"].is_direct_observation is None
    assert all_players["USA"].is_statistically_modelled is None
    assert "includes_unregistered_and_casual_participation" in all_players[
        "USA"
    ].quality_flags

    assert registered["Germany"].numeric_value == 6_308_946
    assert "registration_definition_varies_by_association" in registered[
        "Germany"
    ].quality_flags

    assert "British Virgin Islands" not in clubs
    assert "Montserrat" not in clubs
    assert clubs["Brazil"].numeric_value == 29_208


def test_fifa_research_bundle_verifies_all_big_count_manifests() -> None:
    bundle = load_earth_research_bundle(RESEARCH)

    assert set(bundle.datasets) >= {
        spec["dataset_id"] for spec in FIELD_SPECS.values()
    }
    assert len(bundle.observations) == 1038


def test_bundle_loader_rejects_semantic_hash_mismatch(tmp_path: Path) -> None:
    source_research = json.loads(RESEARCH.read_text(encoding="utf-8"))
    first_id = "fifa-big-count-2006-all-players-v2"
    manifest = source_research["observation_datasets"][first_id]

    research_dir = tmp_path / "research"
    dataset_path = research_dir / manifest["relative_path"]
    dataset_path.parent.mkdir(parents=True)
    original_dataset = json.loads(
        (
            Path("config/earth_research")
            / manifest["relative_path"]
        ).read_text(encoding="utf-8")
    )
    original_dataset["observations"][0]["numeric_value"] += 1
    dataset_path.write_text(
        json.dumps(original_dataset, ensure_ascii=False),
        encoding="utf-8",
    )

    # Keep only the one copied dataset so the test is self-contained.
    source_research["observation_datasets"] = {first_id: manifest}
    (research_dir / "fifa_earth.json").write_text(
        json.dumps(source_research),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="semantic SHA-256 mismatch"):
        load_earth_research_bundle(research_dir / "fifa_earth.json")
