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
