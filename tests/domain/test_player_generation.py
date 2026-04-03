from __future__ import annotations

from beta_engine.core import DeterministicRng
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.matches import MatchEngine
from beta_engine.domain.players import PlayerGenerator
from beta_engine.infrastructure.world_config import (
    PlayerIdentityConfig,
    load_countries_config,
    load_player_identity_config,
)


def _generator(seed: int) -> tuple[PlayerGenerator, list[Country], PlayerIdentityConfig]:
    countries = load_countries_config().countries
    identity = load_player_identity_config()
    generator = PlayerGenerator(
        rng=DeterministicRng(seed),
        identity_config=identity,
        country_talent_model=CountryTalentModel(),
    )
    return generator, countries, identity


def _sample_average_ability(generator: PlayerGenerator, country: Country, count: int = 100) -> float:
    players = [generator.generate(country=country, sequence=i + 1) for i in range(count)]
    total = 0
    for player in players:
        total += (
            player.technique
            + player.movement
            + player.physical
            + player.mental
            + player.consistency
            + player.clutch
            + player.recovery
        ) / 7
    return total / count


def test_same_seed_and_inputs_generate_same_players() -> None:
    gen_a, countries, _ = _generator(2028)
    gen_b, _, _ = _generator(2028)
    egypt = next(c for c in countries if c.code == "EGY")

    a = [gen_a.generate(country=egypt, sequence=i).model_dump() for i in range(1, 8)]
    b = [gen_b.generate(country=egypt, sequence=i).model_dump() for i in range(1, 8)]

    assert a == b


def test_strong_country_distribution_differs_from_weaker_country() -> None:
    generator, countries, _ = _generator(555)
    egypt = next(c for c in countries if c.code == "EGY")
    nigeria = next(c for c in countries if c.code == "NGA")

    egypt_avg = _sample_average_ability(generator, egypt, count=120)
    nigeria_avg = _sample_average_ability(generator, nigeria, count=120)

    assert egypt_avg > nigeria_avg + 8.0


def test_generation_depends_on_more_than_population() -> None:
    generator, _, identity = _generator(901)
    high_strength_small_pop = Country(
        code="HSP",
        name="High Strengthland",
        region="EUROPE",
        population=35_000_000,
        flag_asset=None,
        squash_popularity=5,
        wealth_support=5,
        squash_tradition=5,
        system_quality=5,
    )
    weak_but_large_pop = Country(
        code="WLP",
        name="Weak Populousia",
        region="AMERICAS",
        population=350_000_000,
        flag_asset=None,
        squash_popularity=1,
        wealth_support=1,
        squash_tradition=1,
        system_quality=1,
    )

    high_avg = _sample_average_ability(generator, high_strength_small_pop, count=120)
    weak_avg = _sample_average_ability(generator, weak_but_large_pop, count=120)

    assert high_avg > weak_avg + 12.0

    assert "attacking" in identity.play_styles


def test_generated_player_has_required_mvp_fields() -> None:
    generator, countries, _ = _generator(333)
    england = next(c for c in countries if c.code == "ENG")

    player = generator.generate(country=england, sequence=1)

    expected_fields = {
        "player_id",
        "name",
        "age",
        "nationality",
        "technique",
        "movement",
        "physical",
        "mental",
        "consistency",
        "clutch",
        "recovery",
        "play_style",
        "archetype",
        "hidden_career_traits",
    }
    assert set(player.model_dump().keys()) == expected_fields

    hidden_fields = {
        "potential_ceiling",
        "growth_curve",
        "professionalism",
        "ambition",
        "travel_tolerance",
        "schedule_aggression",
        "injury_proneness",
        "resilience",
    }
    assert set(player.hidden_career_traits.model_dump().keys()) == hidden_fields


def test_generated_identity_values_are_supported_by_matchup_logic() -> None:
    generator, countries, _ = _generator(444)

    generated_styles: set[str] = set()
    generated_archetypes: set[str] = set()
    for country in countries:
        for sequence in range(1, 26):
            player = generator.generate(country=country, sequence=sequence)
            generated_styles.add(player.play_style)
            generated_archetypes.add(player.archetype)

    supported_styles = {left for left, _ in MatchEngine.STYLE_MATCHUP_EDGES}
    supported_archetypes = {left for left, _ in MatchEngine.ARCHETYPE_MATCHUP_EDGES}

    assert generated_styles
    assert generated_archetypes
    assert generated_styles.issubset(supported_styles)
    assert generated_archetypes.issubset(supported_archetypes)
