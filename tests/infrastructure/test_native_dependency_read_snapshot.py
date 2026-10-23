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
