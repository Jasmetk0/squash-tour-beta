"""Read-only application boundary for product Saved Revision history."""

from __future__ import annotations

import hashlib
import json
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


@dataclass(frozen=True)
class RunSavedRevisionHistoryPage:
    run_id: str
    branch_id: str
    saved_head_revision_id: str
    saved_revisions: tuple[BranchSavedRevisionRecord, ...]
    total_count: int
    has_more_older: bool
    next_before_sequence: int | None


@dataclass(frozen=True)
class SavedRevisionComponentComparison:
    component_key: str
    status: str
    before_fingerprint: str | None
    after_fingerprint: str | None


@dataclass(frozen=True)
class RunSavedRevisionComparison:
    run_id: str
    branch_id: str
    saved_head_revision_id: str
    from_revision: BranchSavedRevisionRecord
    to_revision: BranchSavedRevisionRecord
    run_changes: dict[str, dict[str, object | None]]
    branch_changes: dict[str, dict[str, object | None]]
    components: tuple[SavedRevisionComponentComparison, ...]


def _json_fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _dict_field_changes(
    before: object,
    after: object,
) -> dict[str, dict[str, object | None]]:
    before_dict = before if isinstance(before, dict) else {}
    after_dict = after if isinstance(after, dict) else {}
    changes: dict[str, dict[str, object | None]] = {}
    for key in sorted(set(before_dict) | set(after_dict)):
        before_value = before_dict.get(key)
        after_value = after_dict.get(key)
        if before_value != after_value:
            changes[key] = {
                "before": before_value,
                "after": after_value,
            }
    return changes


@dataclass(slots=True)
class RunSavedRevisionHistoryService:
    """Expose validated Branch history without mutating any product state."""

    repository: SimulationPersistenceRepository

    def list_history(
        self,
        *,
        run_id: str,
        branch_id: str,
        limit: int | None = None,
        before_sequence: int | None = None,
    ) -> BranchSavedRevisionHistoryRecord | RunSavedRevisionHistoryPage:
        history = self.repository.get_branch_saved_revision_history(
            run_id=run_id,
            branch_id=branch_id,
        )
        if limit is None and before_sequence is None:
            return history
        if limit is None:
            limit = 50
        if limit < 1 or limit > 200:
            raise ValueError("Saved Revision history limit must be between 1 and 200")
        candidates = tuple(
            revision
            for revision in history.saved_revisions
            if before_sequence is None or revision.sequence < before_sequence
        )
        page = candidates[-limit:]
        has_more_older = len(candidates) > len(page)
        next_before_sequence = page[0].sequence if has_more_older and page else None
        return RunSavedRevisionHistoryPage(
            run_id=history.run_id,
            branch_id=history.branch_id,
            saved_head_revision_id=history.saved_head_revision_id,
            saved_revisions=page,
            total_count=len(history.saved_revisions),
            has_more_older=has_more_older,
            next_before_sequence=next_before_sequence,
        )

    def get_revision(
        self, *, run_id: str, branch_id: str, revision_id: str
    ) -> RunSavedRevisionDetail:
        history = self.repository.get_branch_saved_revision_history(
            run_id=run_id,
            branch_id=branch_id,
        )
        revision = self._find_revision(
            history=history,
            branch_id=branch_id,
            revision_id=revision_id,
        )
        return RunSavedRevisionDetail(
            run_id=history.run_id,
            branch_id=history.branch_id,
            saved_head_revision_id=history.saved_head_revision_id,
            saved_revision=revision,
        )

    def compare_revisions(
        self,
        *,
        run_id: str,
        branch_id: str,
        from_revision_id: str,
        to_revision_id: str,
    ) -> RunSavedRevisionComparison:
        history = self.repository.get_branch_saved_revision_history(
            run_id=run_id,
            branch_id=branch_id,
        )
        before = self._find_revision(
            history=history,
            branch_id=branch_id,
            revision_id=from_revision_id,
        )
        after = self._find_revision(
            history=history,
            branch_id=branch_id,
            revision_id=to_revision_id,
        )

        before_content = before.payload.get("content")
        after_content = after.payload.get("content")
        if not isinstance(before_content, dict) or not isinstance(after_content, dict):
            raise ValueError("Saved Revision comparison requires dictionary content")

        component_rows: list[SavedRevisionComponentComparison] = []
        for key in sorted(set(before_content) | set(after_content)):
            before_value = before_content.get(key)
            after_value = after_content.get(key)
            if key not in before_content:
                status = "added"
            elif key not in after_content:
                status = "removed"
            elif before_value == after_value:
                status = "unchanged"
            else:
                status = "changed"
            component_rows.append(
                SavedRevisionComponentComparison(
                    component_key=key,
                    status=status,
                    before_fingerprint=(
                        None if key not in before_content else _json_fingerprint(before_value)
                    ),
                    after_fingerprint=(
                        None if key not in after_content else _json_fingerprint(after_value)
                    ),
                )
            )

        return RunSavedRevisionComparison(
            run_id=history.run_id,
            branch_id=history.branch_id,
            saved_head_revision_id=history.saved_head_revision_id,
            from_revision=before,
            to_revision=after,
            run_changes=_dict_field_changes(
                before.payload.get("run"),
                after.payload.get("run"),
            ),
            branch_changes=_dict_field_changes(
                before.payload.get("branch"),
                after.payload.get("branch"),
            ),
            components=tuple(component_rows),
        )

    @staticmethod
    def _find_revision(
        *,
        history: BranchSavedRevisionHistoryRecord,
        branch_id: str,
        revision_id: str,
    ) -> BranchSavedRevisionRecord:
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
        return revision
