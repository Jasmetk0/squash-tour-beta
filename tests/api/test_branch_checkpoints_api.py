from __future__ import annotations

from test_simulation_api import ApiServer, _request


def test_capture_and_inspect_initial_branch_checkpoint(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'checkpoint-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, run = _request("POST", f"{server.base_url}/runs", {"run_id": "checkpoint-api", "seed": 12, "season": 2027})
        assert status == 201 and run["run_id"] == "checkpoint-api"

        status, checkpoint = _request(
            "POST",
            f"{server.base_url}/branch-checkpoints/capture-initial",
            {"simulation_run_id": "checkpoint-api", "command_id": "initial-api"},
        )
        assert status == 200
        assert checkpoint["payload"]["fork_capability"] == "not_forkable_player_state_not_migrated"
        assert checkpoint["payload"]["limitations"]["forkable"] is False

        status, repeated = _request(
            "POST",
            f"{server.base_url}/branch-checkpoints/capture-initial",
            {"simulation_run_id": "checkpoint-api", "command_id": "initial-api"},
        )
        assert status == 200 and repeated["checkpoint_id"] == checkpoint["checkpoint_id"]
        status, second_command = _request(
            "POST",
            f"{server.base_url}/branch-checkpoints/capture-initial",
            {"simulation_run_id": "checkpoint-api", "command_id": "other-initial-api"},
        )
        assert status == 200 and second_command["checkpoint_id"] == checkpoint["checkpoint_id"]

        status, listed = _request("GET", f"{server.base_url}/branch-checkpoints")
        assert status == 200 and [item["checkpoint_id"] for item in listed["branch_checkpoints"]] == [checkpoint["checkpoint_id"]]
        status, branch_listed = _request("GET", f"{server.base_url}/branch-checkpoints?branch_id={checkpoint['branch_id']}")
        assert status == 200 and branch_listed == listed
        status, run_listed = _request("GET", f"{server.base_url}/branch-checkpoints?run_id={checkpoint['run_id']}")
        assert status == 200 and run_listed == listed
        status, fetched = _request("GET", f"{server.base_url}/branch-checkpoints/{checkpoint['checkpoint_id']}")
        assert status == 200 and fetched["content_hash"] == checkpoint["content_hash"]

        status, runs = _request("GET", f"{server.base_url}/runs")
        assert status == 200 and any(item["run_id"] == "checkpoint-api" for item in runs["runs"])


def test_capture_initial_uses_a_deterministic_default_command_id(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'checkpoint-default-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "checkpoint-default", "seed": 12, "season": 2027})
        assert status == 201
        status, checkpoint = _request(
            "POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "checkpoint-default"}
        )
        assert status == 200
        status, repeated = _request(
            "POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "checkpoint-default"}
        )
        assert status == 200 and repeated["checkpoint_id"] == checkpoint["checkpoint_id"]
