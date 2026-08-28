"""Application boundary for manual product Working Draft saves."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from beta_engine.infrastructure.db import (
    SimulationPersistenceRepository,
    ViewerBranchSaveResult,
    ViewerBranchWorkingDraftRecord,
)

EntityIdFactory = Callable[[str], str]


class WorkingDraftIdentityError(ValueError):
    """Raised when an injected identity factory returns an unusable id."""


def _validated_entity_id(value: str, *, kind: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkingDraftIdentityError(f"{kind} id factory returned a blank id")
    normalized = value.strip()
    if len(normalized) > 128:
        raise WorkingDraftIdentityError(
            f"{kind} id must contain at most 128 characters"
        )
    return normalized


@dataclass(slots=True)
class RunWorkingDraftService:
    """Stage one logical change and commit the complete Save boundary."""

    repository: SimulationPersistenceRepository
    id_factory: EntityIdFactory

    def get_viewer_branch_draft(
        self, *, run_id: str, branch_id: str
    ) -> ViewerBranchWorkingDraftRecord:
        return self.repository.get_viewer_branch_working_draft(
            run_id=run_id, branch_id=branch_id
        )

    def stage_viewer_branch(
        self,
        *,
        run_id: str,
        branch_id: str,
        viewer_branch_id: str,
        expected_draft_version: int,
    ) -> ViewerBranchWorkingDraftRecord:
        return self.repository.stage_viewer_branch_selection(
            run_id=run_id,
            branch_id=branch_id,
            viewer_branch_id=viewer_branch_id,
            expected_draft_version=expected_draft_version,
        )

    def save(
        self,
        *,
        run_id: str,
        branch_id: str,
        expected_draft_version: int,
    ) -> ViewerBranchSaveResult:
        revision_id = _validated_entity_id(
            self.id_factory("saved-revision"), kind="saved revision"
        )
        audit_event_id = _validated_entity_id(
            self.id_factory("revision-audit-event"), kind="revision audit event"
        )
        return self.repository.save_viewer_branch_selection_atomically(
            run_id=run_id,
            branch_id=branch_id,
            expected_draft_version=expected_draft_version,
            revision_id=revision_id,
            audit_event_id=audit_event_id,
        )
