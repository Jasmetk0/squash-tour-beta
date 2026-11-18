"""ORM/engine wiring of Saved v2 storage (see saved_v2_store.py).

* Every SQLite connection gets the read functions; v1 rows never call them.
* A Run receives its immutable storage-format row only when it is CREATED by an
  engine explicitly configured for Saved v2. Nothing else ever adds one.
* A Saved Revision row of a v2 Run is encoded in ``before_insert`` (same
  transaction), and ``after_insert`` re-reads the ACTUAL stored row through the
  ordinary verified read and requires the exact original text before the flush
  can succeed. Any failure aborts the flush, so the surrounding transaction rolls
  back every node and row together.
"""

from __future__ import annotations

import os
import sqlite3
import weakref

from sqlalchemy import DDL, event, insert, inspect as sa_inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from beta_engine.infrastructure.db import saved_v2_store as store
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunContainerModel,
    RunSavedStorageFormatModel,
    SavedRevisionNodeModel,
)

ENVIRONMENT_VARIABLE = "BETA_ENGINE_NEW_RUN_SAVED_STORAGE"
_new_run_formats: "weakref.WeakKeyDictionary[Engine, str]" = weakref.WeakKeyDictionary()


def resolve_new_run_storage(value: str | None) -> str | None:
    """Explicit opt-in only. ``None``/''/'v1' keep the original inline storage."""
    if value is None:
        value = os.environ.get(ENVIRONMENT_VARIABLE, "")
    value = value.strip()
    if value in ("", "v1", "run_saved_revision_v1"):
        return None
    if value in ("saved_v2", store.FORMAT):
        return store.FORMAT
    raise ValueError(f"Unknown Saved storage format for new Runs: {value!r}")


def configure_new_run_storage(engine: Engine, value: str | None) -> None:
    fmt = resolve_new_run_storage(value)
    if fmt is None:
        _new_run_formats.pop(engine, None)
    else:
        _new_run_formats[engine] = fmt


def new_run_storage(engine: Engine) -> str | None:
    return _new_run_formats.get(engine)


# --------------------------------------------------------------------------- engine

_STATE = "saved_v2_connection_state"


@event.listens_for(Engine, "connect")
def _register_functions(dbapi_connection, record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        state = record.info[_STATE] = store.ConnectionState()
        store.register_sqlite_functions(dbapi_connection, state)


def _state_of(conn):
    try:
        return conn.connection.info.get(_STATE)
    except Exception:  # invalidated/closed connection: nothing cached for it
        return None


def _boundary(conn, *_args, **_kwargs):
    store.bump_snapshot(_state_of(conn))


for _name in ("begin", "commit", "rollback", "savepoint", "rollback_savepoint",
              "release_savepoint", "begin_twophase", "prepare_twophase"):
    event.listen(Engine, _name, _boundary)


@event.listens_for(Engine, "before_cursor_execute")
def _statement_boundary(conn, _cursor, statement, _parameters, _context, _executemany):
    # SELECT keeps the snapshot. Own DML keeps authenticated insert-only nodes
    # (see note_own_write). Everything else issued as SQL (BEGIN, COMMIT,
    # ROLLBACK [TO], SAVEPOINT, RELEASE, DDL such as DROP TRIGGER, PRAGMA, ...)
    # ends all reuse.
    verb = statement.lstrip()[:7].upper()
    if verb.startswith(("SELECT", "WITH")):
        return
    if verb.startswith(("INSERT", "UPDATE", "DELETE", "REPLACE")):
        store.note_own_write(_state_of(conn))
        return
    _boundary(conn)


@event.listens_for(Engine, "handle_error")
def _integrity_error(context):
    original = context.original_exception
    if isinstance(original, sqlite3.OperationalError) and "user-defined function" in str(original):
        error = store.take_error()
        if error is not None:
            raise error from original


# --------------------------------------------------------------------------- immutability

_INSERT_ONLY_TRIGGERS = {
    RunSavedStorageFormatModel.__table__: (
        "CREATE TRIGGER IF NOT EXISTS run_saved_storage_formats_no_update BEFORE UPDATE ON "
        "run_saved_storage_formats BEGIN SELECT RAISE(ABORT, 'run_saved_storage_formats is insert-only'); END",
        "CREATE TRIGGER IF NOT EXISTS run_saved_storage_formats_no_delete BEFORE DELETE ON "
        "run_saved_storage_formats BEGIN SELECT RAISE(ABORT, 'run_saved_storage_formats is insert-only'); END",
    ),
    SavedRevisionNodeModel.__table__: (
        "CREATE TRIGGER IF NOT EXISTS saved_revision_nodes_no_update BEFORE UPDATE ON "
        "saved_revision_nodes BEGIN SELECT RAISE(ABORT, 'saved_revision_nodes is insert-only'); END",
        "CREATE TRIGGER IF NOT EXISTS saved_revision_nodes_no_delete BEFORE DELETE ON "
        "saved_revision_nodes BEGIN SELECT RAISE(ABORT, 'saved_revision_nodes is insert-only'); END",
    ),
}
for _table, _statements in _INSERT_ONLY_TRIGGERS.items():
    for _statement in _statements:
        event.listen(_table, "after_create", DDL(_statement))


def _immutable(_mapper, _connection, target):
    raise store.SavedV2IntegrityError(f"{type(target).__tablename__} rows are immutable")


for _model in (RunSavedStorageFormatModel, SavedRevisionNodeModel):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _immutable)


# --------------------------------------------------------------------------- Run creation

@event.listens_for(Session, "before_flush")
def _record_run_format(session, _context, _instances):
    # Before any row of this flush is written, so the Run's first Saved Revision
    # (flushed together with the Run) already sees its recorded format.
    created = [obj for obj in session.new if isinstance(obj, RunContainerModel)]
    if not created:
        return
    connection = session.connection()
    fmt = new_run_storage(connection.engine)
    if fmt is None:
        return
    for run in created:
        connection.execute(insert(RunSavedStorageFormatModel.__table__).values(
            run_id=run.run_id, storage_format=fmt))


# --------------------------------------------------------------------------- Saved rows

_PENDING = "saved_v2_logical_text"


def _driver(connection):
    return connection.connection.driver_connection


def _warm_index_from_parent(connection, target):
    parent = target.parent_revision_id
    if not parent:
        return
    row = connection.execute(
        text("SELECT run_id, payload_json FROM branch_saved_revisions WHERE revision_id = :id"),
        {"id": parent},
    ).first()
    if row is None or row[0] != target.run_id or type(row[1]) is not str:
        return
    if not row[1].startswith(store.ENVELOPE_PREFIX):
        return
    root, _ = store.parse_envelope(row[1], run_id=target.run_id)
    if store.KNOWN.knows_root(target.run_id, root):
        return
    run_id = target.run_id
    store.read_payload(_driver(connection), run_id, row[1],
                       on_value_node=lambda d, t, s, e: store.KNOWN.add(run_id, d, t, s, e))
    store.KNOWN.remember_root(run_id, root)


def _encode(connection, run_id, logical, *, use_index):
    encoder = store.Encoder(run_id, index=store.KNOWN if use_index else None)
    root = encoder.encode(logical)
    return encoder, root


def _missing(connection, run_id, digests):
    found = store.connection_fetch(_driver(connection))(run_id, list(digests)) if digests else {}
    return [d for d in digests if d not in found]


@event.listens_for(BranchSavedRevisionModel, "before_insert")
def _encode_v2_payload(_mapper, connection, target):
    run_id = target.run_id
    logical = target.payload_json
    driver = _driver(connection)
    if not store.run_is_v2(driver, run_id):
        if type(logical) is str and logical.startswith(store.ENVELOPE_PREFIX):
            raise store.SavedV2IntegrityError("A v1 Run cannot store a Saved v2 envelope")
        return
    if type(logical) is not str or logical.startswith(store.ENVELOPE_PREFIX):
        raise store.SavedV2IntegrityError("Saved v2 writers must supply the exact logical payload text")
    try:
        _warm_index_from_parent(connection, target)
    except store.SavedV2IntegrityError:
        # A damaged parent is rejected by the ordinary verified read; the writer
        # simply proceeds without reuse hints.
        store.KNOWN.clear()
    encoder, root = _encode(connection, run_id, logical, use_index=True)
    if encoder.reused and _missing(connection, run_id, _reused_digests(encoder, root)):
        # A hint names a node this transaction cannot see (e.g. rolled back):
        # drop the hints and encode from the text alone.
        store.KNOWN.clear()
        encoder, root = _encode(connection, run_id, logical, use_index=False)
    if encoder.nodes:
        connection.execute(
            insert(SavedRevisionNodeModel.__table__).prefix_with("OR IGNORE"),
            [{"run_id": run_id, "digest": digest, "body": body} for digest, body in encoder.nodes.items()],
        )
    sa_inspect(target).info[_PENDING] = (logical, encoder, root)
    target.payload_json = store.envelope_text(run_id=run_id, root=root, chars=len(logical))


def _reused_digests(encoder, root):
    """Top-most reused subtrees referenced by the new nodes but not emitted here."""
    referenced = {root}
    for body in encoder.nodes.values():
        _kind, children, _pieces = store.parse_node(body)
        referenced.update(children)
    return sorted(referenced - set(encoder.nodes))


@event.listens_for(BranchSavedRevisionModel, "after_insert")
def _verify_v2_payload(_mapper, connection, target):
    info = sa_inspect(target).info
    pending = info.pop(_PENDING, None)
    if pending is None:
        return
    logical, encoder, root = pending
    stored = store.take_handed_off(connection.execute(
        text("SELECT saved_v2_payload(run_id, payload_json) FROM branch_saved_revisions "
             "WHERE revision_id = :id"),
        {"id": target.revision_id},
    ).scalar_one())
    if stored != logical:
        raise store.SavedV2IntegrityError("Stored Saved v2 payload differs from the written text")
    set_committed_value(target, "payload_json", logical)
    for digest, start, end in encoder.value_nodes:
        store.KNOWN.add(target.run_id, digest, logical, start, end)
    store.KNOWN.remember_root(target.run_id, root)


@event.listens_for(BranchSavedRevisionModel, "before_update")
def _immutable_v2_payload(_mapper, connection, target):
    history = sa_inspect(target).attrs.payload_json.history
    if history.has_changes() and store.run_is_v2(_driver(connection), target.run_id):
        raise store.SavedV2IntegrityError("Saved v2 revision payloads are immutable")


__all__ = [
    "ENVIRONMENT_VARIABLE",
    "StatementError",
    "configure_new_run_storage",
    "new_run_storage",
    "resolve_new_run_storage",
]
