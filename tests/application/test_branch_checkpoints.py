from __future__ import annotations

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine


def _repository(tmp_path) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'checkpoints.db'}"))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def test_initial_checkpoint_is_capture_only_idempotent_and_hash_verified(tmp_path) -> None:
    repository = _repository(tmp_path)
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="checkpoint-run", season=2027, seed=7, config_version="v1", config_fingerprint="cfg")
    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="checkpoint-run", command_id="capture-1")
    repeated = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="checkpoint-run", command_id="capture-1")
    assert checkpoint == repeated
    assert checkpoint.kind == "initial"
    assert checkpoint.parent_checkpoint_id is None
    assert checkpoint.payload["fork_capability"] == "not_forkable_player_state_not_migrated"
    assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
    branch = repository.get_run_branch(branch_id=checkpoint.branch_id)
    assert branch is not None and branch.head_checkpoint_id == checkpoint.checkpoint_id


def test_canonical_checkpoint_hash_is_order_independent_and_detects_tampering(tmp_path) -> None:
    repository = _repository(tmp_path)
    assert repository.checkpoint_content_hash({"b": [1, 2], "a": None}) == repository.checkpoint_content_hash({"a": None, "b": [1, 2]})
    assert repository.checkpoint_content_hash({"a": 1}) != repository.checkpoint_content_hash({"a": 2})
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="tamper-run", season=2027, seed=8, config_version=None, config_fingerprint=None)
    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="tamper-run")
    assert repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
    with repository._session_factory.begin() as session:  # deliberate corruption verifies stored integrity checks
        from beta_engine.infrastructure.db.models import BranchCheckpointModel
        session.get(BranchCheckpointModel, checkpoint.checkpoint_id).payload_json = '{"tampered":true}'
    assert not repository.verify_branch_checkpoint_hash(checkpoint_id=checkpoint.checkpoint_id)
