"""Application boundary for confirmed current-Branch Saved Revision restore."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from beta_engine.infrastructure.db import (
    BranchSavedRevisionRestoreResult,
    SavedRevisionRestoreConflictError,
    SimulationPersistenceRepository,
)

EntityIdFactory = Callable[[str], str]


class SavedRevisionRestoreIdentityError(ValueError):
    """Raised when an injected identity factory returns an unusable id."""


def _validated_entity_id(value: str, *, kind: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SavedRevisionRestoreIdentityError(
            f"{kind} id factory returned a blank id"
        )
    normalized = value.strip()
    if len(normalized) > 128:
        raise SavedRevisionRestoreIdentityError(
            f"{kind} id must contain at most 128 characters"
        )
    return normalized


@dataclass(slots=True)
class RunSavedRevisionRestoreService:
    """Require explicit confirmation before entering the atomic restore boundary."""

    repository: SimulationPersistenceRepository
    id_factory: EntityIdFactory

    def restore_current_branch(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_saved_revision_id: str,
        expected_head_saved_revision_id: str,
        expected_draft_version: int,
        expected_current_viewer_branch_id: str,
        explicit_confirmation: bool,
    ) -> BranchSavedRevisionRestoreResult:
        if not explicit_confirmation:
            raise SavedRevisionRestoreConflictError(
                "Saved Revision restore requires explicit confirmation"
            )
        checkpoint_id = _validated_entity_id(
            self.id_factory("saved-revision-checkpoint"),
            kind="saved revision checkpoint",
        )
        restore_saved_revision_id = _validated_entity_id(
            self.id_factory("saved-revision"), kind="saved revision"
        )
        audit_event_id = _validated_entity_id(
            self.id_factory("revision-audit-event"), kind="revision audit event"
        )
        return self.repository.restore_branch_saved_revision_atomically(
            run_id=run_id,
            branch_id=branch_id,
            target_saved_revision_id=target_saved_revision_id,
            expected_head_saved_revision_id=expected_head_saved_revision_id,
            expected_draft_version=expected_draft_version,
            expected_current_viewer_branch_id=expected_current_viewer_branch_id,
            checkpoint_id=checkpoint_id,
            restore_saved_revision_id=restore_saved_revision_id,
            audit_event_id=audit_event_id,
        )
