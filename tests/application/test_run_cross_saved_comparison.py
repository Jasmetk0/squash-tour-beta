import pytest
from unittest.mock import MagicMock
from beta_engine.application.run_cross_saved_comparison import (
    RunCrossSavedComparisonService,
    CrossSavedRevisionComparison,
)
from beta_engine.infrastructure.db.repositories import (
    BranchSavedRevisionHistoryRecord,
    BranchSavedRevisionRecord,
)

def create_mock_revision(rev_id: str, branch_id: str, payload: dict) -> BranchSavedRevisionRecord:
    rev = MagicMock(spec=BranchSavedRevisionRecord)
    rev.revision_id = rev_id
    rev.branch_id = branch_id
    rev.sequence = 1
    rev.parent_revision_id = None
    rev.content_hash_algorithm = "sha256"
    rev.content_hash = "mock_hash"
    rev.payload = payload
    return rev

def create_mock_history(run_id: str, branch_id: str, head_id: str, revisions: list) -> BranchSavedRevisionHistoryRecord:
    hist = MagicMock(spec=BranchSavedRevisionHistoryRecord)
    hist.run_id = run_id
    hist.branch_id = branch_id
    hist.saved_head_revision_id = head_id
    hist.saved_revisions = revisions
    return hist

def test_compare_missing_components():
    repo = MagicMock()
    service = RunCrossSavedComparisonService(repository=repo)

    rev_a = create_mock_revision("rev-a", "b-a", {
        "run": {"val": 1},
        "branch": {"x": 2},
        "content": {"comp1": "hash1"}
    })
    hist_a = create_mock_history("r-a", "b-a", "rev-a", [rev_a])

    rev_b = create_mock_revision("rev-b", "b-b", {
        "run": {"val": 2},
        "branch": {"x": 2, "y": 3},
        "content": {"comp2": "hash2"}
    })
    hist_b = create_mock_history("r-b", "b-b", "rev-b", [rev_b])

    repo.get_branch_saved_revision_history.side_effect = lambda run_id, branch_id: hist_a if run_id == "r-a" else hist_b

    result = service.compare(
        run_a_id="r-a", branch_a_id="b-a", revision_a_id="rev-a",
        run_b_id="r-b", branch_b_id="b-b", revision_b_id="rev-b",
    )

    assert result.from_source.run_id == "r-a"
    assert result.to_source.run_id == "r-b"

    assert "val" in result.run_changes
    assert result.run_changes["val"]["before"] == 1
    assert result.run_changes["val"]["after"] == 2

    assert "x" not in result.branch_changes
    assert "y" in result.branch_changes
    assert result.branch_changes["y"]["before"] is None
    assert result.branch_changes["y"]["after"] == 3

    assert len(result.components) == 2
    comp1 = next(c for c in result.components if c.component_key == "comp1")
    assert comp1.status == "removed"

    comp2 = next(c for c in result.components if c.component_key == "comp2")
    assert comp2.status == "added"
