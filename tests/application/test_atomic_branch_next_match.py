from __future__ import annotations

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import BranchSimulateNextMatchCommand, DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import BranchCheckpointModel, BranchSimulationCommandModel, BranchStateModel, RunBranchModel, RunContainerModel


def _setup(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'next-match.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    branch = repository.list_run_branches(run_id="source")[0]
    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="source")
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, "source").storage_kind = "custom_local"
    return repository, service, branch.branch_id, checkpoint.checkpoint_id


def test_branch_next_match_is_atomic_and_replay_is_journal_only(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    command = BranchSimulateNextMatchCommand("source", branch_id, head, "next-match-1", "test execution", True)
    result = service.simulate_next_match_on_branch_atomically(command)
    assert result.idempotent_replay is False
    assert result.previous_head_checkpoint_id == head
    assert result.previous_season == 2027
    with repository._session_factory() as session:
        assert session.query(BranchSimulationCommandModel).count() == 1
        assert session.query(BranchCheckpointModel).filter_by(branch_id=branch_id).count() == 2
        assert session.get(RunBranchModel, branch_id).head_checkpoint_id == result.new_head_checkpoint_id
        assert session.get(BranchStateModel, branch_id).head_checkpoint_id == result.new_head_checkpoint_id
    # A completed journal replay must not resolve an executable Branch or calculate a match.
    with repository._session_factory.begin() as session:
        session.get(RunBranchModel, branch_id).read_only = 1
    replay = service.simulate_next_match_on_branch_atomically(command)
    assert replay.idempotent_replay is True
    assert replay.new_head_checkpoint_id == result.new_head_checkpoint_id
    with repository._session_factory() as session:
        assert session.query(BranchCheckpointModel).filter_by(branch_id=branch_id).count() == 2
