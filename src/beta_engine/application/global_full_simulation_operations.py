"""Read-only, validated global view of durable Full Simulation parents.

A pending parent is not a worker. A SQLite invocation lease is evidence only of
unexpired, fenced invocation ownership, never a process-health guarantee.
This projection is one read-only database snapshot; it cannot renew a lease,
resume simulation, change a parent, or Save a revision.
"""

from __future__ import annotations

import json
import time

from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeFullSimulationCommand,
)
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.full_simulation_invocation_lease import LEASE_SCOPE
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    FullSimulationExecutionLeaseModel,
    RunBranchModel,
    RunContainerModel,
)


def _week(value: object, *, label: str) -> dict[str, int]:
    """Do not let Pydantic integer coercion hide invalid stored JSON evidence."""
    if (
        not isinstance(value, dict)
        or set(value) != {"season_index", "week"}
        or type(value["season_index"]) is not int
        or type(value["week"]) is not int
        or not 0 <= value["season_index"] < 50
        or not 1 <= value["week"] <= 61
    ):
        raise ValueError(f"Pending Full Simulation {label} is corrupt")
    return value


def _valid_target_event(event: dict, index: int) -> bool:
    """Validate revision provenance without inventing an updated target."""
    target = _week(event.get("target_week"), label="target audit week")
    if (
        event.get("revision") != index
        or not isinstance(event.get("command_id"), str)
        or not event["command_id"]
        or event.get("target_week") != target
    ):
        return False
    if event.get("boundary_target") is not None:
        from beta_engine.application.full_simulation_boundary_targets import validate_boundary_event
        return validate_boundary_event(event)
    relative = event.get("relative_target")
    if relative is None:
        return "relative_target" not in event  # legacy absolute events
    if (
        not isinstance(relative, dict)
        or set(relative) != {"unit", "count"}
        or relative["unit"] not in ("weeks", "seasons")
        or type(relative["count"]) is not int
        or not 1 <= relative["count"] <= (49 if relative["unit"] == "seasons" else 3050)
    ):
        return False
    origin = _week(event.get("applied_at_week"), label="relative target starting week")
    origin_ordinal = origin["season_index"] * 61 + origin["week"] - 1
    target_ordinal = target["season_index"] * 61 + target["week"] - 1
    return target_ordinal == origin_ordinal + relative["count"] * (
        61 if relative["unit"] == "seasons" else 1
    )


def _progress(frozen: dict, *, start: dict, final: dict) -> tuple[int, int]:
    seasons = frozen.get("completed_seasons", [])
    weeks = frozen.get("final_completed_weeks", [])
    if not isinstance(seasons, list) or not isinstance(weeks, list):
        raise ValueError("Pending Full Simulation progress is corrupt")
    if any(type(item) is not int for item in seasons):
        raise ValueError("Pending Full Simulation completed seasons are corrupt")
    # Every completed season is an actual transition, chronologically following
    # the original start; season 49 is closed separately by final Run closure.
    if seasons != list(range(start["season_index"], start["season_index"] + len(seasons))):
        raise ValueError("Pending Full Simulation completed seasons are not consecutive")
    if any(season < 0 or season >= 49 for season in seasons):
        raise ValueError("Pending Full Simulation completed seasons exceed the Run")
    first_week = start["week"] if start["season_index"] == 49 else 1
    expected_weeks = list(range(first_week, first_week + len(weeks)))
    observed_weeks = [
        _week(item, label="final completed week") for item in weeks
    ]
    if (
        any(item["season_index"] != 49 for item in observed_weeks)
        or [item["week"] for item in observed_weeks] != expected_weeks
        or (weeks and len(seasons) != 49 - start["season_index"])
    ):
        raise ValueError("Pending Full Simulation final weeks are not consecutive")
    # These counts are normally absent in the parent; if present they must
    # never conflict with the actual validated evidence.
    if (
        ("completed_season_count" in frozen and (
            type(frozen["completed_season_count"]) is not int
            or frozen["completed_season_count"] != len(seasons)
        ))
        or ("final_completed_week_count" in frozen and (
            type(frozen["final_completed_week_count"]) is not int
            or frozen["final_completed_week_count"] != len(weeks)
        ))
    ):
        raise ValueError("Pending Full Simulation progress counts are corrupt")
    if final != {"season_index": 49, "week": 61}:
        raise ValueError("Pending Full Simulation original final Run target is corrupt")
    return len(seasons), len(weeks)


def _lease_evidence(lease, *, run_id: str, branch_id: str,
                    command_id: str, now: int) -> tuple[str, int | None]:
    if lease is None:
        return "absent", None
    if not lease.run_id or not lease.branch_id or not lease.command_id:
        raise ValueError("Full Simulation execution lease identity is corrupt")
    if type(lease.expires_at_unix) is not int or lease.expires_at_unix < 0:
        raise ValueError("Full Simulation execution lease expiry is corrupt")
    matching = (
        lease.run_id == run_id
        and lease.branch_id == branch_id
        and lease.command_id == command_id
    )
    active = lease.expires_at_unix > now
    return (
        ("matching_active" if active else "matching_expired")
        if matching else ("other_active" if active else "other_expired"),
        lease.expires_at_unix,
    )


def inspect_global_full_simulation_operations(factory) -> dict:
    """Project all parents and the one current lease in a single read session."""
    items: list[dict] = []
    legacy_count = 0
    now = int(time.time())
    with factory() as session:
        # All database observations use the same SQLite read transaction.
        receipts = session.scalars(
            select(AuthoritativeSimulationCommandModel)
            .where(AuthoritativeSimulationCommandModel.status == "pending")
            .order_by(
                AuthoritativeSimulationCommandModel.run_id,
                AuthoritativeSimulationCommandModel.branch_id,
                AuthoritativeSimulationCommandModel.command_id,
            )
        ).all()
        lease = session.get(FullSimulationExecutionLeaseModel, LEASE_SCOPE)
        seen_scope: set[tuple[str, str]] = set()
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
                or frozen.get("run_id", receipt.run_id) != receipt.run_id
                or frozen.get("branch_id", receipt.branch_id) != receipt.branch_id
                or frozen.get("initial_saved_revision_id", command.expected_revision_id)
                != command.expected_revision_id
            ):
                raise ValueError("Pending Full Simulation parent identity is corrupt")
            scope = (receipt.run_id, receipt.branch_id)
            if scope in seen_scope:
                raise ValueError("Duplicate pending Full Simulation parent scope")
            seen_scope.add(scope)
            if receipt.request_fingerprint != fingerprint({
                "mode": "full_simulation",
                "command": command.model_dump(mode="json"),
            }):
                raise ValueError("Pending Full Simulation parent fingerprint is corrupt")
            review = frozen["review"]
            start = command.expected_start_week.model_dump(mode="json")
            if not isinstance(review, dict):
                raise ValueError("Pending Full Simulation reviewed scope is corrupt")
            reviewed_start = _week(review.get("start_week"), label="reviewed start week")
            reviewed_final = _week(review.get("final_week"), label="reviewed final week")
            if (
                review.get("schema_version") != "authoritative_full_simulation_preview.v1"
                or review.get("run_id") != receipt.run_id
                or review.get("branch_id") != receipt.branch_id
                or review.get("preview_fingerprint") != command.expected_preview_fingerprint
                or review.get("expected_position_fingerprint")
                != command.expected_position_fingerprint
                or review.get("expected_revision_id") != command.expected_revision_id
                or reviewed_start != start
                or ("start_week" in frozen and
                    _week(frozen["start_week"], label="stored start week") != start)
                or ("final_week" in frozen and
                    _week(frozen["final_week"], label="stored final week") != reviewed_final)
            ):
                raise ValueError("Pending Full Simulation reviewed scope is corrupt")
            target_revision = frozen.get("target_revision", 0)
            target_events = frozen.get("target_events", [])
            target = _week(frozen.get("effective_target_week", reviewed_final), label="effective target week")
            if (
                type(target_revision) is not int
                or target_revision < 0
                or not isinstance(target_events, list)
                or len(target_events) != target_revision
                or not all(isinstance(item, dict) for item in target_events)
                or (target_revision == 0 and target != reviewed_final)
                or (target_revision > 0 and target_events[-1].get("target_week") != target)
                or target["season_index"] * 61 + target["week"] <
                    start["season_index"] * 61 + start["week"]
                or len({item.get("command_id") for item in target_events}) != len(target_events)
                or any(
                    not _valid_target_event(event, index)
                    for index, event in enumerate(target_events, 1)
                )
            ):
                raise ValueError("Pending Full Simulation effective target audit is corrupt")
            from beta_engine.application.full_simulation_boundary_targets import effective_boundary
            boundary = effective_boundary(frozen)
            for target_event in target_events:
                if target_event.get("boundary_target") is not None:
                    scope = target_event["boundary_review"]
                    if (scope["run_id"], scope["branch_id"], scope["parent_command_id"]) != (receipt.run_id, receipt.branch_id, receipt.command_id):
                        raise ValueError("Pending boundary target scope is corrupt")
            state = frozen.get("control_state", "running")
            if state not in {"running", "pause_requested", "paused"}:
                raise ValueError("Pending Full Simulation control state is corrupt")
            season_count, week_count = _progress(
                frozen, start=start, final=reviewed_final
            )
            lease_state, expires_at = _lease_evidence(
                lease, run_id=receipt.run_id, branch_id=receipt.branch_id,
                command_id=receipt.command_id, now=now,
            )
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
                "start_week": start,
                "final_week": reviewed_final,
                "effective_target_week": target,
                "effective_boundary_target": boundary.model_dump(mode="json") if boundary else None,
                "target_revision": target_revision,
                "completed_season_count": season_count,
                "final_completed_week_count": week_count,
                "review_fingerprint": review["preview_fingerprint"],
                "worker_activity": "unknown",
                "lease_state": lease_state,
                "lease_expires_at_unix": expires_at,
            })
    return {
        "schema_version": "global_full_simulation_operations.v1",
        "visibility": "durable_receipts_only",
        "operations": items,
        "pending_count": len(items),
        "legacy_pending_count": legacy_count,
    }
