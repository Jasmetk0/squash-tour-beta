from __future__ import annotations

import pytest

from beta_engine.domain.run_revisions import (
    saved_revision_content_hash,
    viewer_branch_id_from_changes,
    viewer_branch_saved_revision_payload,
    viewer_branch_selection_change,
)


def test_saved_revision_hash_is_canonical_and_protects_lineage() -> None:
    common = {
        "revision_id": "revision-1",
        "run_id": "run-1",
        "branch_id": "branch-1",
        "sequence": 1,
        "kind": "initial_run_creation",
        "payload_schema_version": "empty_run_saved_revision_v1",
    }
    first = saved_revision_content_hash(
        **common,
        parent_revision_id=None,
        payload={"run": {"name": "History", "status": "working"}, "content": {}},
        change_summary={"kind": "created", "summary": "Created History"},
    )
    reordered = saved_revision_content_hash(
        **common,
        parent_revision_id=None,
        payload={"content": {}, "run": {"status": "working", "name": "History"}},
        change_summary={"summary": "Created History", "kind": "created"},
    )
    changed_lineage = saved_revision_content_hash(
        **common,
        parent_revision_id="revision-0",
        payload={"run": {"name": "History", "status": "working"}, "content": {}},
        change_summary={"kind": "created", "summary": "Created History"},
    )

    assert first == reordered
    assert len(first) == 64
    assert changed_lineage != first


def test_viewer_branch_change_bundle_has_one_strict_canonical_shape() -> None:
    change = viewer_branch_selection_change(viewer_branch_id="branch-2")

    assert change == {
        "kind": "set_viewer_branch",
        "viewer_branch_id": "branch-2",
    }
    assert viewer_branch_id_from_changes([change]) == "branch-2"
    with pytest.raises(ValueError, match="unsupported fields"):
        viewer_branch_id_from_changes([{**change, "hidden": True}])
    with pytest.raises(ValueError, match="exactly one"):
        viewer_branch_id_from_changes([])


def test_viewer_branch_save_materializes_branch_without_losing_content() -> None:
    base = {
        "run": {"run_id": "run-1", "viewer_branch_id": "branch-1"},
        "branch": {"branch_id": "branch-1"},
        "content": {"future": {"preserved": True}},
    }

    materialized = viewer_branch_saved_revision_payload(
        base_payload=base,
        run_id="run-1",
        display_name="History",
        run_status="working",
        timeline_start_season=2000,
        timeline_end_season=2049,
        branch_id="branch-2",
        branch_display_name="Timeline 2",
        branch_status="active",
        forked_from_branch_id="branch-1",
        forked_from_saved_revision_id="revision-1",
        viewer_branch_id="branch-2",
    )

    assert materialized["run"]["viewer_branch_id"] == "branch-2"
    assert materialized["branch"]["branch_id"] == "branch-2"
    assert materialized["content"] == {"future": {"preserved": True}}
    assert base["run"]["viewer_branch_id"] == "branch-1"
    assert base["branch"]["branch_id"] == "branch-1"
