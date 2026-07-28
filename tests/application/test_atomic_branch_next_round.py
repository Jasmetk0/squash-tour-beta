from __future__ import annotations

from beta_engine.application.api_services import SimulationApiService
import pytest

from beta_engine.infrastructure.db import (BranchSimulateNextMatchCommand,
    BranchSimulateNextRoundCommand, BranchSimulationConflictError,
    BranchSimulationIdempotencyConflictError, DatabaseSettings,
    SimulationPersistenceRepository, create_session_factory, create_sqlite_engine)
from beta_engine.infrastructure.db.models import BranchCheckpointModel, BranchSimulationCommandModel, BranchStateModel, RunBranchModel, RunContainerModel


def _setup(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'next-round.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    branch = repository.list_run_branches(run_id="source")[0]
    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="source")
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, "source").storage_kind = "custom_local"
    return repository, service, branch.branch_id, checkpoint.checkpoint_id


def test_branch_next_round_is_atomic_and_replay_is_journal_only(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    command = BranchSimulateNextRoundCommand("source", branch_id, head, "next-round-1", "test execution", True)
    result = service.simulate_next_round_on_branch_atomically(command)
    assert result.idempotent_replay is False
    assert result.previous_head_checkpoint_id == head
    assert result.previous_season == 2027
    with repository._session_factory() as session:
        assert session.query(BranchSimulationCommandModel).count() == 1
        journal = session.get(BranchSimulationCommandModel, command.command_id)
        assert journal.action_kind == "simulate_next_round"
        assert session.query(BranchCheckpointModel).filter_by(branch_id=branch_id).count() == 2
        checkpoint = session.get(BranchCheckpointModel, result.new_head_checkpoint_id)
        assert checkpoint.command_kind == "simulate_next_round_branch"
        assert checkpoint.command_boundary == "after_branch_next_round_persisted"
        assert session.get(RunBranchModel, branch_id).head_checkpoint_id == result.new_head_checkpoint_id
        assert session.get(BranchStateModel, branch_id).head_checkpoint_id == result.new_head_checkpoint_id
    # A completed journal replay must not resolve an executable Branch or calculate a match.
    with repository._session_factory.begin() as session:
        session.get(RunBranchModel, branch_id).read_only = 1
    replay = service.simulate_next_round_on_branch_atomically(command)
    assert replay.idempotent_replay is True
    assert replay.new_head_checkpoint_id == result.new_head_checkpoint_id
    with repository._session_factory() as session:
        assert session.query(BranchCheckpointModel).filter_by(branch_id=branch_id).count() == 2


def test_branch_next_round_conflicting_replay_and_same_head_are_rejected(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    command = BranchSimulateNextRoundCommand("source", branch_id, head, "round-conflict", "first", True)
    service.simulate_next_round_on_branch_atomically(command)
    with pytest.raises(BranchSimulationIdempotencyConflictError):
        service.simulate_next_round_on_branch_atomically(
            BranchSimulateNextRoundCommand("source", branch_id, head, "round-conflict", "different", True)
        )
    with pytest.raises(BranchSimulationConflictError):
        service.simulate_next_round_on_branch_atomically(
            BranchSimulateNextRoundCommand("source", branch_id, head, "round-same-head", "second", True)
        )
    with repository._session_factory() as session:
        assert session.query(BranchSimulationCommandModel).count() == 1
        assert session.query(BranchCheckpointModel).filter_by(branch_id=branch_id).count() == 2


def test_branch_next_round_command_id_conflicts_across_actions(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    service.simulate_next_match_on_branch_atomically(
        BranchSimulateNextMatchCommand("source", branch_id, head, "cross-action", "test", True)
    )
    with pytest.raises(BranchSimulationIdempotencyConflictError):
        service.simulate_next_round_on_branch_atomically(
            BranchSimulateNextRoundCommand("source", branch_id, head, "cross-action", "test", True)
        )
    with repository._session_factory() as session:
        assert session.query(BranchSimulationCommandModel).count() == 1
