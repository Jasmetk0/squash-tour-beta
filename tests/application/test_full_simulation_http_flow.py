"""Production FastAPI TCP + file-backed SQLite with authentic MatchEngine work."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _request
from beta_engine.infrastructure.db.full_simulation_invocation_lease import renew_invocation_lease
from beta_engine.infrastructure.db.models import FullSimulationExecutionLeaseModel
from tests.support.full_simulation_http_flow import (
    expire, initialize, make_server, reclaim, routes, snapshot,
)


def reviewed_command(server, flow, command_id="original-parent"):
    base = {"command_id": command_id, "operator_label": "Original operator",
        "audit_reason": "Original immutable Full Simulation intent"}
    status, review = _request("POST", server.base_url + flow["scope"] + "/full-simulation/preview", base)
    assert status == 200, review
    return base | {"expected_start_week": review["start_week"],
        "expected_position_fingerprint": review["expected_position_fingerprint"],
        "expected_revision_id": review["expected_revision_id"],
        "expected_preview_fingerprint": review["preview_fingerprint"]}


@pytest.mark.pr_critical
def test_http_pause_lost_response_task_center_resume_preserves_children_and_saved_revision(tmp_path, monkeypatch):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server, ThreadPoolExecutor(max_workers=1) as pool:
        flow = initialize(server, tmp_path)
        original = snapshot(factory, flow["run_id"], flow["branch_id"])
        command = reviewed_command(server, flow)
        reference_path = tmp_path / "uninterrupted.sqlite"
        with sqlite3.connect(str(tmp_path / "api.sqlite")) as source, sqlite3.connect(str(reference_path)) as reference:
            source.backup(reference)
        url = server.base_url + flow["scope"]
        gate.arm()
        invocation = pool.submit(_request, "POST", url + "/simulate-full-simulation", command)
        try:
            assert gate.reached.wait(timeout=40)
            committed = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert committed["groups"], "Pause must happen after real sporting work"
            status, competing = _request("POST", server.base_url + flow["other_scope"] + "/simulate-full-simulation", command)
            assert status == 409 and "global execution lease" in competing["detail"]["message"]
            assert snapshot(factory, flow["other_run"], flow["other_branch"])["groups"] == {}
            pause = {"control_command_id": "lost-response-pause", "target_command_id": command["command_id"],
                "action": "pause", "operator_label": "Controller", "audit_reason": "Pause at transaction boundary"}
            # Deliberately discard the first real HTTP answer after the server commits.
            assert _request("POST", url + "/full-simulation/control", pause)[0] == 200
            status, retry = _request("POST", url + "/full-simulation/control", pause)
            assert status == 200 and retry["replayed"] is True
        finally:
            gate.release.set()
        status, paused = invocation.result(timeout=40)
        assert status == 201 and paused["checkpoint"] == "operator_paused", paused
        before_resume = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert before_resume["groups"] == committed["groups"]
        assert before_resume["saved"] == original["saved"]
        status, inventory = _request("GET", server.base_url + "/run-containers/full-simulation/operations")
        assert status == 200
        assert [(o["run_id"], o["branch_id"], o["command_id"], o["control_state"])
            for o in inventory["operations"]] == [(flow["run_id"], flow["branch_id"], command["command_id"], "paused")]
        status, pending = _request("GET", url + "/full-simulation/pending")
        restored = pending["operations"][0]["command"]
        assert status == 200
        assert {k: restored[k] for k in command} == command
        resume = pause | {"control_command_id": "resume", "action": "resume", "audit_reason": "Continue same intent"}
        assert _request("POST", url + "/full-simulation/control", resume)[0] == 200
        assert _request("POST", url + "/full-simulation/control", resume)[1]["replayed"]
        # Delayed pause replay cannot pause the now-authorized parent again.
        assert _request("POST", url + "/full-simulation/control", pause)[1]["observed_control_state"] == "running"
        status, continued = _request("POST", url + "/simulate-full-simulation", restored)
        assert status == 201, continued
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert len(after["groups"]) > len(committed["groups"])
        assert all(after["groups"][k] == v for k, v in committed["groups"].items())
        assert all(after["slots"][k] == v for k, v in committed["slots"].items())
        parent = after["commands"][command["command_id"]]
        assert parent["fingerprint"] == before_resume["commands"][command["command_id"]]["fingerprint"]
        assert [e["action"] for e in parent["result"]["control_events"]] == ["pause", "resume"]
        assert parent["result"]["resume_command"] == restored
        assert after["saved_head"] == original["saved_head"]
        assert after["saved"] == original["saved"]
        # A lost Full Simulation response is also safe to retry exactly.
        assert _request("POST", url + "/simulate-full-simulation", restored)[0] == 201
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after
        # Same immutable inputs, Run/Branch, command and seed hierarchy in a
        # disposable DB copy must produce identical sport without the pause.
        reference_server = ApiServer(database_url=f"sqlite:///{reference_path}")
        reference_server.app.dependency_overrides.update(server.app.dependency_overrides)
        with reference_server:
            status, uninterrupted = _request("POST", reference_server.base_url + flow["scope"] + "/simulate-full-simulation", command)
            assert status == 201 and uninterrupted["checkpoint"] == continued["checkpoint"]
            reference_snapshot = snapshot(reference_server.app.state.runtime.repository._session_factory,
                flow["run_id"], flow["branch_id"])
            assert reference_snapshot["groups"] == after["groups"]
            assert reference_snapshot["slots"] == after["slots"]
            assert reference_snapshot["saved"] == original["saved"]


@pytest.mark.pr_critical
@pytest.mark.parametrize("takeover", [False, True])
def test_http_expired_or_reclaimed_invocation_cannot_commit_next_sporting_child(tmp_path, monkeypatch, takeover):
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server, ThreadPoolExecutor(max_workers=1) as pool:
        flow = initialize(server, tmp_path)
        command = reviewed_command(server, flow)
        gate.arm()
        invocation = pool.submit(_request, "POST", server.base_url + flow["scope"] + "/simulate-full-simulation", command)
        try:
            assert gate.reached.wait(timeout=40)
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert before["groups"]
            if takeover:
                new_token = reclaim(factory, flow)
            else:
                with factory() as session:
                    old_token = session.get(FullSimulationExecutionLeaseModel, "all_runs").owner_token
                expire(factory)
                assert renew_invocation_lease(factory, token=old_token) is False
        finally:
            gate.release.set()
        status, failure = invocation.result(timeout=40)
        assert status == 409 and "lease ownership was lost" in failure["detail"]["message"]
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == before
        if takeover:
            with factory() as session:
                lease = session.get(FullSimulationExecutionLeaseModel, "all_runs")
                assert lease.owner_token == new_token and lease.run_id == flow["other_run"]


@pytest.mark.pr_critical
@pytest.mark.parametrize("pause_first", [False, True])
def test_http_operator_stop_during_work_or_pause_is_terminal_and_replay_safe(
    tmp_path, monkeypatch, pause_first,
):
    """Real HTTP + SQLite: stop never rolls back committed matches or auto-saves."""
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server, ThreadPoolExecutor(max_workers=1) as pool:
        flow = initialize(server, tmp_path)
        command = reviewed_command(server, flow)
        url = server.base_url + flow["scope"]
        original = snapshot(factory, flow["run_id"], flow["branch_id"])
        gate.arm()
        invocation = pool.submit(_request, "POST", url + "/simulate-full-simulation", command)
        try:
            assert gate.reached.wait(timeout=40)
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert before["groups"], "At least one real MatchEngine child must commit"
            if pause_first:
                pause = {
                    "control_command_id": "pause-before-stop", "target_command_id": command["command_id"],
                    "action": "pause", "operator_label": "Operator",
                    "audit_reason": "Exercise stop from pending pause",
                }
                assert _request("POST", url + "/full-simulation/control", pause)[0] == 200
            stop = {
                "control_command_id": "terminal-stop", "target_command_id": command["command_id"],
                "action": "stop", "operator_label": "Operator",
                "audit_reason": "Stop after safely committed child",
            }
            status, stopped_control = _request("POST", url + "/full-simulation/control", stop)
            assert status == 200, stopped_control
            assert stopped_control["control_state"] == "stopped"
            status, replay = _request("POST", url + "/full-simulation/control", stop)
            assert status == 200 and replay["replayed"] is True
            assert replay["observed_control_state"] == "stopped"
            different = stop | {"action": "resume"}
            assert _request("POST", url + "/full-simulation/control", different)[0] == 409
        finally:
            gate.release.set()
        status, stopped = invocation.result(timeout=40)
        assert status == 201 and stopped["checkpoint"] == "operator_stopped", stopped
        assert stopped["status"] == "stopped"
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"] == before["groups"]
        assert after["slots"] == before["slots"]
        assert after["saved"] == original["saved"]
        assert after["saved_head"] == original["saved_head"]
        parent = after["commands"][command["command_id"]]
        assert parent["status"] == "stopped"
        assert parent["fingerprint"] == before["commands"][command["command_id"]]["fingerprint"]
        assert [x["action"] for x in parent["result"]["control_events"]] == (
            ["pause", "stop"] if pause_first else ["stop"]
        )
        assert _request("GET", url + "/full-simulation/pending")[1]["operations"] == []
        assert _request("GET", url + "/full-simulation/history")[1]["items"][0]["status"] == "stopped"
        status, retry = _request("POST", url + "/simulate-full-simulation", command)
        assert status == 201 and retry["checkpoint"] == "operator_stopped"
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after
        rejected = stop | {"control_command_id": "stop-again"}
        assert _request("POST", url + "/full-simulation/control", rejected)[0] == 409


@pytest.mark.pr_critical
def test_http_versioned_target_change_during_real_sport_reaches_safe_week_boundary(
    tmp_path, monkeypatch,
):
    """A changed target fences new work but never rewrites original intent."""
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server, ThreadPoolExecutor(max_workers=1) as pool:
        flow = initialize(server, tmp_path)
        command = reviewed_command(server, flow, command_id="original-retarget")
        url = server.base_url + flow["scope"]
        original = snapshot(factory, flow["run_id"], flow["branch_id"])
        gate.arm()
        invocation = pool.submit(_request, "POST", url + "/simulate-full-simulation", command)
        try:
            assert gate.reached.wait(timeout=40)
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert before["groups"], "At least one genuine sporting child must already exist"
            status, pos = _request("GET", url + "/position")
            assert status == 200, pos
            current_week = pos["current_week"]
            target = {
                "control_command_id": "new-week-boundary",
                "target_command_id": command["command_id"],
                "target_week": current_week,
                "operator_label": "Commissioner",
                "audit_reason": "Stop at already-reached safe week arrival",
            }
            reset = target | {
                "control_command_id": "original-target-reset",
                "target_week": {"season_index": 49, "week": 61},
                "audit_reason": "Keep original closure available",
            }
            status, first = _request("POST", url + "/full-simulation/target", reset)
            assert status == 200 and first["target_revision"] == 1, first
            status, changed = _request("POST", url + "/full-simulation/target", target)
            assert status == 200 and changed["target_revision"] == 2, changed
            assert changed["original_final_week"] == {"season_index": 49, "week": 61}
            assert changed["effective_target_week"] == current_week
            status, lost_response = _request("POST", url + "/full-simulation/target", target)
            assert status == 200 and lost_response["replayed"] is True, lost_response
            assert lost_response["applied_revision"] == 2
            status, historical_retry = _request("POST", url + "/full-simulation/target", reset)
            assert status == 200 and historical_retry["replayed"] is True
            assert historical_retry["effective_target_week"] == current_week
            assert _request("POST", url + "/full-simulation/target",
                target | {"audit_reason": "Conflicting reuse"})[0] == 409
            assert _request("POST", url + "/full-simulation/target",
                target | {"control_command_id": "invalid-week",
                          "target_week": {"season_index": 0, "week": 62}})[0] == 422
            assert _request("POST", server.base_url + flow["other_scope"] + "/full-simulation/target",
                target)[0] == 409
        finally:
            gate.release.set()
        status, finished = invocation.result(timeout=40)
        assert status == 201 and finished["status"] == "target_reached", finished
        assert finished["checkpoint"] == "operator_target_reached"
        assert finished["effective_target_week"] == current_week
        assert finished["target_revision"] == 2
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"] == before["groups"]
        assert after["slots"] == before["slots"]
        assert after["saved"] == original["saved"]
        assert after["saved_head"] == original["saved_head"]
        parent = after["commands"][command["command_id"]]
        assert parent["status"] == "target_reached"
        assert parent["fingerprint"] == before["commands"][command["command_id"]]["fingerprint"]
        assert len(parent["result"]["target_events"]) == 2
        assert parent["result"]["review"]["final_week"] == {"season_index": 49, "week": 61}
        assert _request("GET", url + "/full-simulation/pending")[1]["operations"] == []
        assert _request("GET", url + "/full-simulation/history")[1]["items"][0]["status"] == "target_reached"
        status, terminal_replay = _request("POST", url + "/full-simulation/target", target)
        assert status == 200 and terminal_replay["replayed"] is True
        assert terminal_replay["target_revision"] == 2
        assert _request("POST", url + "/full-simulation/target",
            target | {"control_command_id": "new-after-terminal"})[0] == 409
        status, repeated_execution = _request("POST", url + "/simulate-full-simulation", command)
        assert status == 201 and repeated_execution["status"] == "target_reached"
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after


@pytest.mark.pr_critical
@pytest.mark.parametrize("start,unit,count,expected", [
    ((0, 61), "weeks", 1, (1, 1)),
    ((2, 61), "weeks", 3, (3, 3)),
    ((2, 17), "seasons", 1, (3, 17)),
    ((48, 61), "seasons", 1, (49, 61)),
    ((49, 60), "weeks", 1, (49, 61)),
])
def test_relative_target_pure_cross_season_chronology(start, unit, count, expected):
    from beta_engine.application.authoritative_run_simulation_driver import (
        AuthoritativeRunSimulationDriver, AuthoritativeFullSimulationRelativeTarget,
    )
    from beta_engine.domain.rankings.official import RankingWeek

    current = RankingWeek(season_index=start[0], week=start[1])
    relative = AuthoritativeFullSimulationRelativeTarget(unit=unit, count=count)
    target = AuthoritativeRunSimulationDriver._resolve_relative_full_target(current, relative)
    assert (target.season_index, target.week) == expected


@pytest.mark.pr_critical
@pytest.mark.parametrize("unit,count", [
    ("weeks", 1), ("seasons", 1)
])
def test_relative_target_rejects_end_of_run(unit, count):
    from beta_engine.application.authoritative_run_simulation_driver import (
        AuthoritativeRunSimulationDriver, AuthoritativeFullSimulationRelativeTarget,
    )
    from beta_engine.domain.rankings.official import RankingWeek

    current = RankingWeek(season_index=49, week=61)
    with pytest.raises(ValueError, match="exceeds the last Run week"):
        AuthoritativeRunSimulationDriver._resolve_relative_full_target(
            current, AuthoritativeFullSimulationRelativeTarget(unit=unit, count=count)
        )


@pytest.mark.pr_critical
def test_relative_target_input_contract_is_exclusive_and_strict():
    from pydantic import ValidationError
    from beta_engine.application.authoritative_run_simulation_driver import (
        AuthoritativeFullSimulationRetargetCommand,
    )

    base = {
        "control_command_id": "new-target", "target_command_id": "parent",
        "run_id": "run", "branch_id": "branch",
        "operator_label": "Operator", "audit_reason": "Exact relative request",
    }
    for invalid in [
        {}, {"target_week": {"season_index": 2, "week": 3},
             "relative_target": {"unit": "weeks", "count": 1}},
        {"relative_target": {"unit": "weeks", "count": 0}},
        {"relative_target": {"unit": "weeks", "count": -1}},
        {"relative_target": {"unit": "seasons", "count": 50}},
        {"relative_target": {"unit": "weeks", "count": 3051}},
        {"relative_target": {"unit": "weeks", "count": "1"}},
        {"relative_target": {"unit": "seasons", "count": True}},
        {"relative_target": {"unit": "months", "count": 1}},
    ]:
        with pytest.raises(ValidationError):
            AuthoritativeFullSimulationRetargetCommand.model_validate(base | invalid)


@pytest.mark.pr_critical
def test_http_relative_full_target_real_sport_audit_and_safe_terminal_replay(tmp_path, monkeypatch):
    """Real HTTP/SQLite: convert increments exactly once, then preserve evidence."""
    server, factory, gate = make_server(tmp_path)
    monkeypatch.setattr(routes, "_driver", gate.driver)
    with server, ThreadPoolExecutor(max_workers=1) as pool:
        flow = initialize(server, tmp_path)
        url = server.base_url + flow["scope"]
        command = reviewed_command(server, flow, command_id="relative-parent")
        original = snapshot(factory, flow["run_id"], flow["branch_id"])
        gate.arm()
        invocation = pool.submit(_request, "POST", url + "/simulate-full-simulation", command)
        try:
            assert gate.reached.wait(timeout=40)
            before = snapshot(factory, flow["run_id"], flow["branch_id"])
            assert before["groups"]
            status, actual = _request("GET", url + "/position")
            assert status == 200, actual
            base_week = actual["current_week"]
            ordinal = base_week["season_index"] * 61 + base_week["week"] - 1
            next_week = {"season_index": (ordinal+1)//61, "week": (ordinal+1)%61+1}
            next_season = {"season_index": (ordinal+61)//61, "week": (ordinal+61)%61+1}
            relative = {
                "control_command_id": "relative-week-one",
                "target_command_id": command["command_id"],
                "relative_target": {"unit": "weeks", "count": 1},
                "operator_label": "Operator",
                "audit_reason": "Advance exactly one week from SQLite current time",
            }
            status, first = _request("POST", url + "/full-simulation/target", relative)
            assert status == 200 and first["requested_target_week"] == next_week, first
            assert first["requested_relative_target"] == {"unit": "weeks", "count": 1}
            assert first["resolved_from_week"] == base_week
            status, lost = _request("POST", url + "/full-simulation/target", relative)
            assert status == 200 and lost["replayed"] is True
            assert lost["requested_target_week"] == first["requested_target_week"]
            assert lost["applied_revision"] == 1
            change = relative | {
                "control_command_id": "relative-season-one",
                "relative_target": {"unit": "seasons", "count": 1},
                "audit_reason": "Move to the same week next season",
            }
            status, second = _request("POST", url + "/full-simulation/target", change)
            assert status == 200 and second["requested_target_week"] == next_season, second
            assert second["applied_revision"] == second["target_revision"] == 2
            status, old = _request("POST", url + "/full-simulation/target", relative)
            assert status == 200 and old["replayed"] is True
            assert old["effective_target_week"] == next_season
            assert old["requested_target_week"] == next_week
            for modification in [
                {"relative_target": {"unit": "weeks", "count": 2}},
                {"relative_target": {"unit": "seasons", "count": 1}},
                {"target_week": next_week, "relative_target": None},
            ]:
                assert _request("POST", url + "/full-simulation/target",
                    relative | modification)[0] == 409
            bad = relative | {"control_command_id": "invalid-bounds",
                             "relative_target": {"unit": "weeks", "count": 3050}}
            assert _request("POST", url + "/full-simulation/target", bad)[0] == 409
            assert _request("POST", url + "/full-simulation/target",
                relative | {"control_command_id": "invalid-shape",
                            "target_week": next_week})[0] == 422
            status, global_state = _request(
                "GET", server.base_url + "/run-containers/full-simulation/operations"
            )
            assert status == 200, global_state
            assert global_state["operations"][0]["effective_target_week"] == next_season
            assert global_state["operations"][0]["target_revision"] == 2
            close = relative | {
                "control_command_id": "close-current-boundary",
                "relative_target": None,
                "target_week": base_week,
                "audit_reason": "Close once current week is reached",
            }
            status, close_result = _request("POST", url + "/full-simulation/target", close)
            assert status == 200 and close_result["target_revision"] == 3, close_result
        finally:
            gate.release.set()
        status, terminal = invocation.result(timeout=40)
        assert status == 201 and terminal["status"] == "target_reached", terminal
        assert terminal["target_revision"] == 3
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"] == before["groups"]
        assert after["slots"] == before["slots"]
        assert after["saved"] == original["saved"]
        assert after["saved_head"] == original["saved_head"]
        parent = after["commands"][command["command_id"]]
        assert parent["status"] == "target_reached"
        assert parent["fingerprint"] == before["commands"][command["command_id"]]["fingerprint"]
        assert [e.get("relative_target") for e in parent["result"]["target_events"]] == [
            {"unit": "weeks", "count": 1}, {"unit": "seasons", "count": 1}, None
        ]
        status, replay_after_terminal = _request("POST", url + "/full-simulation/target", relative)
        assert status == 200 and replay_after_terminal["replayed"] is True
        assert replay_after_terminal["requested_target_week"] == next_week
        assert replay_after_terminal["effective_target_week"] == base_week
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == after
