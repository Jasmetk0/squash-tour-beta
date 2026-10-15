"""Explicit Next Week extension: strict contracts, no hidden execution."""

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    AuthoritativeSimulationCommand,
    AuthoritativeWeekExtensionApproval,
    fingerprint,
)
from beta_engine.infrastructure.db.models import Base, AuthoritativeSimulationCommandModel
from beta_engine.domain.rankings.official import RankingWeek


def payload():
    return {
        "control_command_id": "approve-1",
        "task_id": "task-1",
        "target_week_command_id": "week-1",
        "run_id": "run",
        "branch_id": "branch",
        "expected_task_revision": 2,
        "expected_receipt_fingerprint": "a" * 64,
        "expected_current_schedule_fingerprint": "b" * 64,
        "operator_label": "Reviewer",
        "audit_reason": "Approve this exact verified hybrid suffix",
        "confirm_committed_work_is_immutable": True,
    }


@pytest.mark.pr_critical
def test_explicit_approval_requires_real_confirmation_and_strict_cas():
    command = AuthoritativeWeekExtensionApproval.model_validate(payload())
    assert command.confirm_committed_work_is_immutable is True
    for changes in (
        {"confirm_committed_work_is_immutable": False},
        {"confirm_committed_work_is_immutable": None},
        {"expected_task_revision": 0},
        {"expected_task_revision": "2"},
        {"expected_receipt_fingerprint": "deadbeef"},
        {"operator_label": " Reviewer"},
        {"audit_reason": " "},
        {"target_week_command_id": "approve-1"},
        {"random_extra_field": "not allowed"},
    ):
        with pytest.raises(ValidationError):
            AuthoritativeWeekExtensionApproval.model_validate(payload() | changes)


@pytest.mark.pr_critical
def test_original_week_children_must_be_complete_and_replay_authorized():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    child = AuthoritativeSimulationCommand(
        command_id=AuthoritativeRunSimulationDriver._week_slot_child_command_id(
            "week-1", 1
        ),
        run_id="run",
        branch_id="branch",
        expected_week=RankingWeek(season_index=0, week=1),
        expected_position_fingerprint="a" * 64,
        expected_revision_id="saved-head",
    )
    frozen = {
        "target_slot_ordinals": [1],
        "child_commands": {"1": child.model_dump(mode="json")},
    }
    with Session(engine) as session:
        assert not AuthoritativeRunSimulationDriver._completed_frozen_week_children(
            session, run_id="run", branch_id="branch", command_id="week-1", frozen=frozen
        )
        session.add(AuthoritativeSimulationCommandModel(
            run_id="run", branch_id="branch", command_id=child.command_id,
            request_fingerprint=fingerprint({
                "mode": "slot", "command": child.model_dump(mode="json")
            }),
            status="pending", result_json="{}",
        ))
        session.flush()
        assert not AuthoritativeRunSimulationDriver._completed_frozen_week_children(
            session, run_id="run", branch_id="branch", command_id="week-1", frozen=frozen
        )
        session.get(
            AuthoritativeSimulationCommandModel, ("run", "branch", child.command_id)
        ).status = "complete"
        session.flush()
        assert AuthoritativeRunSimulationDriver._completed_frozen_week_children(
            session, run_id="run", branch_id="branch", command_id="week-1", frozen=frozen
        )
        forged = frozen | {"child_commands": {"1": child.model_dump(mode="json") | {
            "command_id": "wrong-child"
        }}}
        with pytest.raises(ValueError, match="not canonical"):
            AuthoritativeRunSimulationDriver._completed_frozen_week_children(
                session, run_id="run", branch_id="branch",
                command_id="week-1", frozen=forged
            )


@pytest.mark.pr_critical
def test_http_never_commits_invalid_approvals_to_real_sqlite(tmp_path):
    """Production FastAPI rejects invalid operator / foreign child without writes."""
    from tests.support.full_simulation_http_flow import make_server, initialize, snapshot
    from tests.api.test_saved_revision_history_api import _request
    server, factory, _ = make_server(tmp_path)
    with server:
        flow = initialize(server, tmp_path)
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        path = server.base_url + flow["scope"] + "/next-week/extension-approve"
        body = payload()
        status, _ = _request(
            "POST", path, {k: v for k, v in body.items()
                           if k != "confirm_committed_work_is_immutable"}
        )
        assert status == 422
        body = body | {"run_id": flow["run_id"], "branch_id": flow["branch_id"]}
        status, message = _request("POST", path, body)
        assert status == 409, message
        assert snapshot(factory, flow["run_id"], flow["branch_id"]) == before


@pytest.mark.pr_critical
def test_http_explicit_approval_atomic_audit_exact_replay_and_no_sport(tmp_path, monkeypatch):
    """Actual TCP/SQLite and task/child audit, with synthetic future hybrid topology.

    Deliberately not a genuine tournament knockout execution acceptance test.
    Existing Group 1 child is seeded as already complete to isolate approval,
    while original task/season/week receipts use their real request fingerprints.
    """
    import json
    from types import SimpleNamespace
    from sqlalchemy import text
    from beta_engine.api.routers import admin_authoritative_simulation as routes
    from beta_engine.application.authoritative_run_simulation_driver import (
        AuthoritativeFullSimulationCommand, AuthoritativeSeasonCommand,
        AuthoritativeWeekCommand,
    )
    from beta_engine.application.full_simulation_tasks import (
        _event as task_event, _record as task_record, _write as task_write,
    )
    from beta_engine.domain.simulation_slots import (
        WeekSimulationSchedule, WeekSimulationScheduleSlot,
    )
    from beta_engine.infrastructure.db.models import FullSimulationTaskModel, RunBranchModel
    from tests.application.test_full_simulation_http_flow import reviewed_command
    from tests.api.test_saved_revision_history_api import _request
    from tests.support.full_simulation_http_flow import make_server, initialize, snapshot

    server, factory, _gate = make_server(tmp_path)
    original_factory = routes._driver
    driver_ref = {}

    def capture_driver(runtime, matches, awards):
        driver_ref.setdefault("driver", original_factory(runtime, matches, awards))
        return driver_ref["driver"]

    monkeypatch.setattr(routes, "_driver", capture_driver)
    with server:
        flow = initialize(server, tmp_path)
        cmd = AuthoritativeFullSimulationCommand.model_validate({
            **reviewed_command(server, flow, command_id="full-parent"),
            "run_id": flow["run_id"], "branch_id": flow["branch_id"],
        })
        driver = driver_ref["driver"]
        before = snapshot(factory, flow["run_id"], flow["branch_id"])
        week = cmd.expected_start_week
        season_command = AuthoritativeSeasonCommand(
            command_id="owned-season", run_id=cmd.run_id, branch_id=cmd.branch_id,
            operator_label="Seed operator", audit_reason="Seed season lineage",
            expected_start_week=week,
            expected_position_fingerprint=cmd.expected_position_fingerprint,
            expected_revision_id=cmd.expected_revision_id,
            expected_preview_fingerprint="c"*64,
        )
        week_command = AuthoritativeWeekCommand(
            command_id="owned-week", run_id=cmd.run_id, branch_id=cmd.branch_id,
            operator_label="Seed operator", audit_reason="Seed week lineage",
            expected_week=week,
            expected_position_fingerprint=cmd.expected_position_fingerprint,
            expected_revision_id=cmd.expected_revision_id,
            expected_preview_fingerprint="d"*64,
        )
        group_slot = WeekSimulationScheduleSlot(
            ordinal=1, group_ids=("seed-group",), match_day_ordinal=1,
            match_order=1, event_id="hybrid", draw_phase="group",
            round_number=1,
        )
        final_slot = WeekSimulationScheduleSlot(
            ordinal=2, group_ids=("seed-final",), match_day_ordinal=2,
            match_order=1, event_id="hybrid", draw_phase="main",
            round_number=1,
        )
        base = WeekSimulationSchedule(
            schema_version="week_simulation_schedule.v2",
            run_id=cmd.run_id, branch_id=cmd.branch_id, week=week,
            slots=(group_slot,),
        )
        expanded = WeekSimulationSchedule(
            schema_version="week_simulation_schedule.v2",
            run_id=cmd.run_id, branch_id=cmd.branch_id, week=week,
            slots=(group_slot, final_slot),
        )
        child = AuthoritativeSimulationCommand(
            command_id=driver._week_slot_child_command_id(
                week_command.command_id, 1
            ),
            run_id=cmd.run_id, branch_id=cmd.branch_id, expected_week=week,
            expected_position_fingerprint=cmd.expected_position_fingerprint,
            expected_revision_id=cmd.expected_revision_id,
        )
        frozen_week = {
            "schema_version":"authoritative_week_operation.v1",
            "run_id":cmd.run_id, "branch_id":cmd.branch_id,
            "week":week.model_dump(mode="json"),
            "target_week":RankingWeek(
                season_index=week.season_index, week=week.week + 1
            ).model_dump(mode="json"),
            "schedule_fingerprint":base.fingerprint,
            "target_slot_ordinals":[1],
            "target_group_ids":["seed-group"],
            "child_commands":{"1":child.model_dump(mode="json")},
            "week_transition":None,
        }
        with factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            driver.prepare_full_simulation(
                session, cmd,
                fingerprint({
                    "mode":"full_simulation", "command":cmd.model_dump(mode="json")
                }),
            )
            session.flush()  # Materialize newly created parent before lookup.
            full_row = session.get(
                AuthoritativeSimulationCommandModel,
                (cmd.run_id, cmd.branch_id, cmd.command_id),
            )
            frozen_full = json.loads(full_row.result_json)
            frozen_full["season_children"][str(week.season_index)] = {
                "command":season_command.model_dump(mode="json"),
                "preview_fingerprint":season_command.expected_preview_fingerprint,
            }
            full_row.result_json = json.dumps(frozen_full,sort_keys=True)
            session.add_all([
                AuthoritativeSimulationCommandModel(
                    run_id=cmd.run_id,branch_id=cmd.branch_id,
                    command_id=season_command.command_id,
                    request_fingerprint=fingerprint({
                        "mode":"season",
                        "command":season_command.model_dump(mode="json"),
                    }),
                    status="pending",
                    result_json=json.dumps({"week_children":{
                        str(week.ordinal):{
                            "command":week_command.model_dump(mode="json"),
                            "preview_fingerprint":week_command.expected_preview_fingerprint,
                        }
                    }}),
                ),
                AuthoritativeSimulationCommandModel(
                    run_id=cmd.run_id,branch_id=cmd.branch_id,
                    command_id=week_command.command_id,
                    request_fingerprint=fingerprint({
                        "mode":"week",
                        "command":week_command.model_dump(mode="json"),
                    }),
                    status="pending",result_json=json.dumps(frozen_week),
                ),
                AuthoritativeSimulationCommandModel(
                    run_id=cmd.run_id,branch_id=cmd.branch_id,
                    command_id=child.command_id,
                    request_fingerprint=fingerprint({
                        "mode":"slot","command":child.model_dump(mode="json"),
                    }),
                    status="complete", result_json="{}",
                ),
            ])
            row = FullSimulationTaskModel(
                task_id="test-task",run_id=cmd.run_id,branch_id=cmd.branch_id,
                parent_command_id=cmd.command_id,start_request_id="start-test",
                payload_json="{}",payload_fingerprint="a"*64,
            )
            data = {
                "schema_version":"full_simulation_task.v1",
                "task_id":row.task_id,"start_request_id":row.start_request_id,
                "command":cmd.model_dump(mode="json"),"events":[],"requests":[],
                "owner_instance":"test","owner_token":"dead",
                "heartbeat_unix":0,
                "checkpoint":"week_schedule_review_required",
                "progress":None,"error":None,
            }
            task_event(data,"queued","explicit_start")
            task_record(row,data,"start-test",{
                "action":"start","command":data["command"]
            })
            task_event(data,"active","worker_running")
            task_event(data,"awaiting_operator","canonical_checkpoint")
            task_write(row,data)
            session.add(row)

        # Inject only future knockout topology and Position to isolate approval
        # from the real MatchEngine (which is deliberately not executed).
        # The driver is slotted; patch type methods only after genuine initial
        # parent preview/freeze, and restore them automatically after the test.
        monkeypatch.setattr(
            AuthoritativeRunSimulationDriver,"_position",
            lambda self, session, run, branch, **kw: SimpleNamespace(
                current_week=week,current_slot_kind="match",slot_ordinal=2
            ),
        )
        monkeypatch.setattr(
            AuthoritativeRunSimulationDriver,"_schedule",
            lambda self, session, run, branch, target_week: base,
        )
        monkeypatch.setattr(
            AuthoritativeRunSimulationDriver,"_execution_schedule",
            lambda self, session, **kw: expanded,
        )
        monkeypatch.setattr(
            AuthoritativeRunSimulationDriver,"_hybrid_knockout_brackets_for_week",
            lambda self, session, **kw: ((
                SimpleNamespace(event_id="hybrid"),
                SimpleNamespace(event_id="hybrid",matches=(
                    SimpleNamespace(match_id="seed-final"),)),
            ),),
        )
        endpoint = server.base_url+flow["scope"]
        status, report = _request(
            "GET",endpoint+"/next-week/extension-inspection"
        )
        assert status == 200, report
        item = next(i for i in report["items"] if i["command_id"]=="owned-week")
        assert item["status"]=="append_only_proven", item
        body = {
            "control_command_id":"approve-test",
            "task_id":"test-task","target_week_command_id":"owned-week",
            "expected_task_revision":3,
            "expected_receipt_fingerprint":item["receipt_fingerprint"],
            "expected_current_schedule_fingerprint":item["current_schedule_fingerprint"],
            "operator_label":"Admin",
            "audit_reason":"Reviewed the exact new knockout final",
            "confirm_committed_work_is_immutable":True,
        }
        assert _request(
            "POST",endpoint+"/next-week/extension-approve",
            body|{"expected_task_revision":2}
        )[0]==409
        status, approved = _request(
            "POST",endpoint+"/next-week/extension-approve",body
        )
        assert status==200, approved
        assert approved["new_slot_ordinals"]==[2]
        assert approved["sport_executed"] is False
        assert approved["saved_revision_changed"] is False
        assert approved["task_revision"]==4
        status, replay = _request(
            "POST",endpoint+"/next-week/extension-approve",body
        )
        assert status==200 and replay["replayed"] is True
        assert _request(
            "POST",endpoint+"/next-week/extension-approve",
            body|{"audit_reason":"Changed audit on existing ID"}
        )[0]==409
        after = snapshot(factory, flow["run_id"], flow["branch_id"])
        assert after["groups"]==before["groups"]
        assert after["slots"]==before["slots"]
        assert after["saved_head"]==before["saved_head"]
        assert after["saved"]==before["saved"]
        assert after["commands"]["owned-week"]["fingerprint"]==fingerprint({
            "mode":"week","command":week_command.model_dump(mode="json")
        })
        stored = after["commands"]["owned-week"]["result"]
        assert stored["child_commands"]["1"]==child.model_dump(mode="json")
        assert stored["child_commands"]["2"] is None
        assert stored["schedule_fingerprint"]==expanded.fingerprint
        assert len(stored["schedule_extension_approvals"])==1
        from beta_engine.application.full_simulation_tasks import _read
        with factory() as session:
            task_data = _read(session.get(FullSimulationTaskModel,"test-task"))
            assert task_data["checkpoint"]=="week_schedule_extension_approved"
            assert task_data["revision"]==4
            assert task_data["state"]=="awaiting_operator"
