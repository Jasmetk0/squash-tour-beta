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
from scripts.normalize_fifa_professional_2023 import (
    DEFAULT_OUTPUT_DIR,
    FIELD_SPECS,
    build_datasets,
    build_manifests,
)


RESEARCH = Path("config/earth_research/fifa_earth.json")
RAW = Path("config/earth_research/observations/fifa_professional_2023.json")


def test_checked_in_fifa_professional_2023_v2_is_reproducible() -> None:
    datasets = build_datasets()
    manifests = build_manifests(datasets, output_dir=DEFAULT_OUTPUT_DIR)
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))

    assert {
        dataset_id: len(dataset.observations)
        for dataset_id, dataset in datasets.items()
    } == {
        "fifa-professional-2023-players-v2": 112,
        "fifa-professional-2023-clubs-v2": 135,
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


def test_professional_2023_preserves_source_sums_and_missing_values() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    datasets = build_datasets()

    player_sum = sum(
        int(observation.numeric_value)
        for observation in datasets[
            "fifa-professional-2023-players-v2"
        ].observations
    )
    club_sum = sum(
        int(observation.numeric_value)
        for observation in datasets[
            "fifa-professional-2023-clubs-v2"
        ].observations
    )

    assert player_sum == raw["extracted_national_sums"]["professional_players"] == 129_388
    assert club_sum == raw["extracted_national_sums"]["professional_clubs"] == 3_997
    assert player_sum != raw["published_global_totals"]["professional_players"]
    assert club_sum != raw["published_global_totals"]["professional_clubs"]

    players = {
        (observation.source_entity, observation.source_page): observation
        for observation in datasets[
            "fifa-professional-2023-players-v2"
        ].observations
    }
    assert ("AFGHANISTAN", 18) not in players
    assert players[("AUSTRALIA", 19)].numeric_value == 1_597
    assert players[("AUSTRALIA", 19)].sex_scope == "male"
    assert players[("AUSTRALIA", 19)].earth_country_code is None
    assert players[("AUSTRALIA", 19)].is_direct_observation is True
    assert players[("AUSTRALIA", 19)].is_statistically_modelled is False


def test_kuwait_kyrgyzstan_source_anomaly_remains_two_page_specific_facts() -> None:
    datasets = build_datasets()

    players = {
        (observation.source_entity, observation.source_page): observation
        for observation in datasets[
            "fifa-professional-2023-players-v2"
        ].observations
    }
    clubs = {
        (observation.source_entity, observation.source_page): observation
        for observation in datasets[
            "fifa-professional-2023-clubs-v2"
        ].observations
    }

    kuwait_37 = players[("KUWAIT", 37)]
    anomalous_38 = players[("KUWAIT", 38)]

    assert kuwait_37.numeric_value == 451
    assert clubs[("KUWAIT", 37)].numeric_value == 25
    assert "source_identity_anomaly" not in kuwait_37.quality_flags

    assert anomalous_38.numeric_value == 275
    assert clubs[("KUWAIT", 38)].numeric_value == 10
    assert anomalous_38.observation_id.endswith("#kuwait-p38")
    assert "source_identity_anomaly" in anomalous_38.quality_flags
    assert "do_not_auto_map_to_earth" in anomalous_38.quality_flags
    assert anomalous_38.earth_country_code is None
    assert "Kyrgyzstan" in anomalous_38.definition_notes


def test_fifa_bundle_contains_big_count_professional_and_structural_evidence() -> None:
    bundle = load_earth_research_bundle(RESEARCH)

    expected_2023 = {spec["dataset_id"] for spec in FIELD_SPECS.values()}
    assert expected_2023.issubset(bundle.datasets)
    assert len(bundle.datasets) == 65
    assert len(bundle.observations) == 1_437

    for dataset_id in expected_2023:
        assert (
            bundle.datasets[dataset_id].source_document_sha256
            == "fb15135da80e3cf395cadf1b2fcd2762f52268292cebc5e86957115b260c0e71"
        )
