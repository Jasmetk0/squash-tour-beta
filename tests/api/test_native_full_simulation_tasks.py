"""Actual server dispatcher, HTTP sporting services and physically reopened SQLite."""

import time

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def scope(server):
    return server.base_url + f"/admin/runs/run/branches/{getattr(server, 'native_task_branch', 'branch')}/authoritative-simulation/full-simulation"


def tour_url(server):
    return server.base_url + f"/admin/runs/run/branches/{getattr(server, 'native_task_branch', 'branch')}/calendar-tour"


def inspect(server):
    code, body = _request("GET", tour_url(server))
    assert code == 200, body
    return body


def save_tour(server):
    view = inspect(server)
    code, body = _request("POST", tour_url(server) + "/save", {
        "expected_draft_version": view["draft_version"], "expected_calendar_tour_fingerprint": view["tour_fingerprint"]})
    assert code == 201, body
    return body["saved_revision"]


def execute_tour(server, command):
    code, preview = _request("POST", tour_url(server) + "/preview", command)
    assert code == 200, preview
    request = {"command": command, "expected_preview_fingerprint": preview["preview_fingerprint"], "explicit_confirmation": True}
    code, body = _request("POST", tour_url(server) + "/execute", request)
    assert code == 201, body
    return body, request


def reviewed(server, target=None, name="native-full"):
    request = {"schema_version": "authoritative_full_simulation_command.v2", "command_id": name,
        "seed": 231, "operator_label": "Správce Žan", "audit_reason": "Ověření skutečné serverové úlohy a neměnného zdroje",
        "target_week": target}
    code, preview = _request("POST", scope(server) + "/native/preview", request)
    assert code == 200, preview
    return {**preview["request"], "execution_calendar": preview["execution_calendar"],
        "expected_start_week": preview["start_week"],
        "expected_position_fingerprint": preview["expected_position_fingerprint"],
        "expected_revision_id": preview["expected_revision_id"],
        "expected_preview_fingerprint": preview["preview_fingerprint"]}


def wait(server, task_id, *, allow_failed=False):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        code, result = _request("GET", scope(server) + "/tasks/" + task_id)
        assert code == 200, result
        task = result["tasks"][0]
        if task["state"] in {"awaiting_operator", "paused", "failed", "target_reached", "complete", "stopped"} and task["lease_expires_at_unix"] is None:
            assert allow_failed or task["state"] != "failed", task
            return task
        time.sleep(0.15)
    raise AssertionError(task)


def start(server, command):
    body = {"request_id": "start-" + command["command_id"], "command": command}
    code, ack = _request("POST", scope(server) + "/tasks", body)
    assert code == 202, ack
    assert _request("POST", scope(server) + "/tasks", body) == (202, ack)
    return wait(server, ack["task_id"])


def resume(server, task, request_id, action="resume"):
    body = {"request_id": request_id, "action": action, "expected_revision": task["revision"],
        "operator_label": "Admin", "audit_reason": "Saved and reviewed; continue the same original task"}
    code, result = _request("POST", scope(server) + "/tasks/" + task["task_id"] + "/continue", body)
    assert code == 202, result
    return wait(server, task["task_id"])


def approve_draw(server, name="worker-cup"):
    from tests.api.test_calendar_tour_flow import command
    view = inspect(server)
    execute_tour(server, command(view, "submit", name=name + ":applications", edition_id=name,
        data={"player_ids": [p["player_id"] for p in view["players"][:4]]}))
    for action in ("approve", "draw"):
        execute_tour(server, command(inspect(server), action, name=name + ":" + action, edition_id=name))
    save_tour(server)


def test_native_task_real_transition_save_target_restart_and_original_replay(tmp_path):
    import json

    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import CalendarTourAuthorityModel

    db = f"sqlite:///{tmp_path / 'native-task.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(4, 4, 2030, 3), count=4)
        command = reviewed(server, {"season_index": 0, "week": 3}, name="úloha-žluťoučký-kůň")
        task = start(server, command)
        assert task["checkpoint"] == "native_manual_save_required"
        assert task["current_week"] == {"season_index": 0, "week": 3}
        assert not inspect(server)["saved"]
        task = resume(server, task, "target-without-manual-save")
        assert task["state"] == "awaiting_operator"
        assert task["checkpoint"] == "native_manual_save_required"
        assert len(inspect(server)["state"]["transitions"]) == 1
        with repo._session_factory.begin() as session:
            row = session.get(CalendarTourAuthorityModel, ("run", "branch"))
            original_tour, original_hash = row.payload_json, row.fingerprint
            corrupt = json.loads(original_tour)
            corrupt["schema_version"] = "calendar_tour_authority.v3"
            row.payload_json, row.fingerprint = json.dumps(corrupt), canonical_hash(corrupt)
        assert _request("GET", scope(server) + "/tasks/" + task["task_id"])[0] == 409
        with repo._session_factory.begin() as session:
            row = session.get(CalendarTourAuthorityModel, ("run", "branch"))
            assert row.payload_json == json.dumps(corrupt)  # GET did not repair storage.
            row.payload_json, row.fingerprint = original_tour, original_hash
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
        assert _request("POST", scope(restarted) + "/tasks", {"request_id": "start-" + command["command_id"], "command": command})[0] == 202
        assert len(inspect(restarted)["state"]["transitions"]) == 1


def test_native_task_reaches_real_final_closure_with_separate_approval_save_and_rollback(tmp_path, monkeypatch):
    from beta_engine.application import native_full_simulation_closure as closure_app
    from tests.api.test_player_generation_calendar_gate import _dump

    db = f"sqlite:///{tmp_path / 'native-close.db'}"
    with ApiServer(database_url=db) as server:
        setup(server, RunCalendar(3, 2, 2040, 1), count=4)
        command = reviewed(server, name="native-final")
        task = start(server, command)
        assert task["current_week"] == {"season_index": 0, "week": 3}
        save_tour(server)
        task = resume(server, task, "last-week-saved")
        assert task["checkpoint"] == "native_final_closure_review_required"
        url = scope(server) + "/native/native-final/closure"
        code, review = _request("GET", url)
        assert code == 200, review
        assert review["closing_ranking"]["eligibility_boundary_ordinal"] == 3
        body = {"request_id": "final-approve", "review_fingerprint": review["review_fingerprint"],
            "operator_label": "Admin", "audit_reason": "Reviewed genuine final season and ranking",
            "explicit_confirmation": True}
        assert _request("POST", url + "/save", body)[0] == 409
        assert _request("POST", url + "/approve", body)[0] == 200
        before = _dump(tmp_path / 'native-close.db')
        def fail(name):
            raise ValueError("Injected native closure rollback")
        monkeypatch.setattr(closure_app, "_fault_injection_point", fail)
        save_body = {**body, "request_id": "final-save"}
        assert _request("POST", url + "/save", save_body)[0] == 409
        assert _dump(tmp_path / 'native-close.db') == before
        monkeypatch.setattr(closure_app, "_fault_injection_point", lambda name: None)
        code, receipt = _request("POST", url + "/save", save_body)
        assert code == 201, receipt
        assert _request("POST", url + "/save", save_body) == (201, receipt)
        task = resume(server, task, "final-closure-saved")
        assert task["state"] == "complete"
        assert len(inspect(server)["state"]["rankings"]) == 2
        task_id = task["task_id"]
    with ApiServer(database_url=db) as restarted:
        task = wait(restarted, task_id)
        assert task["state"] == "complete"
        assert task["progress_evidence"]["kind"] == "terminal_frozen"


@pytest.mark.parametrize("clock", [RunCalendar(7, 5, 2030, 2), RunCalendar(52, 51, 2030, 2), RunCalendar(61, 37, 2000, 2), RunCalendar(80, 80, 2100, 2)], ids=["short", "w52", "w61", "w80"])
def test_native_task_actual_match_points_all_weeks_and_real_season_rollover(tmp_path, clock):
    from tests.api.test_calendar_tour_flow import command as tour_command
    from tests.api.test_calendar_tour_flow import create_edition
    db = f"sqlite:///{tmp_path / 'matrix.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, count=4)
        create_edition(server, "worker-cup", size=4, offset=clock.weeks_per_year - 3)
        matrix_branch = "branch"
        if clock.weeks_per_year > 7:
            from tests.api.test_native_fork_public_continuation import fork
            alternative = fork(server, inspect(server)["saved_head_revision_id"], name="Worker alternative")
            matrix_branch = alternative["branch_id"]
            server.native_task_branch = matrix_branch
        original = reviewed(server, {"season_index": 1, "week": 1})
        source = repo.get_branch_saved_revision(revision_id=original["expected_revision_id"])
        task = start(server, original)
        played = confirmed = False
        observed = [clock.season_to_calendar(original["expected_start_week"]["season_index"], original["expected_start_week"]["week"])]
        for index in range(clock.weeks_per_year + 12):
            view = inspect(server)
            position = task["current_week"]
            print(f"W{clock.weeks_per_year}: S{position['season_index'] + 1} W{position['week']} {task['state']} {task['checkpoint']}", flush=True)
            observed.append(clock.season_to_calendar(position["season_index"], position["week"]))
            if task["state"] == "target_reached":
                break
            if not view["saved"]:
                save_tour(server)
            elif task["checkpoint"] == "native_entry_review_required":
                approve_draw(server)
            elif task["checkpoint"] == "native_result_review_required":
                evidence = view["edition_evidence"]["worker-cup"]
                assert len(evidence["matches"]) == 3
                assert all(m["rally_count"] > 0 for m in evidence["matches"])
                assert sum(r["main_points"] for r in evidence["results"]) == 220
                played = True
                execute_tour(server, tour_command(view, "confirm-result", name="manual-result", edition_id="worker-cup"))
                save_tour(server)
                confirmed = True
            elif task["checkpoint"] == "native_season_transition_review_required":
                url = scope(server) + "/native/" + original["command_id"] + "/season-transition"
                code, review = _request("GET", url)
                assert code == 200, review
                assert review["preview"]["impact"]["target_week"]["week"] == 1
                assert review["preview"]["impact"]["target_week"]["season_index"] == 1
                approval = {"request_id": "manual-season", "review_fingerprint": review["review_fingerprint"],
                    "operator_label": "Admin", "audit_reason": "Reviewed actual outgoing season and incoming Week 1",
                    "explicit_confirmation": True}
                assert _request("POST", url + "/approve", approval)[0] == 200
            else:
                raise AssertionError(task)
            task = resume(server, task, "matrix-resume-" + str(index))
        else:
            raise AssertionError("Native worker never reached the next season")
        assert played and confirmed
        assert task["state"] == "target_reached"
        assert task["current_week"] == {"season_index": 1, "week": 1}
        final = inspect(server)
        assert len(final["state"]["transitions"]) == clock.weeks_per_year - 1
        assert final["state"]["transitions"][-1]["public_event"]["kind"] == "season_transition_completed"
        assert any(row["points"] == 100 for row in final["state"]["rankings"][-2]["rows"])
        assert any(p.year_week == 1 for p in observed)
        assert repo.get_branch_saved_revision(revision_id=source.revision_id) == source
        task_id = task["task_id"]
    with ApiServer(database_url=db) as restarted:
        restarted.native_task_branch = matrix_branch
        assert wait(restarted, task_id)["original_command"] == original
        assert len(inspect(restarted)["state"]["transitions"]) == clock.weeks_per_year - 1


def test_native_child_rollback_commit_crash_exact_recovery_and_stale_concurrent_worker(tmp_path, monkeypatch):
    import json
    from concurrent.futures import ThreadPoolExecutor

    from beta_engine.application import calendar_tour_service, native_full_simulation
    from beta_engine.application.native_full_simulation import (
        NativeFullSimulationCommand,
        NativeFullSimulationDriver,
    )
    from beta_engine.infrastructure.db.models import FullSimulationTaskModel
    from tests.api.test_player_generation_calendar_gate import _dump

    db = f"sqlite:///{tmp_path / 'native-recovery.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(5, 4, 2040, 2), count=4)
        command = reviewed(server, {"season_index": 0, "week": 4}, name="recover-native")
        before = inspect(server)
        original_fault = calendar_tour_service._fault_injection_point
        def rollback(name):
            if name == "after_tour_write":
                raise ValueError("Injected native child atomic rollback")
            original_fault(name)
        monkeypatch.setattr(calendar_tour_service, "_fault_injection_point", rollback)
        body = {"request_id": "start-recovery", "command": command}
        code, ack = _request("POST", scope(server) + "/tasks", body)
        assert code == 202, ack
        task = wait(server, ack["task_id"], allow_failed=True)
        assert task["state"] == "failed"
        assert inspect(server)["state"] == before["state"]
        monkeypatch.setattr(calendar_tour_service, "_fault_injection_point", original_fault)
        def crash(name):
            raise ValueError("Injected process loss after the actual child commit")
        monkeypatch.setattr(native_full_simulation, "_fault_injection_point", crash)
        request = {"request_id": "recover-after-rollback", "action": "recover", "expected_revision": task["revision"],
            "operator_label": "Admin", "audit_reason": "Recover exact original native child"}
        code, result = _request("POST", scope(server) + "/tasks/" + task["task_id"] + "/continue", request)
        assert code == 202, result
        task = wait(server, task["task_id"], allow_failed=True)
        assert task["state"] == "failed"
        assert len(inspect(server)["state"]["transitions"]) == 1
        with repo._session_factory() as session:
            token = json.loads(session.get(FullSimulationTaskModel, task["task_id"]).payload_json)["owner_token"]
        snapshot = _dump(tmp_path / 'native-recovery.db')
        with pytest.raises(ValueError, match="ownership|lease"):
            NativeFullSimulationDriver(repo).simulate_full_simulation(
                NativeFullSimulationCommand.model_validate(command), execution_lease_token=token)
        assert _dump(tmp_path / 'native-recovery.db') == snapshot
        monkeypatch.setattr(native_full_simulation, "_fault_injection_point", lambda name: None)
        request = {**request, "request_id": "actual-recover", "expected_revision": task["revision"]}
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda n: _request("POST", scope(server) + "/tasks/" + task["task_id"] + "/continue", {**request, "request_id": "concurrent-" + str(n)}), (1, 2)))
        assert sorted(code for code, _ in outcomes) == [202, 409]
        task = wait(server, task["task_id"])
        assert task["checkpoint"] == "native_manual_save_required"
        assert len(inspect(server)["state"]["transitions"]) == 1
        save_tour(server)
        task = resume(server, task, "continue-after-real-save")
        assert task["current_week"] == {"season_index": 0, "week": 4}
        assert len(inspect(server)["state"]["transitions"]) == 2
        stop = {"target_command_id": command["command_id"], "control_command_id": "idle-native-stop",
            "action": "stop", "operator_label": "Admin", "audit_reason": "Explicitly stop the inactive task; preserve committed sport"}
        code, result = _request("POST", scope(server) + "/control", stop)
        assert code == 200, result
        task = wait(server, task["task_id"])
        assert task["state"] == task["desired_state"] == "stopped"
        assert _request("POST", scope(server) + "/control", stop)[0] == 200


def test_native_season_review_and_safe_pause_survive_restart_without_automatic_approval(tmp_path):
    db = f"sqlite:///{tmp_path / 'native-season-review.db'}"
    with ApiServer(database_url=db) as server:
        setup(server, RunCalendar(3, 3, 2040, 2), count=4)
        original = reviewed(server, {"season_index": 1, "week": 1}, name="season-review")
        task = start(server, original)
        save_tour(server)
        task = resume(server, task, "finish-last-week")
        assert task["checkpoint"] == "native_season_transition_review_required"
        before = inspect(server)["state"]
        task = resume(server, task, "no-implicit-approval")
        assert task["checkpoint"] == "native_season_transition_review_required"
        assert inspect(server)["state"] == before
        control = {"target_command_id": original["command_id"], "control_command_id": "pause-at-season",
            "action": "pause", "operator_label": "Admin", "audit_reason": "Safe pause before seasonal approval"}
        code, result = _request("POST", scope(server) + "/control", control)
        assert code == 200, result
        task = wait(server, task["task_id"])
        assert task["state"] == "paused"
        task = resume(server, task, "resume-still-needs-review")
        assert task["checkpoint"] == "native_season_transition_review_required"
        url = scope(server) + "/native/season-review/season-transition"
        code, review = _request("GET", url)
        assert code == 200, review
        assert review["outgoing_season_closure"]["completed_week"] == {"season_index": 0, "week": 3}
        approval = {"request_id": "approve-real-season", "review_fingerprint": review["review_fingerprint"],
            "operator_label": "Admin", "audit_reason": "Reviewed actual closing ranking and next-season inputs",
            "explicit_confirmation": True}
        assert _request("POST", url + "/approve", {**approval, "review_fingerprint": "0" * 64})[0] == 409
        accepted = _request("POST", url + "/approve", approval)
        assert accepted[0] == 200, accepted
        assert _request("POST", url + "/approve", approval) == accepted
        task_id = task["task_id"]
    with ApiServer(database_url=db) as restarted:
        task = wait(restarted, task_id)
        assert task["state"] == "awaiting_operator"
        assert inspect(restarted)["state"] == before
        task = resume(restarted, task, "continue-reviewed-season-after-restart")
        assert task["checkpoint"] == "native_manual_save_required"
        assert task["current_week"] == {"season_index": 1, "week": 1}
        save_tour(restarted)
        task = resume(restarted, task, "save-incoming-week-one")
        assert task["state"] == "target_reached"
        assert task["original_command"] == original


def test_native_original_intent_survives_real_fork_horizon_save_and_independent_continuation(tmp_path):
    import json

    from beta_engine.domain.run_revisions import saved_revision_content_hash
    from beta_engine.infrastructure.db.models import (
        BranchSavedRevisionModel,
        FullSimulationTaskModel,
    )
    from tests.api.test_calendar_sporting_horizon_extension import extend, extension
    from tests.api.test_native_fork_public_continuation import fork

    db = f"sqlite:///{tmp_path / 'native-extension.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(4, 4, 2100, 2), count=4)
        original = reviewed(server, {"season_index": 0, "week": 2}, name="frozen-before-extension")
        task = start(server, original)
        assert task["state"] == "target_reached"
        with repo._session_factory() as session:
            task_bytes = session.get(FullSimulationTaskModel, task["task_id"]).payload_json
            source = session.get(BranchSavedRevisionModel, original["expected_revision_id"])
            source_bytes, source_hash = source.payload_json, source.content_hash
        alternative = fork(server, original["expected_revision_id"], name="Independent native worker")
        from beta_engine.application.run_calendar_read_authority import (
            require_supported_legacy_sporting_calendar,
        )
        with repo._session_factory() as session, pytest.raises(ValueError, match="independent native Branch aggregate"):
            require_supported_legacy_sporting_calendar(session, run_id="run", branch_id=alternative["branch_id"], operation="Unsupported legacy command")
        code, review = extension(server, 3)
        assert code == 200 and review["can_save"], review
        code, saved = extend(server, review)
        assert code == 200, saved
        assert saved["simulation_started"] is False
        server.native_task_branch = alternative["branch_id"]
        next_command = reviewed(server, {"season_index": 0, "week": 3}, name="independent-after-extension")
        assert next_command["execution_calendar"]["season_count"] == 3
        next_task = start(server, next_command)
        assert next_task["checkpoint"] == "native_manual_save_required"
        save_tour(server)
        next_task = resume(server, next_task, "save-independent-native-week")
        assert next_task["state"] == "target_reached"
        assert inspect(server)["state"]["week"]["week"] == 3
        restore_url = server.base_url + f"/run-containers/run/branches/{alternative['branch_id']}/saved-revisions/{next_command['expected_revision_id']}/restore"
        code, preflight = _request("GET", restore_url + "-preflight")
        assert code == 200 and preflight["can_restore"], preflight
        code, restored = _request("POST", restore_url, {
            "expected_head_saved_revision_id": preflight["saved_head_revision_id"],
            "expected_draft_version": preflight["draft_version"],
            "expected_current_viewer_branch_id": preflight["current_viewer_branch_id"], "explicit_confirmation": True})
        assert code == 201, restored
        assert inspect(server)["state"]["week"]["week"] == 2
        assert wait(server, next_task["task_id"])["current_week"] == {"season_index": 0, "week": 3}
        server.native_task_branch = "branch"
        assert inspect(server)["state"]["week"]["week"] == 2
        old = wait(server, task["task_id"])
        assert old["original_command"] == original
        assert old["execution_calendar"]["season_count"] == 2
        assert old["current_week"] == {"season_index": 0, "week": 2}
        with repo._session_factory() as session:
            assert session.get(FullSimulationTaskModel, task["task_id"]).payload_json == task_bytes
            assert session.get(BranchSavedRevisionModel, original["expected_revision_id"]).payload_json == source_bytes
        # Ordinary native Saved restore must also leave the task control row
        # outside the rewound legacy sporting component.
        restore_url = server.base_url + f"/run-containers/run/branches/branch/saved-revisions/{original['expected_revision_id']}/restore"
        code, preflight = _request("GET", restore_url + "-preflight")
        assert code == 200 and preflight["can_restore"], preflight
        code, restored = _request("POST", restore_url, {
            "expected_head_saved_revision_id": preflight["saved_head_revision_id"],
            "expected_draft_version": preflight["draft_version"],
            "expected_current_viewer_branch_id": preflight["current_viewer_branch_id"], "explicit_confirmation": True})
        assert code == 201, restored
        with repo._session_factory() as session:
            assert session.get(FullSimulationTaskModel, task["task_id"]).payload_json == task_bytes
        task_id, alternative_id = task["task_id"], alternative["branch_id"]
    with ApiServer(database_url=db) as restarted:
        assert wait(restarted, task_id)["original_command"] == original
        restarted.native_task_branch = alternative_id
        assert inspect(restarted)["state"]["week"]["week"] == 2
        restarted.native_task_branch = "branch"
        # A valid replacement self-hash cannot replace the originally reviewed
        # Saved source. This is a negative corruption test, never accepted sport.
        repo = restarted.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            source = session.get(BranchSavedRevisionModel, original["expected_revision_id"])
            changed = json.loads(source.payload_json)
            changed["run"]["display_name"] = "Rehashed false historical source"
            source.payload_json = json.dumps(changed, sort_keys=True, separators=(",", ":"))
            source.content_hash = saved_revision_content_hash(
                revision_id=source.revision_id, run_id=source.run_id, branch_id=source.branch_id,
                sequence=source.sequence, parent_revision_id=source.parent_revision_id,
                kind=source.kind, payload_schema_version=source.payload_schema_version,
                payload=changed, change_summary=json.loads(source.change_summary_json))
        assert _request("GET", scope(restarted) + "/tasks/" + task_id)[0] == 409
        with repo._session_factory.begin() as session:
            source = session.get(BranchSavedRevisionModel, original["expected_revision_id"])
            source.payload_json, source.content_hash = source_bytes, source_hash
        assert wait(restarted, task_id)["original_command"] == original
