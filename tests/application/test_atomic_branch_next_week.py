from __future__ import annotations

import json

import pytest
from sqlalchemy import event, select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    BranchSimulateNextMatchCommand, BranchSimulateNextMatchResult,
    BranchSimulateNextWeekCommand, BranchSimulationConflictError,
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
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'next-week.db'}"))
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


def test_legacy_next_week_and_branch_next_week_are_durably_equivalent(tmp_path):
    repository, service, branch_a, head_a = _setup(tmp_path)
    branch_b, head_b = _fork(repository, service, branch_a, head_a)
    service.simulate_next_week(run_id="source")
    service.simulate_next_week_on_branch_atomically(
        BranchSimulateNextWeekCommand("source", branch_b, head_b, "week-b", "equivalence", True))
    assert _legacy_snapshot(repository, "source") == {
        table: [{**row, "run_id": "source"} for row in rows]
        for table, rows in _legacy_snapshot(repository, "legacy-b").items()
    }
    with repository._session_factory() as session:
        events = session.execute(select(CompletedEventModel).where(
            CompletedEventModel.run_id == "legacy-b"
        ).order_by(CompletedEventModel.event_sequence)).scalars().all()
        assert [(row.event_sequence, row.event_id) for row in events] == [
            (0, "ev_2027_w01_malaysia_major"),
            (1, "ev_2027_w01_qatar_platinum"),
        ]
        assert session.execute(select(CompletedTournamentInputModel).where(CompletedTournamentInputModel.run_id == "legacy-b")).scalars().all().__len__() == 2
        assert session.execute(select(CompletedEventMetadataModel).where(CompletedEventMetadataModel.run_id == "legacy-b")).scalars().all().__len__() == 2
        assert session.execute(select(RankingSnapshotModel).where(RankingSnapshotModel.run_id == "legacy-b", RankingSnapshotModel.snapshot_kind == "tournament")).scalars().all().__len__() == 2
        assert session.execute(select(RankingSnapshotModel).where(RankingSnapshotModel.run_id == "legacy-b", RankingSnapshotModel.snapshot_kind == "week")).scalars().all().__len__() == 1


def test_active_tournament_and_following_week_match_legacy_durable_state(tmp_path):
    repository, service, branch_a, head_a = _setup(tmp_path)
    branch_b, head_b = _fork(repository, service, branch_a, head_a)

    service.simulate_next_match(run_id="source")
    branch_match = service.simulate_next_match_on_branch_atomically(
        BranchSimulateNextMatchCommand("source", branch_b, head_b, "active-match", "partial", True)
    )
    assert service._load_run_context(run_id="source")[1].active_tournament is not None
    assert service._load_run_context(run_id="legacy-b")[1].active_tournament is not None

    service.simulate_next_week(run_id="source")
    week = service.simulate_next_week_on_branch_atomically(
        BranchSimulateNextWeekCommand(
            "source", branch_b, branch_match.new_head_checkpoint_id,
            "active-week", "finalize and continue", True,
        )
    )
    assert _legacy_snapshot(repository, "source") == {
        table: [{**row, "run_id": "source"} for row in rows]
        for table, rows in _legacy_snapshot(repository, "legacy-b").items()
    }
    with repository._session_factory() as session:
        events = session.execute(select(CompletedEventModel).where(
            CompletedEventModel.run_id == "legacy-b"
        ).order_by(CompletedEventModel.event_sequence)).scalars().all()
        inputs = session.execute(select(CompletedTournamentInputModel).where(CompletedTournamentInputModel.run_id == "legacy-b")).scalars().all()
        metadata = session.execute(select(CompletedEventMetadataModel).where(CompletedEventMetadataModel.run_id == "legacy-b")).scalars().all()
        assert [row.event_sequence for row in events] == list(range(len(events)))
        assert len(events) == len(inputs) == len(metadata) == len({row.event_id for row in events}) == 2
        assert events[0].event_id == "ev_2027_w01_malaysia_major"
        assert session.execute(select(BranchCheckpointModel).where(BranchCheckpointModel.parent_checkpoint_id == branch_match.new_head_checkpoint_id)).scalars().one().checkpoint_id == week.new_head_checkpoint_id
        assert session.execute(select(BranchSimulationCommandModel).where(BranchSimulationCommandModel.command_id == "active-week")).scalars().one().resulting_head_checkpoint_id == week.new_head_checkpoint_id


def test_final_active_tournament_is_persisted_without_weekly_result(tmp_path):
    repository, service, branch_a, head_a = _setup(tmp_path)
    with repository._session_factory.begin() as session:
        state = session.get(SeasonStateModel, "source")
        events = json.loads(state.ordered_events_json)[:1]
        state.ordered_events_json = repository.canonical_json(events)
        checkpoint = session.get(BranchCheckpointModel, head_a)
        payload = json.loads(checkpoint.payload_json)
        payload["season_state"] = repository._season_state_payload_in_session(session=session, model=state)
        checkpoint.payload_json = repository.canonical_json(payload)
        checkpoint.content_hash = repository.checkpoint_envelope_content_hash(repository._to_branch_checkpoint(checkpoint))
    branch_b, head_b = _fork(repository, service, branch_a, head_a)
    service.simulate_next_match(run_id="source")
    branch_match = service.simulate_next_match_on_branch_atomically(
        BranchSimulateNextMatchCommand("source", branch_b, head_b, "final-match", "partial final", True)
    )
    legacy_step = service.simulate_next_week(run_id="source")
    assert legacy_step.weekly_result is None
    result = service.simulate_next_week_on_branch_atomically(
        BranchSimulateNextWeekCommand("source", branch_b, branch_match.new_head_checkpoint_id, "final-week", "finalize final", True)
    )
    assert _legacy_snapshot(repository, "source") == {
        table: [{**row, "run_id": "source"} for row in rows]
        for table, rows in _legacy_snapshot(repository, "legacy-b").items()
    }
    with repository._session_factory() as session:
        assert session.execute(select(CompletedEventModel).where(CompletedEventModel.run_id == "legacy-b")).scalars().all().__len__() == 1
        assert session.execute(select(CompletedTournamentInputModel).where(CompletedTournamentInputModel.run_id == "legacy-b")).scalars().all().__len__() == 1
        assert session.execute(select(CompletedEventMetadataModel).where(CompletedEventMetadataModel.run_id == "legacy-b")).scalars().all().__len__() == 1
        assert session.execute(select(RankingSnapshotModel).where(RankingSnapshotModel.run_id == "legacy-b", RankingSnapshotModel.snapshot_kind == "tournament")).scalars().all().__len__() == 1
        assert session.execute(select(RaceSnapshotModel).where(RaceSnapshotModel.run_id == "legacy-b", RaceSnapshotModel.snapshot_kind == "tournament")).scalars().all().__len__() == 1
        assert session.get(RunBranchModel, branch_b).head_checkpoint_id == result.new_head_checkpoint_id


def test_non_official_branch_next_week_is_isolated(tmp_path):
    repository, service, branch_a, head_a = _setup(tmp_path)
    branch_b, head_b = _fork(repository, service, branch_a, head_a)
    before_a = _legacy_snapshot(repository, "source")
    before_b = _legacy_snapshot(repository, "legacy-b")
    with repository._session_factory() as session:
        state_a = _rows(session, BranchStateModel); checkpoints_a = _rows(session, BranchCheckpointModel)
    result = service.simulate_next_week_on_branch_atomically(
        BranchSimulateNextWeekCommand("source", branch_b, head_b, "isolated-week", "isolation", True))
    assert _legacy_snapshot(repository, "source") == before_a
    assert _legacy_snapshot(repository, "legacy-b") != before_b
    with repository._session_factory() as session:
        assert session.get(RunContainerModel, "source").official_branch_id == branch_a
        assert session.get(RunBranchModel, branch_a).head_checkpoint_id == head_a
        assert session.get(RunBranchModel, branch_b).head_checkpoint_id == result.new_head_checkpoint_id
        assert session.get(BranchStateModel, branch_b).head_checkpoint_id == result.new_head_checkpoint_id
        assert [x for x in _rows(session, BranchStateModel) if x["branch_id"] == branch_a] == [x for x in state_a if x["branch_id"] == branch_a]
        assert len([x for x in _rows(session, BranchCheckpointModel) if x["branch_id"] == branch_a]) == len([x for x in checkpoints_a if x["branch_id"] == branch_a])
        journals = session.execute(select(BranchSimulationCommandModel)).scalars().all()
        assert len(journals) == 1 and journals[0].branch_id == branch_b


def test_next_week_contract_and_journal_first_replay(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    command = BranchSimulateNextWeekCommand("source", branch_id, head, "next-week-1", "test", True)
    result = service.simulate_next_week_on_branch_atomically(command)
    with repository._session_factory() as session:
        journal = session.get(BranchSimulationCommandModel, command.command_id)
        checkpoint = session.get(BranchCheckpointModel, result.new_head_checkpoint_id)
        assert journal.action_kind == "simulate_next_week"
        assert checkpoint.command_kind == "simulate_next_week_branch"
        assert checkpoint.command_boundary == "after_branch_next_week_persisted"
        assert session.get(RunBranchModel, branch_id).head_checkpoint_id == session.get(BranchStateModel, branch_id).head_checkpoint_id == result.new_head_checkpoint_id
        assert session.get(RunContainerModel, "source").official_branch_id == branch_id
    with repository._session_factory.begin() as session:
        session.get(RunBranchModel, branch_id).read_only = 1
    replay = service.simulate_next_week_on_branch_atomically(command)
    assert replay.idempotent_replay and replay.new_head_checkpoint_id == result.new_head_checkpoint_id


def test_cross_action_different_commands_cannot_advance_same_head(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    before = _durable_snapshot(repository)
    match = service.simulate_next_match_on_branch_atomically(
        BranchSimulateNextMatchCommand("source", branch_id, head, "match-command", "cross action", True))
    assert isinstance(match, BranchSimulateNextMatchResult)
    after_one = _durable_snapshot(repository)
    with pytest.raises(BranchSimulationConflictError):
        service.simulate_next_week_on_branch_atomically(
            BranchSimulateNextWeekCommand("source", branch_id, head, "week-command", "cross action", True))
    assert _durable_snapshot(repository) == after_one != before
    with repository._session_factory() as session:
        assert session.execute(select(BranchSimulationCommandModel).where(BranchSimulationCommandModel.previous_head_checkpoint_id == head)).scalars().all().__len__() == 1
        assert session.execute(select(BranchCheckpointModel).where(BranchCheckpointModel.parent_checkpoint_id == head)).scalars().all().__len__() == 1


def test_command_id_cannot_be_reused_across_actions(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    service.simulate_next_match_on_branch_atomically(BranchSimulateNextMatchCommand("source", branch_id, head, "same-id", "test", True))
    with pytest.raises(BranchSimulationIdempotencyConflictError):
        service.simulate_next_week_on_branch_atomically(BranchSimulateNextWeekCommand("source", branch_id, head, "same-id", "test", True))


def test_reviewed_state_fingerprint_mismatch_rolls_back(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    run, reviewed = service._load_run_context(run_id="source")
    step = service._build_orchestrator(season=run.season, seed=run.seed, run_info=run).simulate_next_week(state=reviewed)
    reviewed_hash = repository.checkpoint_content_hash(reviewed.model_dump(mode="json"))
    with repository._session_factory.begin() as session:
        state = session.get(SeasonStateModel, "source"); state.next_event_index = 1
        checkpoint = session.get(BranchCheckpointModel, head)
        payload = json.loads(checkpoint.payload_json)
        payload["season_state"]["next_event_index"] = 1
        checkpoint.payload_json = repository.canonical_json(payload)
        checkpoint.content_hash = repository.checkpoint_envelope_content_hash(repository._to_branch_checkpoint(checkpoint))
    before = _durable_snapshot(repository)
    with pytest.raises(BranchSimulationConflictError):
        repository.simulate_next_week_on_branch_atomically(
            BranchSimulateNextWeekCommand("source", branch_id, head, "mismatch", "test", True),
            step=step, reviewed_pre_state=reviewed,
            reviewed_pre_state_fingerprint=reviewed_hash)
    assert _durable_snapshot(repository) == before


@pytest.mark.parametrize("failure", ["legacy", "checkpoint", "run_branch", "branch_state", "journal"])
def test_next_week_failure_rolls_back_complete_durable_snapshot(tmp_path, monkeypatch, failure):
    repository, service, branch_id, head = _setup(tmp_path)
    before = _durable_snapshot(repository)
    if failure == "legacy":
        def fail(**kwargs): raise RuntimeError("legacy persistence failure")
        monkeypatch.setattr(repository, "_persist_branch_simulation_step_in_session", fail)
        remove = None
    else:
        needles = {"checkpoint": "INSERT INTO branch_checkpoints", "run_branch": "UPDATE run_branches",
                   "branch_state": "UPDATE branch_states", "journal": "INSERT INTO branch_simulation_commands"}
        def reject(conn, cursor, statement, parameters, context, executemany):
            if needles[failure] in statement: raise RuntimeError(f"{failure} failure")
        event.listen(repository._engine, "before_cursor_execute", reject)
        remove = reject
    with pytest.raises(RuntimeError):
        service.simulate_next_week_on_branch_atomically(
            BranchSimulateNextWeekCommand("source", branch_id, head, f"fail-{failure}", "fault injection", True))
    if remove is not None: event.remove(repository._engine, "before_cursor_execute", remove)
    assert _durable_snapshot(repository) == before
