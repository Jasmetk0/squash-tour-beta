"""Read-only cross-source resolver and comparison service."""

from dataclasses import dataclass
from beta_engine.infrastructure.db import (
    SimulationPersistenceRepository,
    BranchSavedRevisionHistoryRecord,
    BranchSavedRevisionRecord,
)

@dataclass(frozen=True)
class CrossSavedRevisionComparisonSource:
    run_id: str
    branch_id: str
    saved_head_revision_id: str
    revision: BranchSavedRevisionRecord

@dataclass(frozen=True)
class CrossSavedRevisionComponentComparison:
    component_key: str
    status: str
    before_fingerprint: str | None
    after_fingerprint: str | None

@dataclass(frozen=True)
class CrossSavedRevisionComparison:
    from_source: CrossSavedRevisionComparisonSource
    to_source: CrossSavedRevisionComparisonSource
    run_changes: dict[str, dict[str, object | None]]
    branch_changes: dict[str, dict[str, object | None]]
    components: tuple[CrossSavedRevisionComponentComparison, ...]

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
class RunCrossSavedComparisonService:
    repository: SimulationPersistenceRepository

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
            raise ValueError(f"Revision {revision_id!r} not found in {branch_id!r}")
        return revision

    def compare(
        self,
        *,
        run_a_id: str,
        branch_a_id: str,
        revision_a_id: str,
        run_b_id: str,
        branch_b_id: str,
        revision_b_id: str,
    ) -> CrossSavedRevisionComparison:
        history_a = self.repository.get_branch_saved_revision_history(
            run_id=run_a_id,
            branch_id=branch_a_id,
        )
        history_b = self.repository.get_branch_saved_revision_history(
            run_id=run_b_id,
            branch_id=branch_b_id,
        )
        before = self._find_revision(
            history=history_a,
            branch_id=branch_a_id,
            revision_id=revision_a_id,
        )
        after = self._find_revision(
            history=history_b,
            branch_id=branch_b_id,
            revision_id=revision_b_id,
        )

        before_content = before.payload.get("content")
        after_content = after.payload.get("content")
        if not isinstance(before_content, dict) or not isinstance(after_content, dict):
            raise ValueError("Saved Revision comparison requires dictionary content")

        component_rows: list[CrossSavedRevisionComponentComparison] = []
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
                CrossSavedRevisionComponentComparison(
                    component_key=key,
                    status=status,
                    before_fingerprint=str(before_value)
                    if before_value is not None
                    else None,
                    after_fingerprint=str(after_value)
                    if after_value is not None
                    else None,
                )
            )

        return CrossSavedRevisionComparison(
            from_source=CrossSavedRevisionComparisonSource(
                run_id=history_a.run_id,
                branch_id=history_a.branch_id,
                saved_head_revision_id=history_a.saved_head_revision_id,
                revision=before,
            ),
            to_source=CrossSavedRevisionComparisonSource(
                run_id=history_b.run_id,
                branch_id=history_b.branch_id,
                saved_head_revision_id=history_b.saved_head_revision_id,
                revision=after,
            ),
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
