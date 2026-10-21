"""Atomic staging kernel for the native fork's immutable current-fact root.

No API route calls this yet. A pending, read-only target is deliberately not a
runtime Branch until the dedicated continuation adapters can be installed too.
The surrounding transaction belongs to the caller; there are no nested commits.
"""

from sqlalchemy import select

from beta_engine.domain.run_branches import normalize_branch_display_name
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.run_revisions import (
    BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND,
    CLEAN_WORKING_DRAFT_STATUS,
    CONTENT_HASH_ALGORITHM,
    SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION,
    canonical_json,
    saved_revision_content_hash,
    viewer_branch_saved_revision_payload,
)
from beta_engine.infrastructure.db.models import (
    BranchRevisionAuditEventModel,
    BranchSavedRevisionModel,
    BranchStateModel,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.native_fork_baseline import (
    verify_native_fork_baseline_in_session,
)
from beta_engine.infrastructure.db.native_fork_saved_root import (
    COMPONENT_KEY,
    PAYLOAD_SCHEMA,
    PENDING_STATUS,
    load_native_fork_saved_root,
)

EVENT_KIND = "native_fork_baseline_installed"


def install_native_fork_baseline_in_session(
    repository,
    session,
    *,
    baseline,
    revision_id,
    draft_id,
    audit_event_id,
    display_name,
    expected_source_head,
    expected_viewer_branch_id,
    runtime=None,
):
    """Install or exactly retry one pending root, never overwrite a live target."""
    status = "active" if runtime is not None else PENDING_STATUS
    if runtime is not None and (
        runtime.baseline != baseline
        or runtime.root_saved_revision_id != revision_id
        or runtime.journal
    ):
        raise ValueError("Native activation runtime differs from its installation")
    for value in (revision_id, draft_id, audit_event_id, baseline.branch_id):
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > 128
        ):
            raise ValueError(
                "Native fork installation identifiers must be nonblank and at most 128 characters"
            )
    if display_name != normalize_branch_display_name(display_name):
        raise ValueError("Native fork Branch name must already be normalized")
    request = {
        "baseline_fingerprint": baseline.fingerprint,
        "revision_id": revision_id,
        "draft_id": draft_id,
        "audit_event_id": audit_event_id,
        "display_name": display_name,
        "expected_source_head": expected_source_head,
        "expected_viewer_branch_id": expected_viewer_branch_id,
    }
    if runtime is not None:
        request["runtime_fingerprint"] = runtime.fingerprint
    receipt = {"request_fingerprint": canonical_hash(request), "request": request}
    existing = session.get(BranchSavedRevisionModel, revision_id)
    if existing is not None:
        audit = session.get(BranchRevisionAuditEventModel, audit_event_id)
        target = session.get(RunBranchModel, baseline.branch_id)
        draft = session.get(BranchWorkingDraftModel, draft_id)
        state = session.get(BranchStateModel, baseline.branch_id)
        if (
            (existing.run_id, existing.branch_id)
            != (baseline.run_id, baseline.branch_id)
            or audit is None
            or (
                audit.run_id,
                audit.branch_id,
                audit.saved_revision_id,
                audit.event_kind,
                audit.payload_json,
            )
            != (
                baseline.run_id,
                baseline.branch_id,
                revision_id,
                EVENT_KIND,
                canonical_json(receipt),
            )
            or target is None
            or target.saved_head_revision_id != revision_id
            or target.status != status
            or bool(target.read_only) != (runtime is None)
            or target.display_name != display_name
            or draft is None
            or (
                draft.run_id,
                draft.branch_id,
                draft.base_revision_id,
                draft.status,
                draft.change_count,
                draft.draft_version,
                draft.changes_json,
                draft.draft_schema_version,
            )
            != (
                baseline.run_id,
                baseline.branch_id,
                revision_id,
                CLEAN_WORKING_DRAFT_STATUS,
                0,
                0,
                "[]",
                SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION,
            )
            or state is None
            or state.run_id != baseline.run_id
            or state.status != status
        ):
            raise ValueError(
                "Native fork installation receipt conflicts with existing state"
            )
        revision = repository._validated_saved_revision_in_session(
            session=session, model=existing
        )
        if load_native_fork_saved_root(revision) != baseline:
            raise ValueError("Native fork retry has a different baseline")
        return revision

    run = session.get(RunContainerModel, baseline.run_id)
    source_branch = session.get(RunBranchModel, baseline.selected_source_branch_id)
    if run is None or source_branch is None or source_branch.run_id != baseline.run_id:
        raise ValueError("Native fork installation source is missing or foreign")
    if run.read_only or source_branch.status != "active":
        raise ValueError(
            "Native fork installation requires a writable Run and active source"
        )
    if (source_branch.saved_head_revision_id, run.official_branch_id) != (
        expected_source_head,
        expected_viewer_branch_id,
    ):
        raise ValueError("Native fork installation review is stale")
    if any(
        (
            session.get(RunBranchModel, baseline.branch_id),
            session.get(BranchWorkingDraftModel, draft_id),
            session.get(BranchRevisionAuditEventModel, audit_event_id),
        )
    ):
        raise ValueError("Native fork installation identifier is already in use")
    if (
        session.scalar(
            select(RunBranchModel.branch_id).where(
                RunBranchModel.run_id == baseline.run_id,
                RunBranchModel.display_name == display_name,
            )
        )
        is not None
    ):
        raise ValueError("Native fork Branch name is already in use")
    verify_native_fork_baseline_in_session(
        repository,
        session,
        baseline=baseline,
        run_id=baseline.run_id,
        source_branch_id=baseline.selected_source_branch_id,
        source_revision_id=baseline.source_binding.source.revision_id,
        target_branch_id=baseline.branch_id,
    )
    source = repository._validated_saved_revision_in_session(
        session=session,
        model=session.get(
            BranchSavedRevisionModel, baseline.source_binding.source.revision_id
        ),
    )
    payload = viewer_branch_saved_revision_payload(
        base_payload={
            "run": {"run_calendar": baseline.week.calendar.to_metadata()},
            "branch": {},
        },
        run_id=baseline.run_id,
        display_name=run.display_name,
        run_status=run.status,
        timeline_start_season=baseline.week.calendar.start_year,
        timeline_end_season=baseline.week.calendar.start_year
        + baseline.week.calendar.season_count
        - 1,
        branch_id=baseline.branch_id,
        branch_display_name=display_name,
        branch_status=status,
        forked_from_branch_id=baseline.selected_source_branch_id,
        forked_from_saved_revision_id=source.revision_id,
        viewer_branch_id=run.official_branch_id,
    )
    payload["content"] = {
        COMPONENT_KEY: {
            "state": baseline.model_dump(mode="json"),
            "fingerprint": baseline.fingerprint,
        }
    }
    if runtime is not None:
        from beta_engine.infrastructure.db.native_fork_runtime_state import (
            KEY,
            component,
        )

        payload["content"][KEY] = component(runtime)
        prospects = source.payload["content"].get("run_prospect_source")
        if prospects is not None:
            payload["content"]["run_prospect_source"] = prospects
    summary = {
        "kind": EVENT_KIND,
        "source_saved_revision_id": source.revision_id,
        "source_branch_id": baseline.selected_source_branch_id,
        "baseline_fingerprint": baseline.fingerprint,
        "continuation_ready": runtime is not None,
    }
    values = {
        "revision_id": revision_id,
        "run_id": baseline.run_id,
        "branch_id": baseline.branch_id,
        "sequence": source.sequence + 1,
        "parent_revision_id": source.revision_id,
        "kind": BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND,
        "payload_schema_version": "native_fork_saved_root.v2"
        if runtime is not None
        else PAYLOAD_SCHEMA,
    }
    row = BranchSavedRevisionModel(
        **values,
        content_hash_algorithm=CONTENT_HASH_ALGORITHM,
        content_hash=saved_revision_content_hash(
            **values, payload=payload, change_summary=summary
        ),
        payload_json=canonical_json(payload),
        change_summary_json=canonical_json(summary),
    )
    session.add_all(
        [
            RunBranchModel(
                branch_id=baseline.branch_id,
                run_id=baseline.run_id,
                display_name=display_name,
                status=status,
                read_only=int(runtime is None),
                forked_from_branch_id=baseline.selected_source_branch_id,
                forked_from_saved_revision_id=source.revision_id,
                saved_head_revision_id=revision_id,
                metadata_json="{}",
            ),
            BranchStateModel(
                branch_id=baseline.branch_id,
                run_id=baseline.run_id,
                status=status,
            ),
            BranchWorkingDraftModel(
                draft_id=draft_id,
                run_id=baseline.run_id,
                branch_id=baseline.branch_id,
                base_revision_id=revision_id,
                status=CLEAN_WORKING_DRAFT_STATUS,
                change_count=0,
                draft_version=0,
                changes_json="[]",
                draft_schema_version=SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION,
            ),
            row,
        ]
    )
    session.flush()
    # Audit comes last so an insertion failure exercises rollback of all rows.
    session.add(
        BranchRevisionAuditEventModel(
            audit_event_id=audit_event_id,
            run_id=baseline.run_id,
            branch_id=baseline.branch_id,
            saved_revision_id=revision_id,
            event_kind=EVENT_KIND,
            payload_json=canonical_json(receipt),
        )
    )
    session.flush()
    return repository._validated_saved_revision_in_session(session=session, model=row)
