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


ACTIVE_FULL_SIMULATION_GUARD: ContextVar[
    FullSimulationExecutionGuard | None
] = ContextVar("active_full_simulation_execution_guard", default=None)


def require_pending_full_simulation_guard(session: Session) -> None:
    """Require the active parent to remain pending inside the caller transaction."""

    guard = ACTIVE_FULL_SIMULATION_GUARD.get()
    if guard is None:
        return
    row = session.connection().exec_driver_sql(
        "SELECT request_fingerprint, status "
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


@event.listens_for(Session, "before_flush")
def _fence_full_simulation_flush(session, flush_context, instances) -> None:
    require_pending_full_simulation_guard(session)


@event.listens_for(Engine, "before_cursor_execute")
def _pause_before_full_simulation_writer(
    connection, cursor, statement, parameters, context, executemany
) -> None:
    guard = ACTIVE_FULL_SIMULATION_GUARD.get()
    if (
        guard is not None
        and guard.before_transaction_check is not None
        and statement.strip().upper() == "BEGIN IMMEDIATE"
    ):
        guard.before_transaction_check()
