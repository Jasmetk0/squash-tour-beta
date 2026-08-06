from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    BranchSimulateFullSeasonCommand, BranchSimulateWorldTourFinalsCommand,
    BranchSimulationConflictError, BranchSimulationValidationError,
    DatabaseSettings, SimulationPersistenceRepository, create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchSimulationCommandModel, BranchStateModel,
    FinalsQualificationModel, FinalsResultModel, RunBranchModel, RunContainerModel,
    SeasonStateModel,
)


_DURABLE_MODELS = (
    SeasonStateModel, FinalsQualificationModel, FinalsResultModel,
    BranchCheckpointModel, RunBranchModel, BranchStateModel,
    BranchSimulationCommandModel, RunContainerModel,
)


def _snapshot(repository):
    with repository._session_factory() as session:
        result = {}
        for model in _DURABLE_MODELS:
            rows = [
                {column.name: getattr(row, column.name) for column in model.__table__.columns}
                for row in session.execute(select(model)).scalars()
            ]
            result[model.__tablename__] = sorted(
                rows, key=lambda row: json.dumps(row, sort_keys=True, default=str)
            )
        return result


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


@pytest.mark.parametrize(
    ("audit_reason", "explicit_confirmation"),
    (("play finals", False), ("   ", True)),
)
def test_invalid_completed_command_is_rejected_before_replay(
    tmp_path, monkeypatch, audit_reason, explicit_confirmation
):
    repository, service, branch_id, head = _setup(tmp_path)
    valid = BranchSimulateWorldTourFinalsCommand(
        "source", branch_id, head, "finals", "play finals", True
    )
    service.simulate_world_tour_finals_on_branch_atomically(valid)
    before = _snapshot(repository)
    monkeypatch.setattr(
        SimulationApiService,
        "resolve_branch_execution_target",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("resolved invalid replay")),
    )
    monkeypatch.setattr(
        "beta_engine.application.finals_service.FinalsOrchestrationService.derive_world_tour_finals",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("derived invalid replay")),
    )
    invalid = BranchSimulateWorldTourFinalsCommand(
        "source", branch_id, head, "finals", audit_reason, explicit_confirmation
    )
    with pytest.raises(BranchSimulationValidationError):
        service.simulate_world_tour_finals_on_branch_atomically(invalid)
    assert _snapshot(repository) == before


def test_effective_head_must_capture_current_season_state(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    before = _snapshot(repository)
    with repository._session_factory.begin() as session:
        checkpoint = session.get(BranchCheckpointModel, head)
        payload = json.loads(checkpoint.payload_json)
        payload["season_state"]["completed_event_ids"] = []
        checkpoint.payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    divergent = _snapshot(repository)
    with pytest.raises(BranchSimulationConflictError, match="effective head does not match"):
        service.simulate_world_tour_finals_on_branch_atomically(
            BranchSimulateWorldTourFinalsCommand(
                "source", branch_id, head, "finals", "coherence", True
            )
        )
    assert _snapshot(repository) == divergent
    assert before["finals_qualification"] == divergent["finals_qualification"] == []
    assert before["finals_results"] == divergent["finals_results"] == []


def test_finals_rows_roll_back_when_result_upsert_boundary_fails(tmp_path, monkeypatch):
    repository, service, branch_id, head = _setup(tmp_path)
    before = _snapshot(repository)
    original = repository._upsert_finals_result_in_session

    def fail_after_result_upsert(**kwargs):
        original(**kwargs)
        raise RuntimeError("injected after Finals upserts")

    monkeypatch.setattr(repository, "_upsert_finals_result_in_session", fail_after_result_upsert)
    with pytest.raises(RuntimeError, match="injected"):
        service.simulate_world_tour_finals_on_branch_atomically(
            BranchSimulateWorldTourFinalsCommand(
                "source", branch_id, head, "finals", "rollback", True
            )
        )
    assert _snapshot(repository) == before


def test_existing_qualification_is_preserved_and_existing_result_conflicts(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    run, state = service._load_run_context(run_id="source")
    orchestrator = service._load_players_by_id_for_run(run_info=run)
    from beta_engine.application.finals_service import FinalsOrchestrationService

    qualification = FinalsOrchestrationService(repository).derive_qualification(
        run=run, state=state, players_by_id=orchestrator
    )
    repository.upsert_finals_qualification(
        run_id=run.run_id, season=run.season,
        source_as_of_season=qualification.source_as_of_season,
        source_as_of_week=qualification.source_as_of_week,
        qualification=qualification.qualification,
    )
    result = service.simulate_world_tour_finals_on_branch_atomically(
        BranchSimulateWorldTourFinalsCommand(
            "source", branch_id, head, "finals", "existing qualification", True
        )
    )
    persisted = repository.get_finals_qualification(run_id=run.run_id, season=run.season)
    assert persisted.qualification == qualification.qualification
    before = _snapshot(repository)
    with pytest.raises(BranchSimulationConflictError, match="already exists"):
        service.simulate_world_tour_finals_on_branch_atomically(
            BranchSimulateWorldTourFinalsCommand(
                "source", branch_id, result.new_head_checkpoint_id,
                "different-finals", "existing result", True,
            )
        )
    assert _snapshot(repository) == before


def test_reviewed_finals_descriptor_mismatch_is_rejected(tmp_path, monkeypatch):
    repository, service, branch_id, head = _setup(tmp_path)
    original = repository.get_finals_phase_descriptor

    def review_then_insert(*, run_id, season):
        reviewed = original(run_id=run_id, season=season)
        run, state = service._load_run_context(run_id=run_id)
        from beta_engine.application.finals_service import FinalsOrchestrationService
        derived = FinalsOrchestrationService(repository).derive_qualification(
            run=run, state=state,
            players_by_id=service._load_players_by_id_for_run(run_info=run),
        )
        repository.upsert_finals_qualification(
            run_id=run_id, season=season,
            source_as_of_season=derived.source_as_of_season,
            source_as_of_week=derived.source_as_of_week,
            qualification=derived.qualification,
        )
        return reviewed

    monkeypatch.setattr(repository, "get_finals_phase_descriptor", review_then_insert)
    with pytest.raises(BranchSimulationConflictError, match="changed after review"):
        service.simulate_world_tour_finals_on_branch_atomically(
            BranchSimulateWorldTourFinalsCommand(
                "source", branch_id, head, "finals", "descriptor race", True
            )
        )
    snapshot = _snapshot(repository)
    assert len(snapshot["finals_qualification"]) == 1
    assert snapshot["finals_results"] == []
    assert not any(row["command_id"] == "finals" for row in snapshot["branch_simulation_commands"])
