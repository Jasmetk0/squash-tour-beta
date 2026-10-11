from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.run_saved_revision_history_service import (
    RunSavedRevisionHistoryService,
)
from beta_engine.infrastructure.db import (
    BranchSavedRevisionHistoryRecord,
    BranchSavedRevisionRecord,
)


class _Repository:
    def __init__(self, history: BranchSavedRevisionHistoryRecord) -> None:
        self.history = history

    def get_branch_saved_revision_history(self, *, run_id: str, branch_id: str):
        assert run_id == self.history.run_id
        assert branch_id == self.history.branch_id
        return self.history


def _revision(
    revision_id: str,
    sequence: int,
    parent_revision_id: str | None,
    *,
    viewer_branch_id: str,
    content: dict[str, object],
) -> BranchSavedRevisionRecord:
    return BranchSavedRevisionRecord(
        revision_id=revision_id,
        run_id="run-one",
        branch_id="branch-one",
        sequence=sequence,
        parent_revision_id=parent_revision_id,
        kind="test",
        payload_schema_version="run_saved_revision_v1",
        content_hash_algorithm="sha256",
        content_hash=str(sequence) * 64,
        payload={
            "run": {"run_id": "run-one", "viewer_branch_id": viewer_branch_id},
            "branch": {"branch_id": "branch-one", "status": "active"},
            "content": content,
        },
        change_summary={"summary": revision_id},
    )


def test_history_page_is_newest_window_with_stable_older_cursor() -> None:
    revisions = tuple(
        _revision(
            f"revision-{sequence}",
            sequence,
            None if sequence == 1 else f"revision-{sequence - 1}",
            viewer_branch_id="branch-one",
            content={},
        )
        for sequence in range(1, 6)
    )
    service = RunSavedRevisionHistoryService(
        repository=_Repository(
            BranchSavedRevisionHistoryRecord(
                run_id="run-one",
                branch_id="branch-one",
                saved_head_revision_id="revision-5",
                saved_revisions=revisions,
            )
        )
    )

    newest = service.list_history(
        run_id="run-one",
        branch_id="branch-one",
        limit=2,
    )
    assert [item.sequence for item in newest.saved_revisions] == [4, 5]
    assert newest.has_more_older is True
    assert newest.next_before_sequence == 4
    assert newest.total_count == 5

    older = service.list_history(
        run_id="run-one",
        branch_id="branch-one",
        limit=2,
        before_sequence=newest.next_before_sequence,
    )
    assert [item.sequence for item in older.saved_revisions] == [2, 3]
    assert older.has_more_older is True
    assert older.next_before_sequence == 2


def test_comparison_classifies_component_and_metadata_changes() -> None:
    before = _revision(
        "revision-one",
        1,
        None,
        viewer_branch_id="branch-one",
        content={
            "ranking": {"fingerprint": "old"},
            "initial_world": {"fingerprint": "same"},
        },
    )
    after = _revision(
        "revision-two",
        2,
        "revision-one",
        viewer_branch_id="branch-two",
        content={
            "ranking": {"fingerprint": "new"},
            "initial_world": {"fingerprint": "same"},
            "player_sporting_state": {"fingerprint": "added"},
        },
    )
    service = RunSavedRevisionHistoryService(
        repository=_Repository(
            BranchSavedRevisionHistoryRecord(
                run_id="run-one",
                branch_id="branch-one",
                saved_head_revision_id="revision-two",
                saved_revisions=(before, after),
            )
        )
    )

    comparison = service.compare_revisions(
        run_id="run-one",
        branch_id="branch-one",
        from_revision_id="revision-one",
        to_revision_id="revision-two",
    )

    assert comparison.run_changes == {
        "viewer_branch_id": {"before": "branch-one", "after": "branch-two"}
    }
    assert comparison.branch_changes == {}
    assert {
        item.component_key: item.status for item in comparison.components
    } == {
        "initial_world": "unchanged",
        "player_sporting_state": "added",
        "ranking": "changed",
    }
    ranking = next(
        item for item in comparison.components if item.component_key == "ranking"
    )
    assert ranking.before_fingerprint != ranking.after_fingerprint
    assert len(ranking.before_fingerprint or "") == 64
    assert len(ranking.after_fingerprint or "") == 64
