"""Atomic final-season closure writer for 2049/50 Week 61."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from beta_engine.application.final_run_completion import stage_final_run_completion
from beta_engine.application.season_closing_ranking_resolution import (
    stage_canonical_season_closing_ranking,
)
from beta_engine.application.season_closure_resolution import (
    resolve_canonical_season_closure_package,
)
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.run_containers import (
    COMPLETED_RUN_STATUS,
    is_pre_completion_run_status,
)
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    CONTENT_HASH_ALGORITHM,
    FINAL_SEASON_CLOSURE_AUDIT_EVENT_KIND,
    FINAL_SEASON_CLOSURE_SAVED_REVISION_KIND,
    RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
    RUN_WORKING_DRAFT_SCHEMA_VERSION,
    saved_revision_content_hash,
    viewer_branch_saved_revision_payload,
)
from beta_engine.domain.season_closure import bind_season_closure_marker
from beta_engine.infrastructure.db.initial_world_state import capture_saved_initial_world
from beta_engine.infrastructure.db.models import (
    BranchRevisionAuditEventModel,
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import capture_saved_lifecycle
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    capture_saved_tour_entry_triggers,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    capture_saved_run_entry_decision_slots,
)
from beta_engine.infrastructure.db.application_validation_slots import (
    capture_saved_application_validation_slots,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    capture_saved_application_submissions,
)
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    capture_saved_definitive_wild_card_assignments,
)
from beta_engine.infrastructure.db.player_sporting_state import capture_saved_sporting
from beta_engine.infrastructure.db.saved_revision_rankings import (
    capture_saved_ranking_component,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    install_saved_revision_season_closure,
    load_saved_revision_season_closure,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
)


FINAL_WEEK = RankingWeek(season_index=49, week=61)


class FinalSeasonTransitionCommand(FrozenInput):
    schema_version: Literal["final_season_transition_command.v1"] = (
        "final_season_transition_command.v1"
    )
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    expected_preflight_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_saved_revision_id: str = Field(min_length=1)
    expected_draft_version: int = Field(ge=0)
    final_saved_revision_id: str = Field(min_length=1, max_length=128)
    audit_event_id: str = Field(min_length=1, max_length=128)

    @property
    def fingerprint(self) -> str:
        import hashlib
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class FinalSeasonTransitionResult(FrozenInput):
    schema_version: Literal["final_season_transition_result.v1"] = (
        "final_season_transition_result.v1"
    )
    run_id: str
    branch_id: str
    completed_week: RankingWeek
    saved_revision_id: str
    closing_ranking_fingerprint: str
    season_summary_fingerprint: str
    closure_marker_fingerprint: str
    draft_version: int
    run_status: Literal["completed"] = "completed"


def _revision_payload(row: BranchSavedRevisionModel) -> tuple[dict, dict]:
    try:
        payload = json.loads(row.payload_json)
        summary = json.loads(row.change_summary_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Branch Saved Revision JSON is corrupt") from exc
    if not isinstance(payload, dict) or not isinstance(summary, dict):
        raise ValueError("Branch Saved Revision payload is corrupt")
    expected = saved_revision_content_hash(
        revision_id=row.revision_id,
        run_id=row.run_id,
        branch_id=row.branch_id,
        sequence=row.sequence,
        parent_revision_id=row.parent_revision_id,
        kind=row.kind,
        payload_schema_version=row.payload_schema_version,
        payload=payload,
        change_summary=summary,
    )
    if row.content_hash_algorithm != CONTENT_HASH_ALGORITHM or row.content_hash != expected:
        raise ValueError("Branch Saved Revision content hash is corrupt")
    return payload, summary


def _retry_result(
    session: Session,
    command: FinalSeasonTransitionCommand,
) -> FinalSeasonTransitionResult | None:
    revision = session.get(BranchSavedRevisionModel, command.final_saved_revision_id)
    if revision is None:
        return None
    branch = session.get(RunBranchModel, command.branch_id)
    run = session.get(RunContainerModel, command.run_id)
    audit = session.scalar(
        select(BranchRevisionAuditEventModel).where(
            BranchRevisionAuditEventModel.saved_revision_id
            == command.final_saved_revision_id
        )
    )
    if (
        revision.run_id != command.run_id
        or revision.branch_id != command.branch_id
        or revision.kind != FINAL_SEASON_CLOSURE_SAVED_REVISION_KIND
        or branch is None
        or branch.saved_head_revision_id != command.final_saved_revision_id
        or run is None
        or run.status != COMPLETED_RUN_STATUS
        or audit is None
        or audit.audit_event_id != command.audit_event_id
        or audit.event_kind != FINAL_SEASON_CLOSURE_AUDIT_EVENT_KIND
    ):
        raise ValueError("Final season transition revision identity is already in conflict")
    payload, _ = _revision_payload(revision)
    try:
        audit_payload = json.loads(audit.payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Final season transition audit is corrupt") from exc
    if audit_payload.get("request_fingerprint") != command.fingerprint:
        raise ValueError("Final season transition command retry has different inputs")
    component = load_saved_revision_season_closure(
        payload,
        run_id=command.run_id,
        branch_id=command.branch_id,
        revision_id=command.final_saved_revision_id,
    )
    if component is None:
        raise ValueError("Final season transition revision lost closure evidence")
    summary = component.parsed_summary
    marker = component.parsed_marker
    draft = session.scalar(
        select(BranchWorkingDraftModel).where(
            BranchWorkingDraftModel.branch_id == command.branch_id
        )
    )
    if draft is None or draft.base_revision_id != command.final_saved_revision_id:
        raise ValueError("Final season transition retry has incoherent Working Draft")
    return FinalSeasonTransitionResult(
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed_week=marker.completed_week,
        saved_revision_id=command.final_saved_revision_id,
        closing_ranking_fingerprint=marker.closing_ranking_fingerprint,
        season_summary_fingerprint=summary.fingerprint,
        closure_marker_fingerprint=marker.fingerprint,
        draft_version=draft.draft_version,
    )


def commit_final_season_transition(
    session: Session,
    command: FinalSeasonTransitionCommand,
    *,
    fault_at: str | None = None,
) -> FinalSeasonTransitionResult:
    """Commit final Week-61 closure inside a caller-owned transaction."""

    if not session.in_transaction():
        raise ValueError("Final season transition requires a caller transaction")
    retry = _retry_result(session, command)
    if retry is not None:
        return retry

    run = session.get(RunContainerModel, command.run_id)
    branch = session.get(RunBranchModel, command.branch_id)
    draft = session.scalar(
        select(BranchWorkingDraftModel).where(
            BranchWorkingDraftModel.branch_id == command.branch_id
        )
    )
    if run is None or branch is None or branch.run_id != command.run_id or draft is None:
        raise ValueError("Final season transition Run/Branch scope is incomplete")
    if run.read_only or branch.read_only or branch.status != "active":
        raise ValueError("Final season transition requires a writable active Branch")
    if not (
        is_pre_completion_run_status(run.status)
        or run.status == COMPLETED_RUN_STATUS
    ):
        raise ValueError(
            "Final season transition requires a Working or Completed Run"
        )
    if (
        branch.saved_head_revision_id != command.expected_saved_revision_id
        or draft.base_revision_id != command.expected_saved_revision_id
    ):
        raise ValueError("Final season transition Saved Revision head is stale")
    if (
        draft.status != CLEAN_WORKING_DRAFT_STATUS
        or draft.change_count != 0
        or json.loads(draft.changes_json) != []
    ):
        raise ValueError("Final season transition requires a clean Working Draft")
    if draft.draft_version != command.expected_draft_version:
        raise ValueError("Final season transition Working Draft version is stale")

    head = session.get(BranchSavedRevisionModel, command.expected_saved_revision_id)
    if head is None or (head.run_id, head.branch_id) != (
        command.run_id,
        command.branch_id,
    ):
        raise ValueError("Final season transition Saved Revision head is missing")
    base_payload, _ = _revision_payload(head)

    if session.get(BranchSavedRevisionModel, command.final_saved_revision_id) is not None:
        raise ValueError("Final season transition Saved Revision id is already in use")
    if session.get(BranchRevisionAuditEventModel, command.audit_event_id) is not None:
        raise ValueError("Final season transition audit id is already in use")

    closing = stage_canonical_season_closing_ranking(
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed_week=FINAL_WEEK,
    )
    package = resolve_canonical_season_closure_package(
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed_week=FINAL_WEEK,
    )
    marker = bind_season_closure_marker(
        package.marker,
        final_saved_revision_id=command.final_saved_revision_id,
    )

    viewer_branch_id = (run.official_branch_id or "").strip()
    if not viewer_branch_id:
        raise ValueError("Final season transition requires a Viewer Branch")
    payload = viewer_branch_saved_revision_payload(
        base_payload=base_payload,
        run_id=command.run_id,
        display_name=run.display_name or command.run_id,
        run_status=COMPLETED_RUN_STATUS,
        timeline_start_season=run.timeline_start_season,
        timeline_end_season=run.timeline_end_season,
        branch_id=command.branch_id,
        branch_display_name=branch.display_name,
        branch_status=branch.status,
        forked_from_branch_id=branch.forked_from_branch_id,
        forked_from_saved_revision_id=branch.forked_from_saved_revision_id,
        viewer_branch_id=viewer_branch_id,
    )
    capture_saved_ranking_component(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_initial_world(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_lifecycle(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_run_entry_decision_slots(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_application_validation_slots(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_application_submissions(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_definitive_wild_card_assignments(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_tour_entry_triggers(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_sporting(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_simulation_slots(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    install_saved_revision_season_closure(
        payload,
        package=package,
        marker=marker,
    )

    summary = {
        "kind": FINAL_SEASON_CLOSURE_SAVED_REVISION_KIND,
        "summary": "Closed final season 2049/50 and completed Run",
        "completed_week": FINAL_WEEK.model_dump(mode="json"),
        "closing_ranking_fingerprint": closing.fingerprint,
        "season_summary_fingerprint": package.summary.fingerprint,
        "closure_marker_fingerprint": marker.fingerprint,
    }
    sequence = head.sequence + 1
    content_hash = saved_revision_content_hash(
        revision_id=command.final_saved_revision_id,
        run_id=command.run_id,
        branch_id=command.branch_id,
        sequence=sequence,
        parent_revision_id=head.revision_id,
        kind=FINAL_SEASON_CLOSURE_SAVED_REVISION_KIND,
        payload_schema_version=RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
        payload=payload,
        change_summary=summary,
    )
    session.add(
        BranchSavedRevisionModel(
            revision_id=command.final_saved_revision_id,
            run_id=command.run_id,
            branch_id=command.branch_id,
            sequence=sequence,
            parent_revision_id=head.revision_id,
            kind=FINAL_SEASON_CLOSURE_SAVED_REVISION_KIND,
            payload_schema_version=RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
            content_hash_algorithm=CONTENT_HASH_ALGORITHM,
            content_hash=content_hash,
            payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            change_summary_json=json.dumps(
                summary, sort_keys=True, separators=(",", ":")
            ),
        )
    )
    session.flush()
    if fault_at == "after_revision":
        raise RuntimeError("fault after final closure revision")

    claimed = session.execute(
        update(BranchWorkingDraftModel)
        .where(
            BranchWorkingDraftModel.draft_id == draft.draft_id,
            BranchWorkingDraftModel.base_revision_id
            == command.expected_saved_revision_id,
            BranchWorkingDraftModel.draft_version == command.expected_draft_version,
            BranchWorkingDraftModel.status == CLEAN_WORKING_DRAFT_STATUS,
        )
        .values(
            base_revision_id=command.final_saved_revision_id,
            draft_version=command.expected_draft_version + 1,
            draft_schema_version=RUN_WORKING_DRAFT_SCHEMA_VERSION,
            status=CLEAN_WORKING_DRAFT_STATUS,
            change_count=0,
            changes_json="[]",
            updated_at=func.current_timestamp(),
        )
    )
    if claimed.rowcount != 1:
        raise ValueError("Final season transition Working Draft changed concurrently")

    branch.saved_head_revision_id = command.final_saved_revision_id
    session.add(
        BranchRevisionAuditEventModel(
            audit_event_id=command.audit_event_id,
            run_id=command.run_id,
            branch_id=command.branch_id,
            saved_revision_id=command.final_saved_revision_id,
            event_kind=FINAL_SEASON_CLOSURE_AUDIT_EVENT_KIND,
            payload_json=json.dumps(
                {
                    "command_id": command.command_id,
                    "request_fingerprint": command.fingerprint,
                    "previous_saved_revision_id": command.expected_saved_revision_id,
                    "final_saved_revision_id": command.final_saved_revision_id,
                    "closing_ranking_fingerprint": closing.fingerprint,
                    "season_summary_fingerprint": package.summary.fingerprint,
                    "closure_marker_fingerprint": marker.fingerprint,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    )
    session.flush()
    if fault_at == "before_completion":
        raise RuntimeError("fault before final Run completion")

    completion = stage_final_run_completion(
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        final_saved_revision_id=command.final_saved_revision_id,
    )
    if completion.completed_week != FINAL_WEEK:
        raise ValueError("Final Run completion returned the wrong boundary")

    return FinalSeasonTransitionResult(
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed_week=FINAL_WEEK,
        saved_revision_id=command.final_saved_revision_id,
        closing_ranking_fingerprint=closing.fingerprint,
        season_summary_fingerprint=package.summary.fingerprint,
        closure_marker_fingerprint=marker.fingerprint,
        draft_version=command.expected_draft_version + 1,
    )
