from __future__ import annotations

import pytest
from sqlalchemy import select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    BranchForkIdempotencyConflictError, BranchForkSourceStateMismatchError, BranchForkValidationError, DatabaseSettings,
    ForkRunBranchCommand, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchForkCommandModel, BranchStateModel, LegacySimulationRunMappingModel,
    RunBranchModel, RunContainerModel, SeasonStateModel, SimulationRunModel,
)


def _setup(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'fork.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    branch = repository.list_run_branches(run_id="source")[0]
    source_checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="source")
    return repository, service, branch, source_checkpoint


def _command(branch_id: str, checkpoint_id: str, **changes):
    values = dict(product_run_id="source", source_branch_id=branch_id, source_checkpoint_id=checkpoint_id,
        target_branch_id="fork-branch", target_branch_display_name="Fork", target_legacy_simulation_run_id="fork-legacy",
        target_branch_seed=99, command_id="fork-command")
    values.update(changes)
    return ForkRunBranchCommand(**values)


def test_atomic_fork_creates_branch_namespace_checkpoint_and_replays_idempotently(tmp_path):
    repository, service, source_branch, source_checkpoint = _setup(tmp_path)
    original_official = repository.get_run_container(run_id="source").official_branch_id
    result = service.fork_run_branch_atomically(_command(source_branch.branch_id, source_checkpoint.checkpoint_id))
    assert result.idempotent_replay is False and result.created_mapping is False and result.official_branch_changed is False
    assert result.target_checkpoint_id == "checkpoint-f7b6d8b60c815da04f4141d7"
    with repository._session_factory() as session:
        branch = session.get(RunBranchModel, "fork-branch"); state = session.get(BranchStateModel, "fork-branch")
        checkpoint = session.get(BranchCheckpointModel, result.target_checkpoint_id)
        assert session.get(SimulationRunModel, "fork-legacy").seed == 47
        assert session.get(SeasonStateModel, "fork-legacy") is not None
        assert branch.head_checkpoint_id == state.head_checkpoint_id == checkpoint.checkpoint_id
        assert checkpoint.kind == "branch_fork_start" and checkpoint.sequence == 1 and checkpoint.parent_checkpoint_id is None
        assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
        assert checkpoint.payload_json.find('"fork_semantics":"cloned_current_state_not_checkpoint_replay"') >= 0
        assert session.get(LegacySimulationRunMappingModel, "fork-legacy") is None
        assert session.get(BranchForkCommandModel, "fork-command") is not None
    assert repository.get_run_container(run_id="source").official_branch_id == original_official
    assert repository.get_branch_execution_target(branch_id="fork-branch").legacy_simulation_run_id == "fork-legacy"
    replay = service.fork_run_branch_atomically(_command(source_branch.branch_id, source_checkpoint.checkpoint_id))
    assert replay.idempotent_replay is True and replay.target_checkpoint_id == result.target_checkpoint_id
    with pytest.raises(BranchForkIdempotencyConflictError):
        service.fork_run_branch_atomically(_command(source_branch.branch_id, source_checkpoint.checkpoint_id, target_branch_seed=100))


def test_inventory_hash_is_r4c0_inventory_not_clone_equivalence_and_corrupt_replay_fails(tmp_path):
    repository, service, source_branch, source_checkpoint = _setup(tmp_path)
    expected_inventory = repository.inspect_legacy_run_clone_inventory(simulation_run_id="source", branch_id=source_branch.branch_id, checkpoint_id=source_checkpoint.checkpoint_id).inventory.inventory_hash
    result = service.fork_run_branch_atomically(_command(source_branch.branch_id, source_checkpoint.checkpoint_id))
    assert result.source_inventory_hash == expected_inventory
    assert result.source_inventory_hash != result.normalized_clone_equivalence_hash
    with repository._session_factory.begin() as session:
        session.delete(session.get(SeasonStateModel, "fork-legacy"))
    with pytest.raises(BranchForkSourceStateMismatchError, match="inconsistent"):
        service.fork_run_branch_atomically(_command(source_branch.branch_id, source_checkpoint.checkpoint_id))


def test_atomic_fork_accepts_current_capture_and_rejects_read_only_and_missing_state(tmp_path):
    repository, service, source_branch, _ = _setup(tmp_path)
    capture = repository.capture_current_checkpoint_for_legacy_simulation_run(simulation_run_id="source")
    result = service.fork_run_branch_atomically(_command(source_branch.branch_id, capture.checkpoint_id))
    assert result.target_checkpoint_id
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, "source").read_only = 1
    with pytest.raises(BranchForkValidationError, match="editable"):
        service.fork_run_branch_atomically(_command(source_branch.branch_id, capture.checkpoint_id, target_branch_id="other", target_legacy_simulation_run_id="other-legacy", command_id="other"))


@pytest.mark.parametrize("failure", ["equivalence", "branch", "state", "checkpoint", "command"])
def test_atomic_fork_rolls_back_all_target_rows(tmp_path, monkeypatch, failure):
    repository, service, source_branch, source_checkpoint = _setup(tmp_path)
    if failure == "equivalence":
        original = repository._normalized_clone_content_hash
        monkeypatch.setattr(repository, "_normalized_clone_content_hash", lambda **kw: "bad" if kw["run_id"] == "fork-legacy" else original(**kw))
    else:
        original_add = repository._session_factory
        # Fail specifically at flush after target rows are staged; transaction rollback is the invariant under test.
        original_flush = None
        from sqlalchemy.orm import Session
        original_flush = Session.flush
        calls = {"n": 0}
        def fail_flush(self, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2: raise RuntimeError(failure)
            return original_flush(self, *args, **kwargs)
        monkeypatch.setattr(Session, "flush", fail_flush)
    with pytest.raises(Exception):
        service.fork_run_branch_atomically(_command(source_branch.branch_id, source_checkpoint.checkpoint_id))
    with repository._session_factory() as session:
        assert session.get(SimulationRunModel, "fork-legacy") is None
        assert session.get(SeasonStateModel, "fork-legacy") is None
        assert session.get(RunBranchModel, "fork-branch") is None
        assert session.get(BranchStateModel, "fork-branch") is None
        assert session.execute(select(BranchCheckpointModel).where(BranchCheckpointModel.branch_id == "fork-branch")).scalars().all() == []
        assert session.get(BranchForkCommandModel, "fork-command") is None
