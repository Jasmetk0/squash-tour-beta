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
    assert all(15 <= player.current_age_years <= 45 for player in left.players)


def test_initial_pool_generator_allows_older_tail_and_preserves_birth_year_formula() -> None:
    countries = [country("AAA", population=15_000_000, system=4, popularity=4, tradition=4)]
    generator = InitialPlayerPoolGenerator()

    result = generator.generate(countries=countries, seed=123, season="2000/2001", target_pool_size=500)
    ages = [player.current_age_years for player in result.players]

    assert min(ages) >= 15
    assert max(ages) <= 45
    assert any(age >= 39 for age in ages)
    assert all(player.birth_year == 2000 - player.current_age_years for player in result.players)


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

import json

import pytest

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.initial_player_pool_service import InitialPlayerPoolService
from beta_engine.domain.players.initial_pool import (
    CustomInitialPoolPlayerCreate,
    GeneratedPlayerAttributes,
    HiddenCareerTraits,
    InitialPoolGeneratedPlayer,
    InitialPoolPlayerUpdate,
    InitialPoolRegistry,
)


def service_with_countries(tmp_path, countries):
    countries_path = tmp_path / "countries.json"
    countries_path.write_text(json.dumps({"countries": [country.model_dump(mode="json") for country in countries]}), encoding="utf-8")
    return InitialPlayerPoolService(countries_service=CountriesConfigService(config_path=countries_path), config_path=tmp_path / "pool.json")


def custom_payload(**overrides):
    data = {
        "player_id": "CUST-2000-AAA-TEST-PLAYER",
        "name": "Test Player",
        "country_code": "AAA",
        "birth_year": 1976,
        "birth_year_week": 10,
        "current_ability": 80,
        "potential_ability": 88,
        "potential_tier": "A",
        "career_stage": "prime",
        "play_style": "balanced",
        "archetype": "all_court",
        "attributes": {"technique": 80, "movement": 80, "physical": 80, "mental": 80, "consistency": 80, "clutch": 80, "recovery": 80},
        "hidden_career_traits": {
            "potential_ceiling": 88,
            "growth_curve": "steady",
            "professionalism": 0.8,
            "ambition": 0.7,
            "travel_tolerance": 0.6,
            "schedule_aggression": 0.5,
            "injury_proneness": 0.2,
            "resilience": 0.7,
        },
        "reason": "story anchor",
    }
    data.update(overrides)
    return CustomInitialPoolPlayerCreate.model_validate(data)



def generated_player_data(**overrides):
    data = {
        "player_id": "P-2000-AAA-TEST",
        "name": "Generated Test",
        "country_code": "AAA",
        "nationality": "AAA",
        "birth_year": 1955,
        "birth_year_week": 10,
        "age_at_generation": 45,
        "current_age_years": 45,
        "current_ability": 70,
        "potential_ability": 78,
        "potential_tier": "B",
        "career_stage": "late_career",
        "play_style": "balanced",
        "archetype": "all_court",
        "attributes": {"technique": 70, "movement": 70, "physical": 70, "mental": 70, "consistency": 70, "clutch": 70, "recovery": 70},
        "hidden_career_traits": {
            "potential_ceiling": 78,
            "growth_curve": "steady",
            "professionalism": 0.8,
            "ambition": 0.7,
            "travel_tolerance": 0.6,
            "schedule_aggression": 0.5,
            "injury_proneness": 0.2,
            "resilience": 0.7,
        },
        "locked": False,
        "generation_source": "initial_pool",
        "manual_override": False,
        "generation_seed": 123,
        "generation_fingerprint": "test-fingerprint",
        "created_for_season": "2000/2001",
    }
    data.update(overrides)
    return data


def test_initial_pool_generated_player_accepts_age_45_and_birth_year_1955() -> None:
    player = InitialPoolGeneratedPlayer.model_validate(generated_player_data())

    assert player.age_at_generation == 45
    assert player.current_age_years == 45
    assert player.birth_year == 1955
    assert player.birth_year == 2000 - player.current_age_years


def test_initial_pool_generated_player_rejects_age_46() -> None:
    with pytest.raises(ValueError):
        InitialPoolGeneratedPlayer.model_validate(generated_player_data(age_at_generation=46))
    with pytest.raises(ValueError):
        InitialPoolGeneratedPlayer.model_validate(generated_player_data(current_age_years=46))

def test_create_custom_player_is_locked_manual_and_rejects_duplicates_and_invalid_attributes(tmp_path) -> None:
    svc = service_with_countries(tmp_path, [country("AAA", population=2_000_000, system=5, popularity=5, tradition=5)])

    created = svc.create_custom_player(custom_payload())

    assert created.locked is True
    assert created.manual_override is True
    assert created.generation_source == "manual"
    assert created.generation_seed == 0
    assert created.generation_fingerprint != "pending"
    assert svc.get_audit_events(player_id=created.player_id).audit_events[0].action == "create_custom_player"

    with pytest.raises(ValueError, match="already exists"):
        svc.create_custom_player(custom_payload())
    with pytest.raises(ValueError):
        CustomInitialPoolPlayerCreate.model_validate(custom_payload().model_dump(mode="json") | {"attributes": {"technique": 100}})


def test_update_player_auto_locks_manual_override_and_audits_changed_fields(tmp_path) -> None:
    svc = service_with_countries(tmp_path, [country("AAA", population=2_000_000, system=5, popularity=5, tradition=5)])
    generated = svc.generate_pool(season="2000/2001", seed=12, target_pool_size=4, dry_run=False).players[0]

    updated = svc.update_player(player_id=generated.player_id, payload=InitialPoolPlayerUpdate(name="Edited Player", current_ability=70, reason="curated"))

    assert updated.name == "Edited Player"
    assert updated.current_ability == 70
    assert updated.locked is True
    assert updated.manual_override is True
    event = svc.get_audit_events(player_id=generated.player_id).audit_events[-1]
    assert event.action == "update_player"
    assert {"name", "current_ability", "locked", "manual_override"}.issubset(set(event.changed_fields))
    assert event.before_fingerprint == generated.generation_fingerprint
    assert event.after_fingerprint == updated.generation_fingerprint


def test_audit_dry_run_and_lock_unlock_persistence_and_legacy_registry(tmp_path) -> None:
    svc = service_with_countries(tmp_path, [country("AAA", population=2_000_000, system=5, popularity=5, tradition=5)])
    svc.generate_pool(season="2000/2001", seed=12, target_pool_size=4, dry_run=True)
    assert svc.get_audit_events().audit_events == []

    result = svc.generate_pool(season="2000/2001", seed=12, target_pool_size=4, dry_run=False)
    player = result.players[0]
    svc.set_lock(player_id=player.player_id, locked=True)
    svc.set_lock(player_id=player.player_id, locked=False)
    actions = [event.action for event in svc.get_audit_events().audit_events]
    assert actions == ["generate_pool", "lock_player", "unlock_player"]

    legacy = InitialPoolRegistry.model_validate({"players": [player.model_dump(mode="json")]})
    assert legacy.players[0].player_id == player.player_id
    assert legacy.audit_events == []


def test_custom_locked_player_survives_regenerate_unlocked(tmp_path) -> None:
    svc = service_with_countries(tmp_path, [country("AAA", population=2_000_000, system=5, popularity=5, tradition=5)])
    custom = svc.create_custom_player(custom_payload(player_id="CUST-2000-AAA-SURVIVOR"))

    regenerated = svc.regenerate_unlocked(season="2000/2001", seed=99, target_pool_size=5, country_code=None, region=None, dry_run=False)

    assert next(player for player in regenerated.players if player.player_id == custom.player_id) == custom
