from pathlib import Path

import pytest
from pydantic import ValidationError

from beta_engine.api.country_v1_schemas import WorldPackageCountryV1UpdateRequest
from beta_engine.application.world_package_countries_service import (
    WorldPackageCountryCreate,
    WorldPackageCountryUpdate,
)
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore


BASE_UPDATE = {
    "name": "Exampleland",
    "notes": None,
    "area_km2": 123_456,
    "region": "EUROPE",
    "travel_region": "EUROPE",
    "court_count": 100,
    "squash_popularity": 3.25,
    "squash_access": 2.5,
    "development_quality": 4.75,
    "competition_quality": 2.5,
    "elite_support": 3.5,
    "squash_tradition": 4.25,
}


def test_application_and_api_contracts_accept_fractional_country_v1_ratings() -> None:
    application_update = WorldPackageCountryUpdate.model_validate(BASE_UPDATE)
    api_update = WorldPackageCountryV1UpdateRequest.model_validate(BASE_UPDATE)
    create = WorldPackageCountryCreate.model_validate(
        {
            **BASE_UPDATE,
            "code": "EXP",
            "population_by_year": {2020: 1_000_000},
            "expected_package_fingerprint": "fingerprint",
        }
    )

    assert application_update.competition_quality == 2.5
    assert api_update.squash_access == 2.5
    assert create.development_quality == 4.75


def test_decimal_country_v1_contracts_keep_1_to_5_bounds() -> None:
    with pytest.raises(ValidationError):
        WorldPackageCountryUpdate.model_validate({**BASE_UPDATE, "competition_quality": 5.01})
    with pytest.raises(ValidationError):
        WorldPackageCountryV1UpdateRequest.model_validate({**BASE_UPDATE, "competition_quality": 0.99})


def test_official_hungarica_preserves_fractional_legacy_competition_rating() -> None:
    country = WorldPackageCountryStore(
        Path("config/world_packages/official_fax_world")
    ).load_country("HUN")

    assert country.competition_quality == 2.5
