from __future__ import annotations

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_research_identity import (
    EarthObservationIdentityResolution,
    EarthObservationIdentityResolutionSet,
    identity_resolution_sha256,
)
from scripts.build_fifa_observation_identity_resolutions import (
    BIG_COUNT_DATASET_IDS,
    PROFESSIONAL_DATASET_IDS,
    build_resolution_sets,
)


def test_fifa_identity_resolution_sets_cover_every_canonical_observation_once() -> None:
    sets = build_resolution_sets()

    assert set(sets) == {
        "fifa-big-count-2006-identity-v1",
        "fifa-professional-2023-identity-v1",
    }

    big_count = sets["fifa-big-count-2006-identity-v1"]
    professional = sets["fifa-professional-2023-identity-v1"]

    assert len(big_count.resolutions) == 1038
    assert len(professional.resolutions) == 247

    observation_ids = [
        resolution.observation_id
        for resolution_set in sets.values()
        for resolution in resolution_set.resolutions
    ]
    assert len(observation_ids) == 1285
    assert len(observation_ids) == len(set(observation_ids))

    assert set(big_count.input_dataset_sha256s) == set(BIG_COUNT_DATASET_IDS)
    assert set(professional.input_dataset_sha256s) == set(PROFESSIONAL_DATASET_IDS)

    # Semantic hashing must be deterministic for a fully validated resolution set.
    assert identity_resolution_sha256(big_count) == identity_resolution_sha256(
        EarthObservationIdentityResolutionSet.model_validate(
            big_count.model_dump(mode="json")
        )
    )


def test_big_count_identity_resolution_counts_and_manual_boundaries() -> None:
    resolution_set = build_resolution_sets()["fifa-big-count-2006-identity-v1"]

    status_counts: dict[str, int] = {}
    for item in resolution_set.resolutions:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1

    assert status_counts == {
        "direct": 998,
        "aggregate_member": 20,
        "manual_review": 20,
    }

    manual_entities = {
        item.source_entity
        for item in resolution_set.resolutions
        if item.status == "manual_review"
    }
    assert manual_entities == {
        "Netherlands Antilles",
        "Curacao",
        "Serbia",
        "Sudan",
    }

    uk = [
        item
        for item in resolution_set.resolutions
        if item.status == "aggregate_member"
    ]
    assert {item.source_entity for item in uk} == {
        "England",
        "Scotland",
        "Wales",
        "Northern Ireland",
    }
    assert {item.earth_country_code for item in uk} == {"GBR"}

    czech = [
        item
        for item in resolution_set.resolutions
        if item.source_entity == "Czech Republic"
    ]
    assert len(czech) == 5
    assert {item.status for item in czech} == {"direct"}
    assert {item.earth_country_code for item in czech} == {"CZE"}


def test_professional_identity_resolution_is_page_aware() -> None:
    resolution_set = build_resolution_sets()[
        "fifa-professional-2023-identity-v1"
    ]

    status_counts: dict[str, int] = {}
    for item in resolution_set.resolutions:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1

    assert status_counts == {
        "direct": 239,
        "aggregate_member": 6,
        "manual_review": 2,
    }

    page_37 = [
        item
        for item in resolution_set.resolutions
        if item.source_entity == "KUWAIT" and item.source_page == 37
    ]
    page_38 = [
        item
        for item in resolution_set.resolutions
        if item.source_entity == "KUWAIT" and item.source_page == 38
    ]

    assert len(page_37) == 2
    assert {item.status for item in page_37} == {"direct"}
    assert {item.earth_country_code for item in page_37} == {"KWT"}

    assert len(page_38) == 2
    assert {item.status for item in page_38} == {"manual_review"}
    assert {item.earth_country_code for item in page_38} == {None}
    assert {tuple(item.candidate_earth_codes) for item in page_38} == {("KGZ",)}


def test_identity_contract_fails_closed_on_invalid_resolution_shapes() -> None:
    base = dict(
        observation_id="dataset#row",
        source_id="source",
        source_entity="Source association",
        status="direct",
        method="explicit_override",
        confidence="high",
        earth_country_code="CZE",
        candidate_earth_codes=[],
        reason="Reviewed mapping.",
    )

    EarthObservationIdentityResolution.model_validate(base)

    with pytest.raises(ValidationError):
        EarthObservationIdentityResolution.model_validate(
            {**base, "earth_country_code": None}
        )

    with pytest.raises(ValidationError):
        EarthObservationIdentityResolution.model_validate(
            {
                **base,
                "status": "manual_review",
                "method": "manual_review",
                "earth_country_code": "CZE",
            }
        )

    with pytest.raises(ValidationError):
        EarthObservationIdentityResolution.model_validate(
            {**base, "candidate_earth_codes": ["cz"]}
        )
