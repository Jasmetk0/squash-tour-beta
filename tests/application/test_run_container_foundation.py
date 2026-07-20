from __future__ import annotations

from sqlalchemy import inspect

from beta_engine.infrastructure.db import DatabaseSettings, SimulationRunInfo, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


def _repository(tmp_path) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'run-containers.db'}"))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def test_bootstrap_backfills_legacy_runs_idempotently_and_preserves_world_lock(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()
    repository.upsert_simulation_run(SimulationRunInfo(run_id="legacy run", season=2027, seed=7, world_id="custom_world"))

    inspector = inspect(repository._engine)
    assert {"runs", "legacy_simulation_run_mappings"} <= set(inspector.get_table_names())
    first = repository.get_run_container_for_simulation_run(simulation_run_id="legacy run")
    repository.backfill_run_containers_for_existing_simulation_runs()
    second = repository.get_run_container_for_simulation_run(simulation_run_id="legacy run")

    assert first is not None and second is not None
    assert first.run_id == second.run_id == "legacy run"
    assert second.storage_kind == "custom_local"
    assert second.read_only is False
    assert second.world_id == "custom_world"
    assert second.mapped_simulation_run_count == 1
    # A second create call cannot alter the product Run's creation lock.
    repository.upsert_simulation_run(SimulationRunInfo(run_id="legacy run", season=2028, seed=8, world_id="other_world"))
    assert repository.get_run_container(run_id="legacy run").world_id == "custom_world"
