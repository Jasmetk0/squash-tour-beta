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


def _envelope_fields(**overrides):
    fields = dict(revision_id="saved-revision-1", run_id="run", branch_id="branch", sequence=7,
                  parent_revision_id="saved-revision-0", kind="calendar_tour_authority",
                  payload_schema_version="run_saved_revision_v1")
    fields.update(overrides)
    return fields


def test_stored_canonical_text_hash_is_a_sound_sufficient_check():
    import random

    from beta_engine.domain.run_revisions import (
        saved_revision_content_hash,
        stored_canonical_payload_hash_matches,
    )

    rng = random.Random(1803)

    def value(depth=0):
        kind = rng.randrange(8 if depth < 4 else 5)
        if kind == 0:
            return rng.choice([None, True, False])
        if kind == 1:
            return rng.randrange(-10**20, 10**20)
        if kind == 2:
            return rng.choice([0.0, -0.0, 1e16, 2.5, -1e-7, float("nan"), float("inf")])
        if kind in (3, 4):
            return rng.choice(['', 'a"b', '\\', '\ud800', 'ž', ',"payload_schema_version":"x"', '}'])
        if kind == 5:
            return [value(depth + 1) for _ in range(rng.randrange(4))]
        return {rng.choice(['b', 'a', 'payload', 'ž', '"q']) + str(i): value(depth + 1)
                for i in range(rng.randrange(4))}

    for case in range(3000):
        payload = {"content": value(), "run": {"run_id": "run"}}
        summary = {"kind": value()}
        fields = _envelope_fields(parent_revision_id=None if case % 5 == 0 else "saved-revision-0")
        stored = canonical_json(payload)
        expected = saved_revision_content_hash(**fields, payload=json.loads(stored), change_summary=summary)
        assert stored_canonical_payload_hash_matches(
            content_hash=expected, payload_json=stored, change_summary=summary, **fields)
        variants = [
            json.dumps(payload),  # non-canonical spacing/order: must fall back
            stored + " ",
            stored[:-1],
            stored.replace(":", ": ", 1),
            stored + ',"payload_schema_version":"run_saved_revision_v1"',
        ]
        for variant in variants:
            if variant == stored:
                continue
            if stored_canonical_payload_hash_matches(
                    content_hash=expected, payload_json=variant, change_summary=summary, **fields):
                # Never accept different bytes unless the full check agrees.
                assert saved_revision_content_hash(
                    **fields, payload=json.loads(variant), change_summary=summary) == expected
                raise AssertionError("different stored bytes accepted by the fast path")
        # Any other metadata value rejects (and the full check rejects as well).
        for key, changed in (("sequence", 8), ("kind", "other"), ("run_id", "other"),
                             ("parent_revision_id", "saved-revision-x")):
            assert not stored_canonical_payload_hash_matches(
                content_hash=expected, payload_json=stored, change_summary=summary,
                **{**fields, key: changed})


def test_stored_canonical_text_hash_agrees_with_the_full_check_on_real_rows(source):  # noqa: F811
    from beta_engine.domain.run_revisions import (
        saved_revision_content_hash,
        stored_canonical_payload_hash_matches,
    )

    _engine, factory = source
    with factory() as session:
        rows = session.query(BranchSavedRevisionModel).all()
        assert rows
        for row in rows:
            fields = {k: getattr(row, k) for k in (
                "revision_id", "run_id", "branch_id", "sequence", "parent_revision_id", "kind",
                "payload_schema_version")}
            summary = json.loads(row.change_summary_json)
            full = saved_revision_content_hash(**fields, payload=json.loads(row.payload_json), change_summary=summary)
            fast = stored_canonical_payload_hash_matches(
                content_hash=row.content_hash, payload_json=row.payload_json, change_summary=summary, **fields)
            assert fast == (full == row.content_hash) is True
