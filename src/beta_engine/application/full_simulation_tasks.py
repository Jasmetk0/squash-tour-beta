"""Durable task control plane above the unchanged authoritative sporting driver.

Only explicit POSTs enqueue work. GETs never recover, renew or execute anything.
A process-local dispatcher is disposable: command, requests, events and ownership
are persisted before acknowledgement, and a lost dispatcher requires recovery.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from threading import Event, Lock, Thread
from uuid import uuid4

from sqlalchemy import func, select, text

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeFullSimulationCommand,
    AuthoritativeFullSimulationControlCommand,
    fingerprint,
)
from beta_engine.infrastructure.db.full_simulation_invocation_lease import (
    LEASE_SCOPE,
    acquire_in_session,
    full_simulation_invocation_lease,
    require_invocation_lease_owner,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    FullSimulationExecutionLeaseModel,
    FullSimulationTaskModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    RunBranchModel,
    RunContainerModel,
)

_LOG = logging.getLogger(__name__)
STATES = {
    "queued",
    "active",
    "paused",
    "awaiting_operator",
    "stopped",
    "target_reached",
    "complete",
    "failed",
}
TERMINAL = {"stopped", "target_reached", "complete"}
EDGES = {
    "queued": {"queued", "active", "failed"},
    "active": {
        "queued",
        "paused",
        "awaiting_operator",
        "stopped",
        "target_reached",
        "complete",
        "failed",
    },
    "paused": {"queued"},
    "awaiting_operator": {"queued", "paused"},
    "failed": {"queued"},
    "stopped": set(),
    "target_reached": set(),
    "complete": set(),
}


class ChunkYield(Exception):
    """Yield before a new SQLite transaction; committed children remain canonical."""


def _read(row):
    try:
        data = json.loads(row.payload_json)
        if (
            data["schema_version"] != "full_simulation_task.v1"
            or fingerprint(data) != row.payload_fingerprint
        ):
            raise ValueError("Task schema/fingerprint mismatch")
        command = AuthoritativeFullSimulationCommand.model_validate(data["command"])
        if (command.run_id, command.branch_id, command.command_id) != (
            row.run_id,
            row.branch_id,
            row.parent_command_id,
        ):
            raise ValueError("Task command scope mismatch")
        if (
            data["task_id"] != row.task_id
            or data["start_request_id"] != row.start_request_id
        ):
            raise ValueError("Task identity mismatch")
        events = data["events"]
        if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
            raise ValueError("Task events must be an array of objects")
        previous = None
        prior_state = None
        for index, event in enumerate(events, 1):
            body = {k: v for k, v in event.items() if k != "fingerprint"}
            if (
                event["revision"] != index
                or event["previous"] != previous
                or fingerprint(body) != event["fingerprint"]
            ):
                raise ValueError("Task audit chain mismatch")
            state = event["state"]
            if state not in STATES or (prior_state is None and state != "queued"):
                raise ValueError("Invalid task state")
            if prior_state and state not in EDGES[prior_state]:
                raise ValueError("Invalid task transition")
            previous, prior_state = event["fingerprint"], state
        if (
            not events
            or data["revision"] != len(events)
            or data["state"] != prior_state
        ):
            raise ValueError("Task revision mismatch")
        requests = data["requests"]
        if not isinstance(requests, list) or not all(
            isinstance(r, dict) for r in requests
        ):
            raise ValueError("Task requests must be an array of objects")
        if len({r["request_id"] for r in requests}) != len(requests) or not requests:
            raise ValueError("Task request identity mismatch")
        for request in requests:
            if request["fingerprint"] != fingerprint(request["input"]):
                raise ValueError("Task request fingerprint mismatch")
            ack = request["ack"]
            if (
                ack != _ack(row, request["request_id"], ack["accepted_revision"])
                or not 1 <= ack["accepted_revision"] <= data["revision"]
            ):
                raise ValueError("Task acknowledgement mismatch")
        if requests[0]["request_id"] != row.start_request_id or requests[0][
            "input"
        ] != {"action": "start", "command": data["command"]}:
            raise ValueError("Task original request mismatch")
        if type(data["heartbeat_unix"]) is not int or data["heartbeat_unix"] < 0:
            raise ValueError("Task heartbeat corrupt")
        return data
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Full Simulation task evidence is corrupt: {exc}") from exc


def _write(row, data):
    row.payload_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
    row.payload_fingerprint = fingerprint(data)


def _event(data, state, reason):
    previous = data["events"][-1]["fingerprint"] if data["events"] else None
    prior = data.get("state")
    if previous and state not in EDGES[prior]:
        raise ValueError(f"Illegal task transition {prior} -> {state}")
    revision = len(data["events"]) + 1
    event = {
        "revision": revision,
        "previous": previous,
        "state": state,
        "reason": reason,
        "at_unix": int(time.time()),
    }
    event["fingerprint"] = fingerprint(event)
    data["events"].append(event)
    data["state"], data["revision"] = state, revision


def _ack(row, request_id, revision):
    return {
        "schema_version": "full_simulation_task_ack.v1",
        "task_id": row.task_id,
        "run_id": row.run_id,
        "branch_id": row.branch_id,
        "parent_command_id": row.parent_command_id,
        "request_id": request_id,
        "accepted_revision": revision,
    }


def _request(row, data, request_id, body):
    for prior in data["requests"]:
        if prior["request_id"] == request_id:
            if prior["input"] != body:
                raise ValueError("Task request ID was reused with different input")
            return prior["ack"]
    return None


def _record(row, data, request_id, body):
    ack = _ack(row, request_id, data["revision"])
    data["requests"].append(
        {
            "request_id": request_id,
            "input": body,
            "fingerprint": fingerprint(body),
            "ack": ack,
        }
    )
    _write(row, data)
    return ack


def _parent(session, row, data):
    parent = session.get(
        AuthoritativeSimulationCommandModel,
        (row.run_id, row.branch_id, row.parent_command_id),
    )
    if parent is None or parent.request_fingerprint != fingerprint(
        {"mode": "full_simulation", "command": data["command"]}
    ):
        raise ValueError("Task parent identity/fingerprint mismatch")
    payload = json.loads(parent.result_json)
    if parent.status not in {
        "pending",
        "stopped",
        "target_reached",
        "complete",
        "abandoned",
    }:
        raise ValueError("Task parent status corrupt")
    if parent.status != "complete" and payload.get("resume_command") != data["command"]:
        raise ValueError("Task parent immutable command mismatch")
    from beta_engine.application.full_simulation_boundary_targets import effective_boundary
    effective_boundary(payload)
    if payload.get("schema_version") == "authoritative_full_simulation_operation.v1" and any(
            e.get("boundary_target") is not None for e in payload.get("target_events", [])):
        from beta_engine.application.authoritative_run_simulation_driver import AuthoritativeRunSimulationDriver
        AuthoritativeRunSimulationDriver._validate_full_target_audit(parent, payload)
    return parent, payload


def _owned(lease, row, data, now):
    return (
        lease is not None
        and lease.owner_token == data["owner_token"]
        and (lease.run_id, lease.branch_id, lease.command_id)
        == (row.run_id, row.branch_id, row.parent_command_id)
        and lease.expires_at_unix > now
    )


def _progress_evidence(session, row, parent, frozen, command, branch_ordinal):
    """Read-only current Branch receipts or immutable historical task position.

    The live counts cover *all* persisted Branch receipts for the current week,
    NOT work exclusively attributable to this Full Simulation task.
    """
    start = command.expected_start_week.ordinal
    kind = "live_branch" if branch_ordinal is not None else "unavailable"
    ordinal = branch_ordinal
    if parent.status in ("stopped", "target_reached"):
        from beta_engine.application.full_simulation_summary import stored_terminal_summary

        summary = stored_terminal_summary(parent, frozen)
        if summary is None:
            kind, ordinal = "unavailable", None
        else:
            kind = "terminal_frozen"
            end = summary["end_week"]
            ordinal = end["season_index"] * 61 + end["week"] - 1
    elif parent.status == "complete":
        if (frozen.get("schema_version") != "authoritative_full_simulation_result.v1"
                or frozen.get("run_id") != row.run_id
                or frozen.get("branch_id") != row.branch_id
                or frozen.get("start_week") != command.expected_start_week.model_dump(mode="json")
                or frozen.get("final_week") != {"season_index": 49, "week": 61}):
            raise ValueError("Complete Full Simulation terminal position is corrupt")
        kind, ordinal = "terminal_frozen", 50 * 61 - 1
    elif parent.status == "abandoned":
        kind, ordinal = "unavailable", None

    if ordinal is not None and not start <= ordinal < 50 * 61:
        raise ValueError("Task Position precedes reviewed start or exceeds final Run week")
    week = (
        {"season_index": ordinal // 61, "week": ordinal % 61 + 1}
        if ordinal is not None else None
    )
    slots = groups = None
    if kind == "live_branch" and ordinal is not None:
        slots = session.scalar(
            select(func.count()).select_from(SimulationSlotModel).where(
                SimulationSlotModel.run_id == row.run_id,
                SimulationSlotModel.branch_id == row.branch_id,
                SimulationSlotModel.week_ordinal == ordinal,
                SimulationSlotModel.status == "complete",
                SimulationSlotModel.terminal_checkpoint_json.is_not(None),
            )
        )
        groups = session.scalar(
            select(func.count()).select_from(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == row.run_id,
                SimulationEventGroupModel.branch_id == row.branch_id,
                SimulationEventGroupModel.week_ordinal == ordinal,
            )
        )
    return {
        "schema_version": "full_simulation_task_progress_evidence.v1",
        "kind": kind,
        "week": week,
        "weeks_advanced_since_start": ordinal - start if ordinal is not None else None,
        "completed_slot_receipts_this_week": slots,
        "committed_group_receipts_this_week": groups,
        "receipt_scope": "branch_current_week" if kind == "live_branch" else None,
    }


def _project(session, row, observer_instance=None):
    data = _read(row)
    parent, frozen = _parent(session, row, data)
    run, branch = (
        session.get(RunContainerModel, row.run_id),
        session.get(RunBranchModel, row.branch_id),
    )
    if run is None or branch is None or branch.run_id != row.run_id:
        raise ValueError("Task has no matching Run/Branch")
    now = int(time.time())
    lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
    owned = _owned(lease, row, data, now)
    state = data["state"]
    control = frozen.get("control_state", "running")
    if parent.status in TERMINAL:
        state = parent.status
    elif parent.status == "abandoned":
        state = "failed"
    elif state in {"queued", "active"}:
        if not owned:
            state = "recoverable"
        elif (
            observer_instance is not None
            and data["owner_instance"] != observer_instance
        ):
            state = "ownership_unverified"
        elif control == "pause_requested":
            state = "pause_requested"
    health = (
        "recent"
        if owned and 0 <= now - data["heartbeat_unix"] < 30
        else "stale"
        if owned
        else "inactive"
    )
    ordinal = (
        session.connection()
        .exec_driver_sql(
            "SELECT current_ordinal FROM authoritative_world_states WHERE run_id=? AND branch_id=?",
            (row.run_id, row.branch_id),
        )
        .scalar()
    )
    if ordinal is None:
        ordinal = (
            session.connection()
            .exec_driver_sql(
                "SELECT MAX(week_ordinal) FROM player_sporting_week_states WHERE run_id=? AND branch_id=?",
                (row.run_id, row.branch_id),
            )
            .scalar()
        )
    command = AuthoritativeFullSimulationCommand.model_validate(data["command"])
    evidence = _progress_evidence(session, row, parent, frozen, command, ordinal)
    current_week = evidence["week"]
    return {
        "schema_version": "full_simulation_task_view.v1",
        "task_id": row.task_id,
        "run_id": row.run_id,
        "branch_id": row.branch_id,
        "parent_command_id": row.parent_command_id,
        "run_name": run.display_name,
        "branch_name": branch.display_name,
        "current_week": current_week,
        "progress_evidence": evidence,
        "effective_boundary_target": frozen.get("effective_boundary_target"),
        "revision": data["revision"],
        "desired_state": data["state"],
        "state": state,
        "heartbeat_health": health,
        "heartbeat_unix": data["heartbeat_unix"],
        "lease_expires_at_unix": lease.expires_at_unix if owned else None,
        "checkpoint": data.get("checkpoint"),
        "progress": data.get("progress"),
        "error": data.get("error"),
        "needs_operator_action": state
        in {"awaiting_operator", "recoverable", "failed", "paused"},
        "events": data["events"],
        "original_command": data["command"],
    }


def inspect_tasks(
    factory, *, run_id=None, branch_id=None, task_id=None, observer_instance=None
):
    with factory() as session:
        query = select(FullSimulationTaskModel).order_by(
            FullSimulationTaskModel.task_id
        )
        if run_id is not None:
            query = query.where(
                FullSimulationTaskModel.run_id == run_id,
                FullSimulationTaskModel.branch_id == branch_id,
            )
        rows = session.scalars(query).all()
        if task_id is not None:
            rows = [r for r in rows if r.task_id == task_id]
            if not rows:
                raise ValueError("Task is unavailable in this exact Run/Branch")
        return {
            "schema_version": "full_simulation_tasks.v1",
            "tasks": [_project(session, r, observer_instance) for r in rows],
        }


class FullSimulationTaskWorker:
    """One bounded dispatcher per server; SQLite arbitrates across processes.

    Restart intentionally does not scan/enqueue old tasks. An explicit recovery
    POST validates their original command and claims an expired global lease.
    """

    def __init__(self, factory):
        self.factory = factory
        self.instance = uuid4().hex
        self.stopping = Event()
        self.wake = Event()
        self.lock = Lock()
        self.queue = deque()
        self.thread = Thread(
            target=self._dispatch, name="full-simulation-tasks", daemon=True
        )
        self.thread.start()

    def close(self):
        self.stopping.set()
        self.wake.set()
        self.thread.join(timeout=5)

    def enqueue(self, task_id, driver):
        with self.lock:
            self.queue.append((task_id, driver))
        self.wake.set()

    def start(self, driver, *, run_id, branch_id, request_id, command):
        if self.stopping.is_set():
            raise ValueError("Server task worker is shutting down")
        if (command.run_id, command.branch_id) != (run_id, branch_id):
            raise ValueError("Task command scope mismatch")
        body = {"action": "start", "command": command.model_dump(mode="json")}
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            rows = session.scalars(
                select(FullSimulationTaskModel).where(
                    FullSimulationTaskModel.run_id == run_id,
                    FullSimulationTaskModel.branch_id == branch_id,
                )
            ).all()
            for row in rows:
                data = _read(row)
                ack = _request(row, data, request_id, body)
                if ack is not None:
                    _parent(session, row, data)
                    return ack
                if row.parent_command_id == command.command_id:
                    raise ValueError(
                        "Parent already owns a task; use its original start request or explicit continuation"
                    )
            driver._require_writable_scope(session, run_id, branch_id)
            token = acquire_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                command_id=command.command_id,
            )
            prior_parent = session.get(
                AuthoritativeSimulationCommandModel,
                (run_id, branch_id, command.command_id),
            )
            if prior_parent is not None:
                if prior_parent.status != "pending":
                    raise ValueError("Cannot start a terminal parent as a server task")
                if (
                    json.loads(prior_parent.result_json).get("control_state", "running")
                    != "running"
                ):
                    raise ValueError(
                        "A paused legacy parent requires explicit resume authorization first"
                    )
            existing = driver.prepare_full_simulation(
                session,
                command,
                fingerprint({"mode": "full_simulation", "command": body["command"]}),
            )
            if existing is not None:
                raise ValueError("Cannot start a terminal parent as a server task")
            row = FullSimulationTaskModel(
                task_id="fst-" + uuid4().hex,
                run_id=run_id,
                branch_id=branch_id,
                parent_command_id=command.command_id,
                start_request_id=request_id,
            )
            data = {
                "schema_version": "full_simulation_task.v1",
                "task_id": row.task_id,
                "start_request_id": request_id,
                "command": body["command"],
                "events": [],
                "requests": [],
                "owner_instance": self.instance,
                "owner_token": token,
                "heartbeat_unix": 0,
                "checkpoint": None,
                "progress": None,
                "error": None,
            }
            session.flush()  # Materialize the original parent before validating ownership.
            _parent(session, row, data)
            _event(data, "queued", "explicit_start")
            ack = _record(row, data, request_id, body)
            session.add(row)
        self.enqueue(row.task_id, driver)
        return ack

    def continue_task(
        self,
        driver,
        *,
        run_id,
        branch_id,
        task_id,
        request_id,
        action,
        expected_revision,
        operator_label,
        audit_reason,
    ):
        body = {
            "action": action,
            "expected_revision": expected_revision,
            "operator_label": operator_label,
            "audit_reason": audit_reason,
        }
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(FullSimulationTaskModel, task_id)
            if row is None or (row.run_id, row.branch_id) != (run_id, branch_id):
                raise ValueError("Task scope mismatch")
            data = _read(row)
            parent, frozen = _parent(session, row, data)
            prior = _request(row, data, request_id, body)
            if prior is not None:
                return prior
            if data["revision"] != expected_revision:
                raise ValueError("Task revision changed; refresh before continuing")
            driver._require_writable_scope(session, run_id, branch_id)
            if parent.status != "pending":
                raise ValueError("Terminal parent cannot continue")
            lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
            busy = _owned(lease, row, data, int(time.time()))
            if busy:
                raise ValueError(
                    "Task still holds an unexpired execution lease; wait for safe release or expiry"
                )
            if action == "recover":
                if data["state"] not in {"queued", "active", "failed"}:
                    raise ValueError("Task does not require crash recovery")
            elif action == "resume":
                if data["state"] not in {"paused", "awaiting_operator"}:
                    raise ValueError(
                        "Task is not paused or waiting for operator action"
                    )
            else:
                raise ValueError("Unsupported continuation action")
            # Control audit and task claim share the writer lock. Reuse the
            # canonical resume semantics without a second nested transaction.
            if frozen.get("control_state") in {"pause_requested", "paused"}:
                if frozen["control_state"] == "pause_requested":
                    frozen["control_state"] = (
                        "paused"  # expired/absent owner cannot commit further work
                    )
                parent.result_json = json.dumps(
                    frozen, sort_keys=True, separators=(",", ":")
                )
                driver.control_full_simulation_in_session(
                    session,
                    AuthoritativeFullSimulationControlCommand(
                        run_id=run_id,
                        branch_id=branch_id,
                        target_command_id=row.parent_command_id,
                        control_command_id="task-"
                        + fingerprint({"task_id": task_id, "request_id": request_id})[
                            :48
                        ],
                        action="resume",
                        operator_label=operator_label,
                        audit_reason=audit_reason,
                    ),
                )
            token = acquire_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                command_id=row.parent_command_id,
            )
            data.update(
                owner_instance=self.instance,
                owner_token=token,
                heartbeat_unix=0,
                error=None,
            )
            _event(data, "queued", "explicit_" + action)
            ack = _record(row, data, request_id, body)
        self.enqueue(task_id, driver)
        return ack

    def acknowledge_idle_pause(self, driver, command):
        if command.action != "pause":
            return
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.scalar(
                select(FullSimulationTaskModel).where(
                    FullSimulationTaskModel.run_id == command.run_id,
                    FullSimulationTaskModel.branch_id == command.branch_id,
                    FullSimulationTaskModel.parent_command_id
                    == command.target_command_id,
                )
            )
            if row is None:
                return
            data = _read(row)
            parent, frozen = _parent(session, row, data)
            lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
            if data["state"] != "awaiting_operator" or _owned(
                lease, row, data, int(time.time())
            ):
                return
            if (
                parent.status == "pending"
                and frozen.get("control_state") == "pause_requested"
            ):
                frozen["control_state"] = "paused"
                parent.result_json = json.dumps(
                    frozen, sort_keys=True, separators=(",", ":")
                )
                data["checkpoint"] = "operator_paused"
                _event(data, "paused", "idle_safe_pause_acknowledged")
                _write(row, data)

    def _dispatch(self):
        while not self.stopping.is_set():
            self.wake.wait(1)
            self.wake.clear()
            while not self.stopping.is_set():
                with self.lock:
                    item = self.queue.popleft() if self.queue else None
                if item is None:
                    break
                try:
                    self._execute(*item)
                except Exception:  # noqa: BLE001 - isolate one failed disposable dispatcher invocation
                    _LOG.exception("Server task dispatcher failed closed")

    def _heartbeat(self, task_id, token):
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            require_invocation_lease_owner(session, token=token)
            row = session.get(FullSimulationTaskModel, task_id)
            data = _read(row)
            if data["owner_token"] != token:
                raise ValueError("Task ownership changed")
            data["heartbeat_unix"] = int(time.time())
            _write(row, data)

    def _execute(self, task_id, driver):
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(FullSimulationTaskModel, task_id)
            data = _read(row)
            if data["state"] != "queued" or data["owner_instance"] != self.instance:
                return
            token = data["owner_token"]
            require_invocation_lease_owner(session, token=token)
            _parent(session, row, data)
            _event(data, "active", "worker_entered")
            data["heartbeat_unix"] = int(time.time())
            _write(row, data)
            command = AuthoritativeFullSimulationCommand.model_validate(data["command"])
        with full_simulation_invocation_lease(
            self.factory,
            run_id=command.run_id,
            branch_id=command.branch_id,
            command_id=command.command_id,
            existing_token=token,
            on_heartbeat=lambda: self._heartbeat(task_id, token),
        ):
            original_hook = driver.full_simulation_before_transaction_check
            try:
                while not self.stopping.is_set():
                    count = 0

                    def boundary():
                        nonlocal count
                        if self.stopping.is_set():
                            raise RuntimeError(
                                "Server shutdown; explicit recovery required"
                            )
                        count += 1
                        if count > 64:
                            raise ChunkYield()
                        if original_hook is not None:
                            original_hook()

                    driver.full_simulation_before_transaction_check = boundary
                    try:
                        result = driver.simulate_full_simulation(
                            command, execution_lease_token=token
                        )
                    except ChunkYield:
                        self._heartbeat(task_id, token)
                        continue
                    self._finish(task_id, token, result=result)
                    return
                raise RuntimeError("Server shutdown; explicit recovery required")
            except Exception as exc:  # noqa: BLE001 - persist unexpected worker failure before releasing the lease
                _LOG.exception("Server task execution failed")
                message = (
                    str(exc)
                    if isinstance(exc, (ValueError, RuntimeError))
                    else f"{type(exc).__name__}: worker failed; inspect server logs before explicit recovery"
                )
                self._finish(task_id, token, error=message)
            finally:
                driver.full_simulation_before_transaction_check = original_hook

    def _finish(self, task_id, token, *, result=None, error=None):
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(FullSimulationTaskModel, task_id)
            data = _read(row)
            if data["owner_token"] != token or data["owner_instance"] != self.instance:
                return  # A stale owner never overwrites recovery evidence.
            lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
            if not _owned(lease, row, data, int(time.time())):
                return
            parent, frozen = _parent(session, row, data)
            if parent.status in TERMINAL:
                state = parent.status
            elif frozen.get("control_state") == "paused":
                state = "paused"
            elif error is not None:
                state = "failed"
            else:
                state = "awaiting_operator"
            data["progress"] = result
            data["checkpoint"] = result.get("checkpoint") if result else None
            data["error"] = error
            _event(data, state, "worker_error" if error else "canonical_checkpoint")
            _write(row, data)
