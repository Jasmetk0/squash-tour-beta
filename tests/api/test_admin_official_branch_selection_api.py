from __future__ import annotations

from test_simulation_api import ApiServer, _request

from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import OfficialBranchSelectionCommandModel, RunBranchModel


def _repository(url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def _branches(server: ApiServer) -> tuple[str, str]:
    assert _request("POST", f"{server.base_url}/runs", {"run_id": "run", "seed": 47, "season": 2027})[0] == 201
    status, branches = _request("GET", f"{server.base_url}/run-branches?run_id=run")
    assert status == 200
    source = branches["run_branches"][0]["branch_id"]
    status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "run"})
    assert status == 200
    fork = {"source_branch_id": source, "source_checkpoint_id": checkpoint["checkpoint_id"], "target_branch_id": "target", "target_branch_display_name": "Target", "target_legacy_simulation_run_id": "target-legacy", "target_branch_seed": 99, "command_id": "fork"}
    assert _request("POST", f"{server.base_url}/admin/runs/run/branches/fork", fork)[0] == 200
    return source, "target"


def _payload(expected: str | None, **changes: object) -> dict[str, object]:
    result: dict[str, object] = {"expected_current_official_branch_id": expected, "command_id": "select-1", "audit_reason": "Publish reviewed timeline", "explicit_confirmation": True}
    result.update(changes)
    return result


def test_admin_selects_official_branch_atomically_and_idempotently(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'official.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        repository = _repository(url)
        endpoint = f"{server.base_url}/admin/runs/run/branches/{target}/make-official"
        status, result = _request("POST", endpoint, _payload(source))
        assert status == 200
        assert result["previous_official_branch_id"] == source and result["official_branch_id"] == target
        assert result["changed"] is True and result["idempotent_replay"] is False
        status, replay = _request("POST", endpoint, _payload(source))
        assert status == 200 and replay["idempotent_replay"] is True
        with repository._session_factory() as session:
            assert session.query(OfficialBranchSelectionCommandModel).count() == 1
            assert session.get(RunBranchModel, target).read_only == 0
        assert repository.get_run_container(run_id="run").official_branch_id == target


def test_admin_official_branch_selection_conflicts_and_noop(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'official-conflict.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        endpoint = f"{server.base_url}/admin/runs/run/branches/{target}/make-official"
        status, noop = _request("POST", endpoint, _payload(source, expected_current_official_branch_id=source))
        # First switch establishes target; a stale expected pointer must not persist a command.
        assert status == 200 and noop["changed"] is True
        status, stale = _request("POST", endpoint, _payload(source, command_id="stale"))
        assert status == 409
        status, conflict = _request("POST", endpoint, _payload(target, audit_reason="different"))
        assert status == 409
        status, rejected = _request("POST", endpoint, _payload(target, command_id="confirm", explicit_confirmation=False))
        assert status == 400
