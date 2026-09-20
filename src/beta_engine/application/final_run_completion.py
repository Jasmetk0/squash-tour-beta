"""Final Run lifecycle staging inside the caller-owned atomic closure transaction."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.run_containers import (
    COMPLETED_RUN_STATUS,
    is_pre_completion_run_status,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    load_saved_revision_season_closure,
)


class FinalRunCompletionResult(FrozenInput):
    schema_version: Literal["final_run_completion.v1"] = "final_run_completion.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    completed_week: RankingWeek
    final_saved_revision_id: str = Field(min_length=1)
    previous_status: str = Field(min_length=1)
    status: Literal["completed"] = "completed"


def stage_final_run_completion(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    final_saved_revision_id: str,
) -> FinalRunCompletionResult:
    """Mark the Run Completed only after final closure evidence is its saved head.

    This function intentionally does not own the transaction.  The Season Transition
    writer must insert the final Saved Revision, activate it as Branch head and call
    this primitive before the same transaction commits.
    """

    if not session.in_transaction():
        raise ValueError("Final Run completion requires a caller transaction")

    run = session.get(RunContainerModel, run_id)
    branch = session.get(RunBranchModel, branch_id)
    revision = session.get(BranchSavedRevisionModel, final_saved_revision_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise ValueError("Final Run completion scope does not exist")
    if run.read_only or branch.read_only or branch.status != "active":
        raise ValueError("Final Run completion requires a writable active Branch")
    if revision is None or (revision.run_id, revision.branch_id) != (run_id, branch_id):
        raise ValueError("Final Run completion requires its Saved Revision")
    if branch.saved_head_revision_id != final_saved_revision_id:
        raise ValueError("Final Run completion Saved Revision is not the Branch head")

    component = load_saved_revision_season_closure(
        json.loads(revision.payload_json),
        run_id=run_id,
        branch_id=branch_id,
        revision_id=final_saved_revision_id,
    )
    if component is None:
        raise ValueError("Final Run completion requires Season Closure evidence")
    marker = component.parsed_marker
    completed_week = marker.completed_week
    if completed_week != RankingWeek(season_index=49, week=61):
        raise ValueError("Run can complete only after 2049/50 Week 61")
    if run.timeline_start_season != 2000 or run.timeline_end_season != 2049:
        raise ValueError("Final Run completion requires the canonical 50-season timeline")

    previous_status = run.status
    if previous_status == COMPLETED_RUN_STATUS:
        return FinalRunCompletionResult(
            run_id=run_id,
            branch_id=branch_id,
            completed_week=completed_week,
            final_saved_revision_id=final_saved_revision_id,
            previous_status=previous_status,
        )
    if not is_pre_completion_run_status(previous_status):
        raise ValueError(
            f"Run status {previous_status!r} cannot transition to Completed"
        )

    run.status = COMPLETED_RUN_STATUS
    session.flush()
    return FinalRunCompletionResult(
        run_id=run_id,
        branch_id=branch_id,
        completed_week=completed_week,
        final_saved_revision_id=final_saved_revision_id,
        previous_status=previous_status,
    )
