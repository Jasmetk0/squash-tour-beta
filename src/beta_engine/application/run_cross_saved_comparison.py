"""Read-only comparison of two independently authenticated Saved source contexts.

Component fingerprints describe stored content, not a semantic player/ranking
projection. No live Working Draft or current Package substitutes for Saved data.
"""
from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.run_saved_revision_history_service import (
    RunSavedRevisionHistoryService,
    _json_fingerprint,
)
from beta_engine.infrastructure.db import (
    BranchSavedRevisionRecord,
    SimulationPersistenceRepository,
)
from beta_engine.infrastructure.db.repositories import SavedRevisionHistoryConflictError


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
    run_changes: dict[str, dict[str, object]]
    branch_changes: dict[str, dict[str, object]]
    components: tuple[CrossSavedRevisionComponentComparison, ...]


def _field_changes(before: object, after: object) -> dict[str, dict[str, object]]:
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise SavedRevisionHistoryConflictError("Saved comparison requires dictionary metadata")
    changes = {}
    for key in sorted(before.keys() | after.keys()):
        left, right = key in before, key in after
        if left != right or _json_fingerprint(before[key]) != _json_fingerprint(after[key]):
            changes[key] = {
                "before": before.get(key), "after": after.get(key),
                "before_present": left, "after_present": right,
            }
    return changes


@dataclass(slots=True)
class RunCrossSavedComparisonService:
    repository: SimulationPersistenceRepository

    def compare(self, *, run_a_id: str, branch_a_id: str, revision_a_id: str,
                run_b_id: str, branch_b_id: str, revision_b_id: str) -> CrossSavedRevisionComparison:
        history = RunSavedRevisionHistoryService(self.repository)
        # The existing public read boundary authenticates the complete reachable
        # lineage and physical native dependencies. Never prime or bypass caches.
        a = history.get_revision(run_id=run_a_id, branch_id=branch_a_id, revision_id=revision_a_id)
        b = history.get_revision(run_id=run_b_id, branch_id=branch_b_id, revision_id=revision_b_id)
        before, after = a.saved_revision, b.saved_revision
        left, right = before.payload.get("content"), after.payload.get("content")
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise SavedRevisionHistoryConflictError("Saved comparison requires dictionary content")
        rows = []
        for key in sorted(left.keys() | right.keys()):
            # None means absent only; a present JSON null has a real fingerprint.
            old = _json_fingerprint(left[key]) if key in left else None
            new = _json_fingerprint(right[key]) if key in right else None
            state = "added" if old is None else "removed" if new is None else (
                "unchanged" if old == new else "changed")
            rows.append(CrossSavedRevisionComponentComparison(key, state, old, new))
        return CrossSavedRevisionComparison(
            CrossSavedRevisionComparisonSource(a.run_id, a.branch_id, a.saved_head_revision_id, before),
            CrossSavedRevisionComparisonSource(b.run_id, b.branch_id, b.saved_head_revision_id, after),
            _field_changes(before.payload.get("run"), after.payload.get("run")),
            _field_changes(before.payload.get("branch"), after.payload.get("branch")), tuple(rows),
        )
