from __future__ import annotations

from dataclasses import asdict

import pytest
from sqlalchemy import select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    BranchExecutionTargetResolutionError,
    DatabaseSettings,
    RunBranchRecord,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel,
    BranchStateModel,
    RunBranchModel,
    SeasonStateModel,
    SimulationRunModel,
)


def _repository(tmp_path) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'branch-execution-target.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    repository.bootstrap_schema()
    return repository


def _initialize_default_branch(tmp_path):
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(
        run_id="legacy-run", season=2027, seed=47, config_version="test-v1", config_fingerprint="test-fingerprint"
    )
    branch = repository.list_run_branches(run_id="legacy-run")[0]
    return repository, service, branch


def _mutable_state(repository: SimulationPersistenceRepository) -> dict[str, object]:
    with repository._session_factory() as session:
        return {
            "branches": [
                (row.branch_id, row.run_id, row.status, row.read_only, row.legacy_simulation_run_id, row.head_checkpoint_id)
                for row in session.execute(select(RunBranchModel).order_by(RunBranchModel.branch_id)).scalars()
            ],
            "branch_states": [
                (row.branch_id, row.run_id, row.head_checkpoint_id, row.status)
                for row in session.execute(select(BranchStateModel).order_by(BranchStateModel.branch_id)).scalars()
            ],
            "checkpoints": [row.checkpoint_id for row in session.execute(select(BranchCheckpointModel)).scalars()],
            "simulation_runs": [row.run_id for row in session.execute(select(SimulationRunModel).order_by(SimulationRunModel.run_id)).scalars()],
            "season_states": [row.run_id for row in session.execute(select(SeasonStateModel).order_by(SeasonStateModel.run_id)).scalars()],
        }


def test_resolve_branch_execution_target_for_initialized_default_branch_is_read_only(tmp_path) -> None:
    repository, service, branch = _initialize_default_branch(tmp_path)
    before = _mutable_state(repository)

    target = service.resolve_branch_execution_target(branch_id=branch.branch_id)

    assert asdict(target) == {
        "branch_id": branch.branch_id,
        "product_run_id": "legacy-run",
        "legacy_simulation_run_id": "legacy-run",
        "branch_status": "active",
        "branch_read_only": False,
        "is_official": True,
        "display_name": "Main",
        "branch_seed": 47,
        "head_checkpoint_id": None,
    }
    assert _mutable_state(repository) == before


def test_resolve_branch_execution_target_rejects_unknown_branch(tmp_path) -> None:
    repository = _repository(tmp_path)

    with pytest.raises(KeyError, match="run branch missing was not found"):
        repository.get_branch_execution_target(branch_id="missing")


@pytest.mark.parametrize(
    ("legacy_simulation_run_id", "expected_message"),
    [(None, "has no legacy simulation run binding"), ("missing-legacy-run", "references missing legacy simulation run")],
)
def test_resolve_branch_execution_target_rejects_unbound_or_missing_legacy_run(tmp_path, legacy_simulation_run_id, expected_message) -> None:
    repository, _, branch = _initialize_default_branch(tmp_path)
    with repository._session_factory.begin() as session:
        session.get(RunBranchModel, branch.branch_id).legacy_simulation_run_id = legacy_simulation_run_id

    with pytest.raises(BranchExecutionTargetResolutionError, match=expected_message):
        repository.get_branch_execution_target(branch_id=branch.branch_id)


@pytest.mark.parametrize(
    ("status", "read_only", "expected_message"),
    [("active", True, "read-only"), ("inactive", False, "non-executable status")],
)
def test_resolve_branch_execution_target_rejects_non_executable_branch(tmp_path, status, read_only, expected_message) -> None:
    repository, _, branch = _initialize_default_branch(tmp_path)
    with repository._session_factory.begin() as session:
        model = session.get(RunBranchModel, branch.branch_id)
        model.status = status
        model.read_only = int(read_only)

    with pytest.raises(BranchExecutionTargetResolutionError, match=expected_message):
        repository.get_branch_execution_target(branch_id=branch.branch_id)


def test_resolve_branch_execution_target_enforces_product_run_ownership_invariant(tmp_path) -> None:
    repository, _, branch = _initialize_default_branch(tmp_path)
    with repository._session_factory.begin() as session:
        session.get(RunBranchModel, branch.branch_id).run_id = "missing-product-run"

    with pytest.raises(BranchExecutionTargetResolutionError, match="references missing product run"):
        repository.get_branch_execution_target(branch_id=branch.branch_id)


def test_resolve_branch_execution_target_does_not_create_or_mutate_branch_records(tmp_path) -> None:
    repository, _, branch = _initialize_default_branch(tmp_path)
    repository.create_run_branch(RunBranchRecord(
        branch_id="unbound", run_id="legacy-run", display_name="Unbound", status="active", read_only=False,
        branch_seed=None, forked_from_branch_id=None, forked_from_checkpoint_id=None, head_checkpoint_id=None,
        legacy_simulation_run_id=None, metadata={},
    ))
    before = _mutable_state(repository)

    with pytest.raises(BranchExecutionTargetResolutionError, match="has no legacy simulation run binding"):
        repository.get_branch_execution_target(branch_id="unbound")

    assert _mutable_state(repository) == before
