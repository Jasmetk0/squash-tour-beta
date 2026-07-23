from __future__ import annotations

from test_simulation_api import ApiServer, _request


def test_admin_branch_next_match_success_and_exact_replay(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'branch-next-match-api.db'}") as server:
        assert _request("POST", f"{server.base_url}/runs", {"run_id": "source", "seed": 47, "season": 2027})[0] == 201
        status, branches = _request("GET", f"{server.base_url}/run-branches?run_id=source")
        assert status == 200
        branch_id = branches["run_branches"][0]["branch_id"]
        status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "source"})
        assert status == 200
        payload = {"expected_head_checkpoint_id": checkpoint["checkpoint_id"], "command_id": "api-next-match-1", "audit_reason": "test execution", "explicit_confirmation": True}
        url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-next-match"
        status, result = _request("POST", url, payload)
        assert status == 200
        assert result["official_branch_changed"] is False
        assert result["idempotent_replay"] is False
        status, replay = _request("POST", url, payload)
        assert status == 200
        assert replay["idempotent_replay"] is True
        assert replay["new_head_checkpoint_id"] == result["new_head_checkpoint_id"]
