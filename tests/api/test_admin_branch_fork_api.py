from __future__ import annotations

from test_simulation_api import ApiServer, _request

from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel,
    BranchStateModel,
    LegacySimulationRunMappingModel,
    RunBranchModel,
    SeasonStateModel,
    SimulationRunModel,
)


def _repository(database_url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def _source(server: ApiServer) -> tuple[str, str]:
    status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "source", "seed": 47, "season": 2027})
    assert status == 201
    status, branches = _request("GET", f"{server.base_url}/run-branches?run_id=source")
    assert status == 200
    source_branch_id = branches["run_branches"][0]["branch_id"]
    status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "source"})
    assert status == 200
    return source_branch_id, checkpoint["checkpoint_id"]


def _payload(source_branch_id: str, source_checkpoint_id: str, **changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_branch_id": source_branch_id,
        "source_checkpoint_id": source_checkpoint_id,
        "target_branch_id": "fork-branch",
        "target_branch_display_name": "Fork",
        "target_legacy_simulation_run_id": "fork-legacy",
        "target_branch_seed": 99,
        "command_id": "fork-command",
    }
    payload.update(changes)
    return payload


def test_admin_fork_run_branch_success_and_idempotent_replay(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'fork-api.db'}"
    with ApiServer(database_url=database_url) as server:
        source_branch_id, source_checkpoint_id = _source(server)
        repository = _repository(database_url)
        official_branch_id = repository.get_run_container(run_id="source").official_branch_id
        payload = _payload(source_branch_id, source_checkpoint_id)

        status, result = _request("POST", f"{server.base_url}/admin/runs/source/branches/fork", payload)
        assert status == 200
        assert result["target_branch_id"] == "fork-branch"
        assert result["target_checkpoint_id"]
        assert result["idempotent_replay"] is False
        assert result["created_mapping"] is False
        assert result["official_branch_changed"] is False

        with repository._session_factory() as session:
            assert session.get(RunBranchModel, "fork-branch") is not None
            assert session.get(BranchStateModel, "fork-branch") is not None
            assert session.get(BranchCheckpointModel, result["target_checkpoint_id"]) is not None
            assert session.get(SimulationRunModel, "fork-legacy").seed == 47
            assert session.get(SeasonStateModel, "fork-legacy") is not None
            assert session.get(LegacySimulationRunMappingModel, "fork-legacy") is None
            assert session.get(BranchCheckpointModel, result["target_checkpoint_id"]).kind == "branch_fork_start"
        assert repository.get_run_container(run_id="source").official_branch_id == official_branch_id

        status, replay = _request("POST", f"{server.base_url}/admin/runs/source/branches/fork", payload)
        assert status == 200
        assert replay["idempotent_replay"] is True
        assert replay["target_branch_id"] == result["target_branch_id"]
        assert replay["target_checkpoint_id"] == result["target_checkpoint_id"]
        assert replay["target_legacy_simulation_run_id"] == result["target_legacy_simulation_run_id"]
        with repository._session_factory() as session:
            assert session.query(RunBranchModel).filter_by(branch_id="fork-branch").count() == 1
            assert session.query(BranchCheckpointModel).filter_by(branch_id="fork-branch").count() == 1


def test_admin_fork_run_branch_maps_target_and_command_conflicts_without_partial_data(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'fork-conflicts-api.db'}"
    with ApiServer(database_url=database_url) as server:
        source_branch_id, source_checkpoint_id = _source(server)
        repository = _repository(database_url)
        official_branch_id = repository.get_run_container(run_id="source").official_branch_id
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "existing-namespace", "seed": 1, "season": 2027})
        assert status == 201
        status, conflict = _request("POST", f"{server.base_url}/admin/runs/source/branches/fork", _payload(source_branch_id, source_checkpoint_id, target_legacy_simulation_run_id="existing-namespace"))
        assert status == 409 and "already exists" in conflict["detail"]
        assert repository.get_run_branch(branch_id="fork-branch") is None
        assert repository.get_run_container(run_id="source").official_branch_id == official_branch_id

        status, first = _request("POST", f"{server.base_url}/admin/runs/source/branches/fork", _payload(source_branch_id, source_checkpoint_id))
        assert status == 200
        status, conflict = _request("POST", f"{server.base_url}/admin/runs/source/branches/fork", _payload(source_branch_id, source_checkpoint_id, target_branch_seed=100))
        assert status == 409 and "command_id" in conflict["detail"]
        assert repository.get_run_branch(branch_id="fork-branch").legacy_simulation_run_id == "fork-legacy"
        assert repository.get_run_branch(branch_id="second-fork") is None
        assert repository.get_run_container(run_id="source").official_branch_id == official_branch_id
        assert first["target_checkpoint_id"]


def test_admin_fork_run_branch_maps_source_mismatch_and_request_validation(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'fork-validation-api.db'}"
    with ApiServer(database_url=database_url) as server:
        source_branch_id, initial_checkpoint_id = _source(server)
        status, _ = _request("POST", f"{server.base_url}/branch-checkpoints/capture-current", {"simulation_run_id": "source"})
        assert status == 200
        repository = _repository(database_url)
        official_branch_id = repository.get_run_container(run_id="source").official_branch_id

        status, stale = _request("POST", f"{server.base_url}/admin/runs/source/branches/fork", _payload(source_branch_id, initial_checkpoint_id))
        assert status == 409 and "effective branch head" in stale["detail"]
        assert repository.get_run_branch(branch_id="fork-branch") is None
        assert repository.get_run_container(run_id="source").official_branch_id == official_branch_id

        status, invalid_identifier = _request("POST", f"{server.base_url}/admin/runs/source/branches/fork", _payload(source_branch_id, initial_checkpoint_id, target_branch_id=""))
        assert status == 422 and invalid_identifier["detail"]
        status, invalid_seed = _request("POST", f"{server.base_url}/admin/runs/source/branches/fork", _payload(source_branch_id, initial_checkpoint_id, target_branch_seed="not-an-integer"))
        assert status == 422 and invalid_seed["detail"]
