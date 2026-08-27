"""Application service for branching a Run from a Saved Revision."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from beta_engine.domain.run_branches import normalize_branch_display_name
from beta_engine.infrastructure.db import (
    RunBranchRecord,
    SimulationPersistenceRepository,
)

EntityIdFactory = Callable[[str], str]


class BranchCreationIdentityError(ValueError):
    """Raised when an injected product identity factory returns an unusable id."""


def _validated_entity_id(value: str, *, kind: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BranchCreationIdentityError(f"{kind} id factory returned a blank id")
    normalized = value.strip()
    if len(normalized) > 128:
        raise BranchCreationIdentityError(
            f"{kind} id must contain at most 128 characters"
        )
    return normalized


@dataclass(slots=True)
class RunBranchCreationService:
    """Create an independent timeline without duplicating its shared past."""

    repository: SimulationPersistenceRepository
    id_factory: EntityIdFactory

    def create_from_saved_revision(
        self,
        *,
        run_id: str,
        source_branch_id: str,
        source_saved_revision_id: str,
        display_name: str | None = None,
    ) -> RunBranchRecord:
        normalized_name = (
            None
            if display_name is None
            else normalize_branch_display_name(display_name)
        )
        branch_id = _validated_entity_id(self.id_factory("branch"), kind="branch")
        working_draft_id = _validated_entity_id(
            self.id_factory("working-draft"), kind="working draft"
        )
        return self.repository.create_branch_from_saved_revision_atomically(
            run_id=run_id,
            source_branch_id=source_branch_id,
            source_revision_id=source_saved_revision_id,
            branch_id=branch_id,
            working_draft_id=working_draft_id,
            requested_display_name=normalized_name,
        )
