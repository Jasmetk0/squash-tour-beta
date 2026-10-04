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
from scripts.curate_cze_uefa_2006_observations import (
    DEFAULT_OUTPUT_DIR,
    DIRECTORY_DATASET_ID,
    HISTORY_DATASET_ID,
    build_datasets,
    build_manifests,
)


RESEARCH = Path("config/earth_research/fifa_earth.json")


def test_curated_cze_uefa_datasets_are_reproducible_and_registered() -> None:
    datasets = build_datasets()
    manifests = build_manifests(datasets, output_dir=DEFAULT_OUTPUT_DIR)
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))

    assert {dataset_id: len(dataset.observations) for dataset_id, dataset in datasets.items()} == {
        HISTORY_DATASET_ID: 7,
        DIRECTORY_DATASET_ID: 8,
    }

    for dataset_id, manifest in manifests.items():
        assert research["observation_datasets"][dataset_id] == manifest.model_dump(mode="json")
        checked_in = EarthObservationDataset.model_validate_json(
            (Path("config/earth_research") / manifest.relative_path).read_text(encoding="utf-8")
        )
        assert checked_in == datasets[dataset_id]
        assert observation_dataset_sha256(checked_in) == manifest.sha256


def test_cze_history_events_preserve_only_pre_2006_facts_needed_for_anchor_review() -> None:
    history = build_datasets()[HISTORY_DATASET_ID]
    by_id = {observation.observation_id.rsplit("#", 1)[1]: observation for observation in history.observations}

    assert by_id["1892-first-prague-club"].observation_year == 1892
    assert by_id["1901-czech-football-association"].observation_year == 1901
    assert by_id["1954-uefa-founder-member"].observation_year == 1954
    assert by_id["1993-independent-czech-era"].observation_year == 1993
    assert by_id["1996-euro-runner-up"].observation_year == 1996
    assert by_id["2002-u21-european-champion"].observation_year == 2002
    assert by_id["2004-euro-semi-final"].observation_year == 2004
    assert max(observation.observation_year for observation in history.observations) <= 2004
    assert all(observation.earth_country_code == "CZE" for observation in history.observations)


def test_cze_2005_directory_snapshot_preserves_published_counts_and_date() -> None:
    directory = build_datasets()[DIRECTORY_DATASET_ID]
    by_type = {observation.measurement_type: observation for observation in directory.observations}

    assert by_type["professional_non_amateur_players_reported"].numeric_value == 1_576
    assert by_type["adult_amateur_players_reported"].numeric_value == 377_244
    assert by_type["youth_players_under_18_reported"].numeric_value == 229_457
    assert by_type["clubs_reported"].numeric_value == 3_955
    assert by_type["teams_reported"].numeric_value == 15_378
    assert by_type["male_referees_reported"].numeric_value == 3_837
    assert by_type["female_referees_reported"].numeric_value == 51
    assert by_type["top_division_clubs_reported"].numeric_value == 16

    assert all(observation.observation_year == 2005 for observation in directory.observations)
    assert all(observation.source_page == 36 for observation in directory.observations)
    assert all(
        "publication_updated_2005-07-20" in observation.quality_flags
        for observation in directory.observations
    )


def test_research_bundle_loads_context_without_expanding_fifa_identity_partition() -> None:
    bundle = load_earth_research_bundle(RESEARCH)

    assert HISTORY_DATASET_ID in bundle.datasets
    assert DIRECTORY_DATASET_ID in bundle.datasets
    assert len(bundle.observations) == 1_300
