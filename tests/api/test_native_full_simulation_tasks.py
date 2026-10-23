"""Actual server dispatcher, HTTP sporting services and physically reopened SQLite."""

import time

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import inspect, save_tour, setup
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def scope(server):
    return server.base_url + "/admin/runs/run/branches/branch/authoritative-simulation/full-simulation"


def reviewed(server, target=None, name="native-full"):
    request = {"schema_version": "authoritative_full_simulation_command.v2", "command_id": name,
        "seed": 231, "operator_label": "Admin", "audit_reason": "Real native server task acceptance",
        "target_week": target}
    code, preview = _request("POST", scope(server) + "/native/preview", request)
    assert code == 200, preview
    return {**preview["request"], "execution_calendar": preview["execution_calendar"],
        "expected_start_week": preview["start_week"],
        "expected_position_fingerprint": preview["expected_position_fingerprint"],
        "expected_revision_id": preview["expected_revision_id"],
        "expected_preview_fingerprint": preview["preview_fingerprint"]}


def wait(server, task_id):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        code, result = _request("GET", scope(server) + "/tasks/" + task_id)
        assert code == 200, result
        task = result["tasks"][0]
        if task["state"] in {"awaiting_operator", "paused", "failed", "target_reached", "complete", "stopped"} and task["lease_expires_at_unix"] is None:
            assert task["state"] != "failed", task
            return task
        time.sleep(0.04)
    raise AssertionError(task)


def start(server, command):
    body = {"request_id": "start-" + command["command_id"], "command": command}
    code, ack = _request("POST", scope(server) + "/tasks", body)
    assert code == 202, ack
    assert _request("POST", scope(server) + "/tasks", body) == (202, ack)
    return wait(server, ack["task_id"])


def resume(server, task, request_id):
    body = {"request_id": request_id, "action": "resume", "expected_revision": task["revision"],
        "operator_label": "Admin", "audit_reason": "Saved and reviewed; continue the same original task"}
    code, result = _request("POST", scope(server) + "/tasks/" + task["task_id"] + "/continue", body)
    assert code == 202, result
    return wait(server, task["task_id"])


def test_native_task_real_transition_save_target_restart_and_original_replay(tmp_path):
    db = f"sqlite:///{tmp_path / 'native-task.db'}"
    with ApiServer(database_url=db) as server:
        setup(server, RunCalendar(4, 4, 2030, 3), count=4)
        command = reviewed(server, {"season_index": 0, "week": 3})
        task = start(server, command)
        assert task["checkpoint"] == "native_manual_save_required"
        assert task["current_week"] == {"season_index": 0, "week": 3}
        assert not inspect(server)["saved"]
        save_tour(server)
        task = resume(server, task, "after-week-save")
        assert task["state"] == "target_reached"
        assert task["original_command"] == command
        task_id = task["task_id"]
    with ApiServer(database_url=db) as restarted:
        task = wait(restarted, task_id)
        assert task["state"] == "target_reached"
        assert task["original_command"] == command
        assert len(inspect(restarted)["state"]["transitions"]) == 1
        assert _request("POST", scope(restarted) + "/tasks", {"request_id": "start-native-full", "command": command})[0] == 202
        assert len(inspect(restarted)["state"]["transitions"]) == 1
