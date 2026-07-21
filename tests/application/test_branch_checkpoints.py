from __future__ import annotations

import hashlib
from dataclasses import replace

from sqlalchemy import inspect

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import BranchCheckpointModel, BranchStateModel, RunBranchModel
from beta_engine.infrastructure.db.checkpoint_boundaries import (
    BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE,
    BRANCH_CHECKPOINT_KIND_ADMIN_ACTION_APPLIED,
    BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED,
    BRANCH_CHECKPOINT_KIND_INITIAL,
    BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED,
)


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
    assert checkpoint.kind == BRANCH_CHECKPOINT_KIND_INITIAL
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


def test_current_checkpoint_captures_legacy_state_after_initial_and_moves_heads(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="current-capture-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    before_state = repository.load_season_state(run_id="current-capture-run")
    assert before_state is not None
    initial = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="current-capture-run")

    checkpoint = repository.capture_current_checkpoint_for_legacy_simulation_run(
        simulation_run_id="current-capture-run", command_id="current-1"
    )
    assert checkpoint.kind == BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE
    assert checkpoint.parent_checkpoint_id == initial.checkpoint_id
    assert checkpoint.sequence == initial.sequence + 1
    assert checkpoint.payload["capture_mode"] == "legacy_current_state_capture_only"
    assert checkpoint.payload["fork_capability"] == "not_forkable_player_state_not_migrated"
    assert checkpoint.payload["limitations"] == {
        "forkable": False,
        "player_state": "hash_only_or_not_migrated",
        "prospects": "legacy_run_scoped_not_captured_as_durable_identity",
        "simulation_source": "legacy_simulation_run_state",
    }
    assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
    assert repository.load_season_state(run_id="current-capture-run").model_dump() == before_state.model_dump()
    assert repository.list_run_prospects(run_id="current-capture-run") == []
    branch = repository.get_run_branch(branch_id=checkpoint.branch_id)
    state = repository.get_branch_state(branch_id=checkpoint.branch_id)
    assert branch is not None and branch.head_checkpoint_id == checkpoint.checkpoint_id
    assert state is not None and state.head_checkpoint_id == checkpoint.checkpoint_id


def test_current_checkpoint_requires_existing_head_and_is_idempotent_for_unchanged_state(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="current-idempotency-run", season=2027, seed=7, config_version=None, config_fingerprint=None)
    try:
        repository.capture_current_checkpoint_for_legacy_simulation_run(simulation_run_id="current-idempotency-run")
    except ValueError as exc:
        assert "no existing head checkpoint" in str(exc)
    else:
        raise AssertionError("capture-current must require an initial/head checkpoint")

    repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="current-idempotency-run")
    explicit = repository.capture_current_checkpoint_for_legacy_simulation_run(
        simulation_run_id="current-idempotency-run", command_id="same-current-command"
    )
    assert explicit == repository.capture_current_checkpoint_for_legacy_simulation_run(
        simulation_run_id="current-idempotency-run", command_id="same-current-command"
    )
    default = repository.capture_current_checkpoint_for_legacy_simulation_run(simulation_run_id="current-idempotency-run")
    assert default == repository.capture_current_checkpoint_for_legacy_simulation_run(simulation_run_id="current-idempotency-run")


def test_event_completed_checkpoint_captures_persisted_event_once_without_mutating_legacy_state(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="event-capture-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    try:
        repository.capture_completed_event_checkpoint_for_legacy_simulation_run(simulation_run_id="event-capture-run")
    except ValueError as exc:
        assert "event_id or event_sequence" in str(exc)
    else:
        raise AssertionError("event locator is required")
    try:
        repository.capture_completed_event_checkpoint_for_legacy_simulation_run(simulation_run_id="event-capture-run", event_sequence=0)
    except ValueError as exc:
        assert "completed event locator" in str(exc)
    else:
        raise AssertionError("uncompleted events cannot be captured")
    initial = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="event-capture-run")
    service.simulate_next_tournament(run_id="event-capture-run")
    before_state = repository.load_season_state(run_id="event-capture-run")
    completed = repository.list_completed_events(run_id="event-capture-run")[0]
    current = repository.capture_current_checkpoint_for_legacy_simulation_run(simulation_run_id="event-capture-run")
    checkpoint = repository.capture_completed_event_checkpoint_for_legacy_simulation_run(
        simulation_run_id="event-capture-run", event_id=completed.event_id
    )
    assert checkpoint.kind == BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED
    assert checkpoint.parent_checkpoint_id == current.checkpoint_id
    assert checkpoint.sequence == current.sequence + 1
    assert (checkpoint.event_id, checkpoint.event_sequence) == (completed.event_id, completed.event_sequence)
    assert checkpoint.payload["capture_mode"] == "legacy_event_completed_capture_only"
    assert checkpoint.payload["event"]["source"] == "legacy_completed_event"
    assert checkpoint.payload["completed_event"]["record"]["event_id"] == completed.event_id
    assert checkpoint.payload["limitations"]["forkable"] is False
    assert checkpoint.payload["limitations"]["replayable"] is False
    assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
    assert repository.load_season_state(run_id="event-capture-run").model_dump() == before_state.model_dump()
    assert repository.list_run_prospects(run_id="event-capture-run") == []
    assert repository.capture_completed_event_checkpoint_for_legacy_simulation_run(
        simulation_run_id="event-capture-run", event_sequence=completed.event_sequence, command_id="other-command"
    ) == checkpoint
    branch = repository.get_run_branch(branch_id=checkpoint.branch_id)
    branch_state = repository.get_branch_state(branch_id=checkpoint.branch_id)
    assert branch is not None and branch.head_checkpoint_id == checkpoint.checkpoint_id
    assert branch_state is not None and branch_state.head_checkpoint_id == checkpoint.checkpoint_id
    try:
        repository.capture_completed_event_checkpoint_for_legacy_simulation_run(
            simulation_run_id="event-capture-run", event_id=completed.event_id, event_sequence=completed.event_sequence + 99
        )
    except ValueError as exc:
        assert "different completed events" in str(exc)
    else:
        raise AssertionError("mismatched locators must be rejected")


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


def test_week_completed_checkpoint_captures_completed_scheduled_week_once(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="week-capture-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    state = repository.load_season_state(run_id="week-capture-run")
    assert state is not None
    week = state.ordered_events[0].week
    initial = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="week-capture-run")
    for invalid_week in (0, 62):
        try:
            repository.capture_completed_week_checkpoint_for_legacy_simulation_run(simulation_run_id="week-capture-run", week=invalid_week)
        except ValueError as exc:
            assert "1..61" in str(exc)
        else:
            raise AssertionError("invalid weeks must be rejected")
    try:
        repository.capture_completed_week_checkpoint_for_legacy_simulation_run(simulation_run_id="week-capture-run", week=week)
    except ValueError as exc:
        assert "not completed" in str(exc)
    else:
        raise AssertionError("incomplete weeks must be rejected")
    service.simulate_next_week(run_id="week-capture-run")
    before_state = repository.load_season_state(run_id="week-capture-run")
    assert before_state is not None
    completed = [event for event in repository.list_completed_events(run_id="week-capture-run") if event.week == week]
    checkpoint = repository.capture_completed_week_checkpoint_for_legacy_simulation_run(simulation_run_id="week-capture-run", week=week)
    assert checkpoint.kind == BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED
    assert checkpoint.parent_checkpoint_id == initial.checkpoint_id
    assert checkpoint.sequence == initial.sequence + 1
    assert checkpoint.event_sequence == max(event.event_sequence for event in completed)
    assert checkpoint.payload["week"]["completed_event_ids"] == [event.event_id for event in before_state.ordered_events if event.week == week]
    assert checkpoint.payload["limitations"]["forkable"] is False
    assert checkpoint.payload["limitations"]["replayable"] is False
    assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
    assert repository.load_season_state(run_id="week-capture-run").model_dump() == before_state.model_dump()
    assert repository.list_run_prospects(run_id="week-capture-run") == []
    assert repository.capture_completed_week_checkpoint_for_legacy_simulation_run(simulation_run_id="week-capture-run", week=week) == checkpoint
    assert repository.capture_completed_week_checkpoint_for_legacy_simulation_run(simulation_run_id="week-capture-run", week=week, command_id="different") == checkpoint
    assert repository.get_run_branch(branch_id=checkpoint.branch_id).head_checkpoint_id == checkpoint.checkpoint_id
    assert repository.get_branch_state(branch_id=checkpoint.branch_id).head_checkpoint_id == checkpoint.checkpoint_id


def test_checkpoint_boundary_partial_unique_indexes_are_present_and_bootstrap_is_idempotent(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.bootstrap_schema()
    repository.bootstrap_schema()
    indexes = {item["name"]: item for item in inspect(repository._engine).get_indexes("branch_checkpoints")}
    expected = {
        "uq_branch_checkpoints_one_initial_per_branch": ["branch_id"],
        "uq_branch_checkpoints_one_event_completed_per_branch_event_sequence": ["branch_id", "event_sequence"],
        "uq_branch_checkpoints_one_week_completed_per_branch_season_week": ["branch_id", "season", "week"],
    }
    for name, columns in expected.items():
        assert indexes[name]["unique"]
        assert indexes[name]["column_names"] == columns
        assert "kind" in str(indexes[name]["dialect_options"]["sqlite_where"])


def test_direct_checkpoint_creation_rejects_duplicate_event_and_week_boundaries(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="direct-boundary-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="direct-boundary-run")
    state = repository.load_season_state(run_id="direct-boundary-run")
    assert state is not None
    week = state.ordered_events[0].week
    service.simulate_next_week(run_id="direct-boundary-run")
    event = repository.capture_completed_event_checkpoint_for_legacy_simulation_run(simulation_run_id="direct-boundary-run", event_sequence=0)
    week_checkpoint = repository.capture_completed_week_checkpoint_for_legacy_simulation_run(simulation_run_id="direct-boundary-run", week=week)

    for original, expected in ((event, "event_completed checkpoint"), (week_checkpoint, "week_completed checkpoint")):
        duplicate_without_hash = replace(
            original, checkpoint_id=f"duplicate-{original.checkpoint_id}", command_id=f"duplicate-{original.command_id}", sequence=999,
            content_hash="",
        )
        duplicate = replace(
            duplicate_without_hash, content_hash=repository.checkpoint_envelope_content_hash(duplicate_without_hash)
        )
        try:
            repository.create_branch_checkpoint(duplicate)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("duplicate checkpoint boundary must be rejected")


def test_admin_action_checkpoint_is_capture_only_idempotent_and_moves_heads(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="admin-action-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    with __import__("pytest").raises(ValueError, match="no existing head checkpoint"):
        repository.capture_admin_action_checkpoint_for_legacy_simulation_run(simulation_run_id="admin-action-run", action_sequence=1)
    repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="admin-action-run")
    with __import__("pytest").raises(ValueError, match="was not found"):
        repository.capture_admin_action_checkpoint_for_legacy_simulation_run(simulation_run_id="admin-action-run", action_sequence=1)
    with __import__("pytest").raises(ValueError, match="required"):
        repository.capture_admin_action_checkpoint_for_legacy_simulation_run(simulation_run_id="admin-action-run")
    repository.append_admin_action(run_id="admin-action-run", event_id="event-1", action_kind="assign_wildcards", payload={"assignments": []})
    before_state = repository.load_season_state(run_id="admin-action-run").model_dump()
    before_actions = repository.list_admin_actions(run_id="admin-action-run")
    parent = repository.get_run_branch(branch_id=repository.ensure_default_branch_for_simulation_run(simulation_run_id="admin-action-run").branch_id).head_checkpoint_id
    checkpoint = repository.capture_admin_action_checkpoint_for_legacy_simulation_run(simulation_run_id="admin-action-run", action_sequence=1)
    assert checkpoint.kind == BRANCH_CHECKPOINT_KIND_ADMIN_ACTION_APPLIED
    assert checkpoint.parent_checkpoint_id == parent and checkpoint.sequence == 2
    assert checkpoint.payload["admin_action"]["locator"] == "legacy_admin_action_sequence"
    assert checkpoint.payload["admin"]["target_admin_action_hash"] == repository.checkpoint_content_hash(checkpoint.payload["admin_action"]["record"])
    assert checkpoint.payload["limitations"]["forkable"] is False and checkpoint.payload["limitations"]["replayable"] is False
    assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
    assert repository.capture_admin_action_checkpoint_for_legacy_simulation_run(simulation_run_id="admin-action-run", action_sequence=1, command_id="different") == checkpoint
    assert repository.load_season_state(run_id="admin-action-run").model_dump() == before_state
    assert repository.list_admin_actions(run_id="admin-action-run") == before_actions
    branch = repository.get_run_branch(branch_id=checkpoint.branch_id)
    branch_state = repository.get_branch_state(branch_id=checkpoint.branch_id)
    assert branch is not None and branch.head_checkpoint_id == checkpoint.checkpoint_id
    assert branch_state is not None and branch_state.head_checkpoint_id == checkpoint.checkpoint_id


def test_season_rollover_checkpoint_captures_persisted_artifacts_once_without_mutating_legacy_state(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="rollover-capture-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    try:
        repository.capture_season_rollover_checkpoint_for_legacy_simulation_run(simulation_run_id="rollover-capture-run")
    except ValueError as exc:
        assert "no persisted season rollover" in str(exc)
    else:
        raise AssertionError("a persisted rollover is required")
    initial = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="rollover-capture-run")
    repository.upsert_season_rollover(run_id="rollover-capture-run", from_season=2027, to_season=2028, transitioned_players=0, metadata={"status": "persisted"}, transitions=[], next_player_states=[])
    before_state = repository.load_season_state(run_id="rollover-capture-run").model_dump()
    before_rollovers = repository.list_season_rollovers(run_id="rollover-capture-run")
    before_next_players = repository.list_next_season_players(run_id="rollover-capture-run", to_season=2028)
    checkpoint = repository.capture_season_rollover_checkpoint_for_legacy_simulation_run(simulation_run_id="rollover-capture-run")
    assert checkpoint.kind == "season_rollover"
    assert checkpoint.parent_checkpoint_id == initial.checkpoint_id and checkpoint.sequence == initial.sequence + 1
    assert checkpoint.payload["capture_mode"] == "legacy_season_rollover_capture_only"
    assert checkpoint.payload["rollover"]["locator"] == {"from_season": 2027, "to_season": 2028}
    assert checkpoint.payload["limitations"]["forkable"] is False and checkpoint.payload["limitations"]["replayable"] is False
    assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
    assert repository.load_season_state(run_id="rollover-capture-run").model_dump() == before_state
    assert repository.list_season_rollovers(run_id="rollover-capture-run") == before_rollovers
    assert repository.list_next_season_players(run_id="rollover-capture-run", to_season=2028) == before_next_players
    assert repository.capture_season_rollover_checkpoint_for_legacy_simulation_run(simulation_run_id="rollover-capture-run", command_id="different") == checkpoint
    branch = repository.get_run_branch(branch_id=checkpoint.branch_id)
    state = repository.get_branch_state(branch_id=checkpoint.branch_id)
    assert branch is not None and branch.head_checkpoint_id == checkpoint.checkpoint_id
    assert state is not None and state.head_checkpoint_id == checkpoint.checkpoint_id
    try:
        repository.capture_season_rollover_checkpoint_for_legacy_simulation_run(simulation_run_id="rollover-capture-run", from_season=2026, to_season=2027)
    except ValueError as exc:
        assert "locator does not match" in str(exc)
    else:
        raise AssertionError("rollover locator mismatch must be rejected")
