from __future__ import annotations

import hashlib
from dataclasses import replace

from sqlalchemy import inspect

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import BranchCheckpointModel, BranchStateModel, RunBranchModel


def _repository(tmp_path) -> SimulationPersistenceRepository:
    tmp_path.mkdir(parents=True, exist_ok=True)
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'checkpoints.db'}"))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def test_initial_checkpoint_is_capture_only_idempotent_and_hash_verified(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="checkpoint-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")

    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(
        simulation_run_id="checkpoint-run", command_id="capture-1"
    )
    assert checkpoint == repository.capture_initial_checkpoint_for_legacy_simulation_run(
        simulation_run_id="checkpoint-run", command_id="capture-1"
    )
    assert checkpoint == repository.capture_initial_checkpoint_for_legacy_simulation_run(
        simulation_run_id="checkpoint-run", command_id="different-capture-command"
    )
    assert checkpoint.kind == "initial"
    assert checkpoint.parent_checkpoint_id is None
    expected_suffix = hashlib.sha256(f"{checkpoint.branch_id}\x00capture-1".encode("utf-8")).hexdigest()[:24]
    assert checkpoint.checkpoint_id == f"checkpoint-{expected_suffix}"
    assert checkpoint.payload["fork_capability"] == "not_forkable_player_state_not_migrated"
    assert checkpoint.payload["capture_mode"] == "legacy_initial_capture_only"
    assert checkpoint.payload["limitations"] == {
        "forkable": False,
        "player_state": "hash_only_or_not_migrated",
        "prospects": "legacy_run_scoped_not_captured_as_durable_identity",
    }
    assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
    branch = repository.get_run_branch(branch_id=checkpoint.branch_id)
    assert branch is not None and branch.head_checkpoint_id == checkpoint.checkpoint_id


def test_initial_checkpoint_default_command_is_idempotent_and_does_not_overwrite_head(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="default-command-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    branch = repository.ensure_default_branch_for_simulation_run(simulation_run_id="default-command-run")
    assert branch is not None
    with repository._session_factory.begin() as session:
        session.get(RunBranchModel, branch.branch_id).head_checkpoint_id = "preexisting-head"

    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="default-command-run")
    assert checkpoint == repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="default-command-run")
    assert checkpoint == repository.capture_initial_checkpoint_for_legacy_simulation_run(
        simulation_run_id="default-command-run", command_id="another-command"
    )
    branch = repository.get_run_branch(branch_id=checkpoint.branch_id)
    assert branch is not None and branch.head_checkpoint_id == "preexisting-head"
    state = repository.get_branch_state(branch_id=checkpoint.branch_id)
    assert state is not None and state.head_checkpoint_id == "preexisting-head"
    assert state.current_season is None


def test_branch_state_backfill_and_initial_checkpoint_metadata_are_idempotent(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()
    assert "branch_states" in inspect(repository._engine).get_table_names()
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="branch-state-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    branch = repository.ensure_default_branch_for_simulation_run(simulation_run_id="branch-state-run")
    assert branch is not None
    empty_state = repository.get_branch_state(branch_id=branch.branch_id)
    assert empty_state is not None and empty_state.head_checkpoint_id is None

    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="branch-state-run")
    state = repository.get_branch_state(branch_id=branch.branch_id)
    assert state is not None
    assert state.head_checkpoint_id == checkpoint.checkpoint_id
    assert (state.current_season, state.current_week, state.current_event_id, state.current_event_sequence) == (
        checkpoint.season, checkpoint.week, checkpoint.event_id, checkpoint.event_sequence,
    )
    repository.backfill_branch_states_for_existing_branches()
    repository.backfill_branch_states_for_existing_branches()
    with repository._session_factory() as session:
        assert session.query(BranchStateModel).count() == 1


def test_checkpoint_envelope_hash_is_order_independent_and_protects_all_envelope_fields(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="envelope-run", season=2027, seed=8, config_version=None, config_fingerprint=None)
    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="envelope-run")

    reordered = replace(
        checkpoint,
        seed_namespace={key: checkpoint.seed_namespace[key] for key in reversed(checkpoint.seed_namespace)},
        payload={key: checkpoint.payload[key] for key in reversed(checkpoint.payload)},
    )
    assert repository.checkpoint_envelope_content_hash(checkpoint) == repository.checkpoint_envelope_content_hash(reordered)
    assert repository.checkpoint_envelope_content_hash(checkpoint) != repository.checkpoint_envelope_content_hash(
        replace(checkpoint, command_id="other-command")
    )
    assert repository.checkpoint_envelope_content_hash(checkpoint) != repository.checkpoint_envelope_content_hash(
        replace(checkpoint, payload={**checkpoint.payload, "different": True})
    )
    assert repository.checkpoint_envelope_content_hash(checkpoint) != repository.checkpoint_envelope_content_hash(
        replace(checkpoint, seed_namespace={**checkpoint.seed_namespace, "namespace": "changed"})
    )
    assert repository.checkpoint_content_hash({"b": [1, 2], "a": None}) == repository.checkpoint_content_hash({"a": None, "b": [1, 2]})


def test_checkpoint_hash_verification_detects_direct_database_tampering(tmp_path) -> None:
    fields_and_values = {
        "payload_json": '{"tampered":true}',
        "command_id": "tampered-command",
        "sequence": 99,
        "branch_id": "tampered-branch",
        "run_id": "tampered-run",
        "kind": "tampered-kind",
    }
    for field, value in fields_and_values.items():
        repository = _repository(tmp_path / field)
        service = SimulationApiService(repository=repository)
        service.initialize_run(run_id=f"tamper-{field}", season=2027, seed=8, config_version=None, config_fingerprint=None)
        checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id=f"tamper-{field}")
        with repository._session_factory.begin() as session:  # Deliberate corruption verifies stored integrity checks.
            setattr(session.get(BranchCheckpointModel, checkpoint.checkpoint_id), field, value)
        assert not repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id), field
