from __future__ import annotations

from test_simulation_api import ApiServer, _request


def test_capture_and_inspect_initial_branch_checkpoint(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'checkpoint-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, run = _request("POST", f"{server.base_url}/runs", {"run_id": "checkpoint-api", "seed": 12, "season": 2027})
        assert status == 201 and run["run_id"] == "checkpoint-api"
        status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "checkpoint-api", "command_id": "initial-api"})
        assert status == 200
        assert checkpoint["payload"]["fork_capability"] == "not_forkable_player_state_not_migrated"
        status, repeated = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "checkpoint-api", "command_id": "initial-api"})
        assert status == 200 and repeated["checkpoint_id"] == checkpoint["checkpoint_id"]
        status, listed = _request("GET", f"{server.base_url}/branch-checkpoints?branch_id={checkpoint['branch_id']}")
        assert status == 200 and [item["checkpoint_id"] for item in listed["branch_checkpoints"]] == [checkpoint["checkpoint_id"]]
        status, fetched = _request("GET", f"{server.base_url}/branch-checkpoints/{checkpoint['checkpoint_id']}")
        assert status == 200 and fetched["content_hash"] == checkpoint["content_hash"]
