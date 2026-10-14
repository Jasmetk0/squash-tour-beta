"""Cross-process global Full Simulation execution lease and stale-writer fencing."""

import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, text

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.full_simulation_execution_guard import (
    ACTIVE_FULL_SIMULATION_GUARD, FullSimulationExecutionGuard,
)
from beta_engine.infrastructure.db.full_simulation_invocation_lease import (
    LEASE_SCOPE, acquire_invocation_lease, full_simulation_invocation_lease,
    release_invocation_lease, renew_invocation_lease,
)
from beta_engine.infrastructure.db.models import (
    Base, FullSimulationExecutionLeaseModel,
)


@pytest.fixture
def independent_factories(tmp_path):
    url = f"sqlite:///{tmp_path / 'shared-lease.db'}"
    engine_a = create_sqlite_engine(DatabaseSettings(url=url))
    engine_b = create_sqlite_engine(DatabaseSettings(url=url))
    Base.metadata.create_all(engine_a)
    try:
        yield create_session_factory(engine_a), create_session_factory(engine_b)
    finally:
        engine_a.dispose()
        engine_b.dispose()


@pytest.mark.pr_critical
def test_only_one_live_invocation_across_independent_sqlite_connections(independent_factories):
    """Another Run, Branch, command, worker or retry cannot execute concurrently."""
    first, second = independent_factories
    with full_simulation_invocation_lease(
        first, run_id="run-a", branch_id="branch-one", command_id="parent-a",
    ) as first_token:
        assert first_token
        with ThreadPoolExecutor(max_workers=1) as pool:
            competing = pool.submit(
                acquire_invocation_lease, second,
                run_id="run-b", branch_id="branch-other", command_id="parent-b",
            )
            with pytest.raises(ValueError, match="Another Full Simulation invocation"):
                competing.result(timeout=20)
        with second() as session:
            lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
            assert (lease.run_id, lease.branch_id, lease.command_id) == (
                "run-a", "branch-one", "parent-a",
            )
            assert lease.owner_token == first_token
    with second() as session:
        assert session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE) is None
    next_token = acquire_invocation_lease(
        second, run_id="run-b", branch_id="branch-other", command_id="parent-b",
    )
    release_invocation_lease(second, token=next_token)


@pytest.mark.pr_critical
def test_crashed_expired_holder_is_reclaimed_and_stale_owner_cannot_write(independent_factories):
    first, second = independent_factories
    old_token = acquire_invocation_lease(
        first, run_id="run-a", branch_id="branch-one", command_id="old-parent",
    )
    with second.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
        lease.expires_at_unix = 0

    new_token = acquire_invocation_lease(
        second, run_id="run-b", branch_id="branch-two", command_id="new-parent",
    )
    assert new_token != old_token
    assert renew_invocation_lease(first, token=old_token) is False

    # Check writer-token fence *after* BEGIN IMMEDIATE acquired its lock,
    # including future direct-SQL child transactions without an ORM flush.
    guard_token = ACTIVE_FULL_SIMULATION_GUARD.set(FullSimulationExecutionGuard(
        run_id="run-a", branch_id="branch-one", command_id="old-parent",
        request_fingerprint="a" * 64, execution_lease_token=old_token,
    ))
    try:
        with pytest.raises(ValueError, match="lease ownership was lost"):
            with first.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
    finally:
        ACTIVE_FULL_SIMULATION_GUARD.reset(guard_token)

    release_invocation_lease(first, token=old_token)
    with second() as session:
        lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
        assert (lease.owner_token, lease.run_id) == (new_token, "run-b")
    release_invocation_lease(second, token=new_token)


@pytest.mark.pr_critical
def test_renewal_extends_only_current_lease_and_release_is_idempotent(independent_factories):
    first, second = independent_factories
    token = acquire_invocation_lease(
        first, run_id="run", branch_id="branch", command_id="parent",
    )
    with second.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
        lease.expires_at_unix = int(time.time()) + 30
    assert renew_invocation_lease(first, token=token) is True
    with second() as session:
        assert session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE).expires_at_unix > 0
    release_invocation_lease(first, token=token)
    release_invocation_lease(first, token=token)
    assert renew_invocation_lease(second, token=token) is False


@pytest.mark.pr_critical
def test_expired_lease_before_direct_sql_commit_rolls_back_all_writes(independent_factories):
    """BEGIN IMMEDIATE alone is not enough if expiry happens before COMMIT.

    Deliberately expire the lease *inside* an open writer transaction after its
    direct SQL change. The commit hook must reject and roll back both writes;
    no ORM flush is involved. This is a deterministic stand-in for wall-clock
    expiration during a long child transaction.
    """
    first, second = independent_factories
    with first.begin() as session:
        session.execute(text(
            "CREATE TABLE direct_sql_commit_probe (id INTEGER PRIMARY KEY)"
        ))
    token = acquire_invocation_lease(
        first, run_id="run-a", branch_id="branch-one", command_id="parent-a",
    )
    guard_context = ACTIVE_FULL_SIMULATION_GUARD.set(FullSimulationExecutionGuard(
        run_id="run-a", branch_id="branch-one", command_id="parent-a",
        request_fingerprint="a" * 64, execution_lease_token=token,
    ))
    try:
        with pytest.raises(ValueError, match="lease ownership was lost"):
            with first.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                session.execute(text("INSERT INTO direct_sql_commit_probe (id) VALUES (1)"))
                session.execute(text(
                    "UPDATE full_simulation_execution_leases SET expires_at_unix = 0 "
                    "WHERE lease_scope = :scope"
                ), {"scope": LEASE_SCOPE})
                # Deliberately no ORM flush / lease check before context commit.
    finally:
        ACTIVE_FULL_SIMULATION_GUARD.reset(guard_context)
    with second() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM direct_sql_commit_probe")) == 0
        lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
        assert lease is not None and lease.owner_token == token
        assert lease.expires_at_unix > int(time.time())
    release_invocation_lease(first, token=token)


@pytest.mark.pr_critical
def test_driver_does_not_hold_global_lease_after_exception(independent_factories, monkeypatch):
    first, second = independent_factories
    def failed_child(*args, **kwargs):
        raise ValueError("deliberate bounded invocation failure")
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_simulate_full_simulation_guarded",
        failed_child,
    )
    driver = AuthoritativeRunSimulationDriver(first, None, None)
    class ReviewedRequest:
        run_id = "run-a"
        branch_id = "branch-a"
        command_id = "parent-a"
        operator_label = "admin"
        audit_reason = "test"
        def model_dump(self, *, mode):
            return {"run_id": self.run_id, "branch_id": self.branch_id,
                    "command_id": self.command_id}
    with pytest.raises(ValueError, match="deliberate bounded invocation failure"):
        driver.simulate_full_simulation(ReviewedRequest())
    with second() as session:
        assert session.scalar(select(FullSimulationExecutionLeaseModel)) is None
    token = acquire_invocation_lease(
        second, run_id="run-b", branch_id="branch-b", command_id="parent-b",
    )
    release_invocation_lease(second, token=token)
