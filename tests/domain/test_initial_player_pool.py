from beta_engine.domain.countries import Country
from beta_engine.domain.players.initial_pool import InitialPlayerPoolGenerator


def country(code: str, *, population: int, system: int, popularity: int, tradition: int, region: str = "EUROPE") -> Country:
    return Country(
        code=code,
        name=code,
        region=region,
        population=population,
        wealth_support=system,
        squash_popularity=popularity,
        squash_tradition=tradition,
        system_quality=system,
        competition_density=float(system),
        federation_quality=float(system),
        court_count=500 if system >= 4 else 80,
    )


def test_initial_pool_is_deterministic_for_same_seed_and_season() -> None:
    countries = [country("AAA", population=2_000_000, system=5, popularity=5, tradition=5), country("BBB", population=80_000_000, system=2, popularity=2, tradition=2)]
    generator = InitialPlayerPoolGenerator()

    left = generator.generate(countries=countries, seed=123, season="2000/2001", target_pool_size=64)
    right = generator.generate(countries=countries, seed=123, season="2000/2001", target_pool_size=64)

    assert left.model_dump(mode="json") == right.model_dump(mode="json")


def test_initial_pool_changes_with_seed_and_spreads_career_stages() -> None:
    countries = [country("AAA", population=15_000_000, system=4, popularity=4, tradition=4)]
    generator = InitialPlayerPoolGenerator()

    left = generator.generate(countries=countries, seed=123, season="2000/2001", target_pool_size=80)
    right = generator.generate(countries=countries, seed=456, season="2000/2001", target_pool_size=80)

    assert left.players != right.players
    assert len(left.summary.by_career_stage) >= 4
    assert {player.current_age_years for player in left.players} != {15}
    assert all(15 <= player.current_age_years <= 38 for player in left.players)


def test_country_quality_influence_and_population_is_not_only_driver() -> None:
    strong_small = country("SSS", population=1_500_000, system=5, popularity=5, tradition=5)
    weak_large = country("LLL", population=150_000_000, system=1, popularity=1, tradition=1)
    generator = InitialPlayerPoolGenerator()

    result = generator.generate(countries=[strong_small, weak_large], seed=99, season="2000/2001", target_pool_size=240)
    by_country = {code: [player for player in result.players if player.country_code == code] for code in ("SSS", "LLL")}
    avg_strong = sum(player.potential_ability for player in by_country["SSS"]) / len(by_country["SSS"])
    avg_weak = sum(player.potential_ability for player in by_country["LLL"]) / len(by_country["LLL"])

    assert avg_strong > avg_weak
    assert any(player.potential_tier in {"A", "S"} for player in by_country["SSS"])


def test_locked_player_is_preserved_when_regenerating_unlocked_by_country_and_region() -> None:
    countries = [
        country("AAA", population=5_000_000, system=5, popularity=5, tradition=5, region="EUROPE"),
        country("BBB", population=5_000_000, system=3, popularity=3, tradition=3, region="ASIA"),
    ]
    generator = InitialPlayerPoolGenerator()
    initial = generator.generate(countries=countries, seed=10, season="2000/2001", target_pool_size=30)
    locked = initial.players[0].model_copy(update={"locked": True})
    current = [locked, *initial.players[1:]]

    country_regen = generator.regenerate_unlocked(
        countries=countries,
        current_players=current,
        season="2000/2001",
        seed=11,
        country_code=locked.country_code,
    )

    assert next(player for player in country_regen.players if player.player_id == locked.player_id) == locked
    unaffected_country = "BBB" if locked.country_code == "AAA" else "AAA"
    assert [p for p in country_regen.players if p.country_code == unaffected_country] == [p for p in current if p.country_code == unaffected_country]

    region_regen = generator.regenerate_unlocked(
        countries=countries,
        current_players=current,
        season="2000/2001",
        seed=12,
        region=next(c.region for c in countries if c.code == locked.country_code),
    )
    assert next(player for player in region_regen.players if player.player_id == locked.player_id) == locked
