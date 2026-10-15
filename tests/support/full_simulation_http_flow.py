"""Disposable real HTTP/SQLite flow inputs and transaction-boundary coordination.

The existing deterministic four-player source supplies inputs, never match
results. Only real production services execute children. The gate delays one
writer BEFORE BEGIN IMMEDIATE, letting a second HTTP request exercise controls.
This adapter is not installed in the production app.
"""
from __future__ import annotations

import json
from threading import Event

from sqlalchemy import func, select, text

from beta_engine.api.routers import admin_authoritative_simulation as routes
from beta_engine.application.authoritative_run_simulation_driver import AuthoritativeRunSimulationDriver
from beta_engine.infrastructure.db.full_simulation_execution_guard import ACTIVE_FULL_SIMULATION_GUARD
from beta_engine.infrastructure.db.engine import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.full_simulation_invocation_lease import acquire_invocation_lease
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel, BranchSavedRevisionModel,
    FullSimulationExecutionLeaseModel, RunBranchModel, SimulationEventGroupModel,
    SimulationSlotModel,
    OwnedTournamentRankingSourceModel,
)


class TransactionGate:
    def __init__(self, factory):
        self.factory = factory
        self.reached = Event()
        self.release = Event()
        self.armed = False

    def arm(self, *, after_groups=0, after_sources=None):
        self.reached.clear()
        self.release.clear()
        self.armed = True
        self.minimum_groups = after_groups + 1
        self.minimum_sources = 0 if after_sources is None else after_sources + 1

    def before_writer(self):
        guard = ACTIVE_FULL_SIMULATION_GUARD.get()
        if not self.armed or guard is None:
            return
        with self.factory() as session:
            committed = session.scalar(select(func.count()).select_from(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == guard.run_id,
                SimulationEventGroupModel.branch_id == guard.branch_id,
            ))
            sources = session.scalar(select(func.count()).select_from(OwnedTournamentRankingSourceModel).where(
                OwnedTournamentRankingSourceModel.run_id == guard.run_id,
                OwnedTournamentRankingSourceModel.branch_id == guard.branch_id,
            )) if self.minimum_sources else 0
        if committed >= self.minimum_groups and sources >= self.minimum_sources:
            self.armed = False
            self.reached.set()
            if not self.release.wait(timeout=60):
                raise RuntimeError("Test transaction gate was not released")

    def driver(self, runtime, matches, awards):
        return AuthoritativeRunSimulationDriver(
            runtime.repository._session_factory, matches, awards,
            full_simulation_before_transaction_check=self.before_writer,
        )


def snapshot(factory, run_id, branch_id):
    """Read exact persisted JSON and fingerprints, including original owners."""
    with factory() as session:
        groups = session.scalars(select(SimulationEventGroupModel).where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        ).order_by(SimulationEventGroupModel.group_id)).all()
        slots = session.scalars(select(SimulationSlotModel).where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
        ).order_by(SimulationSlotModel.slot_ordinal)).all()
        parents = session.scalars(select(AuthoritativeSimulationCommandModel).where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        ).order_by(AuthoritativeSimulationCommandModel.command_id)).all()
        saved = session.scalars(select(BranchSavedRevisionModel).where(
            BranchSavedRevisionModel.run_id == run_id,
        ).order_by(BranchSavedRevisionModel.revision_id)).all()
        branch = session.get(RunBranchModel, branch_id)
        return {
            "groups": {g.group_id: {"payload": json.loads(g.payload_json),
                "result_fingerprint": g.result_fingerprint,
                "match_input_fingerprint": g.match_input_fingerprint,
                "command_fingerprint": g.command_fingerprint} for g in groups},
            "slots": {s.slot_id: {"start": s.slot_start_checkpoint_json,
                "fingerprint": s.slot_start_fingerprint} for s in slots},
            "commands": {p.command_id: {"fingerprint": p.request_fingerprint,
                "status": p.status, "result": json.loads(p.result_json)} for p in parents},
            "saved_head": branch.saved_head_revision_id,
            "saved": {r.revision_id: {"payload": r.payload_json,
                "hash": r.content_hash} for r in saved},
        }


def initialize(server, root, *, additional_packages=()):
    # Reuse established input fixtures; all outputs below use normal HTTP.
    from test_authoritative_simulation_api import _install_owned_state, initial
    from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
    from beta_engine.infrastructure.db.initial_world_state import get_initial_world
    from beta_engine.infrastructure.db.player_health_state import put_health
    from beta_engine.domain.players.health import bootstrap_health_state
    from tests.api.test_saved_revision_history_api import _create_run, _request

    run_id, branch_id, revision = _create_run(server, display_name="Full Simulation HTTP acceptance")
    week = _install_owned_state(server, server.flow_package, run_id, branch_id, additional_packages=additional_packages)
    with server.app.state.runtime.repository._session_factory.begin() as session:
        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        put_health(session, bootstrap_health_state(run_id=run_id, branch_id=branch_id,
            source_initial_world_fingerprint=world.fingerprint,
            player_ids=tuple(p.player_id for p in world.players)))
    ranking = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
    with server.app.state.runtime.repository._session_factory() as session:
        roster = [p.model_dump(mode="json") for p in get_lifecycle(
            session, run_id=run_id, branch_id=branch_id, week=week).ranking_roster()]
    status, prepared = _request("POST", ranking + "/prepare/initial", initial() | {
        "run_id": run_id, "branch_id": branch_id, "players": roster})
    assert status == 201, prepared
    preview = _request("GET", ranking + "/save/preview")[1]
    status, saved = _request("POST", ranking + "/save", {
        "expected_draft_version": preview["draft_version"],
        "expected_ranking_fingerprint": preview["ranking_fingerprint"]})
    assert status == 201, saved
    revision = saved["saved_revision"]["revision_id"]
    scope = f"/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
    status, proposed = _request("GET", server.base_url + scope + "/week-schedule/proposal")
    assert status == 200, proposed
    status, adopted = _request("POST", server.base_url + scope + "/week-schedule/adopt-proposal", {
        "request_id": "flow-schedule", "expected_week": proposed["schedule"]["week"],
        "expected_schedule_fingerprint": proposed["schedule_fingerprint"],
        "expected_position_fingerprint": proposed["position_fingerprint"],
    })
    assert status == 201, adopted
    other_run, other_branch, _ = _create_run(server, display_name="Competing HTTP Run")
    return {"run_id": run_id, "branch_id": branch_id, "revision": revision,
        "scope": scope, "other_scope": f"/admin/runs/{other_run}/branches/{other_branch}/authoritative-simulation",
        "other_run": other_run, "other_branch": other_branch}


def make_server(root):
    from test_authoritative_simulation_api import _server_state
    server, package = _server_state(root)
    server.flow_package = package
    factory = create_session_factory(create_sqlite_engine(DatabaseSettings(
        url=f"sqlite:///{root / 'api.sqlite'}")))
    gate = TransactionGate(factory)
    return server, factory, gate


def expire(factory):
    with factory.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        lease = session.get(FullSimulationExecutionLeaseModel, "all_runs")
        assert lease is not None
        lease.expires_at_unix = 0


def reclaim(factory, flow):
    expire(factory)
    return acquire_invocation_lease(factory, run_id=flow["other_run"],
        branch_id=flow["other_branch"], command_id="takeover")
