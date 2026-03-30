from __future__ import annotations

import pytest

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


def _service(tmp_path) -> SimulationApiService:
    db_file = tmp_path / "rollover_app.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    return SimulationApiService(repository=repository)


def test_rollover_rejects_incomplete_season(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-incomplete", season=2027, seed=8808, config_version=None, config_fingerprint=None)

    with pytest.raises(ValueError, match="completed season"):
        service.rollover_to_next_season(run_id="run-incomplete")


def test_rollover_is_idempotent_for_same_completed_season(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-idempotent", season=2027, seed=8818, config_version=None, config_fingerprint=None)
    service.simulate_full_season(run_id="run-idempotent")

    first = service.rollover_to_next_season(run_id="run-idempotent")
    second = service.rollover_to_next_season(run_id="run-idempotent")

    assert first.already_persisted is False
    assert second.already_persisted is True
    assert first.model_dump(exclude={"already_persisted"}) == second.model_dump(exclude={"already_persisted"})


def test_rollover_summary_and_player_reads_use_persisted_data(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-read", season=2027, seed=8828, config_version=None, config_fingerprint=None)
    service.simulate_full_season(run_id="run-read")
    rollover = service.rollover_to_next_season(run_id="run-read")

    latest = service.get_latest_rollover(run_id="run-read")
    by_season = service.get_rollover(run_id="run-read", to_season=2028)
    transitions = service.list_player_transitions(run_id="run-read", to_season=2028)
    next_players = service.list_next_season_players(run_id="run-read", to_season=2028)

    assert latest is not None
    assert by_season is not None
    assert latest.to_season == rollover.to_season
    assert by_season.transitioned_players == rollover.transitioned_players
    assert len(transitions) == rollover.transitioned_players
    assert len(next_players) == rollover.transitioned_players
