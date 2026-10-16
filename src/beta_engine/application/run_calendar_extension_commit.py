"""Reviewed, explicitly confirmed, atomic Save of one Run horizon for all Branches.

This changes the current Run time envelope, not a single historical record or
a Full Simulation task. Every Branch gets a new, hash-signed, parent-linked Saved
Revision; old Saved Revision bytes remain unchanged. No sporting work is started.
"""

from __future__ import annotations

import hashlib
import json
import time
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    CONTENT_HASH_ALGORITHM,
    RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
    RUN_WORKING_DRAFT_SCHEMA_VERSION,
    canonical_json,
    saved_revision_content_hash,
    viewer_branch_saved_revision_payload,
)
from beta_engine.infrastructure.db.models import (
    BranchRevisionAuditEventModel,
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    AuthoritativeSimulationCommandModel,
    FullSimulationExecutionLeaseModel,
    FullSimulationTaskModel,
    RunBranchModel,
    RunCalendarExtensionReceiptModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.saved_revision_restore_coverage import (
    active_transient_restore_blockers,
    missing_component_coverage,
    missing_run_scoped_reference_coverage,
)

EXTENSION_KIND = "run_calendar_horizon_extension"
EXTENSION_AUDIT_KIND = "run_calendar_horizon_extended"
REVIEW_SCHEMA = "run_calendar_extension_review.v1"
RECEIPT_SCHEMA = "run_calendar_extension_save.v1"


def _fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _json_object(raw: str, label: str) -> dict:
    try:
        item = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} has malformed JSON") from exc
    if not isinstance(item, dict):
        raise ValueError(f"{label} must be a JSON object")
    return item


def _capture_live_content(session: Session, *, payload: dict, run_id: str, branch_id: str) -> dict:
    # Use exactly the established normal Save capture adapters; do not create
    # an independent incomplete list of component fingerprints.
    from beta_engine.infrastructure.db import repositories as storage

    # Capture into a genuinely empty content container. Starting with
    # deepcopy(saved_payload) would leave *deleted* live components present
    # in the snapshot when their capture adapter returns without a write.
    # A formerly Saved component missing from live state must block Save.
    copy = {"content": {}}
    for capture in (
        storage.capture_saved_ranking_component,
        storage.capture_saved_initial_world,
        storage.capture_saved_run_package_state,
        storage.capture_saved_run_tournament_lab_drafts,
        storage.capture_saved_lifecycle,
        storage.capture_saved_health,
        storage.capture_saved_run_entry_decision_slots,
        storage.capture_saved_application_validation_slots,
        storage.capture_saved_application_submissions,
        storage.capture_saved_definitive_wild_card_assignments,
        storage.capture_saved_tour_entry_triggers,
        storage.capture_saved_sporting,
        storage.capture_saved_simulation_slots,
    ):
        capture(session, copy, run_id=run_id, branch_id=branch_id)
    storage.capture_saved_run_prospect_source(session, copy, run_id=run_id)
    return copy["content"]


def review_run_calendar_extension(
    session: Session, repository, *, run_id: str, new_season_count: int
) -> dict:
    """One coherent read snapshot. The caller opens BEGIN (or BEGIN IMMEDIATE)."""
    run = session.get(RunContainerModel, run_id)
    if run is None:
        raise ValueError("Run not found")
    if run.storage_kind != "custom_local" or run.read_only:
        raise ValueError("Run must be an editable custom Run")

    metadata = _json_object(run.metadata_json, "Run metadata")
    if "run_calendar" not in metadata:
        raise ValueError("Legacy Run calendar requires migration before extension")
    current = RunCalendar.from_metadata(metadata["run_calendar"])
    proposed = current.extend_to(new_season_count)
    if (run.timeline_start_season, run.timeline_end_season) != (
        current.start_year, current.start_year + current.season_count - 1
    ):
        raise ValueError("Run timeline columns conflict with the Saved calendar")

    branches = session.scalars(
        select(RunBranchModel).where(RunBranchModel.run_id == run_id)
        .order_by(RunBranchModel.branch_id)
    ).all()
    if not branches:
        raise ValueError("Run has no Branches")

    all_blockers: set[str] = set()
    cohort = []
    source = []
    for branch in branches:
        blockers: list[str] = []
        head = None
        draft = None
        try:
            # Validate complete old lineage, including shared pre-fork ancestors.
            repository._validated_branch_revision_lineage_in_session(
                session=session, branch=branch
            )
            state = repository._validated_branch_revision_state_in_session(
                session=session, branch=branch
            )
            head = state.saved_revision
            draft = state.working_draft
            if resolve_saved_run_calendar(
                session, run_id=run_id, branch_id=branch.branch_id
            ) != current:
                blockers.append("branch_calendar_mismatch")
        except (ValueError, TypeError) as exc:
            blockers.append("saved_branch_integrity: " + str(exc))

        if branch.read_only or branch.status != "active":
            blockers.append("branch_not_writable_or_active")
        if branch.legacy_simulation_run_id or branch.head_checkpoint_id:
            blockers.append("legacy_or_checkpoint_branch_requires_migration")

        if draft is None:
            blockers.append("working_draft_unavailable")
        elif (
            draft.status != CLEAN_WORKING_DRAFT_STATUS
            or draft.change_count != 0
            or draft.changes != []
            or draft.base_revision_id != branch.saved_head_revision_id
        ):
            blockers.append("save_or_discard_branch_working_draft")
        if head is not None:
            saved_content = head.payload.get("content")
            if not isinstance(saved_content, dict):
                blockers.append("saved_content_invalid")
            else:
                if missing_component_coverage(
                    session, run_id=run_id, branch_id=branch.branch_id,
                    saved_content=saved_content,
                ):
                    blockers.append("unsaved_branch_components")
                if missing_run_scoped_reference_coverage(
                    session, run_id=run_id, saved_content=saved_content,
                ):
                    blockers.append("unsaved_run_reference_components")
                if active_transient_restore_blockers(
                    session, run_id=run_id, branch_id=branch.branch_id,
                ):
                    blockers.append("unfinished_transient_authoring")
                if not blockers:
                    try:
                        captured = _capture_live_content(
                            session, payload=head.payload, run_id=run_id,
                            branch_id=branch.branch_id,
                        )
                        # Some existing normal-Save adapters synthesize a
                        # canonical *empty* component on capture even when the
                        # original Saved head intentionally omitted it.
                        # Missing live rows are checked independently by the
                        # complete component-coverage registry above. Compare
                        # every previously Saved component exactly, without
                        # treating synthesized no-op defaults as user edits.
                        if any(
                            captured.get(key) != value
                            for key, value in saved_content.items()
                        ):
                            blockers.append("unsaved_live_state_differs_from_saved_head")
                    except (TypeError, ValueError) as exc:
                        blockers.append("live_component_integrity: " + str(exc))

        all_blockers.update(blockers)
        cohort.append({
            "branch_id": branch.branch_id,
            "display_name": branch.display_name,
            "saved_head_revision_id": branch.saved_head_revision_id,
            "saved_head_content_hash": head.content_hash if head else None,
            "draft_version": draft.draft_version if draft else None,
            "blockers": blockers,
        })
        source.append({
            "branch_id": branch.branch_id,
            "display_name": branch.display_name,
            "status": branch.status,
            "read_only": branch.read_only,
            "metadata_json": branch.metadata_json,
            "saved_head_revision_id": branch.saved_head_revision_id,
            "head_hash": head.content_hash if head else None,
            "head_sequence": head.sequence if head else None,
            "draft_id": draft.draft_id if draft else None,
            "draft_base": draft.base_revision_id if draft else None,
            "draft_version": draft.draft_version if draft else None,
            "draft_status": draft.status if draft else None,
            "draft_changes": draft.changes if draft else None,
        })

    from beta_engine.application.full_simulation_tasks import _read as read_task, TERMINAL

    frozen_tasks = []
    for task in session.scalars(
        select(FullSimulationTaskModel).where(FullSimulationTaskModel.run_id == run_id)
        .order_by(FullSimulationTaskModel.task_id)
    ):
        try:
            task_data = read_task(task)
            task_state = task_data["state"]
        except (ValueError, KeyError, TypeError):
            task_state = "corrupt"
        frozen_tasks.append({
            "task_id": task.task_id,
            "payload_fingerprint": task.payload_fingerprint,
            "state": task_state,
        })
        if task_state not in TERMINAL:
            all_blockers.add("nonterminal_full_simulation_task")

    # Durable legacy simulation commands can still own a pending frozen
    # target without a server FullSimulationTaskModel. Those must not be
    # reinterpreted by extending their Run while they remain pending.
    pending_commands = session.scalars(
        select(AuthoritativeSimulationCommandModel).where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.status == "pending",
        ).order_by(
            AuthoritativeSimulationCommandModel.branch_id,
            AuthoritativeSimulationCommandModel.command_id,
        )
    ).all()
    if pending_commands:
        all_blockers.add("pending_authoritative_simulation_command")
    pending_command_evidence = [
        {
            "branch_id": item.branch_id,
            "command_id": item.command_id,
            "request_fingerprint": item.request_fingerprint,
            "result_fingerprint": hashlib.sha256(
                item.result_json.encode("utf-8")
            ).hexdigest(),
        }
        for item in pending_commands
    ]

    lease = session.scalars(select(FullSimulationExecutionLeaseModel)).all()
    live_leases = [
        {"run_id": x.run_id, "branch_id": x.branch_id,
         "owner_token": x.owner_token, "expires_at": x.expires_at_unix}
        for x in lease if x.expires_at_unix > int(time.time())
    ]
    if any(x["run_id"] == run_id for x in live_leases):
        all_blockers.add("active_full_simulation_invocation")

    envelope = {
        "run_id": run_id,
        "run_metadata": metadata,
        "run_status": run.status,
        "run_viewer": run.official_branch_id,
        "run_world_id": run.world_id,
        "run_world_package_fingerprint": run.world_package_fingerprint,
        "run_config_version": run.config_version,
        "run_config_fingerprint": run.config_fingerprint,
        "run_global_seed": run.global_seed,
        "start": run.timeline_start_season,
        "end": run.timeline_end_season,
        "new_season_count": new_season_count,
        "branches": source,
        "frozen_tasks": frozen_tasks,
        "pending_commands": pending_command_evidence,
        "active_leases": [x for x in live_leases if x["run_id"] == run_id],
    }
    return {
        "schema_version": REVIEW_SCHEMA,
        "run_id": run_id,
        "read_only": True,
        "save_performed": False,
        "simulation_started": False,
        "review_fingerprint": _fingerprint(envelope),
        "can_save": not all_blockers,
        "blockers": sorted(all_blockers),
        "branch_count": len(cohort),
        "branches": cohort,
        "original_calendar": current.to_metadata(),
        "proposed_calendar": proposed.to_metadata(),
        "added_seasons": proposed.season_count - current.season_count,
        "added_weeks": (proposed.season_count - current.season_count) * current.weeks_per_year,
        "frozen_task_count": len(frozen_tasks),
        "pending_authoritative_command_count": len(pending_commands),
        "sporting_execution_unlocked": False,
    }


def save_run_calendar_extension(
    repository, *, run_id: str, command_id: str, new_season_count: int,
    review_fingerprint: str, explicit_confirmation: bool,
) -> dict:
    """Idempotent all-Branch Save, serialized with all SQLite product writers."""
    if not explicit_confirmation:
        raise ValueError("Explicit confirmation and Save are required")
    if not isinstance(command_id, str) or not command_id.strip() or (
        command_id != command_id.strip() or len(command_id) > 128
    ):
        raise ValueError("command_id must be a nonblank identifier up to 128 characters")
    if not isinstance(review_fingerprint, str) or len(review_fingerprint) != 64:
        raise ValueError("An exact reviewed fingerprint is required")
    request_fingerprint = _fingerprint({
        "run_id": run_id, "command_id": command_id,
        "new_season_count": new_season_count,
        "review_fingerprint": review_fingerprint,
        "explicit_confirmation": True,
    })

    with repository._session_factory.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        receipt = session.get(RunCalendarExtensionReceiptModel, (run_id, command_id))
        if receipt is not None:
            if receipt.request_fingerprint != request_fingerprint:
                raise ValueError("The command identity was already used for a different request")
            # Response-loss retry: no new Save, versions, or history.
            return _json_object(receipt.result_json, "Run extension receipt")

        review = review_run_calendar_extension(
            session, repository, run_id=run_id, new_season_count=new_season_count
        )
        if not review["can_save"]:
            raise ValueError(
                "Run horizon Save is blocked: " + ", ".join(review["blockers"])
            )
        if review["review_fingerprint"] != review_fingerprint:
            raise ValueError(
                "Run/Branch state changed since review; inspect all Branches again"
            )

        run = session.get(RunContainerModel, run_id)
        proposed = review["proposed_calendar"]
        old_calendar = review["original_calendar"]
        metadata = _json_object(run.metadata_json, "Run metadata")
        metadata["run_calendar"] = proposed
        # Freeze all verified source Branch states BEFORE changing any HEAD:
        # a shared-history fork validates its ancestor Branch's current HEAD,
        # so validating branch B after changing ancestor A would read a mixed
        # in-transaction cohort. No partial cohort may influence later checks.
        prepared_states = {
            item["branch_id"]: repository._validated_branch_revision_state_in_session(
                session=session,
                branch=session.get(RunBranchModel, item["branch_id"]),
            )
            for item in review["branches"]
        }
        updated_heads = []
        for source in review["branches"]:
            branch_id = source["branch_id"]
            branch = session.get(RunBranchModel, branch_id)
            state = prepared_states[branch_id]
            old = state.saved_revision
            draft = session.get(BranchWorkingDraftModel, state.working_draft.draft_id)
            new_revision_id = str(uuid5(
                NAMESPACE_URL, f"squash-engine:{run_id}:{command_id}:{branch_id}:calendar-revision"
            ))
            audit_event_id = str(uuid5(
                NAMESPACE_URL, f"squash-engine:{run_id}:{command_id}:{branch_id}:calendar-audit"
            ))
            payload = viewer_branch_saved_revision_payload(
                base_payload=old.payload, run_id=run_id,
                display_name=run.display_name or run_id,
                run_status=run.status,
                timeline_start_season=run.timeline_start_season,
                timeline_end_season=proposed["start_year"] + proposed["season_count"] - 1,
                branch_id=branch_id, branch_display_name=branch.display_name,
                branch_status=branch.status,
                forked_from_branch_id=branch.forked_from_branch_id,
                forked_from_saved_revision_id=branch.forked_from_saved_revision_id,
                viewer_branch_id=run.official_branch_id,
            )
            payload["run"]["run_calendar"] = proposed
            # Preserve the original population clock as explicit provenance,
            # not as a claim that existing players have been regenerated.
            old_run_snapshot = old.payload["run"]
            previous_population_basis = old_run_snapshot.get(
                "run_calendar_content_origin", old_run_snapshot.get("run_calendar")
            )
            initial_world = old.payload.get("content", {}).get("initial_world")
            if (
                isinstance(initial_world, dict)
                and initial_world.get("state", {}).get("schema_version") == "initial_world_state.v2"
            ):
                payload["run"]["run_calendar_content_origin"] = previous_population_basis
            summary = {
                "kind": EXTENSION_KIND,
                "summary": "Explicitly saved Run horizon extension across all Branches",
                "command_id": command_id,
                "review_fingerprint": review_fingerprint,
                "before_calendar": old_calendar,
                "after_calendar": proposed,
                "affected_branches": review["branch_count"],
            }
            sequence = old.sequence + 1
            revision_hash = saved_revision_content_hash(
                revision_id=new_revision_id, run_id=run_id, branch_id=branch_id,
                sequence=sequence, parent_revision_id=old.revision_id,
                kind=EXTENSION_KIND,
                payload_schema_version=RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
                payload=payload, change_summary=summary,
            )
            session.add(BranchSavedRevisionModel(
                revision_id=new_revision_id, run_id=run_id, branch_id=branch_id,
                sequence=sequence, parent_revision_id=old.revision_id,
                kind=EXTENSION_KIND,
                payload_schema_version=RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
                content_hash_algorithm=CONTENT_HASH_ALGORITHM,
                content_hash=revision_hash,
                payload_json=canonical_json(payload),
                change_summary_json=canonical_json(summary),
            ))
            session.add(BranchRevisionAuditEventModel(
                audit_event_id=audit_event_id, run_id=run_id, branch_id=branch_id,
                saved_revision_id=new_revision_id, event_kind=EXTENSION_AUDIT_KIND,
                payload_json=canonical_json({
                    "command_id": command_id, "review_fingerprint": review_fingerprint,
                    "previous_saved_head_revision_id": old.revision_id,
                    "previous_saved_head_content_hash": old.content_hash,
                    "new_saved_revision_id": new_revision_id,
                    "new_saved_revision_content_hash": revision_hash,
                    "explicit_confirmation": True, "manual_save": True,
                }),
            ))
            branch.saved_head_revision_id = new_revision_id
            draft.base_revision_id = new_revision_id
            draft.status = CLEAN_WORKING_DRAFT_STATUS
            draft.change_count = 0
            draft.draft_version += 1
            draft.draft_schema_version = RUN_WORKING_DRAFT_SCHEMA_VERSION
            draft.changes_json = "[]"
            updated_heads.append({
                "branch_id": branch_id,
                "previous_saved_head_revision_id": old.revision_id,
                "saved_revision_id": new_revision_id,
                "saved_revision_content_hash": revision_hash,
                "audit_event_id": audit_event_id,
                "draft_version": draft.draft_version,
            })

        run.timeline_end_season = proposed["start_year"] + proposed["season_count"] - 1
        run.metadata_json = canonical_json(metadata)
        result = {
            "schema_version": RECEIPT_SCHEMA,
            "run_id": run_id,
            "command_id": command_id,
            "review_fingerprint": review_fingerprint,
            "saved": True,
            "simulation_started": False,
            "sporting_execution_unlocked": False,
            "previous_calendar": old_calendar,
            "current_calendar": proposed,
            "branch_count": len(updated_heads),
            "branches": updated_heads,
        }
        session.add(RunCalendarExtensionReceiptModel(
            run_id=run_id, command_id=command_id,
            request_fingerprint=request_fingerprint,
            result_json=canonical_json(result),
        ))
        session.flush()
        # All the above rows, including receipt, roll back on any exception.
    return result
