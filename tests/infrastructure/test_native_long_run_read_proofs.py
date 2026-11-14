"""Real SQLite boundaries of the long-Run read optimizations; nothing is mocked.

Covers the exact-text digest reuse, the per-snapshot dependency closure memo and
the scoped cyclic-GC pause. Each reuse must stay bound to the actual current bytes
of one read snapshot: changed rows are rejected even after a successful read.
"""

import gc
import hashlib
import json
import threading

import pytest
from sqlalchemy import text

from beta_engine.domain.run_revisions import canonical_json
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


def plain(text_value):
    return hashlib.sha256(text_value.encode("utf-8")).digest()


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
        assert _dependency_proof_key(again) == hashlib.sha256(canonical_json(first).encode()).hexdigest()
        # An actual (re-hashed) rewrite changes the snapshot: nothing memoized survives.
        rewrite_source(session, "Changed after a successful read")
        fresh = session.get(BranchSavedRevisionModel, "saved")
        session.refresh(fresh)
        changed = actual_dependency_signature(session, fresh)
        assert changed != first
        assert changed == without_scope(actual_dependency_signature, session, fresh)
        assert _dependency_proof_key(changed) == hashlib.sha256(canonical_json(changed).encode()).hexdigest()


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
