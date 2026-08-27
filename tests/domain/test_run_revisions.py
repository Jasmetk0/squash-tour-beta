from __future__ import annotations

from beta_engine.domain.run_revisions import saved_revision_content_hash


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
