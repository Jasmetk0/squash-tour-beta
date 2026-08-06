from __future__ import annotations

from sqlalchemy import select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    BranchSimulateFullSeasonCommand, BranchSimulateWorldTourFinalsCommand,
    DatabaseSettings, SimulationPersistenceRepository, create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchSimulationCommandModel, BranchStateModel,
    FinalsQualificationModel, FinalsResultModel, RunBranchModel, RunContainerModel,
)


def _setup(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'finals.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    branch = repository.list_run_branches(run_id="source")[0]
    head = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="source").checkpoint_id
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, "source").storage_kind = "custom_local"
    regular = service.simulate_full_season_on_branch_atomically(BranchSimulateFullSeasonCommand("source", branch.branch_id, head, "regular", "complete regular season", True))
    return repository, service, branch.branch_id, regular.new_head_checkpoint_id


def test_atomic_branch_finals_success_and_exact_replay(tmp_path, monkeypatch):
    repository, service, branch_id, head = _setup(tmp_path)
    before_state = repository.load_season_state(run_id="source")
    official = repository.get_run_container(run_id="source").official_branch_id
    command = BranchSimulateWorldTourFinalsCommand("source", branch_id, head, "finals", "play finals", True)
    result = service.simulate_world_tour_finals_on_branch_atomically(command)
    assert result.finals.already_simulated is False
    assert result.previous_season == result.current_season
    assert (result.previous_week, result.previous_event_id, result.previous_event_sequence) == (result.current_week, result.current_event_id, result.current_event_sequence)
    assert repository.load_season_state(run_id="source") == before_state
    assert repository.get_run_container(run_id="source").official_branch_id == official
    with repository._session_factory() as session:
        assert len(session.execute(select(FinalsQualificationModel)).scalars().all()) == 1
        assert len(session.execute(select(FinalsResultModel)).scalars().all()) == 1
        assert len(session.execute(select(BranchSimulationCommandModel).where(BranchSimulationCommandModel.command_id == "finals")).scalars().all()) == 1
        checkpoint = session.get(BranchCheckpointModel, result.new_head_checkpoint_id)
        assert checkpoint.command_kind == "simulate_world_tour_finals_branch"
        assert checkpoint.kind == "current_state_capture"
        assert session.get(RunBranchModel, branch_id).head_checkpoint_id == session.get(BranchStateModel, branch_id).head_checkpoint_id
    monkeypatch.setattr("beta_engine.application.finals_service.FinalsOrchestrationService.derive_world_tour_finals", lambda *a, **k: (_ for _ in ()).throw(AssertionError("derived on replay")))
    replay = service.simulate_world_tour_finals_on_branch_atomically(command)
    assert replay.idempotent_replay is True
    assert replay.new_head_checkpoint_id == result.new_head_checkpoint_id
