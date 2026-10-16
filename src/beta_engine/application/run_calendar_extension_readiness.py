"""Fail-closed, read-only inventory for an all-Branch Run calendar extension.

No current Save head, history, Run status or frozen task is modified here.
This inspection is *not* an extension permission or write command.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import (
    RunContainerModel, RunBranchModel, BranchSavedRevisionModel,
)


def inspect_run_calendar_extension_readiness(
    session: Session, *, run_id: str, new_season_count: int
) -> dict:
    run = session.get(RunContainerModel, run_id)
    if run is None:
        raise ValueError("Run is not found")
    if run.storage_kind != "custom_local" or bool(run.read_only):
        raise ValueError("Run is not writable by Admin")

    branches = session.scalars(
        select(RunBranchModel).where(RunBranchModel.run_id == run_id)
        .order_by(RunBranchModel.branch_id)
    ).all()
    if not branches:
        raise ValueError("Run has no Branches")

    results: list[dict] = []
    current: RunCalendar | None = None
    for branch in branches:
        blockers: list[str] = []
        head_id = branch.saved_head_revision_id
        hash_value: str | None = None
        if not head_id:
            blockers.append("missing_saved_head")
        else:
            revision = session.get(BranchSavedRevisionModel, head_id)
            if revision is None or revision.run_id != run_id:
                blockers.append("invalid_saved_head_identity")
            else:
                hash_value = revision.content_hash
        try:
            calendar = resolve_saved_run_calendar(
                session, run_id=run_id, branch_id=branch.branch_id
            )
        except ValueError:
            blockers.append("saved_calendar_authority_failed")
        else:
            if calendar.schema_version != "run_calendar.v1":
                blockers.append("historical_legacy_calendar_requires_migration")
            elif current is None:
                current = calendar
            elif current != calendar:
                blockers.append("branch_calendar_mismatch")
        results.append({
            "branch_id": branch.branch_id,
            "saved_head_revision_id": head_id,
            "saved_head_content_hash": hash_value,
            "blockers": blockers,
        })

    if current is None:
        raise ValueError("No valid versioned Saved Run calendar authority")
    proposed = current.extend_to(new_season_count)
    blockers = sorted({code for item in results for code in item["blockers"]})
    return {
        "schema_version": "run_calendar_extension_readiness.v1",
        "run_id": run_id,
        "read_only": True,
        "state_changed": False,
        "commit_supported": False,
        "all_branch_heads_checked": True,
        "branch_count": len(results),
        "branches": results,
        "ready_for_future_commit_preflight": not blockers,
        "blockers": blockers,
        "original_calendar": current.to_metadata(),
        "proposed_calendar": proposed.to_metadata(),
        "added_seasons": proposed.season_count - current.season_count,
        "added_weeks": (proposed.season_count - current.season_count) * current.weeks_per_year,
        "limitations": [
            "extension_transaction_not_implemented",
            "branch_snapshot_migration_not_implemented",
        ],
    }
