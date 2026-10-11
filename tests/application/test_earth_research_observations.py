from __future__ import annotations

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_research_observations import (
    EarthObservation,
    EarthObservationDataset,
    EarthObservationDatasetManifest,
)


def observation(**overrides):
    payload = dict(
        observation_id="synthetic#AAA-active-players-2006",
        source_id="source",
        source_entity="AAA association",
        earth_country_code="AAA",
        observation_year=2006,
        measurement_type="active_players",
        sex_scope="male",
        numeric_value=1234,
        unit="players",
        collection_method="survey",
        coverage_scope="association",
        comparability_group="active-players-male",
        cross_country_comparable=True,
        is_direct_observation=True,
        definition_notes="Synthetic observation for contract testing.",
    )
    payload.update(overrides)
    return EarthObservation.model_validate(payload)


def dataset(**overrides):
    payload = dict(
        dataset_id="synthetic",
        source_id="source",
        source_url="https://example.com/source",
        generated_by="tests",
        scope="Synthetic observations.",
        limitations="Not real evidence.",
        observations=[observation().model_dump()],
    )
    payload.update(overrides)
    return EarthObservationDataset.model_validate(payload)


def test_observation_requires_exactly_one_value_representation():
    with pytest.raises(ValidationError):
        observation(numeric_value=None)
    with pytest.raises(ValidationError):
        observation(text_value="event")
    event = observation(
        observation_id="synthetic#AAA-event-2006",
        numeric_value=None,
        text_value="Professional league launched",
        unit="event",
        measurement_type="structural_event",
        sex_scope="not_applicable",
    )
    assert event.text_value == "Professional league launched"


def test_observation_validates_periods_territory_and_codes():
    with pytest.raises(ValidationError):
        observation(observation_year=None, period_start_year=2010)
    with pytest.raises(ValidationError):
        observation(observation_year=None, period_start_year=2011, period_end_year=2010)
    with pytest.raises(ValidationError):
        observation(earth_country_code="AaA")
    with pytest.raises(ValidationError):
        observation(territory_weight=0.5)
    mapped = observation(territory_mapping_method="population share", territory_weight=0.5)
    assert mapped.territory_weight == 0.5


def test_dataset_requires_namespaced_unique_observations_and_matching_source():
    with pytest.raises(ValidationError):
        dataset(observations=[observation(observation_id="other#row").model_dump()])
    with pytest.raises(ValidationError):
        dataset(observations=[observation().model_dump(), observation().model_dump()])
    with pytest.raises(ValidationError):
        dataset(observations=[observation(source_id="other").model_dump()])


def test_manifest_rejects_unsafe_paths_and_invalid_hashes():
    base = dict(
        dataset_id="synthetic",
        source_id="source",
        relative_path="observations/synthetic.json",
        sha256="a" * 64,
        record_count=1,
        generated_by="tests",
    )
    manifest = EarthObservationDatasetManifest.model_validate(base)
    assert manifest.record_count == 1
    with pytest.raises(ValidationError):
        EarthObservationDatasetManifest.model_validate({**base, "relative_path": "../escape.json"})
    with pytest.raises(ValidationError):
        EarthObservationDatasetManifest.model_validate({**base, "sha256": "not-a-hash"})
