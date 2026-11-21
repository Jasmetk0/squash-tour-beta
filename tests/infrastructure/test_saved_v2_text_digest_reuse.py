"""Reuse of an actual Saved v2 text digest across SQLite snapshots (real SQLite).

A dependency/physical-row signature needs SHA-256 of every Saved payload text.
For a v2 row that text is a deterministic function of its stored envelope and of
content-addressed node bodies. A digest computed from an earlier materialization
may be reused in a NEW snapshot only after every reachable node is re-fetched and
re-hashed there; any changed, missing or foreign node, a different envelope or a
changed row relationship must not reuse it. Component tests: no HTTP.
"""

import hashlib
import json

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm.attributes import set_committed_value

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db import saved_v2_store as st
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.native_fork_runtime_state import (
    StoredTextDigest,
    actual_dependency_signature,
    native_read_proof_scope,
)
from tests.application.test_full_simulation_task_calendar import setup_calendar
from tests.infrastructure.test_saved_v2_store import _child_digest, _sqlite_store, canonical, payload

pytestmark = pytest.mark.pr_critical


@pytest.fixture(autouse=True)
def _fresh_digest_index():
    st.TEXT_DIGESTS.clear()
    yield
    st.TEXT_DIGESTS.clear()


# --------------------------------------------------------------------------- store level

def _remember(connection, envelope, state):
    connection.execute("BEGIN")
    logical = st.read_payload(connection, "run", envelope, state=state)
    st.remember_text_sha256("run", envelope, logical, hashlib.sha256(logical.encode()).digest())
    connection.execute("COMMIT")
    st.bump_snapshot(state)
    return logical


def test_digest_needs_a_prior_hash_and_then_reauthenticates_without_materializing(tmp_path, monkeypatch):
    logical = canonical(payload(events=3))
    _path, connection, envelope, state = _sqlite_store(tmp_path, logical)
    connection.execute("BEGIN")
    assert st.stored_text_sha256(connection, "run", envelope, state=state) is None
    connection.execute("ROLLBACK")
    st.bump_snapshot(state)
    _remember(connection, envelope, state)

    fetched = []
    original_fetch = st.connection_fetch

    def counting_fetch(dbapi_connection):
        fetch = original_fetch(dbapi_connection)
        return lambda run_id, digests: fetched.extend(digests) or fetch(run_id, digests)

    monkeypatch.setattr(st, "connection_fetch", counting_fetch)
    monkeypatch.setattr(st, "_materialize_nodes", lambda *a, **k: pytest.fail("materialized"))
    connection.execute("BEGIN")
    digest = st.stored_text_sha256(connection, "run", envelope, state=state)
    assert digest == hashlib.sha256(logical.encode()).digest()
    nodes = {d for (d,) in connection.execute("SELECT digest FROM saved_revision_nodes")}
    assert set(fetched) == nodes          # every actual node re-read in this snapshot
    connection.execute("ROLLBACK")


@pytest.mark.parametrize("change, error", [
    ("UPDATE saved_revision_nodes SET body = body || ' ' WHERE digest = ?", "does not match"),
    ("DELETE FROM saved_revision_nodes WHERE digest = ?", "missing"),
    ("UPDATE saved_revision_nodes SET run_id = 'foreign' WHERE digest = ?", "missing"),
])
def test_changed_missing_or_foreign_node_never_reuses_the_digest(tmp_path, change, error):
    logical = canonical(payload(events=3))
    path, connection, envelope, state = _sqlite_store(tmp_path, logical)
    _remember(connection, envelope, state)
    import sqlite3

    other = sqlite3.connect(path)
    other.execute(change, (_child_digest(other, envelope),))
    other.commit()
    connection.execute("BEGIN")
    with pytest.raises(st.SavedV2IntegrityError, match=error):
        st.stored_text_sha256(connection, "run", envelope, state=state)
    connection.execute("ROLLBACK")


def test_other_envelope_size_or_run_is_a_different_key(tmp_path):
    logical = canonical(payload(events=2))
    _path, connection, envelope, state = _sqlite_store(tmp_path, logical)
    _remember(connection, envelope, state)
    root, chars = st.parse_envelope(envelope, run_id="run")
    connection.execute("BEGIN")
    forged = st.envelope_text(run_id="run", root=root, chars=chars + 1)
    assert st.stored_text_sha256(connection, "run", forged, state=state) is None
    other_root = st.envelope_text(run_id="run", root="0" * 64, chars=chars)
    assert st.stored_text_sha256(connection, "run", other_root, state=state) is None
    with pytest.raises(st.SavedV2IntegrityError, match="v1 Run contains a v2"):
        st.stored_text_sha256(connection, "other", envelope, state=state)
    # An inline (downgraded) row of a v2 Run is rejected as by the reader.
    with pytest.raises(st.SavedV2IntegrityError, match="inline"):
        st.stored_text_sha256(connection, "run", logical, state=state)
    connection.execute("ROLLBACK")


# --------------------------------------------------------------------------- physical signature

@pytest.fixture
def v2_history(tmp_path, monkeypatch):
    monkeypatch.setenv("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "saved_v2")
    engine, factory, repo = setup_calendar(tmp_path, RunCalendar(52, 1, 2030, 2))
    with factory.begin() as session:
        parent = session.get(BranchSavedRevisionModel, "saved")
        body = json.loads(parent.payload_json)
        body["run"]["display_name"] = "Second signed revision"
        session.add(BranchSavedRevisionModel(
            revision_id="child", run_id="run", branch_id="branch", sequence=2,
            parent_revision_id="saved", kind="calendar_tour_authority",
            payload_schema_version=parent.payload_schema_version,
            content_hash_algorithm=parent.content_hash_algorithm,
            content_hash="0" * 64, payload_json=json.dumps(body, sort_keys=True, separators=(",", ":")),
            change_summary_json="{}",
        ))
    with engine.begin() as connection:
        stored = connection.exec_driver_sql("SELECT payload_json FROM branch_saved_revisions").fetchall()
        assert all(row[0].startswith(st.ENVELOPE_PREFIX) for row in stored)
        for trigger in ("saved_revision_nodes_no_update", "saved_revision_nodes_no_delete"):
            connection.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trigger}")  # a tamperer
    yield engine, factory, repo
    engine.dispose()


def _signature(history, *, physical_rows=None):
    _engine, factory, repository = history
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN"))
        child = session.get(BranchSavedRevisionModel, "child")
        result = actual_dependency_signature(session, child, repository=repository)
        if physical_rows is not None:
            from beta_engine.infrastructure.db.native_fork_runtime_state import _physical_read_cache

            physical_rows.update(_physical_read_cache(session)["revisions"])
        session.rollback()
    return result


def _count_materializations(engine):
    calls = []

    def count(_connection, _cursor, statement, _parameters, _context, _many):
        if "saved_v2_payload(" in statement and "branch_saved_revisions" in statement:
            calls.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    return calls, lambda: event.remove(engine, "before_cursor_execute", count)


def test_signature_is_identical_and_the_old_text_is_not_materialized_again(v2_history):
    engine, _factory, _repository = v2_history
    first = _signature(v2_history)            # hashes and records both texts
    calls, stop = _count_materializations(engine)
    rows = {}
    try:
        second = _signature(v2_history, physical_rows=rows)
    finally:
        stop()
    assert second == first
    # Only the ORM load of the target row itself; the parent came from its
    # envelope and re-hashed nodes.
    assert len(calls) == 1
    assert type(rows[("run", "saved")][0][9]) is StoredTextDigest
    st.TEXT_DIGESTS.clear()
    assert _signature(v2_history) == first    # the ordinary full path agrees


def _tamper(engine, sql, *parameters):
    with engine.begin() as connection:
        connection.exec_driver_sql(sql, parameters)


def test_changed_node_of_an_old_revision_fails_closed(v2_history):
    engine = v2_history[0]
    _signature(v2_history)
    with engine.connect() as connection:
        child_root = st.parse_envelope(connection.exec_driver_sql(
            "SELECT payload_json FROM branch_saved_revisions WHERE revision_id='child'").scalar(), run_id="run")[0]
        parent_root = st.parse_envelope(connection.exec_driver_sql(
            "SELECT payload_json FROM branch_saved_revisions WHERE revision_id='saved'").scalar(), run_id="run")[0]
    assert parent_root != child_root
    _tamper(engine, "UPDATE saved_revision_nodes SET body = body || ' ' WHERE run_id='run' AND digest = ?",
            parent_root)
    with pytest.raises(ValueError):
        _signature(v2_history)


def test_changed_envelope_or_relationship_changes_the_signature(v2_history):
    engine = v2_history[0]
    first = _signature(v2_history)
    # Point the parent row at the CHILD's genuine nodes: a valid but different row.
    _tamper(engine, "UPDATE branch_saved_revisions SET payload_json = "
            "(SELECT payload_json FROM branch_saved_revisions WHERE revision_id='child') "
            "WHERE revision_id='saved'")
    swapped = _signature(v2_history)
    assert swapped != first
    _tamper(engine, "UPDATE branch_saved_revisions SET parent_revision_id = NULL WHERE revision_id='child'")
    detached = _signature(v2_history)
    assert detached not in (first, swapped)
    assert {entry[0] for entry in detached[1]} == {"child"}


def test_in_memory_text_cannot_match_an_authenticated_stored_digest(v2_history):
    _engine, factory, repository = v2_history
    _signature(v2_history)
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN IMMEDIATE"))
        child = session.get(BranchSavedRevisionModel, "child")
        actual_dependency_signature(session, child, repository=repository)
        set_committed_value(child, "payload_json", child.payload_json.replace("Second", "Other!"))
        # Any write starts a new snapshot: the row is reread (by digest), and
        # the in-memory ORM text must not certify it.
        session.execute(text("UPDATE run_branches SET read_only = read_only"))
        with pytest.raises(ValueError, match="actual stored bytes"):
            actual_dependency_signature(session, child, repository=repository)
        session.rollback()


def test_a_later_orm_load_of_the_same_snapshot_is_bound_to_the_authenticated_digest(v2_history):
    from beta_engine.infrastructure.db.exact_text_digest import DIGESTS
    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        _physical_read_cache,
        assert_current_saved_row,
    )

    _engine, factory, repository = v2_history
    _signature(v2_history)
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN"))
        child = session.get(BranchSavedRevisionModel, "child")
        actual_dependency_signature(session, child, repository=repository)
        cache = _physical_read_cache(session)
        assert type(cache["revisions"][("run", "saved")][0][9]) is StoredTextDigest
        parent = session.get(BranchSavedRevisionModel, "saved")   # an actual load, now
        bound = cache[DIGESTS][("run", "saved", "payload_json")]
        assert bound[0] is parent.payload_json
        assert bound[1] == hashlib.sha256(parent.payload_json.encode()).digest()
        assert_current_saved_row(session, parent)
        # A different in-memory string is hashed on its own and rejected.
        set_committed_value(parent, "payload_json", parent.payload_json.replace("Task", "Fake"))
        with pytest.raises(ValueError, match="actual stored bytes"):
            assert_current_saved_row(session, parent)
        session.rollback()
