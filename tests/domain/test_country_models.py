from __future__ import annotations

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
