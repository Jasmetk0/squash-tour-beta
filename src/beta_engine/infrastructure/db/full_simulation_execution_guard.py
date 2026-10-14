"""Invocation-local execution fence for durable Full Simulation parents."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
import time
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
    execution_lease_token: str | None = None
    before_transaction_check: Callable[[], None] | None = None


class FullSimulationPauseRequested(Exception):
    """Cooperative pause before a child writer flush; its transaction rolls back."""


class FullSimulationStopped(Exception):
    """A terminal stop was committed at a safe SQLite writer boundary."""


class FullSimulationTargetReached(Exception):
    """The effective start-of-week target was reached at a writer boundary."""


ACTIVE_FULL_SIMULATION_GUARD: ContextVar[
    FullSimulationExecutionGuard | None
] = ContextVar("active_full_simulation_execution_guard", default=None)


def _verify_invocation_lease(connection, token: str | None) -> None:
    if token is None:
        return
    row = connection.exec_driver_sql(
        "SELECT owner_token, expires_at_unix FROM full_simulation_execution_leases "
        "WHERE lease_scope = 'all_runs'"
    ).first()
    if row is None or row[0] != token or row[1] <= int(time.time()):
        raise ValueError(
            "Full Simulation execution lease ownership was lost; "
            "stale child work is fenced"
        )


def require_pending_full_simulation_guard(session: Session) -> None:
    """Require the active parent to remain pending inside the caller transaction."""

    guard = ACTIVE_FULL_SIMULATION_GUARD.get()
    if guard is None:
        return
    _verify_invocation_lease(session.connection(), guard.execution_lease_token)
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
    if row[1] == "stopped":
        raise FullSimulationStopped("Full Simulation operator stop committed")
    if row[1] == "target_reached":
        raise FullSimulationTargetReached("Full Simulation effective target reached")
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


@event.listens_for(Session, "before_commit")
def _fence_full_simulation_commit(session: Session) -> None:
    """Recheck the invocation on commit, including direct-SQL-only transactions.

    A long-running child may outlive a previously valid lease after its
    BEGIN IMMEDIATE / last ORM flush. A final check blocks that transaction
    from committing after expiry, even if no ORM flush was needed.
    """
    guard = ACTIVE_FULL_SIMULATION_GUARD.get()
    if guard is not None:
        _verify_invocation_lease(session.connection(), guard.execution_lease_token)


@event.listens_for(Engine, "before_cursor_execute")
def _pause_before_full_simulation_writer(
    connection, cursor, statement, parameters, context, executemany
) -> None:
    guard = ACTIVE_FULL_SIMULATION_GUARD.get()
    if guard is None or statement.strip().upper() != "BEGIN IMMEDIATE":
        return
    if guard.before_transaction_check is not None:
        guard.before_transaction_check()
    _verify_invocation_lease(connection, guard.execution_lease_token)
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
    if row[1] == "stopped":
        raise FullSimulationStopped("Full Simulation operator stop committed")
    if row[1] == "target_reached":
        raise FullSimulationTargetReached("Full Simulation effective target reached")
    if row[1] == "abandoned":
        raise ValueError("Full Simulation parent has an invalid status: abandoned; execution is fenced")
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


@event.listens_for(Engine, "after_cursor_execute")
def _fence_full_simulation_after_sqlite_writer_lock(
    connection, cursor, statement, parameters, context, executemany
) -> None:
    """Recheck *after* SQLite reserves the writer lock, closing the precheck race.

    A concurrent owner can reclaim between before_cursor_execute and the
    completion of BEGIN IMMEDIATE. Once the writer lock is held, another lease
    claimant cannot commit an ownership change until this transaction exits.
    """
    guard = ACTIVE_FULL_SIMULATION_GUARD.get()
    if guard is None or statement.strip().upper() != "BEGIN IMMEDIATE":
        return
    _verify_invocation_lease(connection, guard.execution_lease_token)
    # This recheck also fences pause commands committed during BEGIN wait.
    row = connection.exec_driver_sql(
        "SELECT request_fingerprint, status, result_json "
        "FROM authoritative_simulation_commands "
        "WHERE run_id = ? AND branch_id = ? AND command_id = ?",
        (guard.run_id, guard.branch_id, guard.command_id),
    ).first()
    if row is None:
        return  # A new parent receipt may be created in this transaction.
    if row[1] == "stopped":
        raise FullSimulationStopped("Full Simulation operator stop committed")
    if row[1] == "target_reached":
        raise FullSimulationTargetReached("Full Simulation effective target reached")
    if row[0] != guard.request_fingerprint or row[1] == "abandoned":
        raise ValueError("Full Simulation parent ownership was revoked")
    if row[1] not in ("pending", "complete"):
        raise ValueError("Full Simulation parent is no longer executable")
    if row[1] == "pending":
        import json
        frozen = json.loads(row[2])
        if frozen.get("control_state", "running") in ("pause_requested", "paused"):
            raise FullSimulationPauseRequested(
                "Full Simulation pause requested after writer lock acquisition"
            )
        # Query AFTER BEGIN IMMEDIATE: target and world Position cannot move
        # between this check and the following transaction's sporting writes.
        if frozen.get("target_revision", 0) > 0:
            target = frozen.get("effective_target_week")
            if (
                not isinstance(target, dict)
                or type(target.get("season_index")) is not int
                or type(target.get("week")) is not int
                or not 0 <= target["season_index"] < 50
                or not 1 <= target["week"] <= 61
            ):
                raise ValueError("Full Simulation target revision is corrupt")
            ordinal = target["season_index"] * 61 + target["week"] - 1
            if ordinal < 50 * 61 - 1:
                current = connection.exec_driver_sql(
                    "SELECT current_ordinal FROM authoritative_world_states "
                    "WHERE run_id = ? AND branch_id = ?",
                    (guard.run_id, guard.branch_id),
                ).first()
                if current is None:
                    current = connection.exec_driver_sql(
                        "SELECT MAX(week_ordinal) FROM player_sporting_week_states "
                        "WHERE run_id = ? AND branch_id = ?",
                        (guard.run_id, guard.branch_id),
                    ).first()
                if current is None or current[0] is None:
                    raise ValueError("Cannot resolve target versus current week")
                if current[0] >= ordinal:
                    raise FullSimulationTargetReached("Effective weekly boundary reached")
