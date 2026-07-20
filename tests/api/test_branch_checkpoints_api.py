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


def test_capture_current_branch_checkpoint_requires_head_then_is_idempotent(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'checkpoint-current-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "checkpoint-current", "seed": 12, "season": 2027})
        assert status == 201
        status, rejected = _request("POST", f"{server.base_url}/branch-checkpoints/capture-current", {"simulation_run_id": "checkpoint-current"})
        assert status == 400 and "no existing head checkpoint" in rejected["detail"]
        status, initial = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "checkpoint-current"})
        assert status == 200
        status, current = _request("POST", f"{server.base_url}/branch-checkpoints/capture-current", {"simulation_run_id": "checkpoint-current", "command_id": "current-api"})
        assert status == 200
        assert current["parent_checkpoint_id"] == initial["checkpoint_id"]
        assert current["sequence"] == initial["sequence"] + 1
        status, repeated = _request("POST", f"{server.base_url}/branch-checkpoints/capture-current", {"simulation_run_id": "checkpoint-current", "command_id": "current-api"})
        assert status == 200 and repeated["checkpoint_id"] == current["checkpoint_id"]
        status, default = _request("POST", f"{server.base_url}/branch-checkpoints/capture-current", {"simulation_run_id": "checkpoint-current"})
        assert status == 200
        status, default_repeated = _request("POST", f"{server.base_url}/branch-checkpoints/capture-current", {"simulation_run_id": "checkpoint-current"})
        assert status == 200 and default_repeated["checkpoint_id"] == default["checkpoint_id"]
        status, listed = _request("GET", f"{server.base_url}/branch-checkpoints?branch_id={current['branch_id']}")
        assert status == 200 and [item["sequence"] for item in listed["branch_checkpoints"]] == [1, 2, 3]
        status, branch_state = _request("GET", f"{server.base_url}/branch-states/{current['branch_id']}")
        assert status == 200 and branch_state["head_checkpoint_id"] == default["checkpoint_id"]


def test_capture_completed_event_branch_checkpoint_api(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'checkpoint-event-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "checkpoint-event", "seed": 12, "season": 2027})
        assert status == 201
        status, rejected = _request("POST", f"{server.base_url}/branch-checkpoints/capture-completed-event", {"simulation_run_id": "checkpoint-event", "event_sequence": 0})
        assert status == 400
        status, initial = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "checkpoint-event"})
        assert status == 200
        status, simulated = _request("POST", f"{server.base_url}/runs/checkpoint-event/simulate/next-tournament")
        assert status == 200
        event_id = simulated["step"]["tournament_result"]["event"]["event_id"]
        status, current = _request("POST", f"{server.base_url}/branch-checkpoints/capture-current", {"simulation_run_id": "checkpoint-event"})
        assert status == 200
        status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-completed-event", {"simulation_run_id": "checkpoint-event", "event_id": event_id})
        assert status == 200 and checkpoint["kind"] == "event_completed"
        assert checkpoint["parent_checkpoint_id"] == current["checkpoint_id"]
        status, repeated = _request("POST", f"{server.base_url}/branch-checkpoints/capture-completed-event", {"simulation_run_id": "checkpoint-event", "event_id": event_id, "command_id": "different"})
        assert status == 200 and repeated["checkpoint_id"] == checkpoint["checkpoint_id"]
        status, listed = _request("GET", f"{server.base_url}/branch-checkpoints?branch_id={checkpoint['branch_id']}")
        assert status == 200 and [item["kind"] for item in listed["branch_checkpoints"]] == ["initial", "current_state_capture", "event_completed"]
        status, branch_state = _request("GET", f"{server.base_url}/branch-states/{checkpoint['branch_id']}")
        assert status == 200 and branch_state["head_checkpoint_id"] == checkpoint["checkpoint_id"]


def test_branch_state_inspection_is_read_only_and_filterable(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'branch-state-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, run = _request("POST", f"{server.base_url}/runs", {"run_id": "branch-state-api", "seed": 12, "season": 2027})
        assert status == 201
        status, empty = _request("GET", f"{server.base_url}/branch-states")
        assert status == 200 and len(empty["branch_states"]) == 1
        branch_state = empty["branch_states"][0]
        assert branch_state["run_id"] == run["run_id"] and branch_state["head_checkpoint_id"] is None
        status, filtered = _request("GET", f"{server.base_url}/branch-states?run_id=branch-state-api")
        assert status == 200 and filtered == empty
        status, detail = _request("GET", f"{server.base_url}/branch-states/{branch_state['branch_id']}")
        assert status == 200 and detail == branch_state
        status, missing = _request("GET", f"{server.base_url}/branch-states/missing")
        assert status == 404 and "not found" in missing["detail"]


def test_capture_completed_week_branch_checkpoint_api(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'checkpoint-week-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, state = _request("POST", f"{server.base_url}/runs", {"run_id": "checkpoint-week", "seed": 12, "season": 2027})
        assert status == 201
        status, run_state = _request("GET", f"{server.base_url}/runs/checkpoint-week")
        assert status == 200
        week = run_state["season_state"]["ordered_events"][0]["week"]
        status, rejected = _request("POST", f"{server.base_url}/branch-checkpoints/capture-completed-week", {"simulation_run_id": "checkpoint-week", "week": week})
        assert status == 400
        status, initial = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "checkpoint-week"})
        assert status == 200
        status, rejected = _request("POST", f"{server.base_url}/branch-checkpoints/capture-completed-week", {"simulation_run_id": "checkpoint-week", "week": week})
        assert status == 400 and "not completed" in rejected["detail"]
        status, _ = _request("POST", f"{server.base_url}/runs/checkpoint-week/simulate/next-week")
        assert status == 200
        status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-completed-week", {"simulation_run_id": "checkpoint-week", "week": week})
        assert status == 200 and checkpoint["kind"] == "week_completed" and checkpoint["parent_checkpoint_id"] == initial["checkpoint_id"]
        status, repeated = _request("POST", f"{server.base_url}/branch-checkpoints/capture-completed-week", {"simulation_run_id": "checkpoint-week", "week": week, "command_id": "different"})
        assert status == 200 and repeated["checkpoint_id"] == checkpoint["checkpoint_id"]
        status, listed = _request("GET", f"{server.base_url}/branch-checkpoints?branch_id={checkpoint['branch_id']}")
        assert status == 200 and [item["sequence"] for item in listed["branch_checkpoints"]] == [1, 2]
        status, branch_state = _request("GET", f"{server.base_url}/branch-states/{checkpoint['branch_id']}")
        assert status == 200 and branch_state["head_checkpoint_id"] == checkpoint["checkpoint_id"]
