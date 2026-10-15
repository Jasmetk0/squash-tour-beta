"""Real production HTTP/TCP + file SQLite + actual sporting children."""

import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from beta_engine.infrastructure.db.models import FullSimulationTaskModel
from tests.api.test_saved_revision_history_api import _request
from tests.application.test_full_simulation_http_flow import reviewed_command
from tests.support.full_simulation_http_flow import (
    expire,
    initialize,
    make_server,
    routes,
    snapshot,
)


def wait_task(server, root, task_id, states):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        status, result = _request(
            "GET", server.base_url + root + "/full-simulation/tasks/" + task_id
        )
        assert status == 200, result
        task = result["tasks"][0]
        if task["state"] in states:
            return task
        time.sleep(0.05)
    raise AssertionError(task)


def continuation(server, flow, task, action="resume", request_id="continue"):
    body = {
        "request_id": request_id,
        "action": action,
        "expected_revision": task["revision"],
        "operator_label": "Task operator",
        "audit_reason": "Explicitly continue unchanged original intent",
    }
    url = (
        server.base_url
        + flow["scope"]
        + "/full-simulation/tasks/"
        + task["task_id"]
        + "/continue"
    )
    return url, body


@pytest.mark.pr_critical
def test_durable_start_disconnect_pause_resume_stop_and_exact_replay(
    tmp_path, monkeypatch
):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server:
        flow = initialize(server, tmp_path)
        root = flow["scope"]
        url = server.base_url + root
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        command = reviewed_command(server, flow)
        start = {"request_id": "lost-start", "command": command}
        gate.arm()
        status, ack = _request("POST", url + "/full-simulation/tasks", start)
        assert status == 202, ack
        assert gate.reached.wait(40), (
            "worker must continue independently after POST has returned"
        )
        try:
            during = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert len(during["groups"]) >= 1
            assert _request("POST", url + "/full-simulation/tasks", start) == (202, ack)
            assert (
                _request(
                    "POST",
                    url + "/full-simulation/tasks",
                    {"request_id": "other", "command": command},
                )[0]
                == 409
            )
            assert (
                _request("POST", url + "/simulate-full-simulation", command)[0] == 409
            )
            assert (
                _request(
                    "GET",
                    server.base_url
                    + flow["other_scope"]
                    + "/full-simulation/tasks/"
                    + ack["task_id"],
                )[0]
                == 409
            )
            inventory = _request(
                "GET", server.base_url + "/run-containers/full-simulation/tasks"
            )[1]
            assert inventory["tasks"][0]["task_id"] == ack["task_id"]
            measured = inventory["tasks"][0]["progress_evidence"]
            assert measured["kind"] == "live_branch"
            assert measured["receipt_scope"] == "branch_current_week"
            assert measured["committed_group_receipts_this_week"] == len(during["groups"])
            assert measured["completed_slot_receipts_this_week"] >= 1
            assert measured["weeks_advanced_since_start"] == 0
            assert inventory["tasks"][0]["heartbeat_health"] == "recent"
            assert "owner_token" not in json.dumps(inventory)
            pause = {
                "control_command_id": "pause",
                "target_command_id": command["command_id"],
                "action": "pause",
                "operator_label": "Operator",
                "audit_reason": "Pause task safely",
            }
            assert _request("POST", url + "/full-simulation/control", pause)[0] == 200
        finally:
            gate.release.set()
        paused = wait_task(server, root, ack["task_id"], {"paused"})
        resumed_url, resume = continuation(server, flow, paused)
        gate.arm(after_groups=len(during["groups"]))
        resumed = _request("POST", resumed_url, resume)
        assert resumed[0] == 202, resumed
        assert _request("POST", resumed_url, resume) == resumed
        assert gate.reached.wait(40)
        try:
            progressed = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert len(progressed["groups"]) > len(during["groups"])
            assert (
                _request(
                    "POST",
                    url + "/full-simulation/control",
                    pause
                    | {
                        "control_command_id": "stop",
                        "action": "stop",
                        "audit_reason": "Finish safely",
                    },
                )[0]
                == 200
            )
        finally:
            gate.release.set()
        stopped = wait_task(server, root, ack["task_id"], {"stopped"})
        summary = _request("GET", url + "/full-simulation/parents/" + command["command_id"] + "/summary")[1]["summary"]
        assert stopped["progress_evidence"]["kind"] == "terminal_frozen"
        assert stopped["progress_evidence"]["week"] == summary["end_week"]
        assert stopped["current_week"] == summary["end_week"]
        assert stopped["progress_evidence"]["committed_group_receipts_this_week"] is None
        assert stopped["progress_evidence"]["completed_slot_receipts_this_week"] is None
        assert stopped["original_command"]["command_id"] == command["command_id"]
        assert _request("POST", url + "/full-simulation/tasks", start) == (202, ack)
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"] == progressed["groups"]
        assert after["saved"] == before["saved"]
        assert all(after["groups"][k] == v for k, v in during["groups"].items())
        assert _request(
            "GET",
            url + "/full-simulation/parents/" + command["command_id"] + "/summary",
        )[1]["available"]


@pytest.mark.pr_critical
def test_task_waits_at_real_manual_checkpoint_and_corruption_fails_closed(tmp_path):
    server, factory, _ = make_server(tmp_path)
    with server:
        flow = initialize(server, tmp_path)
        url = server.base_url + flow["scope"]
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        command = reviewed_command(server, flow)
        status, ack = _request(
            "POST",
            url + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202, ack
        waiting = wait_task(
            server, flow["scope"], ack["task_id"], {"awaiting_operator", "failed"}
        )
        assert waiting["state"] == "awaiting_operator", waiting
        assert waiting["needs_operator_action"]
        assert waiting["checkpoint"]
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"] and after["saved"] == before["saved"]
        # GET and exact acknowledgement replay never re-enqueue a waiting task.
        assert _request(
            "POST",
            url + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        ) == (202, ack)
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after
        # Idle pause is acknowledged without executing more sport; a stale
        # continuation revision cannot implicitly resume it.
        assert (
            _request(
                "POST",
                url + "/full-simulation/control",
                {
                    "control_command_id": "idle-pause",
                    "target_command_id": command["command_id"],
                    "action": "pause",
                    "operator_label": "Idle controller",
                    "audit_reason": "Pause waiting task",
                },
            )[0]
            == 200
        )
        paused = wait_task(server, flow["scope"], ack["task_id"], {"paused"})
        stale_url, stale = continuation(server, flow, waiting)
        assert _request("POST", stale_url, stale)[0] == 409
        after_pause = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert (
            after_pause["groups"] == after["groups"]
            and after_pause["saved"] == after["saved"]
        )
        after = after_pause
        assert paused["revision"] > waiting["revision"]
        with factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(FullSimulationTaskModel, ack["task_id"])
            data = json.loads(row.payload_json)
            data["events"][0]["state"] = "complete"
            row.payload_json = json.dumps(data)
        assert _request("GET", url + "/full-simulation/tasks")[0] == 409
        assert (
            _request(
                "POST",
                url + "/full-simulation/tasks",
                {"request_id": "start", "command": command},
            )[0]
            == 409
        )
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after


@pytest.mark.pr_critical
def test_expired_worker_recovery_fences_old_owner_and_reuses_same_children(
    tmp_path, monkeypatch
):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server:
        flow = initialize(server, tmp_path)
        url = server.base_url + flow["scope"]
        command = reviewed_command(server, flow)
        gate.arm()
        status, ack = _request(
            "POST",
            url + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202 and gate.reached.wait(40)
        try:
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            active = wait_task(server, flow["scope"], ack["task_id"], {"active"})
            recover_url, recover = continuation(
                server, flow, active, "recover", "recover"
            )
            assert (
                _request("POST", recover_url, recover)[0] == 409
            )  # cannot steal unexpired lease
            expire(factory)
            recovered_view = wait_task(
                server, flow["scope"], ack["task_id"], {"recoverable"}
            )
            recover_url, recover = continuation(
                server, flow, recovered_view, "recover", "recover"
            )
            # A second process-equivalent dispatcher claims while old executor is blocked.
            from beta_engine.application.full_simulation_tasks import (
                FullSimulationTaskWorker,
            )

            second = FullSimulationTaskWorker(factory)
            old = server.app.state.full_simulation_worker
            server.app.state.full_simulation_worker = second
            recovered = _request("POST", recover_url, recover)
            assert recovered[0] == 202, recovered
            assert _request("POST", recover_url, recover) == recovered
            waiting = wait_task(
                server, flow["scope"], ack["task_id"], {"awaiting_operator"}
            )
            after = snapshot(factory, flow["run_id"], flow["branch_id"])
        finally:
            gate.release.set()
            if "old" in locals():
                old.close()
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after
        assert waiting["task_id"] == ack["task_id"]
        assert after["saved"] == before["saved"]
        assert all(after["groups"][k] == v for k, v in before["groups"].items())


@pytest.mark.pr_critical
def test_task_starts_serialize_across_workers_and_runs(tmp_path, monkeypatch):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server, ThreadPoolExecutor(max_workers=2) as pool:
        flow = initialize(server, tmp_path)
        command = reviewed_command(server, flow)
        url = server.base_url + flow["scope"]
        gate.arm()
        try:
            starts = [
                pool.submit(
                    _request,
                    "POST",
                    url + "/full-simulation/tasks",
                    {"request_id": "same", "command": command},
                )
                for _ in range(2)
            ]
            results = [future.result(40) for future in starts]
            assert results[0] == results[1] and results[0][0] == 202, results
            assert gate.reached.wait(40)
            # Another scope cannot take the global claim, even with its own reviewed parent.
            status, denied = _request(
                "POST",
                server.base_url + flow["other_scope"] + "/full-simulation/tasks",
                {"request_id": "competing", "command": command},
            )
            assert (
                status == 409
                and "global execution lease" in denied["detail"]["message"]
            )
            assert (
                snapshot(factory, flow["other_run"], flow["other_branch"])["commands"]
                == {}
            )
        finally:
            gate.release.set()


@pytest.mark.pr_critical
def test_task_corruption_during_live_execution_fences_next_writer(
    tmp_path, monkeypatch
):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server:
        flow = initialize(server, tmp_path)
        command = reviewed_command(server, flow)
        url = server.base_url + flow["scope"]
        gate.arm()
        status, ack = _request(
            "POST",
            url + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202 and gate.reached.wait(40)
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        with factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(FullSimulationTaskModel, ack["task_id"])
            data = json.loads(row.payload_json)
            data["revision"] += 1
            row.payload_json = json.dumps(data)
        gate.release.set()
        # Wait for the disposable dispatcher to exit its current invocation.
        deadline = time.monotonic() + 10
        from beta_engine.infrastructure.db.models import (
            FullSimulationExecutionLeaseModel,
        )

        while time.monotonic() < deadline:
            with factory() as session:
                if session.get(FullSimulationExecutionLeaseModel, "all_runs") is None:
                    break
            time.sleep(0.05)
        assert _request("GET", url + "/full-simulation/tasks")[0] == 409
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == before


@pytest.mark.pr_critical
def test_task_start_rejects_body_scope_and_changed_lost_response_retry(tmp_path):
    server, factory, _ = make_server(tmp_path)
    with server:
        flow = initialize(server, tmp_path)
        command = reviewed_command(server, flow)
        url = server.base_url + flow["scope"]
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert (
            _request(
                "POST",
                url + "/full-simulation/tasks",
                {
                    "request_id": "start",
                    "command": command | {"branch_id": flow["other_branch"]},
                },
            )[0]
            == 409
        )
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == before
        status, _ack = _request(
            "POST",
            url + "/full-simulation/tasks",
            {"request_id": "start", "command": command},
        )
        assert status == 202
        assert (
            _request(
                "POST",
                url + "/full-simulation/tasks",
                {
                    "request_id": "start",
                    "command": command | {"audit_reason": "Changed original"},
                },
            )[0]
            == 409
        )
