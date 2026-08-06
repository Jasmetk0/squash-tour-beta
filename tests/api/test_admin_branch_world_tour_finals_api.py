from __future__ import annotations

from test_simulation_api import ApiServer, _request


def test_admin_branch_world_tour_finals_typed_success_and_replay(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'api-finals.db'}"
    with ApiServer(database_url=database_url) as server:
        assert _request("POST", f"{server.base_url}/runs", {"run_id": "source", "seed": 47, "season": 2027})[0] == 201
        _, branches = _request("GET", f"{server.base_url}/run-branches?run_id=source")
        branch_id = branches["run_branches"][0]["branch_id"]
        _, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "source"})
        common = {"audit_reason": "test", "explicit_confirmation": True}
        full_url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-full-season"
        status, regular = _request("POST", full_url, {**common, "expected_head_checkpoint_id": checkpoint["checkpoint_id"], "command_id": "regular"})
        assert status == 200
        url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-world-tour-finals"
        payload = {**common, "expected_head_checkpoint_id": regular["new_head_checkpoint_id"], "command_id": "finals"}
        status, result = _request("POST", url, payload)
        assert status == 200
        assert result["finals"]["already_simulated"] is False
        assert result["finals"]["event_id"] == "WORLD_TOUR_FINALS"
        assert result["official_branch_changed"] is False
        assert result["previous_season"] == result["current_season"]
        assert _request("POST", url, payload)[1]["idempotent_replay"] is True
        assert _request("POST", url, {**payload, "audit_reason": "changed"})[0] == 409


def test_admin_branch_world_tour_finals_validation(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'validation.db'}") as server:
        url = f"{server.base_url}/admin/runs/missing/branches/missing/simulate-world-tour-finals"
        payload = {"expected_head_checkpoint_id": "head", "command_id": "finals", "audit_reason": "test", "explicit_confirmation": True}
        assert _request("POST", url, payload)[0] == 404
        assert _request("POST", url, {**payload, "explicit_confirmation": False})[0] == 400
