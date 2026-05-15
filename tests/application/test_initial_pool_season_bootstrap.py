from __future__ import annotations

import json
from pathlib import Path

import pytest

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.initial_player_pool_service import InitialPlayerPoolService
from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService, SeasonActivePlayersRegistry

COUNTRIES = {
    "countries": [
        {"code": "AAA", "name": "Alpha", "region": "EUROPE", "population": 5_000_000, "wealth_support": 5, "squash_popularity": 5, "squash_tradition": 5, "system_quality": 5},
        {"code": "BBB", "name": "Beta", "region": "ASIA", "population": 60_000_000, "wealth_support": 2, "squash_popularity": 2, "squash_tradition": 2, "system_quality": 2},
    ]
}


def custom_api_payload(player_id="CUST-2000-AAA-API") -> dict:
    return {
        "player_id": player_id,
        "name": "API Player",
        "country_code": "AAA",
        "birth_year": 1977,
        "birth_year_week": 8,
        "current_ability": 77,
        "potential_ability": 86,
        "potential_tier": "A",
        "career_stage": "prime",
        "play_style": "balanced",
        "archetype": "all_court",
        "attributes": {"technique": 77, "movement": 76, "physical": 75, "mental": 78, "consistency": 77, "clutch": 76, "recovery": 75},
        "hidden_career_traits": {"potential_ceiling": 86, "growth_curve": "steady", "professionalism": 0.8, "ambition": 0.7, "travel_tolerance": 0.6, "schedule_aggression": 0.5, "injury_proneness": 0.2, "resilience": 0.7},
        "reason": "api test",
    }


def services(tmp_path: Path) -> tuple[InitialPlayerPoolService, InitialPoolSeasonBootstrapService]:
    countries_path = tmp_path / "countries.json"
    countries_path.write_text(json.dumps(COUNTRIES), encoding="utf-8")
    pool = InitialPlayerPoolService(countries_service=CountriesConfigService(config_path=countries_path), config_path=tmp_path / "pool.json")
    bootstrap = InitialPoolSeasonBootstrapService(initial_pool_service=pool, active_players_path=tmp_path / "season_active_players.json")
    return pool, bootstrap


def test_dry_run_does_not_persist(tmp_path) -> None:
    pool, bootstrap = services(tmp_path)
    pool.generate_pool(season="2000/2001", seed=7, target_pool_size=12, dry_run=False)

    result = bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=12345, dry_run=True)

    assert result.summary.total_active_players == 12
    assert bootstrap.get_active_players(season="2000/2001").players == []
    assert not (tmp_path / "season_active_players.json").exists()


def test_persist_preserves_provenance_and_zero_points(tmp_path) -> None:
    pool, bootstrap = services(tmp_path)
    pool.generate_pool(season="2000/2001", seed=7, target_pool_size=8, dry_run=False)
    from beta_engine.domain.players.initial_pool import CustomInitialPoolPlayerCreate
    created = pool.create_custom_player(CustomInitialPoolPlayerCreate.model_validate(custom_api_payload("CUST-2000-AAA-BOOT")))

    result = bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=222, dry_run=False)
    persisted = bootstrap.get_active_players(season="2000/2001")

    assert persisted.summary.total_active_players == result.summary.total_active_players == 9
    by_id = {player.player_id: player for player in persisted.players}
    assert created.player_id in by_id
    active = by_id[created.player_id]
    assert active.manual_override is True
    assert active.source_generation == "manual"
    assert active.locked_from_initial_pool is True
    assert active.ranking_points == 0
    assert active.race_points == 0
    assert active.player_id == active.source_pool_player_id


def test_empty_initial_pool_rejected(tmp_path) -> None:
    _, bootstrap = services(tmp_path)
    with pytest.raises(ValueError, match="initial pool is empty"):
        bootstrap.bootstrap_from_initial_pool(season="2000/2001", dry_run=False)


def test_duplicate_source_player_ids_rejected(tmp_path) -> None:
    pool, bootstrap = services(tmp_path)
    result = pool.generate_pool(season="2000/2001", seed=7, target_pool_size=2, dry_run=True)
    duplicate = result.players[0].model_dump(mode="json")
    (tmp_path / "pool.json").write_text(json.dumps({"players": [duplicate, duplicate], "audit_events": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate source"):
        bootstrap.bootstrap_from_initial_pool(season="2000/2001", dry_run=True)


def test_overwrite_safety_and_season_isolation(tmp_path) -> None:
    pool, bootstrap = services(tmp_path)
    pool.generate_pool(season="2000/2001", seed=7, target_pool_size=4, dry_run=False)
    pool.generate_pool(season="2001/2002", seed=8, target_pool_size=3, dry_run=False)

    bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=1, dry_run=False)
    bootstrap.bootstrap_from_initial_pool(season="2001/2002", source_season="2001/2002", seed=2, dry_run=False)
    with pytest.raises(ValueError, match="already exist"):
        bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=3, dry_run=False)

    overwritten = bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=3, dry_run=False, overwrite_existing=True)
    assert overwritten.metadata.bootstrap_seed == 3
    assert bootstrap.get_active_players(season="2001/2002").summary.total_active_players == 3


def test_fingerprint_determinism(tmp_path) -> None:
    pool, bootstrap = services(tmp_path)
    pool.generate_pool(season="2000/2001", seed=7, target_pool_size=5, dry_run=False)

    first = bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=99, dry_run=True)
    second = bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=99, dry_run=True)
    third = bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=100, dry_run=True)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.metadata.bootstrap_fingerprint != third.metadata.bootstrap_fingerprint
    assert first.players[0].bootstrap_fingerprint != third.players[0].bootstrap_fingerprint


def test_active_players_registry_loads_legacy_season_mapping(tmp_path) -> None:
    pool, bootstrap = services(tmp_path)
    pool.generate_pool(season="2000/2001", seed=7, target_pool_size=1, dry_run=False)
    preview = bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=1, dry_run=True)
    (tmp_path / "season_active_players.json").write_text(json.dumps({"2000/2001": [preview.players[0].model_dump(mode="json")]}), encoding="utf-8")

    response = bootstrap.get_active_players(season="2000/2001")
    assert response.summary.total_active_players == 1
    assert SeasonActivePlayersRegistry.model_validate(json.loads((tmp_path / "season_active_players.json").read_text()))
