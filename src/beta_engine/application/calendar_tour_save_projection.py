"""Optional value continuity for a just-verified native Tour inspection.

This is NOT a source/Save verifier. Both callers must finish their original
complete physical/replay gates first. A matching full payload permits the UI
to retain values after confirmed Save; it cannot authorize any server action.
Unsupported/external read dependencies keep the independent inspection GET.
"""

import json

from sqlalchemy import select

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    RunProspectModel,
    StagedCalendarRankingResultVersionModel,
    StagedCalendarRankingZeroVersionModel,
)


def saved_inspection_value_fingerprint(session, payload, *, expected_head):
    run, branch, content = (payload.get(k, {}) for k in ("run", "branch", "content"))
    checkpoint = (content.get("calendar_player_sporting_checkpoint") or {}).get("state") or {}
    tour = (content.get("calendar_tour_authority") or {}).get("state") or {}
    if (
        checkpoint.get("schema_version") != "calendar_sporting_checkpoint.v13"
        or tour.get("schema_version") != "calendar_tour_authority.v5"
        or branch.get("forked_from_branch_id") is not None
        or branch.get("forked_from_saved_revision_id") is not None
        or run.get("native_branch_closures")
        or content.get("run_prospect_source") is not None
        or any(t.get("public_event", {}).get("kind") == "season_transition_completed"
               for t in tour.get("transitions", ()))
    ):
        return None
    run_id, branch_id = run.get("run_id"), branch.get("branch_id")
    if ((checkpoint.get("run_id"), checkpoint.get("branch_id")) != (run_id, branch_id)
        or (tour.get("run_id"), tour.get("branch_id")) != (run_id, branch_id)):
        return None
    actual_run = session.get(RunContainerModel, run_id)
    actual_branch = session.get(RunBranchModel, branch_id)
    if (actual_run is None or actual_branch is None
        or actual_branch.run_id != run_id
        or actual_branch.saved_head_revision_id != expected_head):
        return None
    calendar = json.loads(actual_run.metadata_json).get("run_calendar")
    if (calendar is None or run.get("run_calendar") != calendar
        or tour.get("week", {}).get("calendar") != calendar):
        return None
    # These extra live reads influence transition blockers but are not all
    # represented by the candidate payload. Do not reuse their presentation.
    for model in (RunProspectModel, StagedCalendarRankingZeroVersionModel,
                  StagedCalendarRankingResultVersionModel):
        query = select(model.run_id).where(model.run_id == run_id)
        if model is not RunProspectModel:
            query = query.where(model.branch_id == branch_id)
        if session.scalar(query.limit(1)) is not None:
            return None
    # Includes EVERY component, Run/Branch metadata and all historical values;
    # never compare only the declared Tour/checkpoint fingerprint columns.
    return canonical_hash(payload)
