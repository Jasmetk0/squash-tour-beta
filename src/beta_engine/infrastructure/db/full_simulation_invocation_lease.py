"""Cross-process *invocation* arbitration for authoritative Full Simulation.

A pending parent receipt remains durable across HTTP requests, but a live
executor is owned only while one synchronous invocation holds this lease.
SQLite BEGIN IMMEDIATE makes acquire/reclaim/release atomic across workers.
A renewable expiry recovers after crashes. Guarded writes verify the token,
so an expired, reclaimed executor cannot continue committing sporting work.
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
from threading import Event, Lock, Thread
import time
from typing import Iterator
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.infrastructure.db.models import FullSimulationExecutionLeaseModel

LEASE_SCOPE = "all_runs"
LEASE_SECONDS = 180
RENEW_INTERVAL_SECONDS = 10
# A native Full Simulation step may read and prepare one child from a single
# SQLite snapshot and then reuse it only if no other connection committed in
# the meantime. A renewal commit would always invalidate that snapshot, so the
# step may hold renewal back for at most this long. The guarded child writer
# still verifies the lease time at BEGIN IMMEDIATE and at COMMIT: a longer
# step falls back to its complete path, and an expired lease is still fenced.
HEARTBEAT_DEFERRAL_SECONDS = 90
_heartbeat_gate = Lock()
_LOG = logging.getLogger(__name__)


class DeferredLeaseHeartbeat:
    """Process-local, bounded hold on lease heartbeat commits.

    ``acquire`` waits at most ``wait_seconds`` for an in-flight heartbeat and
    reports whether the hold was obtained; ``release`` is idempotent. The
    heartbeat thread itself waits at most ``HEARTBEAT_DEFERRAL_SECONDS`` and
    then renews anyway, so this never grants or extends lease ownership.
    """

    def __init__(self):
        self.held = False

    def acquire(self, wait_seconds=35.0):
        self.held = _heartbeat_gate.acquire(timeout=wait_seconds)
        return self.held

    def release(self):
        if self.held:
            self.held = False
            _heartbeat_gate.release()


def _start_writer(session: Session) -> None:
    session.execute(text("BEGIN IMMEDIATE"))


def acquire_invocation_lease(
    factory: sessionmaker[Session], *,
    run_id: str, branch_id: str, command_id: str,
) -> str:
    """Fail closed if any Full Simulation invocation currently owns the DB."""
    with factory.begin() as session:
        _start_writer(session)
        return acquire_in_session(session, run_id=run_id, branch_id=branch_id, command_id=command_id)


def acquire_in_session(session, *, run_id, branch_id, command_id):
    """Reserve the same global fence in the caller's SQLite writer transaction."""
    token = uuid4().hex
    now = int(time.time())
    lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
    if lease is not None and lease.expires_at_unix > now:
        raise ValueError(
            "Another Full Simulation invocation holds the global execution "
            f"lease for Run {lease.run_id}, Branch {lease.branch_id}; "
            "retry after it finishes. A pending parent receipt alone "
            "does not imply that its executor is active."
        )
    if lease is None:
        session.add(FullSimulationExecutionLeaseModel(
            lease_scope=LEASE_SCOPE,
            owner_token=token, run_id=run_id, branch_id=branch_id,
            command_id=command_id,
            expires_at_unix=now + LEASE_SECONDS,
        ))
    else:
        # Crash recovery: a now-expired holder is fenced by its old token.
        lease.owner_token = token
        lease.run_id = run_id
        lease.branch_id = branch_id
        lease.command_id = command_id
        lease.expires_at_unix = now + LEASE_SECONDS
    session.flush()
    return token


def renew_invocation_lease(
    factory: sessionmaker[Session], *,
    token: str,
) -> bool:
    """Only the current owner can extend the lease; never resurrect a lost one."""
    with factory.begin() as session:
        _start_writer(session)
        lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
        if lease is None or lease.owner_token != token:
            return False
        now = int(time.time())
        if lease.expires_at_unix <= now:
            return False  # An expired invocation must explicitly acquire a new lease.
        lease.expires_at_unix = now + LEASE_SECONDS
        session.flush()
    return True


def release_invocation_lease(
    factory: sessionmaker[Session], *,
    token: str,
) -> None:
    """A stale executor must never delete the lease of a newer one."""
    with factory.begin() as session:
        _start_writer(session)
        lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
        if lease is not None and lease.owner_token == token:
            session.delete(lease)
            session.flush()


@contextmanager
def full_simulation_invocation_lease(
    factory: sessionmaker[Session], *,
    run_id: str, branch_id: str, command_id: str,
    existing_token: str | None = None, on_heartbeat=None,
) -> Iterator[str]:
    """Own the global writer lease only during this explicit HTTP invocation."""
    token = existing_token or acquire_invocation_lease(
        factory, run_id=run_id, branch_id=branch_id, command_id=command_id,
    )
    stop = Event()

    def heartbeat() -> None:
        while not stop.wait(RENEW_INTERVAL_SECONDS):
            # Bounded: a held gate only postpones this commit, never skips it.
            gated = _heartbeat_gate.acquire(timeout=HEARTBEAT_DEFERRAL_SECONDS)
            try:
                if stop.is_set():
                    return
                if not renew_invocation_lease(factory, token=token):
                    _LOG.warning("Full Simulation invocation lease was reclaimed")
                    return
                if on_heartbeat is not None:
                    on_heartbeat()
            except Exception:
                # A temporary SQLite writer lock may block renewal; the
                # next child commit still checks owner token transactionally.
                _LOG.exception("Full Simulation invocation heartbeat failed")
            finally:
                if gated:
                    _heartbeat_gate.release()

    worker = Thread(target=heartbeat, name="full-simulation-lease-renewal", daemon=True)
    worker.start()
    try:
        yield token
    finally:
        stop.set()
        worker.join(timeout=1)
        release_invocation_lease(factory, token=token)


def require_invocation_lease_owner(
    session: Session, *, token: str,
) -> None:
    """Fence a stale execution inside the sporting child writer transaction."""
    lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
    if (lease is None or lease.owner_token != token
            or lease.expires_at_unix <= int(time.time())):
        raise ValueError(
            "Full Simulation execution lease ownership was lost; "
            "stale child work is fenced"
        )
