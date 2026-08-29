"""Read-only application boundary for product Saved Revision history."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.infrastructure.db import (
    BranchSavedRevisionHistoryRecord,
    BranchSavedRevisionRecord,
    SavedRevisionHistoryNotFoundError,
    SimulationPersistenceRepository,
)


@dataclass(frozen=True)
class RunSavedRevisionDetail:
    run_id: str
    branch_id: str
    saved_head_revision_id: str
    saved_revision: BranchSavedRevisionRecord


@dataclass(slots=True)
class RunSavedRevisionHistoryService:
    """Expose validated Branch history without mutating any product state."""

    repository: SimulationPersistenceRepository

    def list_history(
        self, *, run_id: str, branch_id: str
    ) -> BranchSavedRevisionHistoryRecord:
        return self.repository.get_branch_saved_revision_history(
            run_id=run_id,
            branch_id=branch_id,
        )

    def get_revision(
        self, *, run_id: str, branch_id: str, revision_id: str
    ) -> RunSavedRevisionDetail:
        history = self.repository.get_branch_saved_revision_history(
            run_id=run_id,
            branch_id=branch_id,
        )
        revision = next(
            (
                candidate
                for candidate in history.saved_revisions
                if candidate.revision_id == revision_id
            ),
            None,
        )
        if revision is None:
            raise SavedRevisionHistoryNotFoundError(
                f"Saved Revision {revision_id!r} was not found in Branch "
                f"{branch_id!r} history"
            )
        return RunSavedRevisionDetail(
            run_id=history.run_id,
            branch_id=history.branch_id,
            saved_head_revision_id=history.saved_head_revision_id,
            saved_revision=revision,
        )
