from __future__ import annotations

from beta_engine.domain.countries import Country, CountryTalentModel


def _v1_country(**overrides: object) -> Country:
    payload: dict[str, object] = {
        "code": "AAA",
        "name": "Alpha",
        "region": "TEST",
        "population": 10_000_000,
        "squash_popularity": 3,
        "squash_access": 3,
        "development_quality": 3,
        "competition_quality": 3,
        "elite_support": 3,
        "squash_tradition": 3,
    }
    payload.update(overrides)
    return Country.model_validate(payload)


def test_country_v1_serializes_only_six_game_attributes() -> None:
    country = _v1_country(court_count=42)
    payload = country.model_dump(mode="json")

    for field in (
        "squash_popularity",
        "squash_access",
        "development_quality",
        "competition_quality",
        "elite_support",
        "squash_tradition",
    ):
        assert field in payload

    for legacy in ("wealth_support", "system_quality", "competition_density", "federation_quality", "style_dna"):
        assert legacy not in payload
    assert payload["court_count"] == 42


def test_legacy_country_payload_migrates_deterministically_to_v1() -> None:
    country = Country.model_validate(
        {
            "code": "LEG",
            "name": "Legacy",
            "region": "TEST",
            "population": 5_000_000,
            "wealth_support": 2,
            "squash_popularity": 4,
            "squash_tradition": 5,
            "system_quality": 3,
            "competition_density": 4.0,
            "federation_quality": 2.0,
            "style_dna": {"pace": 1.2},
        }
    )

    assert country.squash_popularity == 4
    assert country.squash_access == 2
    assert country.development_quality == 3
    assert country.competition_quality == 4
    assert country.elite_support == 2
    assert country.squash_tradition == 5
    assert "style_dna" not in country.model_dump()


def test_participation_pool_depends_on_popularity_and_access_only() -> None:
    model = CountryTalentModel()
    strong_pipeline = _v1_country(
        squash_popularity=3,
        squash_access=3,
        development_quality=5,
        competition_quality=5,
        elite_support=5,
        squash_tradition=5,
    )
    weak_pipeline = _v1_country(
        squash_popularity=3,
        squash_access=3,
        development_quality=1,
        competition_quality=1,
        elite_support=1,
        squash_tradition=1,
    )

    assert model.effective_squash_pool_weight(strong_pipeline) == model.effective_squash_pool_weight(weak_pipeline)
    assert model.development_environment(strong_pipeline) > model.development_environment(weak_pipeline)


def test_effective_squash_pool_uses_diminishing_population_returns() -> None:
    model = CountryTalentModel()
    small = _v1_country(population=10_000_000)
    large = _v1_country(population=40_000_000)

    small_weight = model.effective_squash_pool_weight(small)
    large_weight = model.effective_squash_pool_weight(large)

    assert large_weight > small_weight
    assert large_weight < small_weight * 4.0


def test_court_count_does_not_directly_change_v1_prospect_volume() -> None:
    model = CountryTalentModel()
    few_courts = _v1_country(court_count=5)
    many_courts = _v1_country(court_count=5_000)

    assert model.effective_squash_pool_weight(few_courts) == model.effective_squash_pool_weight(many_courts)
