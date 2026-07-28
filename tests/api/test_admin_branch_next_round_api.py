from __future__ import annotations

from test_simulation_api import ApiServer, _request


def test_admin_branch_next_round_success_and_exact_replay(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'branch-next-round-api.db'}") as server:
        assert _request("POST", f"{server.base_url}/runs", {"run_id": "source", "seed": 47, "season": 2027})[0] == 201
        status, branches = _request("GET", f"{server.base_url}/run-branches?run_id=source")
        assert status == 200
        branch_id = branches["run_branches"][0]["branch_id"]
        status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "source"})
        assert status == 200
        payload = {"expected_head_checkpoint_id": checkpoint["checkpoint_id"], "command_id": "api-next-round-1", "audit_reason": "test execution", "explicit_confirmation": True}
        url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-next-round"
        status, result = _request("POST", url, payload)
        assert status == 200
        assert result["official_branch_changed"] is False
        assert result["idempotent_replay"] is False
        status, replay = _request("POST", url, payload)
        assert status == 200
        assert replay["idempotent_replay"] is True
        assert replay["new_head_checkpoint_id"] == result["new_head_checkpoint_id"]
        assert _request("POST", url, {**payload, "audit_reason": "different"})[0] == 409
        assert _request("POST", url, {**payload, "command_id": "same-head"})[0] == 409


def test_admin_branch_next_round_execution_failures_use_404_or_409_not_400(tmp_path):
    from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
    from beta_engine.infrastructure.db.models import RunBranchModel
    database_url = f"sqlite:///{tmp_path / 'branch-next-round-errors.db'}"
    with ApiServer(database_url=database_url) as server:
        assert _request("POST", f"{server.base_url}/runs", {"run_id": "source", "seed": 47, "season": 2027})[0] == 201
        _, branches = _request("GET", f"{server.base_url}/run-branches?run_id=source")
        branch_id = branches["run_branches"][0]["branch_id"]
        _, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "source"})
        payload = {"expected_head_checkpoint_id": checkpoint["checkpoint_id"], "command_id": "failure-1", "audit_reason": "test", "explicit_confirmation": True}
        url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-next-round"
        # Missing bound legacy namespace is a not-found, not generic bad request.
        engine = create_sqlite_engine(DatabaseSettings(url=database_url)); repo = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
        with repo._session_factory.begin() as session:
            session.get(RunBranchModel, branch_id).legacy_simulation_run_id = "missing"
        assert _request("POST", url, payload)[0] == 404
        with repo._session_factory.begin() as session:
            session.get(RunBranchModel, branch_id).legacy_simulation_run_id = "source"
            session.get(RunBranchModel, branch_id).read_only = 1
        assert _request("POST", url, {**payload, "command_id": "failure-2"})[0] == 409
        assert _request("POST", url, {**payload, "command_id": "failure-3", "explicit_confirmation": False})[0] == 400
        assert _request("POST", url, {**payload, "command_id": "failure-4", "audit_reason": "   "})[0] == 400
