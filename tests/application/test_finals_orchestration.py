from __future__ import annotations

import pytest

from beta_engine.application.finals_service import FinalsOrchestrationService
from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.persistence import SimulationPersistenceService
from beta_engine.application.services import SeasonSimulationOrchestrator
from beta_engine.core import DeterministicRng
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.players import Player, PlayerGenerator
from beta_engine.infrastructure.db import DatabaseSettings, SimulationRunInfo, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.points_config import load_points_config
from beta_engine.infrastructure.tournament_config import load_season_calendar, load_tournament_templates_config
from beta_engine.infrastructure.world_config import load_countries_config, load_player_identity_config


def _players(seed: int, per_country: int = 24) -> tuple[list[Player], dict[str, Country]]:
    countries = load_countries_config().countries
    generator = PlayerGenerator(
        rng=DeterministicRng(seed),
        identity_config=load_player_identity_config(),
        country_talent_model=CountryTalentModel(),
    )
    players: list[Player] = []
    for country in countries:
        players.extend(generator.generate(country=country, sequence=i + 1) for i in range(per_country))
    return players, {country.code: country for country in countries}


def _orchestrator(seed: int = 6060) -> SeasonSimulationOrchestrator:
    calendar = load_season_calendar()
    templates = load_tournament_templates_config().templates
    players, countries_by_code = _players(seed=99)
    return SeasonSimulationOrchestrator.build(
        calendar=calendar,
        templates=templates,
        players=players,
        countries_by_code=countries_by_code,
        points_by_ref=load_points_config(),
        entry_tuning=load_entry_tuning_config(),
        seed=seed,
    )


def _repository(tmp_path) -> SimulationPersistenceRepository:
    db_file = tmp_path / "sim_finals.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    return SimulationPersistenceRepository(engine=engine, session_factory=session_factory)


def test_finals_simulation_requires_completed_season(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9401)
    repository = _repository(tmp_path)
    run = SimulationRunInfo(run_id="run-finals-incomplete", season=2027, seed=9401)
    SimulationPersistenceService(repository=repository).initialize_run(run=run)

    players, _ = _players(seed=99)
    service = FinalsOrchestrationService(repository=repository)

    with pytest.raises(ValueError, match="completed regular season"):
        service.simulate_world_tour_finals(
            run=run,
            state=orchestrator.initialize_state(),
            players_by_id={player.player_id: player for player in players},
        )


def test_finals_simulation_is_deterministic_and_idempotent(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9501)
    full_season = orchestrator.simulate_full_season(state=orchestrator.initialize_state())

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-finals-deterministic", season=full_season.season_state.season, seed=9501)
    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=full_season)

    players, _ = _players(seed=99)
    service = FinalsOrchestrationService(repository=repository)
    first = service.simulate_world_tour_finals(
        run=run,
        state=full_season.season_state,
        players_by_id={player.player_id: player for player in players},
    )
    second = service.simulate_world_tour_finals(
        run=run,
        state=full_season.season_state,
        players_by_id={player.player_id: player for player in players},
    )

    assert first.already_simulated is False
    assert second.already_simulated is True
    assert first.result.result.model_dump() == second.result.result.model_dump()
    assert first.qualification.qualification.model_dump() == second.qualification.qualification.model_dump()


def test_get_finals_qualification_is_read_only_when_not_materialized(tmp_path) -> None:
    orchestrator = _orchestrator(seed=9601)
    full_season = orchestrator.simulate_full_season(state=orchestrator.initialize_state())

    repository = _repository(tmp_path)
    persistence = SimulationPersistenceService(repository=repository)
    run = SimulationRunInfo(run_id="run-finals-readonly", season=full_season.season_state.season, seed=9601)
    persistence.initialize_run(run=run)
    persistence.persist_step(run_id=run.run_id, step=full_season)

    service = SimulationApiService(repository=repository)
    assert repository.get_finals_qualification(run_id=run.run_id, season=run.season) is None

    qualification = service.get_finals_qualification(run_id=run.run_id)
    assert qualification.season == run.season
    assert repository.get_finals_qualification(run_id=run.run_id, season=run.season) is None

    summary = service.get_finals_summary(run_id=run.run_id)
    assert summary.qualification is not None
    assert summary.result is None
    assert repository.get_finals_qualification(run_id=run.run_id, season=run.season) is None
