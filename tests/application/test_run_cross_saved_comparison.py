"""Mocked validated-history contract tests; real persistence lives in API acceptance."""
import hashlib
from dataclasses import replace

import pytest

from beta_engine.application.run_cross_saved_comparison import (
    RunCrossSavedComparisonService,
)
from beta_engine.infrastructure.db import (
    BranchSavedRevisionHistoryRecord,
    BranchSavedRevisionRecord,
)
from beta_engine.infrastructure.db.repositories import SavedRevisionHistoryNotFoundError

pytestmark = pytest.mark.pr_critical


def source(run, content, *, metadata=None):
    return BranchSavedRevisionRecord(
        revision_id="rev-" + run, run_id=run, branch_id="branch-" + run, sequence=1,
        parent_revision_id=None, kind="unit", payload_schema_version="unit.v1",
        content_hash_algorithm="sha256", content_hash="a" * 64,
        payload={"run": metadata or {}, "branch": {}, "content": content}, change_summary={})


def compare(left, right):
    class Repository:
        def get_branch_saved_revision_history(self, *, run_id, branch_id):
            revision = left if run_id == left.run_id else right
            assert (run_id, branch_id) == (revision.run_id, revision.branch_id)
            return BranchSavedRevisionHistoryRecord(run_id, branch_id, revision.revision_id, (revision,))
    return RunCrossSavedComparisonService(Repository()).compare(
        run_a_id=left.run_id, branch_a_id=left.branch_id, revision_a_id=left.revision_id,
        run_b_id=right.run_id, branch_b_id=right.branch_id, revision_b_id=right.revision_id)


def test_canonical_fingerprints_and_all_four_states_without_payload_leak():
    result = compare(source("a", {"removed": None, "same": {"a": 1, "b": 2}, "changed": 0}),
                     source("b", {"added": None, "same": {"b": 2, "a": 1}, "changed": False}))
    rows = {r.component_key: r for r in result.components}
    assert {k: r.status for k, r in rows.items()} == {
        "added": "added", "removed": "removed", "same": "unchanged", "changed": "changed"}
    null_hash = hashlib.sha256(b"null").hexdigest()
    assert rows["added"].before_fingerprint is None
    assert rows["added"].after_fingerprint == null_hash
    assert rows["removed"].before_fingerprint == null_hash
    assert rows["same"].before_fingerprint == rows["same"].after_fingerprint
    assert rows["changed"].before_fingerprint != rows["changed"].after_fingerprint


def test_metadata_distinguishes_absent_null_zero_false_and_empty():
    result = compare(source("a", {}, metadata={"zero": 0, "null": None, "empty": ""}),
                     source("b", {}, metadata={"zero": False, "new_null": None}))
    assert result.run_changes["zero"]["before"] == 0
    assert result.run_changes["zero"]["after"] is False
    assert result.run_changes["null"] == {"before": None, "after": None, "before_present": True, "after_present": False}
    assert result.run_changes["new_null"]["before_present"] is False
    assert result.run_changes["new_null"]["after_present"] is True
    assert result.run_changes["empty"]["before"] == ""


def test_response_size_does_not_scale_with_component_payload():
    secret = "not-a-fingerprint" * 100000
    result = compare(source("a", {"large": {"payload": secret}}), source("b", {}))
    row = result.components[0]
    assert len(row.before_fingerprint) == 64
    from beta_engine.api.routers.admin_saved_cross_compare import _map_response
    encoded = _map_response(result).model_dump_json()
    assert secret not in encoded
    assert len(encoded) < 4000


def test_missing_revision_uses_existing_not_found_boundary():
    a = source("a", {})
    with pytest.raises(SavedRevisionHistoryNotFoundError):
        compare(replace(a, revision_id="missing"), replace(a, revision_id="other"))
