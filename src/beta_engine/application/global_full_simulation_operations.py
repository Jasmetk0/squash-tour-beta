"""Read-only global inventory of durable Full Simulation parents.

A receipt describes committed progress and authorization state, NOT a live worker
or a recoverable background task. This projection never starts or resumes work.
"""

from __future__ import annotations

import json

from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeFullSimulationCommand,
)
from beta_engine.domain.fingerprint import fingerprint
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    RunBranchModel,
    RunContainerModel,
)


def inspect_global_full_simulation_operations(factory) -> dict:
    """List exact pending parents across Run/Branch within one read transaction."""
    items: list[dict] = []
    legacy_count = 0
    with factory() as session:
        receipts = session.scalars(
            select(AuthoritativeSimulationCommandModel)
            .where(AuthoritativeSimulationCommandModel.status == "pending")
            .order_by(
                AuthoritativeSimulationCommandModel.run_id,
                AuthoritativeSimulationCommandModel.branch_id,
                AuthoritativeSimulationCommandModel.command_id,
            )
        ).all()
        for receipt in receipts:
            try:
                frozen = json.loads(receipt.result_json)
            except (ValueError, TypeError) as exc:
                raise ValueError("Pending simulation receipt JSON is corrupt") from exc
            if not isinstance(frozen, dict):
                raise ValueError("Pending simulation receipt must be an object")
            if frozen.get("schema_version") != "authoritative_full_simulation_operation.v1":
                continue
            run = session.get(RunContainerModel, receipt.run_id)
            branch = session.get(RunBranchModel, receipt.branch_id)
            if run is None or branch is None or branch.run_id != receipt.run_id:
                raise ValueError("Pending Full Simulation parent has no matching Run/Branch")
            if frozen.get("resume_command") is None or frozen.get("review") is None:
                legacy_count += 1
                continue
            try:
                command = AuthoritativeFullSimulationCommand.model_validate(
                    frozen["resume_command"]
                )
            except (ValueError, TypeError) as exc:
                raise ValueError("Pending Full Simulation command is corrupt") from exc
            if (
                command.run_id != receipt.run_id
                or command.branch_id != receipt.branch_id
                or command.command_id != receipt.command_id
            ):
                raise ValueError("Pending Full Simulation parent identity is corrupt")
            if receipt.request_fingerprint != fingerprint({
                "mode": "full_simulation",
                "command": command.model_dump(mode="json"),
            }):
                raise ValueError("Pending Full Simulation parent fingerprint is corrupt")
            review = frozen["review"]
            if not isinstance(review, dict) or (
                review.get("schema_version") != "authoritative_full_simulation_preview.v1"
                or review.get("run_id") != receipt.run_id
                or review.get("branch_id") != receipt.branch_id
                or review.get("preview_fingerprint") != command.expected_preview_fingerprint
                or review.get("expected_position_fingerprint")
                != command.expected_position_fingerprint
                or review.get("expected_revision_id") != command.expected_revision_id
                or review.get("start_week")
                != command.expected_start_week.model_dump(mode="json")
                or not isinstance(review.get("final_week"), dict)
            ):
                raise ValueError("Pending Full Simulation reviewed scope is corrupt")
            state = frozen.get("control_state", "running")
            if state not in {"running", "pause_requested", "paused"}:
                raise ValueError("Pending Full Simulation control state is corrupt")
            seasons = frozen.get("completed_seasons", [])
            weeks = frozen.get("final_completed_weeks", [])
            if not isinstance(seasons, list) or not isinstance(weeks, list):
                raise ValueError("Pending Full Simulation progress is corrupt")
            items.append({
                "run_id": receipt.run_id,
                "run_name": run.display_name or receipt.run_id,
                "run_status": run.status,
                "run_read_only": bool(run.read_only),
                "branch_id": receipt.branch_id,
                "branch_name": branch.display_name,
                "branch_status": branch.status,
                "branch_read_only": bool(branch.read_only),
                "command_id": receipt.command_id,
                "control_state": state,
                "start_week": review["start_week"],
                "final_week": review["final_week"],
                "completed_season_count": len(seasons),
                "final_completed_week_count": len(weeks),
                "review_fingerprint": review["preview_fingerprint"],
                "worker_activity": "unknown",
            })
    return {
        "schema_version": "global_full_simulation_operations.v1",
        "visibility": "durable_receipts_only",
        "operations": items,
        "pending_count": len(items),
        "legacy_pending_count": legacy_count,
    }
