"""One-snapshot native Full Simulation step over real HTTP, SQLite and Task Center.

Each case starts from an SQLite backup of the same genuinely produced native
Tour and runs the production task worker. The original complete path is the
comparison oracle: it is forced only by returning None from the prepared step.
"""

import json
from collections import Counter
import sqlite3
import time

import pytest

from beta_engine.application import native_full_simulation as native
from beta_engine.application.calendar_tour_service import CalendarTourService
from beta_engine.application.native_full_simulation import NativeFullSimulationDriver
from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_native_full_simulation_tasks import (
    inspect,
    resume,
    reviewed,
    save_tour,
    scope,
    start,
    wait,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

# Persistence/audit tables whose identities or clocks legitimately differ.
_VOLATILE_TABLES = {"full_simulation_tasks", "full_simulation_execution_leases"}
_VOLATILE_COLUMNS = {"created_at", "updated_at"}


def _copy(source, target):
    with sqlite3.connect(source) as s, sqlite3.connect(target) as t:
        s.backup(t)


def _rows(path):
    """Every authoritative row except task/lease audit identities and clocks."""
    with sqlite3.connect(path) as connection:
        tables = [r[0] for r in connection.execute(
            "select name from sqlite_master where type='table' order by name")]
        result = {}
        for table in tables:
            if table in _VOLATILE_TABLES:
                continue
            columns = [r[1] for r in connection.execute(f"pragma table_info('{table}')")
                       if r[1] not in _VOLATILE_COLUMNS]
            quoted = ", ".join('"' + c + '"' for c in columns)
            result[table] = sorted(connection.execute(f"select {quoted} from '{table}'").fetchall(), key=repr)
        return result


def _sporting(path):
    """Authoritative rows without the Full Simulation parent itself."""
    rows = _rows(path)
    rows.pop("authoritative_simulation_commands")
    return rows


def _parent(path, command_id):
    with sqlite3.connect(path) as connection:
        status, raw = connection.execute(
            "select status, result_json from authoritative_simulation_commands where command_id=?",
            (command_id,)).fetchone()
    return status, json.loads(raw)


class Calls:
    """Count production calls without changing their arguments or results."""

    def __init__(self, monkeypatch):
        self.counts = {}
        self.monkeypatch = monkeypatch

    def watch(self, owner, name, label=None):
        original = getattr(owner, name)
        label = label or name

        def counted(*args, **kwargs):
            self.counts[label] = self.counts.get(label, 0) + 1
            return original(*args, **kwargs)

        self.monkeypatch.setattr(owner, name, counted)

    def __getitem__(self, label):
        return self.counts.get(label, 0)


def _watch_driver(monkeypatch):
    from beta_engine.application import (
        calendar_tour_appended_slot_verification as appended,
    )
    from beta_engine.application import native_fork_runtime_service as fork_service

    calls = Calls(monkeypatch)
    calls.watch(fork_service.NativeForkRuntimeService, "_context", "fork_context")
    calls.watch(fork_service, "prepare_command", "fork_prepare")
    calls.watch(NativeFullSimulationDriver, "_install_calendar_step", "prepared_install")
    calls.watch(NativeFullSimulationDriver, "_install_fork_step", "prepared_install")
    calls.watch(NativeFullSimulationDriver, "_simulate_full_path", "full_path")
    calls.watch(CalendarTourService, "_context", "context")
    calls.watch(CalendarTourService, "_prepare_from_context", "prepare")
    calls.watch(CalendarTourService, "preview", "preview")
    calls.watch(CalendarTourService, "execute", "execute")
    original = appended.verify_appended_slot

    def accepted(*args, **kwargs):
        result = original(*args, **kwargs)
        if result is not None:
            calls.counts["appended_slot"] = calls.counts.get("appended_slot", 0) + 1
        return result

    monkeypatch.setattr(appended, "verify_appended_slot", accepted)
    return calls


def _force_full_path(monkeypatch):
    monkeypatch.setattr(NativeFullSimulationDriver, "_simulate_prepared_step", lambda *a, **k: None)


def _after_read(monkeypatch, action):
    """Run ``action`` once, after the read snapshot ends and before the writer."""
    original = NativeFullSimulationDriver._read_prepared_step
    fired = []

    def read(self, connection, command, token):
        step = original(self, connection, command, token)
        if step is not None and step["kind"] == "child" and not fired:
            fired.append(True)
            action(self, command, token, step)
        return step

    monkeypatch.setattr(NativeFullSimulationDriver, "_read_prepared_step", read)
    return fired


def _transitions(server):
    return len(inspect(server)["state"]["transitions"])


@pytest.fixture(scope="module")
def native_source(tmp_path_factory):
    """One real Saved native Tour at Week 2 and its reviewed task command."""
    from tests.api.test_calendar_tour_flow import setup

    path = tmp_path_factory.mktemp("prepared-native-source") / "source.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        setup(server, RunCalendar(4, 4, 2030, 3), count=4)
        command = reviewed(server, {"season_index": 0, "week": 3}, name="prepared-step")
    return path, command


@pytest.fixture(scope="module")
def native_fork_source(tmp_path_factory):
    """The same real Tour continued on an independent native fork v2 Branch."""
    from tests.api.test_calendar_tour_flow import setup
    from tests.api.test_native_fork_public_continuation import fork

    path = tmp_path_factory.mktemp("prepared-fork-source") / "source.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        setup(server, RunCalendar(8, 8, 2030, 2), count=4)
        branch = fork(server, inspect(server)["saved_head_revision_id"], name="Prepared fork")["branch_id"]
        server.native_task_branch = branch
        command = reviewed(server, {"season_index": 0, "week": 4}, name="prepared-fork-step")
    return path, command, branch


@pytest.fixture(scope="module")
def global_slot_source(prepared_slots, tmp_path_factory):
    """The shared real W52 global-slot Run (Tour v5, checkpoint v13) and its task."""
    path = tmp_path_factory.mktemp("prepared-global-source") / "source.db"
    _copy(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        command = reviewed(server, {"season_index": 0, "week": 5}, name="prepared-global-step")
    return path, command


@pytest.mark.parametrize("variant", ["original", "fork", "global"])
def test_prepared_step_equals_original_path_bytes_with_half_the_authentication(
    tmp_path, request, monkeypatch, variant,
):
    branch = "branch"
    if variant == "original":
        source, command = request.getfixturevalue("native_source")
    elif variant == "fork":
        source, command, branch = request.getfixturevalue("native_fork_source")
    else:
        source, command = request.getfixturevalue("global_slot_source")
    outcomes = {}
    for mode in ("prepared", "full"):
        path = tmp_path / f"{mode}.db"
        _copy(source, path)
        with monkeypatch.context() as patch:
            calls = _watch_driver(patch)
            if mode == "full":
                _force_full_path(patch)
            with ApiServer(database_url=f"sqlite:///{path}") as server:
                server.native_task_branch = branch
                task = start(server, command)
                assert task["checkpoint"] == "native_manual_save_required", task
                counts = Counter(calls.counts)
                # A second invocation without a Save must not repeat the child.
                task = resume(server, task, "no-save-no-second-child")
                assert task["checkpoint"] == "native_manual_save_required", task
                view = inspect(server)
                if variant == "global":
                    assert view["next_slot"]["number"] == 5  # one real global slot played
                else:
                    assert task["current_week"]["week"] == command["expected_start_week"]["week"] + 1
                    assert len(view["state"]["transitions"]) == 1
        outcomes[mode] = (counts, _rows(path), _parent(path, command["command_id"]))
    prepared, full = outcomes["prepared"], outcomes["full"]
    assert prepared[1] == full[1]  # byte-identical sporting, Saved, draft and parent rows
    assert prepared[2] == full[2]
    status, parent = prepared[2]
    assert status == "pending" and len(parent["children"]) == 1 and parent["pending_child"] is None
    assert prepared[0]["prepared_install"] == 1 and prepared[0]["full_path"] == 0
    assert full[0]["prepared_install"] == 0
    # Both include the one review context of the POST that creates the task.
    if variant == "global":
        # Child: one planning context, versus planning, Preview and Execute;
        # one preparation, not two. Both paths verify the appended next-slot
        # increment without a second complete post-write context (the
        # prepared worker against its read snapshot, Execute against its own
        # pre-write context); a fallback would add that context back here.
        assert (prepared[0]["context"], prepared[0]["prepare"]) == (1 + 1, 1)
        assert (full[0]["context"], full[0]["prepare"]) == (1 + 3, 2)
        assert prepared[0]["appended_slot"] == full[0]["appended_slot"] == 1
    elif variant == "original":
        # The legacy configured Tour v1 has no post-write replay in Execute.
        assert (prepared[0]["context"], prepared[0]["prepare"]) == (1 + 1, 1)
        assert (full[0]["context"], full[0]["prepare"]) == (1 + 3, 2)
    else:
        # A fork child has no post-write replay: one context instead of three.
        assert (prepared[0]["fork_context"], prepared[0]["fork_prepare"]) == (1 + 1, 1)
        assert (full[0]["fork_context"], full[0]["fork_prepare"]) == (1 + 3, 2)
    assert prepared[0]["preview"] == prepared[0]["execute"] == 0


def test_commit_between_read_and_write_takes_the_original_path(tmp_path, native_source, monkeypatch):
    from beta_engine.infrastructure.db.full_simulation_invocation_lease import (
        renew_invocation_lease,
    )

    source, command = native_source
    reference = tmp_path / "reference.db"
    _copy(source, reference)
    with ApiServer(database_url=f"sqlite:///{reference}") as server:
        start(server, command)
    path = tmp_path / "concurrent.db"
    _copy(source, path)
    calls = _watch_driver(monkeypatch)
    # A real competing commit: the lease renewal another heartbeat would make.
    fired = _after_read(monkeypatch, lambda driver, _command, token, _step: renew_invocation_lease(
        driver.repository._session_factory, token=token))
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        task = start(server, command)
        assert task["checkpoint"] == "native_manual_save_required", task
        assert _transitions(server) == 1
    assert fired and calls["prepared_install"] == 0 and calls["full_path"] == 1
    assert _rows(path) == _rows(reference)
    assert _parent(path, command["command_id"]) == _parent(reference, command["command_id"])


@pytest.mark.parametrize("scope_row", ["branch", "draft", "parent"])
def test_prepared_child_requires_the_same_head_draft_and_parent_bytes(tmp_path, native_source, monkeypatch, scope_row):
    """Second line of defence: even with an unchanged SQLite data_version, a
    prepared child never installs over a different Saved HEAD, Working Draft
    or parent row. It then takes the original complete path."""
    source, command = native_source
    reference = tmp_path / "reference.db"
    _copy(source, reference)
    with ApiServer(database_url=f"sqlite:///{reference}") as server:
        start(server, command)
    path = tmp_path / "scope.db"
    _copy(source, path)
    calls = _watch_driver(monkeypatch)

    def recorded_elsewhere(_driver, _command, _token, step):
        values = list(step[scope_row])
        index = {"branch": 0, "draft": 1, "parent": 2}[scope_row]
        values[index] = "different-head" if scope_row == "branch" else (
            values[index] + 1 if scope_row == "draft" else values[index] + " ")
        step[scope_row] = tuple(values)

    fired = _after_read(monkeypatch, recorded_elsewhere)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        task = start(server, command)
        assert task["checkpoint"] == "native_manual_save_required", task
    assert fired and calls["prepared_install"] == 0 and calls["full_path"] == 1
    assert _rows(path) == _rows(reference)


def test_working_draft_change_between_phases_is_never_overwritten(tmp_path, native_source, monkeypatch):
    from tests.api.test_calendar_tour_flow import command as tour_command
    from tests.api.test_native_full_simulation_tasks import execute_tour

    source, command = native_source
    path = tmp_path / "stale.db"
    _copy(source, path)
    calls = _watch_driver(monkeypatch)
    holder = {}

    def edit(_driver, _command, _token, _step):
        # An Admin edit stages a new Edition, making the reviewed child stale.
        view = inspect(holder["server"])
        week = view["state"]["week"]
        execute_tour(holder["server"], tour_command(view, "create-edition", name="late-admin-edit", data={
            "edition_id": "late-admin-edit", "name": "Late Admin edit",
            "week": {**week, "week": 4}, "announcement_week": {**week, "week": 3},
            "start_slot": 1, "main_entrant_count": 4, "ranked": True,
            "validity_weeks": week["calendar"]["weeks_per_year"],
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30}}))

    fired = _after_read(monkeypatch, edit)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        holder["server"] = server
        before = inspect(server)
        task = start(server, command)
        after = inspect(server)
        assert task["checkpoint"] == "native_manual_save_required", task
        assert not after["saved"] and after["tour_fingerprint"] != before["tour_fingerprint"]
        assert after["state"]["week"] == before["state"]["week"]
        assert len(after["state"]["transitions"]) == len(before["state"]["transitions"])
        assert any(a["edition"]["edition_id"] == "late-admin-edit" for a in after["state"]["editions"])
    assert fired and calls["prepared_install"] == 0
    status, parent = _parent(path, command["command_id"])
    assert status == "pending" and parent["children"] == [] and parent["pending_child"] is None


def test_pause_between_read_and_write_then_continue(tmp_path, native_source, monkeypatch):
    source, command = native_source
    path = tmp_path / "pause.db"
    _copy(source, path)
    calls = _watch_driver(monkeypatch)
    calls.watch(NativeFullSimulationDriver, "_read_prepared_step")
    holder = {}

    def pause(_driver, _command, _token, _step):
        body = {"target_command_id": command["command_id"], "control_command_id": "pause-between-phases",
                "action": "pause", "operator_label": "Admin", "audit_reason": "Pause while the child is prepared"}
        code, result = _request("POST", scope(holder["server"]) + "/control", body)
        assert code == 200, result

    fired = _after_read(monkeypatch, pause)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        holder["server"] = server
        task = start(server, command)
        assert task["state"] == "paused", task
        assert _transitions(server) == 0
        assert calls["prepared_install"] == 0
        assert calls["_read_prepared_step"] == 1
        assert calls["full_path"] == 1
        task = resume(server, task, "continue-after-pause")
        assert task["checkpoint"] == "native_manual_save_required", task
        assert _transitions(server) == 1
    assert fired and calls["prepared_install"] == 1
    status, parent = _parent(path, command["command_id"])
    assert parent["control_state"] == "running" and len(parent["children"]) == 1


def test_fork_progress_reuses_only_exact_authenticated_inputs(tmp_path, native_fork_source, monkeypatch):
    source, command, branch = native_fork_source
    path = tmp_path / "fork-progress.db"
    _copy(source, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        server.native_task_branch = branch
        task = start(server, command)
        assert task["checkpoint"] == "native_manual_save_required", task
        _, parent = _parent(path, command["command_id"])
        factory = server.app.state.runtime.repository._session_factory

        def read(payload=parent):
            from sqlalchemy import text
            with factory() as session:
                session.execute(text("BEGIN"))
                return native.read_native_task_progress(
                    session, run_id=command["run_id"], branch_id=branch, parent=payload,
                )

        monkeypatch.setattr(native, "_exact_facts", native.OrderedDict())
        calls = Calls(monkeypatch)
        calls.watch(native, "resolve_saved_run_calendar")
        first = read()
        assert read() == first
        assert calls["resolve_saved_run_calendar"] == 1

        # Keep the version, head, identity and claimed hash. Only persisted
        # content changes, so the previous successful result must miss.
        with sqlite3.connect(path) as sql:
            original, = sql.execute(
                "SELECT changes_json FROM branch_working_drafts WHERE branch_id=?", (branch,),
            ).fetchone()
            damaged = json.loads(original)
            damaged[0]["component"]["state"]["tour"]["receipts"][0]["result"]["changed"] = True
            sql.execute(
                "UPDATE branch_working_drafts SET changes_json=? WHERE branch_id=?",
                (json.dumps(damaged), branch),
            )
        with pytest.raises(ValueError, match="runtime hash/schema is corrupt"):
            read()
        with sqlite3.connect(path) as sql:
            sql.execute(
                "UPDATE branch_working_drafts SET changes_json=? WHERE branch_id=?",
                (original, branch),
            )
        bad_parent = json.loads(json.dumps(parent))
        bad_parent["children"][0]["result_fingerprint"] = "0" * 64
        with pytest.raises(ValueError, match="child differs"):
            read(bad_parent)
        assert read() == first
        save_tour(server)
        assert read() == first
        assert calls["resolve_saved_run_calendar"] == 4


def test_original_progress_reuses_only_exact_tour_and_receipt_inputs(
    tmp_path, global_slot_source, monkeypatch,
):
    from sqlalchemy import text

    source, command = global_slot_source
    path = tmp_path / "original-progress.db"
    _copy(source, path)
    run_id, branch_id = command["run_id"], command["branch_id"]
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        task = start(server, command)
        assert task["checkpoint"] == "native_manual_save_required", task
        _, parent = _parent(path, command["command_id"])
        factory = server.app.state.runtime.repository._session_factory

        def read(payload=parent):
            with factory() as session:
                session.execute(text("BEGIN"))
                return native.read_native_task_progress(
                    session, run_id=run_id, branch_id=branch_id, parent=payload,
                )

        monkeypatch.setattr(native, "_exact_facts", native.OrderedDict())
        calls = Calls(monkeypatch)
        calls.watch(native, "_native_progress_from_tour")
        first = read()
        assert first[1] > 0
        assert read() == first

        assert calls["_native_progress_from_tour"] == 1

        # A change to actual Tour bytes must miss, even when the stored
        # fingerprint and the task's accepted receipts have not changed.
        with sqlite3.connect(path) as sql:
            where = (run_id, branch_id)
            original, = sql.execute(
                "SELECT payload_json FROM calendar_tour_authorities WHERE run_id=? AND branch_id=?", where,
            ).fetchone()
            damaged = json.loads(original)
            damaged["receipts"][-1]["result"]["changed"] = True
            update = "UPDATE calendar_tour_authorities SET payload_json=? WHERE run_id=? AND branch_id=?"
            sql.execute(update, (json.dumps(damaged), *where))
        with pytest.raises(ValueError, match="sporting/Tour hash or position is corrupt"):
            read()
        with sqlite3.connect(path) as sql:
            sql.execute(update, (original, *where))

        bad_parent = json.loads(json.dumps(parent))
        bad_parent["children"][0]["result_fingerprint"] = "0" * 64
        with pytest.raises(ValueError, match="child differs"):
            read(bad_parent)
        assert read() == first


@pytest.mark.pr_critical
def test_task_calendar_rechecks_saved_v2_nodes_without_warm_materialization(tmp_path, monkeypatch):
    from sqlalchemy import text

    from beta_engine.infrastructure.db import saved_v2_store
    from beta_engine.infrastructure.db.saved_v2_hooks import ENVIRONMENT_VARIABLE
    from tests.api.test_saved_v2_http import _tamper

    monkeypatch.setenv(ENVIRONMENT_VARIABLE, "saved_v2")
    path = tmp_path / "task-calendar-v2.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        code, run = _request("POST", server.base_url + "/run-containers", {"display_name": "Task Calendar"})
        assert code == 201, run
        factory = server.app.state.runtime.repository._session_factory
        with sqlite3.connect(path) as sql:
            revision_id, stored = sql.execute(
                "SELECT revision_id, payload_json FROM branch_saved_revisions WHERE run_id=?", (run["run_id"],),
            ).fetchone()
        root, _ = saved_v2_store.parse_envelope(stored, run_id=run["run_id"])

        def read():
            with factory() as session:
                session.execute(text("BEGIN"))
                return native.verified_revision_calendar(
                    session, run_id=run["run_id"], revision_id=revision_id,
                )

        monkeypatch.setattr(native, "_exact_facts", native.OrderedDict())
        calls = Calls(monkeypatch)
        calls.watch(saved_v2_store, "_materialize_nodes")
        first = read()
        count = calls["_materialize_nodes"]
        assert count > 0
        assert read() == first
        assert calls["_materialize_nodes"] == count

        _tamper(path, [("UPDATE saved_revision_nodes SET body='damaged' WHERE run_id=? AND digest=?",
                       (run["run_id"], root))])
        with pytest.raises(saved_v2_store.SavedV2IntegrityError):
            read()


def test_lease_expiry_between_read_and_write_writes_nothing(tmp_path, native_source, monkeypatch):
    from beta_engine.infrastructure.db import full_simulation_execution_guard as guard

    source, command = native_source
    path = tmp_path / "lease.db"
    _copy(source, path)
    real_time = guard.time.time

    class Expired:
        @staticmethod
        def time():
            return real_time() + 10_000

    fired = _after_read(monkeypatch, lambda *_args: monkeypatch.setattr(guard, "time", Expired))
    before = _sporting(path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        task = start_failed(server, command)
        assert "lease ownership was lost" in task["error"], task
        monkeypatch.setattr(guard, "time", time)
        assert _sporting(path) == before
        status, parent = _parent(path, command["command_id"])
        assert parent["children"] == [] and parent["pending_child"] is None
        task = resume(server, task, "recover-after-lost-lease", action="recover")
        assert task["checkpoint"] == "native_manual_save_required", task
        assert _transitions(server) == 1
    assert fired


def start_failed(server, command):
    body = {"request_id": "start-" + command["command_id"], "command": command}
    code, ack = _request("POST", scope(server) + "/tasks", body)
    assert code == 202, ack
    task = wait(server, ack["task_id"], allow_failed=True)
    assert task["state"] == "failed", task
    return task


def test_restart_after_committed_step_before_task_center_result(tmp_path, native_source, monkeypatch):
    from beta_engine.application.full_simulation_tasks import FullSimulationTaskWorker

    source, command = native_source
    path = tmp_path / "restart.db"
    _copy(source, path)
    finish = FullSimulationTaskWorker._finish
    lost = []

    def process_lost_before_result(self, task_id, token, **kwargs):
        if not lost:
            lost.append(kwargs)
            return None  # the child committed; Task Center never records it
        return finish(self, task_id, token, **kwargs)

    monkeypatch.setattr(FullSimulationTaskWorker, "_finish", process_lost_before_result)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        body = {"request_id": "start-" + command["command_id"], "command": command}
        code, ack = _request("POST", scope(server) + "/tasks", body)
        assert code == 202, ack
        deadline = time.monotonic() + 90
        while not lost or _request("GET", scope(server) + "/tasks/" + ack["task_id"])[1]["tasks"][0]["state"] != "recoverable":
            assert time.monotonic() < deadline
            time.sleep(0.5)
        assert lost[0]["result"]["checkpoint"] == "native_manual_save_required"
    status, parent = _parent(path, command["command_id"])
    assert status == "pending" and len(parent["children"]) == 1 and parent["pending_child"] is None
    with ApiServer(database_url=f"sqlite:///{path}") as restarted:
        task = _request("GET", scope(restarted) + "/tasks/" + ack["task_id"])[1]["tasks"][0]
        assert task["state"] == "recoverable" and _transitions(restarted) == 1
        task = resume(restarted, task, "recover-after-restart", action="recover")
        assert task["checkpoint"] == "native_manual_save_required", task
        assert _transitions(restarted) == 1  # no duplicate child or match
        save_tour(restarted)
        task = resume(restarted, task, "saved-after-restart")
        assert task["state"] == "target_reached", task
        assert _transitions(restarted) == 1
    status, parent = _parent(path, command["command_id"])
    assert status == "target_reached" and len(parent["children"]) == 1


def test_pending_child_from_original_path_recovers_by_exact_retry(tmp_path, native_source, monkeypatch):
    source, _command = native_source
    path = tmp_path / "legacy-pending.db"
    _copy(source, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        # A later target: recovery must execute the frozen child, not end at it.
        command = reviewed(server, {"season_index": 0, "week": 4}, name="legacy-pending")

    def crash(name):
        raise ValueError("Injected process loss after the actual child commit")

    with ApiServer(database_url=f"sqlite:///{path}") as server:
        with monkeypatch.context() as patch:
            _force_full_path(patch)
            patch.setattr(native, "_fault_injection_point", crash)
            task = start_failed(server, command)
        status, parent = _parent(path, command["command_id"])
        assert parent["pending_child"] is not None and parent["children"] == []
        assert _transitions(server) == 1
        calls = _watch_driver(monkeypatch)
        task = resume(server, task, "recover-frozen-child", action="recover")
        assert task["checkpoint"] == "native_manual_save_required", task
        assert _transitions(server) == 1
        assert calls["prepared_install"] == 0 and calls["full_path"] == 1
        # The frozen child is executed only as an exact receipt retry.
        assert calls["prepare"] == 0
    status, parent = _parent(path, command["command_id"])
    assert parent["pending_child"] is None and len(parent["children"]) == 1


def test_bounded_heartbeat_deferral_never_skips_renewal(tmp_path, monkeypatch):
    from sqlalchemy import text

    from beta_engine.infrastructure.db import full_simulation_invocation_lease as lease
    from beta_engine.infrastructure.db.engine import (
        DatabaseSettings,
        create_session_factory,
        create_sqlite_engine,
    )
    from beta_engine.infrastructure.db.models import Base, FullSimulationExecutionLeaseModel

    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'lease.db'}"))
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    monkeypatch.setattr(lease, "RENEW_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(lease, "HEARTBEAT_DEFERRAL_SECONDS", 0.5)
    beats = []
    hold = lease.DeferredLeaseHeartbeat()
    with lease.full_simulation_invocation_lease(factory, run_id="r", branch_id="b", command_id="c",
                                                on_heartbeat=lambda: beats.append(time.monotonic())) as token:
        time.sleep(0.3)
        assert beats, "heartbeat runs normally"
        assert hold.acquire(wait_seconds=5)
        held_at, count = time.monotonic(), len(beats)
        time.sleep(0.2)
        assert len(beats) == count, "renewal waits while the snapshot is read"
        time.sleep(0.6)
        assert len(beats) > count and beats[count] - held_at >= 0.45, "but never longer than the bound"
        hold.release()
        hold.release()  # idempotent
        with factory() as session:
            session.execute(text("BEGIN"))
            assert session.get(FullSimulationExecutionLeaseModel, lease.LEASE_SCOPE).owner_token == token
    engine.dispose()
