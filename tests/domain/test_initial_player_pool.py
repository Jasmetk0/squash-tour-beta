"""Country V1 adapter around the established initial-player-pool regression suite."""

from __future__ import annotations

from tests.domain import initial_player_pool_contract_suite as _suite


_REPLACED_TEST = "test_country_quality_influence_and_population_is_not_only_driver"

# Keep the established lifecycle, population-history, lock/regeneration and Admin
# regression suite intact. Only the one legacy assertion that country strength
# should raise innate potential is replaced by the Master-v43 invariant below.
for _name, _value in vars(_suite).items():
    if _name.startswith("test_") and _name != _REPLACED_TEST:
        globals()[_name] = _value


def test_country_quality_influence_and_population_is_not_only_driver() -> None:
    generator = _suite.InitialPlayerPoolGenerator()
    strong = _suite.country(
        "AAA",
        population=20_000_000,
        system=5,
        popularity=3,
        tradition=5,
        squash_access=3,
        development_quality=5,
        competition_quality=5,
        elite_support=5,
        squash_tradition=5,
    )
    weak = _suite.country(
        "AAA",
        population=20_000_000,
        system=1,
        popularity=3,
        tradition=1,
        squash_access=3,
        development_quality=1,
        competition_quality=1,
        elite_support=1,
        squash_tradition=1,
    )

    strong_player = generator._generate_player(country=strong, season="2000/2001", seed=99, sequence=7)
    weak_player = generator._generate_player(country=weak, season="2000/2001", seed=99, sequence=7)

    # Same individual RNG stream => same innate potential and identity. Country
    # development can change only how much of that potential is currently realised.
    assert strong_player.potential_tier == weak_player.potential_tier
    assert strong_player.potential_ability == weak_player.potential_ability
    assert strong_player.hidden_career_traits.potential_ceiling == weak_player.hidden_career_traits.potential_ceiling
    assert strong_player.archetype == weak_player.archetype
    assert strong_player.play_style == weak_player.play_style
    assert strong_player.hidden_career_traits == weak_player.hidden_career_traits
    assert strong_player.current_ability > weak_player.current_ability
    assert strong_player.current_ability <= strong_player.potential_ability + 4
    assert weak_player.current_ability <= weak_player.potential_ability + 4


def test_initial_pool_volume_uses_population_popularity_access_not_development() -> None:
    generator = _suite.InitialPlayerPoolGenerator()
    high_development = _suite.country(
        "AAA",
        population=30_000_000,
        system=5,
        popularity=3,
        tradition=5,
        squash_access=3,
        development_quality=5,
        competition_quality=5,
        elite_support=5,
        squash_tradition=5,
    )
    low_development = _suite.country(
        "BBB",
        population=30_000_000,
        system=1,
        popularity=3,
        tradition=1,
        squash_access=3,
        development_quality=1,
        competition_quality=1,
        elite_support=1,
        squash_tradition=1,
    )

    result = generator.generate(
        countries=[high_development, low_development],
        seed=2026,
        season="2000/2001",
        target_pool_size=100,
    )
    diagnostics = {row.country_code: row for row in result.metadata.population_weighting_diagnostics}

    assert diagnostics["AAA"].allocation_weight == diagnostics["BBB"].allocation_weight
    assert result.summary.by_country["AAA"] == result.summary.by_country["BBB"]


def test_initial_pool_popularity_and_access_increase_sampling_volume() -> None:
    generator = _suite.InitialPlayerPoolGenerator()
    accessible = _suite.country(
        "AAA",
        population=30_000_000,
        system=3,
        popularity=5,
        tradition=3,
        squash_access=5,
        development_quality=3,
        competition_quality=3,
        elite_support=3,
    )
    limited = _suite.country(
        "BBB",
        population=30_000_000,
        system=3,
        popularity=1,
        tradition=3,
        squash_access=1,
        development_quality=3,
        competition_quality=3,
        elite_support=3,
    )

    result = generator.generate(
        countries=[accessible, limited],
        seed=2026,
        season="2000/2001",
        target_pool_size=100,
    )

    assert result.summary.by_country["AAA"] > result.summary.by_country["BBB"]
