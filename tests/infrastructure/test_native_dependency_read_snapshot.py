"""Real SQLite read-cache boundaries; no sporting outputs are fabricated."""

import json

import pytest
from sqlalchemy import event, text

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_revisions import canonical_json, saved_revision_content_hash
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunBranchModel,
)
from beta_engine.infrastructure.db.native_fork_runtime_state import (
    _MAX_DEPENDENCY_PROOFS,
    actual_dependency_signature,
    native_read_proof_scope,
    verify_with_actual_dependencies,
)
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
from tests.application.test_full_simulation_task_calendar import setup_calendar

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize('installed', [False, True])
def test_global_append_requires_unchanged_complete_graph_and_exact_head(installed):
    from copy import deepcopy
    from beta_engine.infrastructure.db.native_fork_runtime_state import assert_global_save_append

    owner = ('branch', 'run', None, None, 'active', False)
    foreign = ('foreign', 'run', None, None, 'active', False)
    rows = (('old', 'old-actual-bytes', owner), ('foreign-source', 'foreign-bytes', foreign))
    heads = (('branch', owner + ('old',)), ('foreign', foreign + ('foreign-source',)))
    before = ('old', rows, heads)
    after = ('new', rows + (('new', 'new-actual-bytes', owner),),
        (('branch', owner + (('new' if installed else 'old'),)), heads[1]))
    args = dict(run_id='run', branch_id='branch', revision_id='new', installed=installed)
    assert set(assert_global_save_append(before, after, **args)) == {'old', 'new'}
    changed = []
    graph = list(deepcopy(after[1])); graph[0] = ('old', 'rehashed-changed-bytes', owner)
    changed.append((after[0], tuple(graph), after[2]))
    graph = list(after[1]); graph[0] = ('old', 'old-actual-bytes', owner[:-2] + ('closed', False))
    changed.append((after[0], tuple(graph), after[2]))
    changed.append((after[0], after[1][1:], after[2]))
    changed.append((after[0], after[1] + (('unverified', 'extra', owner),), after[2]))
    changed.append((after[0], after[1][:-1] + (('new', 'new-actual-bytes', foreign),), after[2]))
    changed.append((after[0], after[1], (after[2][0], ('foreign', foreign + ('other-head',)))))
    wrong_head = 'old' if installed else 'new'
    changed.append((after[0], after[1], (('branch', owner + (wrong_head,)), after[2][1])))
    for invalid in changed:
        with pytest.raises(ValueError):
            assert_global_save_append(before, invalid, **args)


@pytest.fixture
def source(tmp_path):
    engine, factory, _repo = setup_calendar(tmp_path, RunCalendar(80, 80, 2100, 2))
    yield engine, factory
    engine.dispose()


def rewrite_source(session, label):
    row = session.get(BranchSavedRevisionModel, "saved")
    payload = json.loads(row.payload_json)
    payload["run"]["display_name"] = label
    fields = {key: getattr(row, key) for key in (
        "revision_id", "run_id", "branch_id", "sequence", "parent_revision_id", "kind", "payload_schema_version",
    )}
    content_hash = saved_revision_content_hash(**fields, payload=payload, change_summary=json.loads(row.change_summary_json))
    session.execute(text("UPDATE branch_saved_revisions SET payload_json=:payload, content_hash=:content_hash WHERE revision_id='saved'"),
        {"payload": canonical_json(payload), "content_hash": content_hash})


def test_small_actual_parent_reference_follows_snapshot_writes_and_rollback(source):
    from beta_engine.infrastructure.db.native_fork_runtime_state import actual_saved_revision_reference

    engine, factory = source
    reads = []

    def count(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith('SELECT'):
            reads.append(statement)

    event.listen(engine, 'before_cursor_execute', count)
    try:
        with factory() as session, native_read_proof_scope():
            session.execute(text('BEGIN'))
            row = session.get(BranchSavedRevisionModel, 'saved')
            actual_dependency_signature(session, row)
            before = len(reads)
            original = actual_saved_revision_reference(session, 'run', 'saved')
            assert original == ('saved', 'run', 'branch', row.sequence, None)
            assert len(reads) == before
            session.execute(text('SAVEPOINT parent_reference'))
            session.execute(text("UPDATE branch_saved_revisions SET parent_revision_id='changed' WHERE revision_id='saved'"))
            assert actual_saved_revision_reference(session, 'run', 'saved')[-1] == 'changed'
            assert 'payload_json' not in reads[-1]
            session.execute(text('ROLLBACK TO SAVEPOINT parent_reference'))
            assert actual_saved_revision_reference(session, 'run', 'saved') == original
    finally:
        event.remove(engine, 'before_cursor_execute', count)


def test_physical_reads_reuse_one_snapshot_and_reread_after_external_commit(source):
    engine, factory = source
    reads = []

    def count(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT") and any(table in statement for table in ("branch_saved_revisions", "run_branches")):
            reads.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        with factory() as session, native_read_proof_scope():
            session.execute(text("BEGIN"))
            row = session.get(BranchSavedRevisionModel, "saved")
            first = actual_dependency_signature(session, row)
            count_before = len(reads)
            assert count_before > 0
            assert actual_dependency_signature(session, row) == first
            assert len(reads) == count_before
            with factory.begin() as other:
                other.execute(text("UPDATE run_branches SET read_only=1 WHERE branch_id='branch'"))
            # SQLite's current read snapshot remains consistent with its first read.
            assert actual_dependency_signature(session, row) == first
            assert len(reads) == count_before
            session.commit()
            session.execute(text("BEGIN"))
            assert actual_dependency_signature(session, row) != first
            assert len(reads) > count_before
    finally:
        event.remove(engine, "before_cursor_execute", count)


def test_viewer_projection_and_its_physical_gate_share_one_read_snapshot(source, monkeypatch):
    """A concurrent owner edit is visible on the next read, never half a read."""
    engine, factory = source
    repository = SimulationPersistenceRepository(engine=engine, session_factory=factory)
    original = repository._validated_branch_revision_lineage_in_session
    observed = []

    def read_with_concurrent_change(*, session, **kwargs):
        assert session.connection().connection.driver_connection.in_transaction
        result = original(session=session, **kwargs)
        if not observed:
            with factory.begin() as writer:
                writer.execute(text("UPDATE run_branches SET read_only=1 WHERE branch_id='branch'"))
            # Independent physical read still sees the selected immutable owner
            # from this transaction, rather than mixing the committed edit in.
            observed.append(session.scalar(text("SELECT read_only FROM run_branches WHERE branch_id='branch'")))
        return result

    monkeypatch.setattr(repository, '_validated_branch_revision_lineage_in_session', read_with_concurrent_change)
    before = repository.get_viewer_saved_revision_snapshot(product_run_id='run')
    after = repository.get_viewer_saved_revision_snapshot(product_run_id='run')
    assert observed == [0]
    assert before.context.official_branch_read_only is False
    assert after.context.official_branch_read_only is True
    assert before.revision == after.revision


def test_rehashed_actual_saved_bytes_invalidate_cached_rows_and_stale_orm(source):
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN IMMEDIATE"))
        row = session.get(BranchSavedRevisionModel, "saved")
        first = actual_dependency_signature(session, row)
        rewrite_source(session, "Přepsaný skutečný zdroj")
        with pytest.raises(ValueError, match="actual stored bytes"):
            actual_dependency_signature(session, row)
        session.expire_all()
        assert actual_dependency_signature(session, session.get(BranchSavedRevisionModel, "saved")) != first


def test_savepoint_rollback_invalidates_snapshot_even_without_total_changes_increment(source):
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN IMMEDIATE"))
        first = actual_dependency_signature(session, session.get(BranchSavedRevisionModel, "saved"))
        session.execute(text("SAVEPOINT changed_source"))
        rewrite_source(session, "Temporary actual source")
        session.expire_all()
        assert actual_dependency_signature(session, session.get(BranchSavedRevisionModel, "saved")) != first
        changes = session.connection().connection.driver_connection.total_changes
        session.execute(text("/* explicit rollback */ ROLLBACK TO SAVEPOINT changed_source"))
        assert session.connection().connection.driver_connection.total_changes == changes
        session.expire_all()
        assert actual_dependency_signature(session, session.get(BranchSavedRevisionModel, "saved")) == first
        session.execute(text("RELEASE SAVEPOINT changed_source"))


def test_direct_driver_write_invalidates_owner_reads_via_total_changes(source):
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN IMMEDIATE"))
        row = session.get(BranchSavedRevisionModel, "saved")
        first = actual_dependency_signature(session, row)
        session.connection().connection.driver_connection.execute("UPDATE run_branches SET read_only=1 WHERE branch_id='branch'")
        assert actual_dependency_signature(session, row) != first


def test_current_head_proof_survives_history_walk_but_not_changed_actual_ancestor(source):
    engine, factory = source
    history_length = _MAX_DEPENDENCY_PROOFS + 4
    # Metadata-only Saved rows exercise cache eviction, not accepted sport or closure.
    with factory.begin() as session:
        first = session.get(BranchSavedRevisionModel, "saved")
        payload = json.loads(first.payload_json)
        parent = first.revision_id
        for index in range(1, history_length + 1):
            details = {"revision_id": f"metadata-{index}", "run_id": "run", "branch_id": "branch",
                "sequence": first.sequence + index, "parent_revision_id": parent, "kind": "manual_save", "payload_schema_version": first.payload_schema_version}
            summary = {"kind": "metadata-only cache fixture"}
            session.add(BranchSavedRevisionModel(**details, content_hash_algorithm="sha256",
                content_hash=saved_revision_content_hash(**details, payload=payload, change_summary=summary),
                payload_json=canonical_json(payload), change_summary_json=canonical_json(summary)))
            parent = details["revision_id"]
        session.get(RunBranchModel, "branch").saved_head_revision_id = parent
    repository = SimulationPersistenceRepository(engine=engine, session_factory=factory)
    verified = []
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN IMMEDIATE"))
        head = session.get(BranchSavedRevisionModel, f"metadata-{history_length}")
        verify_with_actual_dependencies(repository, session, head, lambda: verified.append(head.revision_id))
        for index in range(history_length - 1, -1, -1):
            row = session.get(BranchSavedRevisionModel, f"metadata-{index}" if index else "saved")
            verify_with_actual_dependencies(repository, session, row, lambda rid=row.revision_id: verified.append(rid))
        verify_with_actual_dependencies(repository, session, head, lambda: verified.append(head.revision_id))
        assert verified.count(head.revision_id) == 1
        rewrite_source(session, "Changed and rehashed actual ancestor")

        def reject_changed_source():
            raise ValueError("actual source changed")

        with pytest.raises(ValueError, match="actual source changed"):
            verify_with_actual_dependencies(repository, session, head, reject_changed_source)


def test_completed_operation_proofs_follow_snapshot_writes_and_pending_orm(source):
    from beta_engine.infrastructure.db.native_fork_runtime_state import snapshot_proofs
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text('BEGIN IMMEDIATE'))
        first = snapshot_proofs(session)
        first['completed'] = True
        assert snapshot_proofs(session) is first
        owner = session.get(RunBranchModel, 'branch')
        owner.read_only = True
        assert 'completed' not in snapshot_proofs(session)
        session.flush()
        second = snapshot_proofs(session)
        assert second is not first
        second['completed'] = True
        session.execute(text('SAVEPOINT proof_boundary'))
        third = snapshot_proofs(session)
        assert third is not second
        third['completed'] = True
        session.execute(text('ROLLBACK TO SAVEPOINT proof_boundary'))
        assert snapshot_proofs(session) is not third
        session.rollback()
        session.execute(text('BEGIN'))
        assert 'completed' not in snapshot_proofs(session)


def test_malformed_physical_json_fails_closed_without_caching(source):
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text('BEGIN IMMEDIATE'))
        row = session.get(BranchSavedRevisionModel, 'saved')
        actual_dependency_signature(session, row)
        session.execute(text("UPDATE branch_saved_revisions SET payload_json='{' WHERE revision_id='saved'"))
        with pytest.raises(ValueError, match='malformed JSON'):
            actual_dependency_signature(session, row)


def test_direct_driver_savepoint_rollback_and_transaction_restart_invalidate(source):
    from beta_engine.infrastructure.db.native_fork_runtime_state import snapshot_proofs
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text('BEGIN IMMEDIATE'))
        driver = session.connection().connection.driver_connection
        row = session.get(BranchSavedRevisionModel, 'saved')
        first = actual_dependency_signature(session, row)
        driver.execute('SAVEPOINT direct_driver')
        driver.execute("UPDATE run_branches SET read_only=1 WHERE branch_id='branch'")
        assert actual_dependency_signature(session, row) != first
        changed = snapshot_proofs(session)
        changes = driver.total_changes
        driver.execute('ROLLBACK TO SAVEPOINT direct_driver')
        assert driver.total_changes == changes
        assert snapshot_proofs(session) is not changed
        assert actual_dependency_signature(session, row) == first
        before = snapshot_proofs(session)
        driver.execute('COMMIT')
        driver.execute('BEGIN')
        assert snapshot_proofs(session) is not before


def test_stale_original_orm_cannot_reuse_completed_validation_after_sql_rehash(source):
    from beta_engine.infrastructure.db.repositories import (
        BranchRevisionStateConflictError,
    )
    engine, factory = source
    repo = SimulationPersistenceRepository(engine=engine, session_factory=factory)
    with factory() as session, native_read_proof_scope():
        session.execute(text('BEGIN IMMEDIATE'))
        row = session.get(BranchSavedRevisionModel, 'saved')
        repo._validated_saved_revision_in_session(session=session, model=row)
        actual_dependency_signature(session, row)
        repo._validated_saved_revision_in_session(session=session, model=row)
        rewrite_source(session, 'Rehashed actual original while ORM remains stale')
        with pytest.raises(BranchRevisionStateConflictError, match='actual stored bytes'):
            repo._validated_saved_revision_in_session(session=session, model=row)


def test_stale_loaded_owner_cannot_certify_changed_actual_origin(source):
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text('BEGIN IMMEDIATE'))
        owner = session.get(RunBranchModel, 'branch')
        row = session.get(BranchSavedRevisionModel, 'saved')
        actual_dependency_signature(session, row)
        session.execute(text("UPDATE run_branches SET read_only=1 WHERE branch_id='branch'"))
        assert not owner.read_only
        with pytest.raises(ValueError, match='Branch owner differs'):
            actual_dependency_signature(session, row)


def test_driver_rollback_from_another_context_invalidates_connection_snapshot(source):
    from concurrent.futures import ThreadPoolExecutor
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text('BEGIN IMMEDIATE'))
        driver = session.connection().connection.driver_connection
        row = session.get(BranchSavedRevisionModel, 'saved')
        first = actual_dependency_signature(session, row)
        driver.execute('SAVEPOINT other_context')
        driver.execute("UPDATE run_branches SET read_only=1 WHERE branch_id='branch'")
        assert actual_dependency_signature(session, row) != first
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(driver.execute, 'ROLLBACK TO SAVEPOINT other_context').result()
        assert actual_dependency_signature(session, row) == first


@pytest.mark.parametrize(('raw', 'expected'), [
    ('{"content":{"calendar_tour_authority":{}},"content":{}}', ()),
    ('{"content":{},"content":{"calendar_tour_authority":{}}}', ('branch',)),
    ('{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":"wrong"}}},' +
     '"\\u0063ontent":{"native_fork_baseline":{"state":{"selected_source_branch_id":"right"}}}}', ('right',)),
    ('{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":"wrong"},' +
     '"state":{"selected_source_branch_id":"right"}}}}', ('right',)),
])
def test_dependency_reference_hints_preserve_python_duplicate_key_semantics(raw, expected):
    from threading import Lock
    from types import SimpleNamespace

    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        _dependency_references,
    )
    row = (None, None, 'branch', None, None, None, None, None, None, raw)
    repo = SimpleNamespace(_revision_validation_lock=Lock())
    assert _dependency_references(repo, row, 'actual-byte-digest') == expected
    assert _dependency_references(repo, row, 'actual-byte-digest') == expected


def test_dependency_reference_hint_retention_is_compact_and_bounded(monkeypatch):
    from threading import Lock
    from types import SimpleNamespace

    from beta_engine.infrastructure.db import native_fork_runtime_state as storage
    monkeypatch.setattr(storage, '_MAX_DEPENDENCY_REFERENCE_HINTS', 2)
    repo = SimpleNamespace(_revision_validation_lock=Lock())
    for index in range(5):
        row = (None, None, 'branch', None, None, None, None, None, None, '{"content":{}}')
        assert storage._dependency_references(repo, row, str(index)) == ()
    assert repo._native_dependency_reference_hints == {'3': (), '4': ()}


def test_oversized_dependency_reference_hint_is_not_retained():
    from threading import Lock
    from types import SimpleNamespace

    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        _dependency_references,
    )
    repo = SimpleNamespace(_revision_validation_lock=Lock())
    branch = 'x' * 1025
    raw = json.dumps({'content': {'native_fork_baseline': {'state': {'selected_source_branch_id': branch}}}})
    row = (None, None, 'branch', None, None, None, None, None, None, raw)
    assert _dependency_references(repo, row, 'fresh-digest') == (branch,)
    assert not getattr(repo, '_native_dependency_reference_hints', {})
