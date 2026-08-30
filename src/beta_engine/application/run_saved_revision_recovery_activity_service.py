"""Validated read-only recovery activity for one product Run Branch."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.domain.run_revisions import (
    BRANCH_RESTORE_AUDIT_EVENT_KIND,
    BRANCH_RESTORE_SAVED_REVISION_KIND,
    PRE_RESTORE_CHECKPOINT_KIND,
    SAVED_REVISION_AUDIT_EVENT_KIND,
    VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND,
    saved_viewer_branch_id,
)
from beta_engine.infrastructure.db import (
    BranchRevisionAuditEventRecord,
    BranchRevisionStateConflictError,
    BranchSavedRevisionCheckpointRecord,
    SavedRevisionHistoryConflictError,
    SavedRevisionHistoryNotFoundError,
    SavedRevisionRestoreConflictError,
    SimulationPersistenceRepository,
)


class RunSavedRevisionRecoveryActivityError(ValueError):
    """Base error for the Saved Revision recovery activity read model."""


class RunSavedRevisionRecoveryActivityNotFoundError(
    RunSavedRevisionRecoveryActivityError
):
    """Raised when the requested Run or Branch does not exist."""


class RunSavedRevisionRecoveryActivityConflictError(
    RunSavedRevisionRecoveryActivityError
):
    """Raised when recovery records are corrupt or mutually incoherent."""


@dataclass(frozen=True)
class RunSavedRevisionRecoveryActivity:
    run_id: str
    branch_id: str
    saved_head_revision_id: str
    safety_checkpoints: tuple[BranchSavedRevisionCheckpointRecord, ...]
    audit_events: tuple[BranchRevisionAuditEventRecord, ...]


def _conflict(message: str) -> RunSavedRevisionRecoveryActivityConflictError:
    return RunSavedRevisionRecoveryActivityConflictError(message)


@dataclass(slots=True)
class RunSavedRevisionRecoveryActivityService:
    """Expose only recovery records proven coherent with reachable history."""

    repository: SimulationPersistenceRepository

    def get_activity(
        self, *, run_id: str, branch_id: str
    ) -> RunSavedRevisionRecoveryActivity:
        try:
            history = self.repository.get_branch_saved_revision_history(
                run_id=run_id,
                branch_id=branch_id,
            )
        except SavedRevisionHistoryNotFoundError as exc:
            raise RunSavedRevisionRecoveryActivityNotFoundError(str(exc)) from exc
        except SavedRevisionHistoryConflictError as exc:
            raise _conflict(str(exc)) from exc

        try:
            checkpoints = tuple(
                self.repository.list_branch_saved_revision_checkpoints(
                    branch_id=branch_id
                )
            )
            audit_events = tuple(
                self.repository.list_branch_revision_audit_events(branch_id=branch_id)
            )
        except (
            BranchRevisionStateConflictError,
            SavedRevisionRestoreConflictError,
        ) as exc:
            raise _conflict(str(exc)) from exc

        revision_by_id = {
            revision.revision_id: revision for revision in history.saved_revisions
        }
        reachable_revision_sequences = {
            revision.revision_id: revision.sequence
            for revision in history.saved_revisions
        }
        reachable_revision_ids = reachable_revision_sequences.keys()
        checkpoint_by_id: dict[str, BranchSavedRevisionCheckpointRecord] = {}

        for checkpoint in checkpoints:
            if checkpoint.run_id != run_id or checkpoint.branch_id != branch_id:
                raise _conflict(
                    f"restore checkpoint {checkpoint.checkpoint_id!r} has mismatched "
                    "Run or Branch ownership"
                )
            if checkpoint.kind != PRE_RESTORE_CHECKPOINT_KIND:
                raise _conflict(
                    f"restore checkpoint {checkpoint.checkpoint_id!r} has unsupported "
                    f"kind {checkpoint.kind!r}"
                )
            if checkpoint.checkpoint_id in checkpoint_by_id:
                raise _conflict(
                    f"restore checkpoint {checkpoint.checkpoint_id!r} is duplicated"
                )
            for label, revision_id in (
                ("pre-restore head", checkpoint.saved_revision_id),
                ("restore target", checkpoint.target_saved_revision_id),
                ("restore result", checkpoint.restore_saved_revision_id),
            ):
                if revision_id not in reachable_revision_ids:
                    raise _conflict(
                        f"restore checkpoint {checkpoint.checkpoint_id!r} refers to "
                        f"an unreachable {label} Saved Revision {revision_id!r}"
                    )
            checkpoint_by_id[checkpoint.checkpoint_id] = checkpoint

        restore_audit_by_checkpoint_id: dict[str, BranchRevisionAuditEventRecord] = {}
        for audit_event in audit_events:
            if audit_event.run_id != run_id or audit_event.branch_id != branch_id:
                raise _conflict(
                    f"audit event {audit_event.audit_event_id!r} has mismatched Run "
                    "or Branch ownership"
                )
            if audit_event.saved_revision_id not in reachable_revision_ids:
                raise _conflict(
                    f"audit event {audit_event.audit_event_id!r} refers to unreachable "
                    f"Saved Revision {audit_event.saved_revision_id!r}"
                )
            audit_revision = revision_by_id[audit_event.saved_revision_id]
            if audit_revision.branch_id != branch_id:
                raise _conflict(
                    f"audit event {audit_event.audit_event_id!r} points to a Saved "
                    "Revision not owned by its Branch"
                )
            if not audit_event.event_kind.strip():
                raise _conflict(
                    f"audit event {audit_event.audit_event_id!r} has a blank kind"
                )
            if audit_event.event_kind == SAVED_REVISION_AUDIT_EVENT_KIND:
                if audit_revision.kind != VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND:
                    raise _conflict(
                        f"save audit event {audit_event.audit_event_id!r} points to "
                        "an incompatible Saved Revision kind"
                    )
                try:
                    saved_viewer_branch = saved_viewer_branch_id(audit_revision.payload)
                except ValueError as exc:  # pragma: no cover - history validates this
                    raise _conflict(str(exc)) from exc
                expected_save_payload = {
                    "base_saved_revision_id": audit_revision.parent_revision_id,
                    "viewer_branch_id": saved_viewer_branch,
                }
                for field, expected in expected_save_payload.items():
                    if audit_event.payload.get(field) != expected:
                        raise _conflict(
                            f"save audit event {audit_event.audit_event_id!r} does "
                            f"not match Saved Revision field {field!r}"
                        )
                saved_draft_version = audit_event.payload.get("saved_draft_version")
                if (
                    isinstance(saved_draft_version, bool)
                    or not isinstance(saved_draft_version, int)
                    or saved_draft_version < 0
                ):
                    raise _conflict(
                        f"save audit event {audit_event.audit_event_id!r} has an "
                        "invalid saved Draft version"
                    )
                draft_id = audit_event.payload.get("draft_id")
                if not isinstance(draft_id, str) or not draft_id.strip():
                    raise _conflict(
                        f"save audit event {audit_event.audit_event_id!r} has no "
                        "Draft identity"
                    )
                continue
            if audit_event.event_kind != BRANCH_RESTORE_AUDIT_EVENT_KIND:
                continue

            checkpoint_id = audit_event.payload.get("checkpoint_id")
            if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
                raise _conflict(
                    f"restore audit event {audit_event.audit_event_id!r} has no "
                    "checkpoint identity"
                )
            checkpoint = checkpoint_by_id.get(checkpoint_id)
            if checkpoint is None:
                raise _conflict(
                    f"restore audit event {audit_event.audit_event_id!r} refers to "
                    f"unknown checkpoint {checkpoint_id!r}"
                )
            if checkpoint_id in restore_audit_by_checkpoint_id:
                raise _conflict(
                    f"restore checkpoint {checkpoint_id!r} has more than one audit event"
                )
            expected_payload = {
                "checkpoint_id": checkpoint.checkpoint_id,
                "previous_saved_head_revision_id": checkpoint.saved_revision_id,
                "target_saved_revision_id": checkpoint.target_saved_revision_id,
                "previous_viewer_branch_id": checkpoint.viewer_branch_id,
                "draft_id": checkpoint.draft_id,
                "previous_draft_version": checkpoint.draft_version,
                "draft_version": checkpoint.draft_version + 1,
                "explicit_confirmation": True,
            }
            for field, expected in expected_payload.items():
                if audit_event.payload.get(field) != expected:
                    raise _conflict(
                        f"restore audit event {audit_event.audit_event_id!r} does not "
                        f"match checkpoint {checkpoint_id!r} field {field!r}"
                    )
            if audit_event.saved_revision_id != checkpoint.restore_saved_revision_id:
                raise _conflict(
                    f"restore audit event {audit_event.audit_event_id!r} does not "
                    f"point to checkpoint {checkpoint_id!r} restore revision"
                )
            if (
                audit_revision.kind != BRANCH_RESTORE_SAVED_REVISION_KIND
                or audit_revision.parent_revision_id != checkpoint.saved_revision_id
            ):
                raise _conflict(
                    f"restore audit event {audit_event.audit_event_id!r} points to "
                    f"an incompatible restore revision for checkpoint {checkpoint_id!r}"
                )
            try:
                target_viewer_branch_id = saved_viewer_branch_id(
                    revision_by_id[checkpoint.target_saved_revision_id].payload
                )
                restored_viewer_branch_id = saved_viewer_branch_id(
                    audit_revision.payload
                )
            except ValueError as exc:  # pragma: no cover - history validates this
                raise _conflict(str(exc)) from exc
            if (
                restored_viewer_branch_id != target_viewer_branch_id
                or audit_event.payload.get("viewer_branch_id")
                != restored_viewer_branch_id
            ):
                raise _conflict(
                    f"restore audit event {audit_event.audit_event_id!r} has an "
                    "incoherent restored Viewer Branch"
                )
            restore_audit_by_checkpoint_id[checkpoint_id] = audit_event

        missing_audit_checkpoint_ids = (
            checkpoint_by_id.keys() - restore_audit_by_checkpoint_id.keys()
        )
        if missing_audit_checkpoint_ids:
            checkpoint_id = min(missing_audit_checkpoint_ids)
            raise _conflict(
                f"restore checkpoint {checkpoint_id!r} has no matching audit event"
            )

        ordered_checkpoints = tuple(
            sorted(
                checkpoints,
                key=lambda checkpoint: (
                    reachable_revision_sequences[checkpoint.restore_saved_revision_id],
                    checkpoint.created_at or "",
                    checkpoint.checkpoint_id,
                ),
            )
        )
        ordered_audit_events = tuple(
            sorted(
                audit_events,
                key=lambda audit_event: (
                    reachable_revision_sequences[audit_event.saved_revision_id],
                    audit_event.created_at or "",
                    audit_event.audit_event_id,
                ),
            )
        )
        return RunSavedRevisionRecoveryActivity(
            run_id=history.run_id,
            branch_id=history.branch_id,
            saved_head_revision_id=history.saved_head_revision_id,
            safety_checkpoints=ordered_checkpoints,
            audit_events=ordered_audit_events,
        )
