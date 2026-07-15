from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.countries.models import Country


def _base_country_payload() -> dict[str, object]:
    return {
        "code": "AAA",
        "name": "Alpha",
        "flag_asset": None,
        "region": "EUROPE",
        "population": 1_000_000,
        "wealth_support": 3,
        "squash_popularity": 4,
        "squash_tradition": 2,
        "system_quality": 5,
    }


def test_country_accepts_legacy_payload_without_phase_two_fields() -> None:
    country = Country.model_validate(_base_country_payload())

    assert country.competition_density == 3.0
    assert country.federation_quality == 5.0
    assert country.court_count is None
    assert country.style_dna == {}


def test_country_accepts_phase_two_optional_fields() -> None:
    country = Country.model_validate(
        {
            **_base_country_payload(),
            "competition_density": 4.5,
            "federation_quality": 4.0,
            "court_count": 120,
            "style_dna": {"front_court": 0.2, "attrition": -0.1},
        }
    )

    assert country.competition_density == 4.5
    assert country.federation_quality == 4.0
    assert country.court_count == 120
    assert country.style_dna == {"front_court": 0.2, "attrition": -0.1}


def test_country_effective_travel_region_defaults_to_region_and_tracks_region_copy() -> None:
    country = Country.model_validate(_base_country_payload())

    assert country.travel_region is None
    assert country.effective_travel_region == "EUROPE"

    copied = country.model_copy(update={"region": "MIDDLE_EAST"})

    assert copied.travel_region is None
    assert copied.effective_travel_region == "MIDDLE_EAST"


def test_country_explicit_travel_region_overrides_region_and_blank_normalizes_to_default() -> None:
    explicit = Country.model_validate({**_base_country_payload(), "region": "AFRICA", "travel_region": "MIDDLE_EAST"})
    blank = Country.model_validate({**_base_country_payload(), "region": "AFRICA", "travel_region": "   "})

    assert explicit.effective_travel_region == "MIDDLE_EAST"
    assert blank.travel_region is None
    assert blank.effective_travel_region == "AFRICA"


def test_country_accepts_default_population_year_2020() -> None:
    country = Country.model_validate({**_base_country_payload(), "default_population_year": 2020})

    assert country.default_population_year == 2020


def test_country_accepts_missing_default_population_year() -> None:
    country = Country.model_validate(_base_country_payload())

    assert country.default_population_year is None


def test_country_accepts_phase_7b_population_timeline_fields() -> None:
    country = Country.model_validate(
        {
            **_base_country_payload(),
            "area_km2": 12345,
            "default_population_year": 2020,
            "default_population": 1_500_000,
            "population_by_year": {"1955": 1_000_000, "2020": 1_500_000, "2035": None},
        }
    )

    assert country.area_km2 == 12345
    assert country.default_population_year == 2020
    assert country.default_population == 1_500_000
    assert country.population_by_year == {1955: 1_000_000, 2020: 1_500_000, 2035: None}


@pytest.mark.parametrize(
    "field,value",
    [
        ("area_km2", 0),
        ("default_population", 0),
        ("default_population_year", 2019),
        ("default_population_year", 2035),
    ],
)
def test_country_rejects_invalid_phase_7b_scalar_fields(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Country.model_validate({**_base_country_payload(), field: value})


@pytest.mark.parametrize(
    "population_by_year",
    [
        {"1954": 1_000_000},
        {"2036": 1_000_000},
        {"2020": 0},
        {"2020": -1},
    ],
)
def test_country_rejects_invalid_population_by_year(population_by_year: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        Country.model_validate({**_base_country_payload(), "population_by_year": population_by_year})


def test_country_still_rejects_unknown_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Country.model_validate({**_base_country_payload(), "unexpected": "blocked"})
