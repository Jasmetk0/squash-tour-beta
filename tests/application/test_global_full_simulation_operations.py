"""Global Full Simulation inventory must remain read-only and scope-authentic."""

import json

from beta_engine.application import global_full_simulation_operations as inventory_module

import pytest

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeFullSimulationCommand,
)
from beta_engine.application.global_full_simulation_operations import (
    inspect_global_full_simulation_operations,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel, Base, FullSimulationExecutionLeaseModel,
    RunBranchModel, RunContainerModel,
)


@pytest.fixture
def factory(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(
        url=f"sqlite:///{tmp_path / 'global-operations.db'}"
    ))
    Base.metadata.create_all(engine)
    result = create_session_factory(engine)
    yield result
    engine.dispose()


def _parent(run_id, branch_id, command_id, control_state):
    start = RankingWeek(season_index=1, week=5)
    final = RankingWeek(season_index=49, week=61)
    command = AuthoritativeFullSimulationCommand(
        command_id=command_id,
        run_id=run_id,
        branch_id=branch_id,
        operator_label="Admin",
        audit_reason="Audit",
        expected_start_week=start,
        expected_position_fingerprint="a" * 64,
        expected_revision_id="original-revision",
        expected_preview_fingerprint="b" * 64,
    )
    payload = {
        "schema_version": "authoritative_full_simulation_operation.v1",
        "resume_command": command.model_dump(mode="json"),
        "review": {
            "schema_version": "authoritative_full_simulation_preview.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "start_week": start.model_dump(mode="json"),
            "final_week": final.model_dump(mode="json"),
            "preview_fingerprint": "b" * 64,
            "expected_position_fingerprint": "a" * 64,
            "expected_revision_id": "original-revision",
        },
        "control_state": control_state,
        "completed_seasons": [1, 2],
        "final_completed_weeks": [],
    }
    return AuthoritativeSimulationCommandModel(
        run_id=run_id, branch_id=branch_id, command_id=command_id,
        request_fingerprint=fingerprint({
            "mode": "full_simulation", "command": command.model_dump(mode="json"),
        }),
        status="pending",
        result_json=json.dumps(payload),
    )


@pytest.mark.pr_critical
def test_global_pending_is_across_runs_with_no_execution_or_synthetic_worker(factory):
    with factory.begin() as session:
        for run_id, branch_id, read_only in [
            ("run-b", "branch-b", False), ("run-a", "branch-a", True),
        ]:
            session.add(RunContainerModel(
                run_id=run_id, display_name=f"Name {run_id}",
                storage_kind="custom_local", read_only=int(read_only),
                timeline_start_season=2000, timeline_end_season=2049,
                official_branch_id=branch_id, status="working",
            ))
            session.add(RunBranchModel(
                branch_id=branch_id, run_id=run_id,
                display_name=f"Timeline {branch_id}", status="active", read_only=0,
            ))
        session.add(_parent("run-b", "branch-b", "parent-b", "pause_requested"))
        session.add(_parent("run-a", "branch-a", "parent-a", "paused"))
        session.add(AuthoritativeSimulationCommandModel(
            run_id="run-a", branch_id="branch-a", command_id="other-action",
            request_fingerprint="c" * 64, status="pending",
            result_json=json.dumps({"schema_version": "other_pending_kind"}),
        ))
    before = {}
    with factory() as session:
        for row in session.query(AuthoritativeSimulationCommandModel):
            before[row.command_id] = row.result_json
    snapshot = inspect_global_full_simulation_operations(factory)
    assert snapshot["visibility"] == "durable_receipts_only"
    assert snapshot["pending_count"] == 2
    assert snapshot["legacy_pending_count"] == 0
    a, b = snapshot["operations"]
    assert (a["run_id"], a["branch_id"], a["command_id"]) == (
        "run-a", "branch-a", "parent-a",
    )
    assert a["run_read_only"] is True
    assert a["control_state"] == "paused"
    assert a["completed_season_count"] == 2
    assert a["worker_activity"] == "unknown"
    assert b["control_state"] == "pause_requested"
    assert b["final_week"] == {"season_index": 49, "week": 61}
    with factory() as session:
        assert {row.command_id: row.result_json
                for row in session.query(AuthoritativeSimulationCommandModel)} == before


@pytest.mark.pr_critical
def test_global_inventory_fails_closed_on_wrong_parent_scope(factory):
    with factory.begin() as session:
        session.add(RunContainerModel(
            run_id="run-a", display_name="First",
            storage_kind="custom_local", read_only=0,
            timeline_start_season=2000, timeline_end_season=2049,
            official_branch_id="branch-a", status="working",
        ))
        session.add(RunBranchModel(
            run_id="run-a", branch_id="branch-a",
            display_name="Timeline 1", status="active", read_only=0,
        ))
        bad = _parent("run-a", "branch-a", "bad-scope", "running")
        payload = json.loads(bad.result_json)
        payload["resume_command"]["run_id"] = "run-b"
        bad.result_json = json.dumps(payload)
        session.add(bad)
    with pytest.raises(ValueError, match="identity is corrupt"):
        inspect_global_full_simulation_operations(factory)


@pytest.mark.pr_critical
def test_global_inventory_counts_legacy_without_claiming_recoverability(factory):
    with factory.begin() as session:
        session.add(RunContainerModel(
            run_id="run", display_name="Run", storage_kind="custom_local",
            read_only=0, timeline_start_season=2000, timeline_end_season=2049,
            official_branch_id="branch", status="working",
        ))
        session.add(RunBranchModel(
            run_id="run", branch_id="branch",
            display_name="Timeline 1", status="active", read_only=0,
        ))
        session.add(AuthoritativeSimulationCommandModel(
            run_id="run", branch_id="branch", command_id="old-parent",
            request_fingerprint="0" * 64, status="pending",
            result_json=json.dumps({
                "schema_version": "authoritative_full_simulation_operation.v1",
                "completed_seasons": [1],
            }),
        ))
    result = inspect_global_full_simulation_operations(factory)
    assert result["pending_count"] == 0
    assert result["legacy_pending_count"] == 1
    assert result["operations"] == []


def _scope(factory, *, run_id="run", branch_id="branch", command_id="parent"):
    with factory.begin() as session:
        session.add(RunContainerModel(
            run_id=run_id, display_name="Test Run",
            storage_kind="custom_local", read_only=0,
            timeline_start_season=2000, timeline_end_season=2049,
            official_branch_id=branch_id, status="working",
        ))
        session.add(RunBranchModel(
            run_id=run_id, branch_id=branch_id,
            display_name="Timeline 1", status="active", read_only=0,
        ))
        session.add(_parent(run_id, branch_id, command_id, "running"))


@pytest.mark.pr_critical
@pytest.mark.parametrize("mutate", [
    lambda p: p["review"].update(final_week={"season_index": 99, "week": 999}),
    lambda p: p["review"].update(final_week={"season_index": 48, "week": 61}),
    lambda p: p["review"].update(start_week={"season_index": 1, "week": 62}),
    lambda p: p.update(run_id="foreign-run"),
    lambda p: p.update(final_week={"season_index": 2, "week": 61}),
    lambda p: p.update(completed_seasons=[1, 1]),
    lambda p: p.update(completed_seasons=[1, 3]),
    lambda p: p.update(completed_seasons=[True]),
    lambda p: p.update(completed_seasons=list(range(1, 50))),
    lambda p: p.update(completed_season_count=999),
    lambda p: p.update(final_completed_weeks=[{"season_index": 99, "week": 1}]),
    lambda p: p.update(final_completed_weeks=[
        {"season_index": 49, "week": 1},
        {"season_index": 49, "week": 1},
    ]),
    lambda p: p.update(final_completed_weeks=[{"season_index": 49, "week": 62}]),
])
def test_global_inventory_rejects_malformed_progress_without_writing(factory, mutate):
    _scope(factory)
    with factory.begin() as session:
        row = session.get(AuthoritativeSimulationCommandModel, ("run", "branch", "parent"))
        payload = json.loads(row.result_json)
        mutate(payload)
        row.result_json = json.dumps(payload)
    with factory() as session:
        original = session.get(
            AuthoritativeSimulationCommandModel, ("run", "branch", "parent")
        ).result_json
    with pytest.raises(ValueError):
        inspect_global_full_simulation_operations(factory)
    with factory() as session:
        assert session.get(
            AuthoritativeSimulationCommandModel, ("run", "branch", "parent")
        ).result_json == original


@pytest.mark.pr_critical
def test_global_inventory_validates_chronological_final_week_progress(factory):
    _scope(factory)
    with factory.begin() as session:
        row = session.get(AuthoritativeSimulationCommandModel, ("run", "branch", "parent"))
        payload = json.loads(row.result_json)
        payload["completed_seasons"] = list(range(1, 49))
        payload["final_completed_weeks"] = [
            {"season_index": 49, "week": week} for week in range(1, 4)
        ]
        row.result_json = json.dumps(payload)
    snapshot = inspect_global_full_simulation_operations(factory)
    assert snapshot["operations"][0]["completed_season_count"] == 48
    assert snapshot["operations"][0]["final_completed_week_count"] == 3
    with factory.begin() as session:
        row = session.get(AuthoritativeSimulationCommandModel, ("run", "branch", "parent"))
        payload = json.loads(row.result_json)
        payload["final_completed_weeks"][1]["week"] = 3
        row.result_json = json.dumps(payload)
    with pytest.raises(ValueError, match="final weeks"):
        inspect_global_full_simulation_operations(factory)


@pytest.mark.pr_critical
def test_global_inventory_lease_is_read_only_and_not_worker_health(factory, monkeypatch):
    _scope(factory)
    monkeypatch.setattr(inventory_module.time, "time", lambda: 1000)
    snapshot = inspect_global_full_simulation_operations(factory)
    assert snapshot["operations"][0]["lease_state"] == "absent"
    with factory.begin() as session:
        session.add(FullSimulationExecutionLeaseModel(
            lease_scope="all_runs", owner_token="INTERNAL-SECRET",
            run_id="run", branch_id="branch", command_id="parent",
            expires_at_unix=1100,
        ))
    with factory() as session:
        prior = session.get(AuthoritativeSimulationCommandModel, ("run", "branch", "parent")).result_json
    active = inspect_global_full_simulation_operations(factory)["operations"][0]
    assert active["lease_state"] == "matching_active"
    assert active["lease_expires_at_unix"] == 1100
    assert active["worker_activity"] == "unknown"
    assert "INTERNAL-SECRET" not in json.dumps(active)
    monkeypatch.setattr(inventory_module.time, "time", lambda: 1200)
    expired = inspect_global_full_simulation_operations(factory)["operations"][0]
    assert expired["lease_state"] == "matching_expired"
    with factory.begin() as session:
        lease = session.get(FullSimulationExecutionLeaseModel, "all_runs")
        lease.run_id = "other-run"
        lease.command_id = "other-parent"
        lease.expires_at_unix = 1300
    other = inspect_global_full_simulation_operations(factory)["operations"][0]
    assert other["lease_state"] == "other_active"
    with factory() as session:
        lease = session.get(FullSimulationExecutionLeaseModel, "all_runs")
        assert lease.owner_token == "INTERNAL-SECRET"
        assert lease.expires_at_unix == 1300
        assert session.get(
            AuthoritativeSimulationCommandModel, ("run", "branch", "parent")
        ).result_json == prior


@pytest.mark.pr_critical
def test_global_inventory_rejects_two_pending_parents_in_same_branch(factory):
    _scope(factory)
    with factory.begin() as session:
        session.add(_parent("run", "branch", "second-parent", "paused"))
    with pytest.raises(ValueError, match="Duplicate pending Full Simulation"):
        inspect_global_full_simulation_operations(factory)
