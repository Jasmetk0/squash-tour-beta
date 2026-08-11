from __future__ import annotations

from tests.support.world_packages import load_fax_reference_countries

from beta_engine.core import DeterministicRng
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.matches import MatchEngine
from beta_engine.domain.players import PlayerGenerator
from beta_engine.infrastructure.world_config import PlayerIdentityConfig, load_player_identity_config


def _generator(seed: int) -> tuple[PlayerGenerator, list[Country], PlayerIdentityConfig]:
    countries = load_fax_reference_countries().countries
    identity = load_player_identity_config()
    generator = PlayerGenerator(
        rng=DeterministicRng(seed),
        identity_config=identity,
        country_talent_model=CountryTalentModel(),
    )
    return generator, countries, identity


def _sample_average_ability(generator: PlayerGenerator, country: Country, count: int = 100) -> float:
    players = [generator.generate(country=country, sequence=i + 1) for i in range(count)]
    total = 0.0
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


def _v1_country(*, code: str, strength: int, population: int = 50_000_000) -> Country:
    return Country(
        code=code,
        name=f"Country {code}",
        region="TEST",
        population=population,
        squash_popularity=strength,
        squash_access=strength,
        development_quality=strength,
        competition_quality=strength,
        elite_support=strength,
        squash_tradition=strength,
    )


def test_same_seed_and_inputs_generate_same_players() -> None:
    gen_a, countries, _ = _generator(2028)
    gen_b, _, _ = _generator(2028)
    germanica = next(c for c in countries if c.code == "GER")

    a = [gen_a.generate(country=germanica, sequence=i).model_dump() for i in range(1, 8)]
    b = [gen_b.generate(country=germanica, sequence=i).model_dump() for i in range(1, 8)]

    assert a == b


def test_strong_country_distribution_differs_from_weaker_country() -> None:
    generator, countries, _ = _generator(555)
    germanica = next(c for c in countries if c.code == "GER")
    hungarica = next(c for c in countries if c.code == "HUN")

    germanica_avg = _sample_average_ability(generator, germanica, count=120)
    hungarica_avg = _sample_average_ability(generator, hungarica, count=120)

    assert germanica_avg > hungarica_avg + 8.0


def test_generation_depends_on_development_environment_not_population_alone() -> None:
    generator, _, identity = _generator(901)
    high_strength_small_pop = _v1_country(code="HSP", strength=5, population=35_000_000)
    weak_but_large_pop = _v1_country(code="WLP", strength=1, population=350_000_000)

    high_avg = _sample_average_ability(generator, high_strength_small_pop, count=120)
    weak_avg = _sample_average_ability(generator, weak_but_large_pop, count=120)

    assert high_avg > weak_avg + 12.0
    assert "attacking" in identity.play_styles


def test_country_strength_does_not_change_intrinsic_potential_with_same_seed() -> None:
    weak = _v1_country(code="TST", strength=1)
    strong = _v1_country(code="TST", strength=5)
    weak_generator, _, _ = _generator(7781)
    strong_generator, _, _ = _generator(7781)

    weak_players = [weak_generator.generate(country=weak, sequence=i) for i in range(1, 50)]
    strong_players = [strong_generator.generate(country=strong, sequence=i) for i in range(1, 50)]

    assert [player.hidden_career_traits.potential_ceiling for player in weak_players] == [
        player.hidden_career_traits.potential_ceiling for player in strong_players
    ]
    assert sum(player.technique + player.mental for player in strong_players) > sum(
        player.technique + player.mental for player in weak_players
    )


def test_generated_player_has_required_mvp_fields() -> None:
    generator, countries, _ = _generator(333)
    germanica = next(c for c in countries if c.code == "GER")

    player = generator.generate(country=germanica, sequence=1)

    expected_fields = {
        "player_id",
        "name",
        "age",
        "birth_year",
        "birth_year_week",
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
