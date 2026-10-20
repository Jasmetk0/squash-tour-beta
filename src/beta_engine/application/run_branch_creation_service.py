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

    def preview(
        self, *, run_id, source_branch_id, source_saved_revision_id, display_name=None
    ):
        from beta_engine.infrastructure.db.saved_revision_branch_review import (
            review_in_session,
        )

        name = (
            None
            if display_name is None
            else normalize_branch_display_name(display_name)
        )
        with self.repository._session_factory() as session:
            # One consistent SQLite snapshot for lineage, Viewer and naming.
            from sqlalchemy import text

            session.execute(text("BEGIN"))
            return review_in_session(
                self.repository,
                session,
                run_id=run_id,
                source_branch_id=source_branch_id,
                source_revision_id=source_saved_revision_id,
                display_name=name,
            )

    def create_from_saved_revision(
        self,
        *,
        run_id: str,
        source_branch_id: str,
        source_saved_revision_id: str,
        display_name: str | None = None,
        review: dict | None = None,
    ) -> RunBranchRecord:
        normalized_name = (
            None
            if display_name is None
            else normalize_branch_display_name(display_name)
        )
        if review is not None:
            existing = self.repository.get_reviewed_branch_creation_result(
                run_id=run_id,
                source_branch_id=source_branch_id,
                source_revision_id=source_saved_revision_id,
                display_name=normalized_name,
                review=review,
            )
            if existing is not None:
                return existing
        branch_id = _validated_entity_id(self.id_factory("branch"), kind="branch")
        working_draft_id = _validated_entity_id(
            self.id_factory("working-draft"), kind="working draft"
        )
        materialized_fork_revision_id = None
        if self.repository.saved_revision_requires_materialized_fork_root(
            run_id=run_id,
            source_branch_id=source_branch_id,
            source_revision_id=source_saved_revision_id,
        ):
            materialized_fork_revision_id = _validated_entity_id(
                self.id_factory("saved-revision"),
                kind="materialized fork saved revision",
            )
        return self.repository.create_branch_from_saved_revision_atomically(
            run_id=run_id,
            source_branch_id=source_branch_id,
            source_revision_id=source_saved_revision_id,
            branch_id=branch_id,
            working_draft_id=working_draft_id,
            requested_display_name=normalized_name,
            materialized_fork_revision_id=materialized_fork_revision_id,
            review=review,
        )
