"""Scoped copy-on-write optimization for the native fork Saved writer.

These are pure equivalence/isolation tests, not a substitute for the real
HTTP/SQLite Save, restore and replay acceptance gates.
"""

from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from beta_engine.application import native_fork_runtime_service as writer

from beta_engine.application.native_fork_runtime_service import (
    NativeForkRuntimeService,
    _copy_append_payload_without_replaced_runtime,
)
from beta_engine.domain.run_revisions import canonical_json, saved_revision_content_hash
from beta_engine.infrastructure.db.native_fork_runtime_state import KEY

pytestmark = pytest.mark.pr_critical


def sample():
    return {
        "run": {
            "run_id": "r",
            "run_calendar": {"weeks_per_year": 52, "season_count": 2},
            "timeline_end_season": 2031,
            "other": [{"nested": {"text": "žluťoučký", "flag": True}}],
        },
        "branch": {"branch_id": "b", "history": [{"parents": ["a", "b"]}]},
        "content": {
            KEY: {"state": {"players": [{"ids": list(range(200))}]}},
            "original_source": {"nested": [{"value": 1.5, "zero": -0.0}]},
        },
        "future_extension": {"unchanged": [1, {"list": [2, 3]}]},
    }


def test_retained_fields_preserve_exact_json_and_content_hash():
    source = sample()
    before = deepcopy(source)
    new_component = {"state": {"players": [{"ids": [99]}]}, "fingerprint": "f" * 64}
    expected = deepcopy(source)
    expected["run"]["run_calendar"] = deepcopy(source["run"]["run_calendar"])
    expected["run"]["timeline_end_season"] = source["run"]["timeline_end_season"]
    expected["content"][KEY] = new_component
    expected["run"]["viewer_branch_id"] = "viewer"

    actual = _copy_append_payload_without_replaced_runtime(source)
    actual["run"]["run_calendar"] = deepcopy(source["run"]["run_calendar"])
    actual["run"]["timeline_end_season"] = source["run"]["timeline_end_season"]
    actual["content"][KEY] = new_component
    actual["run"]["viewer_branch_id"] = "viewer"

    assert source == before
    assert canonical_json(actual) == canonical_json(expected)
    envelope = dict(
        revision_id="saved-2", run_id="r", branch_id="b", sequence=2,
        parent_revision_id="saved-1", kind="native_fork_save",
        payload_schema_version="native_fork_saved_root.v2",
        change_summary={"kind": "native_fork_save"},
    )
    assert saved_revision_content_hash(**envelope, payload=actual) == (
        saved_revision_content_hash(**envelope, payload=expected)
    )
    # The stored JSON is a fresh value tree, never a shared mutable source.
    stored = json.loads(canonical_json(actual))
    stored["content"]["original_source"]["nested"][0]["value"] = 9
    assert source["content"]["original_source"]["nested"][0]["value"] == 1.5


def test_every_retained_mutable_subtree_is_defensively_copied():
    source = sample()
    kept = _copy_append_payload_without_replaced_runtime(source)
    assert KEY not in kept["content"]
    kept["branch"]["history"][0]["parents"].append("new")
    kept["run"]["other"][0]["nested"]["flag"] = False
    kept["content"]["original_source"]["nested"][0]["value"] = 999
    kept["future_extension"]["unchanged"][1]["list"].append(5)
    assert source["branch"]["history"][0]["parents"] == ["a", "b"]
    assert source["run"]["other"][0]["nested"]["flag"] is True
    assert source["content"]["original_source"]["nested"][0]["value"] == 1.5
    assert source["future_extension"]["unchanged"][1]["list"] == [2, 3]
    source["branch"]["history"][0]["parents"].append("later")
    assert kept["branch"]["history"][0]["parents"] == ["a", "b", "new"]


def test_discarded_runtime_is_never_traversed_by_deepcopy():
    class MustNeverCopy:
        def __deepcopy__(self, memo):
            raise AssertionError("Discarded runtime was copied")

    source = sample()
    source["content"][KEY] = MustNeverCopy()
    kept = _copy_append_payload_without_replaced_runtime(source)
    assert KEY not in kept["content"]
    assert kept["content"]["original_source"] == source["content"]["original_source"]


def test_absent_previous_runtime_does_not_discard_other_components():
    source = sample()
    del source["content"][KEY]
    assert _copy_append_payload_without_replaced_runtime(source) == source


def test_append_builds_independent_persisted_bytes_and_valid_content_hash(monkeypatch):
    source = sample()
    original = deepcopy(source)
    updated_runtime = {"state": {"new": ["value", {"nested": [1, 2]}]}}
    monkeypatch.setattr(writer, "component", lambda runtime: updated_runtime)

    class MemorySession:
        def __init__(self):
            self.rows = []

        def add(self, value):
            self.rows.append(value)

        def flush(self):
            pass

    class RecordingRepository:
        def _validated_saved_revision_in_session(self, *, session, model):
            payload = json.loads(model.payload_json)
            assert model.content_hash == saved_revision_content_hash(
                revision_id=model.revision_id,
                run_id=model.run_id,
                branch_id=model.branch_id,
                sequence=model.sequence,
                parent_revision_id=model.parent_revision_id,
                kind=model.kind,
                payload_schema_version=model.payload_schema_version,
                payload=payload,
                change_summary=json.loads(model.change_summary_json),
            )
            return SimpleNamespace(revision_id=model.revision_id, payload=payload)

    run = SimpleNamespace(run_id="r")
    branch = SimpleNamespace(branch_id="b", saved_head_revision_id="saved-1")
    previous = SimpleNamespace(payload=source, revision_id="saved-1", sequence=1)
    draft = SimpleNamespace(draft_version=3)
    session = MemorySession()
    record, audit = NativeForkRuntimeService(RecordingRepository())._append(
        session, (run, branch, previous, draft), object(),
        revision_id="saved-2", audit_event_id="audit-2",
        summary={"kind": "native_fork_save", "runtime_fingerprint": "a" * 64},
        viewer_id="b",
    )
    expected = deepcopy(original)
    expected["content"][KEY] = updated_runtime
    expected["run"]["viewer_branch_id"] = "b"
    assert record.payload == expected
    assert source == original
    assert branch.saved_head_revision_id == "saved-2"
    assert audit.saved_revision_id == "saved-2"
    # Even after the write returns, a consumer cannot mutate the original root.
    record.payload["content"]["original_source"]["nested"][0]["value"] = 123
    assert source["content"]["original_source"]["nested"][0]["value"] == 1.5
