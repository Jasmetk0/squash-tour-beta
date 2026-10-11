from __future__ import annotations

import json

import pytest
from sqlalchemy import event, select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    BranchSimulateNextMatchCommand,
    BranchSimulateNextWeekCommand, BranchSimulateNextWeekResult,
    BranchSimulateFullSeasonCommand, BranchSimulationConflictError,
    BranchSimulationIdempotencyConflictError, DatabaseSettings, ForkRunBranchCommand,
    SimulationPersistenceRepository, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchSimulationCommandModel, BranchStateModel,
    CompletedEventMetadataModel, CompletedEventModel, CompletedTournamentInputModel,
    RaceSnapshotModel, RankingSnapshotModel, RunBranchModel, RunContainerModel,
    SeasonStateModel,
)

DURABLE_MODELS = (SeasonStateModel, CompletedEventModel, CompletedTournamentInputModel,
                  CompletedEventMetadataModel, RankingSnapshotModel, RaceSnapshotModel,
                  BranchCheckpointModel, RunBranchModel, BranchStateModel,
                  BranchSimulationCommandModel)


def _setup(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'full-season.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    branch = repository.list_run_branches(run_id="source")[0]
    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="source")
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, "source").storage_kind = "custom_local"
    return repository, service, branch.branch_id, checkpoint.checkpoint_id


def _rows(session, model, *, run_id=None):
    statement = select(model)
    if run_id is not None and hasattr(model, "run_id"):
        statement = statement.where(model.run_id == run_id)
    values = [{column.name: getattr(row, column.name) for column in model.__table__.columns}
              for row in session.execute(statement).scalars()]
    return sorted(values, key=lambda value: json.dumps(value, sort_keys=True, default=str))


def _durable_snapshot(repository):
    with repository._session_factory() as session:
        return {model.__tablename__: _rows(session, model) for model in DURABLE_MODELS}


def _legacy_snapshot(repository, run_id):
    with repository._session_factory() as session:
        return {
            model.__tablename__: [
                {key: value for key, value in row.items() if key != "id"}
                for row in _rows(session, model, run_id=run_id)
            ]
            for model in DURABLE_MODELS[:6]
        }


def _fork(repository, service, source_branch, head):
    result = service.fork_run_branch_atomically(ForkRunBranchCommand(
        "source", source_branch, head, "branch-b", "Branch B", "legacy-b", 99, "fork-b"))
    return result.target_branch_id, result.target_checkpoint_id


def test_legacy_full_season_and_branch_full_season_are_durably_equivalent(tmp_path):
    repository, service, branch_a, head_a = _setup(tmp_path)
    branch_b, head_b = _fork(repository, service, branch_a, head_a)
    service.simulate_full_season(run_id="source")
    service.simulate_full_season_on_branch_atomically(
        BranchSimulateFullSeasonCommand("source", branch_b, head_b, "tournament-b", "equivalence", True))
    source = _legacy_snapshot(repository, "source")
    branch = _legacy_snapshot(repository, "legacy-b")
    for table in source:
        normalize = lambda rows: sorted(
            [{k: v for k, v in row.items() if k != "run_id"} for row in rows],
            key=lambda row: json.dumps(row, sort_keys=True, default=str),
        )
        assert normalize(source[table]) == normalize(branch[table])
    with repository._session_factory() as session:
        events = session.execute(select(CompletedEventModel).where(
            CompletedEventModel.run_id == "legacy-b"
        ).order_by(CompletedEventModel.event_sequence)).scalars().all()
        assert [row.event_sequence for row in events] == list(range(len(events)))
        assert len(events) == len(session.execute(select(CompletedTournamentInputModel).where(CompletedTournamentInputModel.run_id == "legacy-b")).scalars().all())
        assert len(events) == len(session.execute(select(CompletedEventMetadataModel).where(CompletedEventMetadataModel.run_id == "legacy-b")).scalars().all())
        assert len(events) == len(session.execute(select(RankingSnapshotModel).where(RankingSnapshotModel.run_id == "legacy-b", RankingSnapshotModel.snapshot_kind == "tournament")).scalars().all())



def test_full_season_contract_replay_and_no_executable(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    command = BranchSimulateFullSeasonCommand("source", branch_id, head, "full-season-1", "remaining season", True)
    result = service.simulate_full_season_on_branch_atomically(command)
    assert result.simulation_result["mode"] == "simulate_full_season"
    assert result.simulation_result["season_complete"] is True
    assert result.simulation_result["completed_in_command_count"] > 0
    assert result.simulation_result["completed_week_group_count"] > 0
    assert result.official_branch_changed is False
    with repository._session_factory() as session:
        journal = session.get(BranchSimulationCommandModel, command.command_id)
        checkpoint = session.get(BranchCheckpointModel, result.new_head_checkpoint_id)
        assert journal.action_kind == "simulate_full_season"
        assert checkpoint.command_kind == "simulate_full_season_branch"
        assert checkpoint.command_boundary == "after_branch_full_season_persisted"
        assert session.get(RunBranchModel, branch_id).head_checkpoint_id == session.get(BranchStateModel, branch_id).head_checkpoint_id
    replay = service.simulate_full_season_on_branch_atomically(command)
    assert replay.idempotent_replay is True
    with pytest.raises(BranchSimulationConflictError):
        service.simulate_full_season_on_branch_atomically(BranchSimulateFullSeasonCommand("source", branch_id, head, "stale", "stale", True))
    with pytest.raises(Exception, match="no executable full season"):
        service.simulate_full_season_on_branch_atomically(BranchSimulateFullSeasonCommand("source", branch_id, result.new_head_checkpoint_id, "complete", "complete", True))
