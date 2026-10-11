from __future__ import annotations

from sqlalchemy import inspect

from beta_engine.infrastructure.db import DatabaseSettings, RunBranchRecord, SimulationRunInfo, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


def _repository(tmp_path) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'run-containers.db'}"))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def test_bootstrap_backfills_legacy_runs_idempotently_and_preserves_world_lock(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()
    repository.upsert_simulation_run(SimulationRunInfo(run_id="legacy run", season=2027, seed=7, world_id="custom_world"))

    inspector = inspect(repository._engine)
    assert {"runs", "run_branches", "legacy_simulation_run_mappings"} <= set(inspector.get_table_names())
    first = repository.get_run_container_for_simulation_run(simulation_run_id="legacy run")
    repository.backfill_run_containers_for_existing_simulation_runs()
    second = repository.get_run_container_for_simulation_run(simulation_run_id="legacy run")

    assert first is not None and second is not None
    assert first.run_id == second.run_id == "legacy run"
    assert second.storage_kind == "custom_local"
    assert second.read_only is False
    assert second.world_id == "custom_world"
    assert second.mapped_simulation_run_count == 1
    branches = repository.list_run_branches(run_id="legacy run")
    assert len(branches) == 1
    branch = branches[0]
    assert branch.display_name == "Main"
    assert branch.read_only is False
    assert branch.branch_seed == 7
    assert branch.legacy_simulation_run_id == "legacy run"
    assert branch.is_official is True
    assert second.official_branch_id == branch.branch_id
    # A second create call cannot alter the product Run's creation lock.
    repository.upsert_simulation_run(SimulationRunInfo(run_id="legacy run", season=2028, seed=8, world_id="other_world"))
    assert repository.get_run_container(run_id="legacy run").world_id == "custom_world"


def test_default_branch_backfill_preserves_an_existing_official_branch(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()
    repository.upsert_simulation_run(SimulationRunInfo(run_id="legacy", season=2027, seed=7))
    repository.create_run_branch(RunBranchRecord(
        branch_id="already-official", run_id="legacy", display_name="Official", status="active",
        read_only=False, branch_seed=7, forked_from_branch_id=None, forked_from_checkpoint_id=None,
        head_checkpoint_id=None, legacy_simulation_run_id=None, metadata={},
    ))
    with repository._session_factory.begin() as session:
        from beta_engine.infrastructure.db.models import RunContainerModel
        session.get(RunContainerModel, "legacy").official_branch_id = "already-official"

    repository.backfill_default_branches_for_existing_run_containers()

    assert repository.get_run_container(run_id="legacy").official_branch_id == "already-official"
    branches = repository.list_run_branches(run_id="legacy")
    assert {branch.branch_id for branch in branches} == {
        "already-official", repository.deterministic_default_branch_id(run_id="legacy", legacy_simulation_run_id="legacy"),
    }
    assert next(branch for branch in branches if branch.branch_id == "already-official").is_official is True
