"""Real SQLite boundaries of the long-Run read optimizations; nothing is mocked.

Covers the exact-text digest reuse, the per-snapshot dependency closure memo and
the scoped cyclic-GC pause. Each reuse must stay bound to the actual current bytes
of one read snapshot: changed rows are rejected even after a successful read.
"""

import gc
import hashlib
import json
import threading
import time

import pytest
from sqlalchemy import text

from beta_engine.domain.run_revisions import VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND, canonical_json
from beta_engine.infrastructure.db.cyclic_gc import paused_cyclic_gc, with_paused_cyclic_gc
from beta_engine.infrastructure.db.exact_text_digest import row_text_sha256
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.native_fork_runtime_state import (
    _dependency_proof_key,
    _proofs,
    actual_dependency_signature,
    native_read_proof_scope,
)
from tests.infrastructure.test_native_dependency_read_snapshot import rewrite_source, source  # noqa: F401

pytestmark = pytest.mark.pr_critical


def test_gc_collection_callback_can_reenter_a_paused_operation():
    """Collection may execute arbitrary finalizers/callbacks; never hold our lock."""
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent('''
        import gc, time
        from beta_engine.infrastructure.db import cyclic_gc
        called = []
        def callback(phase, info):
            if phase == 'start':
                with cyclic_gc.paused_cyclic_gc():
                    called.append(True)
        with cyclic_gc.paused_cyclic_gc():
            gc.callbacks.append(callback)
            try:
                cyclic_gc._paused_since = time.monotonic() - 31
                with cyclic_gc.paused_cyclic_gc():
                    pass
                assert called
            finally:
                gc.callbacks.remove(callback)
        assert gc.isenabled()
        assert cyclic_gc._active == 0
    ''')
    result = subprocess.run([sys.executable, '-c', code], capture_output=True,
                            text=True, timeout=5, check=False)
    assert result.returncode == 0, result.stderr


def plain(text_value):
    return hashlib.sha256(text_value.encode("utf-8")).digest()


def test_restore_append_proofs_only_cover_verified_ancestors_in_scope():
    from types import SimpleNamespace

    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        has_actual_dependency_proof,
        reuse_verified_append_ancestors,
    )

    owner = ("branch", "run", None, None, "active", False)
    old_graph = (("first", "digest-1", owner), ("old", "digest-2", owner))
    new_graph = old_graph + (("restored", "digest-3", owner),)
    before = ("old", old_graph, (("branch", (*owner, "old")),))
    after = ("restored", new_graph, (("branch", (*owner, "restored")),))
    repository = SimpleNamespace(
        _revision_validation_lock=threading.Lock(),
        _native_dependency_proofs={_dependency_proof_key(before): True},
    )

    def covered(revision, graph=new_graph):
        return has_actual_dependency_proof(
            repository, (revision, graph, after[2]), run_id="run", branch_id="branch",
        )

    assert not covered("old")
    with reuse_verified_append_ancestors(repository, before, after, run_id="run", branch_id="branch") as ancestors:
        assert ancestors == ("old",)
        assert covered("old")
        assert not covered("first")  # Not verified in the original graph.
        assert not covered("restored")  # The new revision must verify normally.
        assert not covered("old", new_graph[1:])  # A different actual graph.
    assert not covered("old")

    changed_graph = (("first", "different-bytes", owner), *new_graph[1:])
    with reuse_verified_append_ancestors(
        repository, before, (after[0], changed_graph, after[2]), run_id="run", branch_id="branch",
    ):
        assert not covered("old", changed_graph)


def without_scope(function, *args, **kwargs):
    """The original algorithm: no read scope, hence no snapshot memo at all."""
    token = _proofs.set(None)
    try:
        return function(*args, **kwargs)
    finally:
        _proofs.reset(token)


def test_digest_reuse_is_bound_to_identical_actual_text(source):  # noqa: F811
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN"))
        row = session.get(BranchSavedRevisionModel, "saved")
        original = row.payload_json
        assert row_text_sha256(row, "payload_json") == plain(original)
        actual_dependency_signature(session, row)  # caches the actual row and its digest
        assert row_text_sha256(row, "payload_json") == plain(original)
        # A different in-memory value of the same row/column (stale or tampered
        # model) never borrows the actual row's digest.
        row.payload_json = original.replace('"display_name"', '"display_name" ')
        assert row_text_sha256(row, "payload_json") == plain(row.payload_json) != plain(original)
        session.rollback()
    # Outside any read scope the helper simply hashes.
    with factory() as session:
        row = session.get(BranchSavedRevisionModel, "saved")
        assert row_text_sha256(row, "payload_json") == plain(row.payload_json)


def test_memoized_dependency_graph_equals_original_and_follows_writes(source):  # noqa: F811
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN IMMEDIATE"))
        row = session.get(BranchSavedRevisionModel, "saved")
        first = actual_dependency_signature(session, row)
        again = actual_dependency_signature(session, row)
        assert first == again == without_scope(actual_dependency_signature, session, row)
        assert again[1] is first[1]  # one shared graph value inside one snapshot
        assert _dependency_proof_key(again) == without_scope(_dependency_proof_key, first)
        # An actual (re-hashed) rewrite changes the snapshot: nothing memoized survives.
        rewrite_source(session, "Changed after a successful read")
        fresh = session.get(BranchSavedRevisionModel, "saved")
        session.refresh(fresh)
        changed = actual_dependency_signature(session, fresh)
        assert changed != first
        assert changed == without_scope(actual_dependency_signature, session, fresh)
        assert _dependency_proof_key(changed) == without_scope(_dependency_proof_key, changed)


def test_same_snapshot_tour_ancestors_share_one_graph_and_one_graph_hash(source, monkeypatch):
    from sqlalchemy import insert
    from sqlalchemy.orm.attributes import set_committed_value

    from beta_engine.infrastructure.db import native_fork_runtime_state as runtime
    from beta_engine.infrastructure.db.models import RunBranchModel

    _, factory = source
    first_tour = 40
    last = 80
    ids = [f"native-{i:03}" for i in range(last)]
    with factory.begin() as session:
        original = session.get(BranchSavedRevisionModel, "saved")
        session.execute(insert(BranchSavedRevisionModel), [
            {
                "revision_id": revision_id, "run_id": "run", "branch_id": "branch",
                "sequence": original.sequence + index + 1,
                "parent_revision_id": ids[index - 1] if index else "saved",
                "kind": VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND,
                "payload_schema_version": original.payload_schema_version,
                "content_hash_algorithm": original.content_hash_algorithm,
                "content_hash": original.content_hash,
                "payload_json": canonical_json({"content": {"calendar_tour_authority": {}}})
                if index >= first_tour else original.payload_json,
                "change_summary_json": original.change_summary_json,
            }
            for index, revision_id in enumerate(ids)
        ])
        session.get(RunBranchModel, "branch").saved_head_revision_id = ids[-1]

    encoded_graphs = []
    large_hash_inputs = []
    sha256 = hashlib.sha256

    def count_graph_encodes(value):
        if type(value) is tuple and len(value) > 10:
            encoded_graphs.append(len(value))
        return canonical_json(value)

    def count_graph_hashes(data=b""):
        if len(data) > 4096:
            large_hash_inputs.append(len(data))
        return sha256(data)

    monkeypatch.setattr(runtime, "canonical_json", count_graph_encodes)
    monkeypatch.setattr(runtime.hashlib, "sha256", count_graph_hashes)
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN"))
        head = actual_dependency_signature(session, session.get(BranchSavedRevisionModel, ids[-1]))
        for revision_id in ids[first_tour:]:
            model = session.get(BranchSavedRevisionModel, revision_id)
            result = actual_dependency_signature(session, model)
            assert result[1] is head[1] and result[2] is head[2]
            assert len(_dependency_proof_key(result)) == 64
        assert encoded_graphs == [last + 1]
        assert len(large_hash_inputs) == 1

        tour_ancestor = session.get(BranchSavedRevisionModel, ids[first_tour])
        ancestor = actual_dependency_signature(session, tour_ancestor)
        assert ancestor == without_scope(actual_dependency_signature, session, tour_ancestor)
        assert _dependency_proof_key(ancestor) == without_scope(_dependency_proof_key, ancestor)
        assert _dependency_proof_key(ancestor) != _dependency_proof_key(head)
        set_committed_value(tour_ancestor, "change_summary_json", '{"stale":true}')
        with pytest.raises(ValueError, match="differs from its actual stored bytes"):
            actual_dependency_signature(session, tour_ancestor)

        # An older row without a back edge must retain its own smaller graph.
        early = session.get(BranchSavedRevisionModel, ids[first_tour - 1])
        signature = actual_dependency_signature(session, early)
        assert len(signature[1]) == first_tour + 1
        assert signature == without_scope(actual_dependency_signature, session, early)

        for revision_id in ids[:first_tour]:
            actual_dependency_signature(session, session.get(BranchSavedRevisionModel, revision_id))
        snapshot = runtime._physical_read_cache(session)
        assert len(snapshot["dependency_graphs"]) <= runtime._MAX_SNAPSHOT_DEPENDENCY_GRAPHS


def test_changed_actual_row_is_rejected_even_with_a_warm_snapshot(source):  # noqa: F811
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN IMMEDIATE"))
        row = session.get(BranchSavedRevisionModel, "saved")
        actual_dependency_signature(session, row)
        payload = json.loads(row.payload_json)
        payload["run"]["display_name"] = "Rewritten behind the ORM"
        session.execute(text("UPDATE branch_saved_revisions SET payload_json=:p WHERE revision_id='saved'"),
                        {"p": canonical_json(payload)})
        # The caller's model no longer equals the actual stored bytes.
        with pytest.raises(ValueError, match="differs from its actual stored bytes"):
            actual_dependency_signature(session, row)


def test_cyclic_gc_pause_is_nested_thread_safe_and_restored():
    assert gc.isenabled()
    with paused_cyclic_gc():
        assert not gc.isenabled()
        with paused_cyclic_gc():
            assert not gc.isenabled()
        assert not gc.isenabled()
    assert gc.isenabled()

    @with_paused_cyclic_gc
    def failing():
        assert not gc.isenabled()
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        failing()
    assert gc.isenabled()

    inside, release = threading.Barrier(5), threading.Event()

    def worker():
        with paused_cyclic_gc():
            inside.wait()
            release.wait()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    inside.wait()
    assert not gc.isenabled()
    release.set()
    for thread in threads:
        thread.join()
    assert gc.isenabled()

    gc.disable()
    try:
        with paused_cyclic_gc():
            pass
        assert not gc.isenabled()  # an already disabled collector stays disabled
    finally:
        gc.enable()



def test_cyclic_gc_pause_is_bounded_under_continuous_overlap(monkeypatch):
    """Overlapping operations never let the count reach zero; cycles still go."""
    import weakref

    from beta_engine.infrastructure.db import cyclic_gc

    monkeypatch.setattr(cyclic_gc, "MAX_CONTINUOUS_PAUSE_SECONDS", 0.05)

    class Node:
        pass

    def cycle():
        a, b = Node(), Node()
        a.other, b.other = b, a
        return weakref.ref(a)

    gc.collect()
    holder_inside, release = threading.Event(), threading.Event()

    def long_operation():
        with paused_cyclic_gc():
            holder_inside.set()
            release.wait()

    holder = threading.Thread(target=long_operation)
    holder.start()
    holder_inside.wait()
    try:
        assert not gc.isenabled()
        refs = [cycle() for _ in range(1000)]
        assert any(ref() is not None for ref in refs)  # nothing collects them yet
        deadline = time.monotonic() + 5
        while any(ref() is not None for ref in refs) and time.monotonic() < deadline:
            with paused_cyclic_gc():  # another overlapping short operation
                pass
            time.sleep(0.01)
        assert all(ref() is None for ref in refs), "cyclic garbage survived the bound"
        assert not gc.isenabled()  # the long operation is still paused
    finally:
        release.set()
        holder.join()
    assert gc.isenabled()
