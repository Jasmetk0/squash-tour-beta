"""Invocation-local execution fence for durable Full Simulation parents."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class FullSimulationExecutionGuard:
    run_id: str
    branch_id: str
    command_id: str
    request_fingerprint: str
    before_transaction_check: Callable[[], None] | None = None


class FullSimulationPauseRequested(Exception):
    """Cooperative stop before a child writer flush; its transaction rolls back."""


ACTIVE_FULL_SIMULATION_GUARD: ContextVar[
    FullSimulationExecutionGuard | None
] = ContextVar("active_full_simulation_execution_guard", default=None)


def require_pending_full_simulation_guard(session: Session) -> None:
    """Require the active parent to remain pending inside the caller transaction."""

    guard = ACTIVE_FULL_SIMULATION_GUARD.get()
    if guard is None:
        return
    row = session.connection().exec_driver_sql(
        "SELECT request_fingerprint, status, result_json "
        "FROM authoritative_simulation_commands "
        "WHERE run_id = ? AND branch_id = ? AND command_id = ?",
        (guard.run_id, guard.branch_id, guard.command_id),
    ).first()
    if row is None:
        return
    if row[0] != guard.request_fingerprint:
        raise ValueError("Full Simulation execution guard fingerprint mismatch")
    if row[1] == "abandoned":
        raise ValueError(
            "Full Simulation parent has an invalid status: abandoned; "
            "execution is fenced"
        )
    if row[1] != "pending":
        raise ValueError("Full Simulation execution guard found an invalid status")
    # A pause never truncates a MatchEngine/slot transaction: the next pending
    # child flush is rolled back atomically and acknowledged by the parent.
    import json
    control = json.loads(row[2]).get("control_state", "running")
    if control in ("pause_requested", "paused"):
        raise FullSimulationPauseRequested("Full Simulation pause requested at safe transaction boundary")


@event.listens_for(Session, "before_flush")
def _fence_full_simulation_flush(session, flush_context, instances) -> None:
    require_pending_full_simulation_guard(session)


@event.listens_for(Engine, "before_cursor_execute")
def _pause_before_full_simulation_writer(
    connection, cursor, statement, parameters, context, executemany
) -> None:
    guard = ACTIVE_FULL_SIMULATION_GUARD.get()
    if guard is None or statement.strip().upper() != "BEGIN IMMEDIATE":
        return
    if guard.before_transaction_check is not None:
        guard.before_transaction_check()
    # SQLite reserves the writer lock at BEGIN IMMEDIATE: checking the durable
    # parent immediately before it fences ORM flushes AND direct SQL writers.
    # Another control request cannot commit while the child holds this lock.
    row = connection.exec_driver_sql(
        "SELECT request_fingerprint, status, result_json "
        "FROM authoritative_simulation_commands "
        "WHERE run_id = ? AND branch_id = ? AND command_id = ?",
        (guard.run_id, guard.branch_id, guard.command_id),
    ).first()
    if row is None:
        return  # The first parent creation has not been committed yet.
    if row[0] != guard.request_fingerprint:
        raise ValueError("Full Simulation execution guard fingerprint mismatch")
    if row[1] == "abandoned":
        raise ValueError("Full Simulation parent abandoned; execution is fenced")
    if row[1] == "complete":
        # After explicit final Run closure the parent performs read-only
        # reconciliation; existing before_flush still fences new ORM writes.
        return
    if row[1] != "pending":
        raise ValueError("Full Simulation execution guard found an invalid status")
    import json
    if json.loads(row[2]).get("control_state", "running") in (
        "pause_requested", "paused"
    ):
        raise FullSimulationPauseRequested("Full Simulation pause requested before writer transaction")
