"""Actual-row authority and suffix replay for independent native fork aggregates."""

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic_core import SchemaValidator, core_schema
from sqlalchemy import event as sqlalchemy_event, inspect as sqlalchemy_inspect
from sqlalchemy.engine import Engine

from beta_engine.application.calendar_tour_service import CalendarTourCommit
from beta_engine.application.native_fork_runtime_reducer import (
    initial_runtime,
    prepare_command,
    source_inputs,
)
from beta_engine.domain.native_fork_runtime import ForkRuntimeCommand, NativeForkRuntime
from beta_engine.domain.run_revisions import canonical_json
from beta_engine.domain.tournaments.calendar_tour import CalendarTourReceipt
from beta_engine.infrastructure.db.exact_text_digest import physical_text_sha256
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.run_prospect_source_state import (
    load_saved_run_prospect_source,
)

KEY = "native_fork_runtime"
SAVED_SCHEMA = "native_fork_saved_root.v2"
DRAFT_SCHEMA = "native_fork_runtime_draft.v1"
_proofs = ContextVar("native_read_proofs", default=None)
_append_ancestor_proofs = ContextVar("append_ancestor_proofs", default=None)
_MAX_DEPENDENCY_PROOFS = 256
_MAX_DEPENDENCY_REFERENCE_HINTS = 4096
_MAX_DEPENDENCY_REFERENCE_BYTES = 1024
_MAX_PARSED_RUNTIMES = 8
_MAX_PARSED_RUNTIME_BYTES = 8 * 1024 * 1024


def _projection_object(**fields):
    return core_schema.typed_dict_schema({
        key: core_schema.typed_dict_field(value, required=False)
        for key, value in fields.items()
    }, extra_behavior='ignore', strict=True)


_DEPENDENCY_PROJECTION = SchemaValidator(_projection_object(content=_projection_object(
    native_fork_baseline=_projection_object(state=_projection_object(
        selected_source_branch_id=core_schema.nullable_schema(core_schema.str_schema(strict=True)),
    )),
    calendar_tour_authority=_projection_object(),
)), config=core_schema.CoreConfig(cache_strings=False))


def _dependency_content(raw):
    """Extract routing data without materializing unrelated Saved components.

    This is NOT a Saved decoder. Every actual byte still enters the physical
    signature and the original full payload/component/hash/replay gates. The
    projection discards large population/rally trees that this reference walk
    never reads. Unfamiliar shapes retain Python's original JSON path, including
    its duplicate-key behavior and errors. No decoded payload or proof is kept.
    """
    if type(raw) is str:
        try:
            return _DEPENDENCY_PROJECTION.validate_json(raw, strict=True).get('content', {})
        except (TypeError, ValueError):
            pass
    return json.loads(raw).get('content', {})


@sqlalchemy_event.listens_for(Engine, "before_cursor_execute")
def _invalidate_physical_read_cache(connection, cursor, statement, parameters, context, executemany):
    memo = _proofs.get()
    if memo is None or statement.lstrip()[:6].upper() == "SELECT":
        return
    # Includes SAVEPOINT/ROLLBACK TO and direct SQL writes, not just ORM flushes.
    key = ("native_dependency_sql_generation", connection.connection.driver_connection)
    memo[key] = memo.get(key, 0) + 1


def _statement_may_change_snapshot(statement):
    """Everything except a plain or function-nested SELECT counts as a change.

    SQLite's trace reports statements run inside a user function (the Saved v2
    reader's own node SELECTs) as ``-- <sql>``; a nested SELECT cannot change
    this snapshot. Trigger bodies and any other statement still count.
    """
    text = statement.lstrip()
    if text.startswith("-- "):
        text = text[3:].lstrip()
    return text[:6].upper() != "SELECT"


def _physical_read_cache(session):
    """Reuse actual bytes only inside one unchanged SQLite read snapshot.

    This is not a validation proof or a cross-request cache. Every new transaction
    rereads all dependencies. Own writes (including direct SQL and savepoint
    rollback) invalidate it; pending ORM work disables it until flushed.
    """
    memo = _proofs.get()
    if memo is None or session.new or session.dirty or session.deleted:
        return None
    sqlalchemy_connection = session.connection()
    connection = sqlalchemy_connection.connection.driver_connection
    if not getattr(connection, "in_transaction", False) or type(getattr(connection, "total_changes", None)) is not int:
        return None
    if not sqlalchemy_connection.info.get("native_dependency_trace_installed"):
        # total_changes does not change on ROLLBACK TO. Observe SQLite itself so
        # direct driver savepoints/transactions cannot reuse an earlier snapshot.
        connection_info = sqlalchemy_connection.info
        def trace(statement):
            if _statement_may_change_snapshot(statement):
                # Connection-local, including calls from another Python context.
                # Do not retain SQL text, parameters, rows or request objects.
                connection_info["native_dependency_sqlite_generation"] = connection_info.get("native_dependency_sqlite_generation", 0) + 1
        connection.set_trace_callback(trace)
        sqlalchemy_connection.info["native_dependency_trace_installed"] = True
    snapshot = (
        session.get_transaction(),
        session.get_nested_transaction(), connection, connection.total_changes,
        memo.get(("native_dependency_sql_generation", connection), 0),
        sqlalchemy_connection.info.get("native_dependency_sqlite_generation", 0),
    )
    key = ("native_dependency_physical_rows", session)
    previous = memo.get(key)
    if previous is None or previous[0] != snapshot:
        if previous is not None:
            # The old snapshot's rows, retained models and proofs of their
            # strings must not outlive it (see canonical_text).
            from beta_engine.infrastructure.db.canonical_text import clear_operation_proofs
            clear_operation_proofs()
        previous = memo[key] = (snapshot, {"owners": {}, "revisions": {}, "proofs": {}})
    return previous[1]


def retain_saved_model(session, model):
    """Keep one loaded Saved ORM row alive for this unchanged read snapshot.

    SQLAlchemy's identity map is weak. A lineage walk dropped each row after use,
    so every later ``Session.get`` of the same revision selected, materialized
    and copied its complete payload text again (W9: ~8 full reads of each of 53
    revisions, 23 GB of text in one cold Tour read). Retaining an object neither
    validates it nor replaces any gate: the dependency reader reuses only a row
    the ORM actually loaded from SQLite in this same unchanged snapshot (see
    _remember_snapshot_loaded_row) and selects every other row afresh. The
    reference disappears with the snapshot cache on any change or scope exit.
    """
    if model is None:
        return model
    cache = _physical_read_cache(session)
    if cache is not None:
        cache.setdefault("retained_models", {})[(model.run_id, model.revision_id)] = model
    return model


def may_hold_validation_proof(session, run_id, revision_id):
    """False only for a Saved v2 row whose text digest this process never bound.

    A validation proof is keyed by the SHA-256 of the row's exact text. When
    this process has not bound that digest to the row's stored envelope
    (``saved_v2_store.TEXT_DIGESTS``), checking the proof cache would first
    materialize and hash the complete text only to find no proof (a cold
    process). Treating the row as unproven is never weaker: it is validated
    in full. v1 rows and unknown shapes return True (the ordinary check).
    """
    from sqlalchemy import select

    from beta_engine.infrastructure.db import saved_v2_store

    connection, state = _connection_and_state(session)
    if not saved_v2_store.run_is_v2(connection, run_id, saved_v2_store.snapshot_cache(connection, state)):
        return True
    stored = session.execute(select(_raw_payload_column()).select_from(BranchSavedRevisionModel).where(
        BranchSavedRevisionModel.run_id == run_id,
        BranchSavedRevisionModel.revision_id == revision_id,
    )).scalar()
    if type(stored) is not str or not stored.startswith(saved_v2_store.ENVELOPE_PREFIX):
        return True
    root, chars = saved_v2_store.parse_envelope(stored, run_id=run_id)
    return saved_v2_store.TEXT_DIGESTS.get(run_id, root, chars) is not None


def release_snapshot_saved_text(session, run_id, revision_id):
    """Stop holding one fully validated Saved v2 row's text in this snapshot.

    A cold lineage validation reads every historical ``payload_json``. The
    snapshot read cache, the retained ORM row, the digest memo and the
    operation's canonical-text proofs each kept that complete text alive until
    the request ended (W9: 2.7 GB of texts for 53 revisions, held from the first
    seconds; W12 is quadratic in the revision count). Call this only after the
    revision's own validation finished. Nothing here grants anything:

    * The text's SHA-256 is bound to its ACTUAL stored envelope, read now in
      the same unchanged snapshot whose verified reader produced the text
      (``saved_v2_store.remember_text_sha256``). A later digest still requires
      every reachable node to be re-fetched and re-hashed (``stored_text_sha256``).
    * Each cached physical row keeps every field; its text becomes the
      ``StoredTextDigest`` of exactly those characters. A consumer that needs the
      characters re-reads them from SQLite and compares that digest
      (``_materialized_row``), as for any row the reader never materialized.
    * The retained ORM row's ``payload_json`` is expired. An access loads the
      actual stored text again; an unloaded column has no in-memory copy that
      could differ (``row_matches_model``).

    v1 rows, rows of another Run, a dirty session or a row without a cached
    text are left untouched. Returns the number of released references.
    """
    from sqlalchemy import select

    from beta_engine.infrastructure.db import saved_v2_store
    from beta_engine.infrastructure.db.canonical_text import forget_operation_text
    from beta_engine.infrastructure.db.exact_text_digest import DIGESTS

    cache = _physical_read_cache(session)
    if cache is None:
        return 0
    key = (run_id, revision_id)
    retained = cache.get("retained_models", {}).get(key)
    texts = []

    def collect(value):
        if type(value) is str and not any(value is known for known in texts):
            texts.append(value)

    if retained is not None:
        collect(sqlalchemy_inspect(retained).dict.get("payload_json"))
    for name in ("loaded_rows", "physical_rows"):
        row = cache.get(name, {}).get(key)
        if row is not None:
            collect(row[9])
    for name in ("revisions", "unreferenced_revisions"):
        entry = cache.get(name, {}).get(key)
        if entry is not None and entry[0] is not None:
            collect(entry[0][9])
    memo = cache.get(DIGESTS, {}).get((run_id, revision_id, "payload_json"))
    if memo is not None:
        collect(memo[0])
    if not texts:
        return 0
    connection, state = _connection_and_state(session)
    if not saved_v2_store.run_is_v2(connection, run_id, saved_v2_store.snapshot_cache(connection, state)):
        return 0  # a v1 text IS its stored value; keep the original behaviour
    stored = session.execute(select(_raw_payload_column()).select_from(BranchSavedRevisionModel).where(
        BranchSavedRevisionModel.run_id == run_id,
        BranchSavedRevisionModel.revision_id == revision_id,
    )).scalar()
    if type(stored) is not str or not stored.startswith(saved_v2_store.ENVELOPE_PREFIX):
        return 0
    _root, chars = saved_v2_store.parse_envelope(stored, run_id=run_id)
    text = texts[0]
    if len(text) != chars or any(other != text for other in texts[1:]):
        # Different characters (or a size that differs from the envelope) for
        # one immutable row: never pick one. The ordinary gates decide.
        return 0
    digest = physical_text_sha256(cache, run_id=run_id, revision_id=revision_id,
                                  column="payload_json", text=text)
    saved_v2_store.remember_text_sha256(run_id, stored, text, digest)
    stand_in = StoredTextDigest(digest, chars)

    def held(value):
        return type(value) is str and any(value is known for known in texts)

    released = 0
    for name in ("loaded_rows", "physical_rows"):
        rows = cache.get(name, {})
        row = rows.get(key)
        if row is not None and held(row[9]):
            rows[key] = (*row[:9], stand_in, *row[10:])
            released += 1
    for name in ("revisions", "unreferenced_revisions"):
        entries = cache.get(name, {})
        entry = entries.get(key)
        if entry is not None and entry[0] is not None and held(entry[0][9]):
            entries[key] = ((*entry[0][:9], stand_in, *entry[0][10:]), *entry[1:])
            released += 1
    # physical_text_sha256 above memoizes (text, digest) when it had to hash.
    memo = cache.get(DIGESTS, {}).get((run_id, revision_id, "payload_json"))
    if memo is not None and held(memo[0]):
        del cache[DIGESTS][(run_id, revision_id, "payload_json")]
        released += 1
    if retained is not None and held(sqlalchemy_inspect(retained).dict.get("payload_json")):
        state_of = sqlalchemy_inspect(retained)
        if state_of.session is session and state_of.persistent and not state_of.modified:
            session.expire(retained, ["payload_json"])
            released += 1
    for value in texts:
        released += forget_operation_text(value)
    released += saved_v2_store.forget_snapshot_text(connection, run_id, stored, state=state)
    return released


@sqlalchemy_event.listens_for(BranchSavedRevisionModel, "load")
def _remember_snapshot_loaded_row(target, context):
    """An ORM load IS an actual read of these bytes in the current snapshot.

    Record the freshly loaded row (not an identity-map hit, which fires no load
    event) in this snapshot's physical read cache, so the dependency reader of
    the SAME unchanged snapshot need not select and materialize the same bytes
    again. The cache is discarded on any write, savepoint or new transaction,
    and is disabled while the session has pending changes.
    """
    if _proofs.get() is None:
        return
    session = getattr(context, "session", None)
    if session is None:
        return
    cache = _physical_read_cache(session)
    if cache is None:
        return
    attributes = sqlalchemy_inspect(target).dict
    field_names = tuple(field.key for field in _physical_revision_fields())
    if any(name not in attributes for name in field_names):
        return  # An ORM projection may defer some of the physical fields.
    key = (attributes["run_id"], attributes["revision_id"])
    known = cache["revisions"].get(key) or cache.get("unreferenced_revisions", {}).get(key)
    if known is not None:
        # The physical reader already holds these bytes; keeping this second
        # copy alive would only double the snapshot's memory. When it holds
        # only the authenticated digest of the stored text, this load read
        # the same stored row through the verified reader in the SAME
        # snapshot, so its text has that digest (exact_text_digest then
        # recognizes this very string object; any other string is hashed).
        row = known[0]
        loaded = tuple(attributes[name] for name in field_names)
        if (
            row is not None
            and type(row[9]) is StoredTextDigest
            and loaded[:9] == tuple(row[:9])
            and loaded[10] == row[10]
            and type(loaded[9]) is str
            and len(loaded[9]) == row[9].chars
        ):
            from beta_engine.infrastructure.db.exact_text_digest import DIGESTS

            cache.setdefault(DIGESTS, {})[(key[0], key[1], "payload_json")] = (loaded[9], row[9].digest)
        return
    # The object itself can later be changed without marking the session dirty
    # (e.g. set_committed_value). Record what SQLite supplied at load time.
    cache.setdefault("loaded_rows", {})[key] = tuple(attributes[name] for name in field_names)
    cache.setdefault("retained_models", {})[key] = target


def snapshot_proofs(session):
    """Completed operation proofs cannot outlive their actual read snapshot."""
    cache = _physical_read_cache(session)
    return cache["proofs"] if cache is not None else {}


def actual_saved_revision_reference(session, run_id, revision_id):
    """Fresh identity/topology only, never a payload or component proof.

    A complete actual graph read may already own these fields in this unchanged
    SQLite snapshot. Otherwise select the five small fields, not every rally and
    historical population merely to follow one parent edge.
    """
    from sqlalchemy import select

    cache = _physical_read_cache(session)
    known = cache["revisions"].get((run_id, revision_id)) if cache is not None else None
    if known is not None:
        return known[0][:5] if known[0] is not None else None
    row = session.execute(select(
        BranchSavedRevisionModel.revision_id, BranchSavedRevisionModel.run_id,
        BranchSavedRevisionModel.branch_id, BranchSavedRevisionModel.sequence,
        BranchSavedRevisionModel.parent_revision_id,
    ).where(BranchSavedRevisionModel.revision_id == revision_id)).first()
    return tuple(row) if row is not None else None


def assert_current_saved_row(session, revision):
    """A source ORM identity is not evidence of its current physical bytes."""
    memo = _proofs.get()
    if memo is None or not memo.get("native_actual_reads"):
        return
    cache = _physical_read_cache(session)
    cached = cache["revisions"].get((revision.run_id, revision.revision_id)) if cache is not None else None
    actual = cached[0] if cached is not None else read_physical_row(
        session, revision.run_id, revision.revision_id, cache)
    if actual is None or not row_matches_model(cache, actual, revision):
        raise ValueError("Native Saved row differs from its actual stored bytes")


class StoredTextDigest:
    """An actual Saved v2 text authenticated by its digest, not materialized.

    Stands in a physical row tuple for the exact ``payload_json`` text whose
    SHA-256 ``saved_v2_store.stored_text_sha256`` just bound to this row's actual
    envelope and the actual, re-hashed node bodies of the current snapshot. It is
    never equal to any string: a consumer that needs the characters must
    materialize them (see ``_materialized_row``); ``row_matches_model`` compares an
    ORM text by its own SHA-256.
    """

    __slots__ = ("digest", "chars")

    def __init__(self, digest, chars):
        self.digest, self.chars = digest, chars

    def __repr__(self):
        return f"StoredTextDigest({self.digest.hex()[:12]}, chars={self.chars})"


def _connection_and_state(session):
    sqlalchemy_connection = session.connection()
    state = sqlalchemy_connection.connection.info.get("saved_v2_connection_state")
    return sqlalchemy_connection.connection.driver_connection, state


def _raw_payload_column():
    from sqlalchemy import Text, literal_column

    # The STORED column value (a v2 envelope), not the verified materialization
    # that SavedPayloadText.column_expression compiles for payload_json.
    return literal_column("branch_saved_revisions.payload_json", Text())


def _stored_v2_digest(session, row_run_id, stored):
    from beta_engine.infrastructure.db import saved_v2_store

    connection, state = _connection_and_state(session)
    digest = saved_v2_store.stored_text_sha256(connection, row_run_id, stored, state=state)
    if digest is None:
        return None
    _root, chars = saved_v2_store.parse_envelope(stored, run_id=row_run_id)
    return StoredTextDigest(digest, chars)


def _remember_stored_text(read_cache, row, stored):
    """After hashing a just materialized v2 text, memo its digest by envelope."""
    from beta_engine.infrastructure.db import saved_v2_store

    if type(row[9]) is str and type(stored) is str and stored.startswith(saved_v2_store.ENVELOPE_PREFIX):
        digest = physical_text_sha256(read_cache, run_id=row[1], revision_id=row[0],
                                      column="payload_json", text=row[9])
        saved_v2_store.remember_text_sha256(row[1], stored, row[9], digest)


def read_physical_row(session, run_id, revision_id, read_cache):
    """Actual physical fields of one Saved row in the current snapshot.

    For a Saved v2 row whose text digest this process already knows, the stored
    envelope is read and every node it reaches is re-fetched and re-hashed; the
    text itself is NOT materialized again and ``payload_json`` is represented by
    a ``StoredTextDigest``. Every other row (unknown digest, v1) returns its
    exactly materialized text, as before.
    """
    from sqlalchemy import select

    from beta_engine.infrastructure.db import saved_v2_store

    fields = _physical_revision_fields()
    where = (BranchSavedRevisionModel.run_id == run_id,
             BranchSavedRevisionModel.revision_id == revision_id)
    connection, state = _connection_and_state(session)
    if not saved_v2_store.run_is_v2(connection, run_id, saved_v2_store.snapshot_cache(connection, state)):
        # v1: the stored value IS the text (the reader still rejects an envelope).
        actual = session.execute(select(*fields).where(*where)).first()
        return tuple(actual[:len(fields)]) if actual is not None else None
    small = session.execute(select(*fields[:9], _raw_payload_column(), fields[10]).where(*where)).first()
    if small is None:
        return None
    stored = small[9]
    known = _stored_v2_digest(session, small[1], stored)
    if known is not None:
        return (*tuple(small[:9]), known, small[10])
    actual = session.execute(select(*fields, _raw_payload_column()).where(*where)).first()
    if actual is None:
        return None
    row = tuple(actual[:len(fields)])
    if actual[len(fields)] == stored:
        _remember_stored_text(read_cache, row, stored)
    return row


def _materialized_row(session, row, read_cache):
    """The same physical row with its exact text, checked against its digest."""
    if type(row[9]) is not StoredTextDigest:
        return row
    from sqlalchemy import select

    fields = _physical_revision_fields()
    actual = session.execute(select(*fields).where(
        BranchSavedRevisionModel.run_id == row[1],
        BranchSavedRevisionModel.revision_id == row[0],
    )).first()
    text = actual[9] if actual is not None else None
    if (
        actual is None
        or tuple(actual[:9]) != tuple(row[:9])
        or actual[10] != row[10]
        or type(text) is not str
        or len(text) != row[9].chars
        # A transient read for this caller only: hash it without memoizing
        # (text, digest), which would keep every such text alive in the
        # snapshot cache (a bounded cold walk re-reads released ancestors).
        or hashlib.sha256(text.encode("utf-8")).digest() != row[9].digest
    ):
        raise ValueError("Native Saved row differs from its actual stored bytes")
    # Nor keep it in the Saved v2 snapshot cache: its verified nodes stay cached.
    from beta_engine.infrastructure.db import saved_v2_store

    connection, state = _connection_and_state(session)
    stored = session.execute(select(_raw_payload_column()).select_from(BranchSavedRevisionModel).where(
        BranchSavedRevisionModel.run_id == row[1],
        BranchSavedRevisionModel.revision_id == row[0],
    )).scalar()
    saved_v2_store.forget_snapshot_text(connection, row[1], stored, state=state)
    return (*row[:9], text, row[10])


def _has_physical_fields(revision):
    """Whether ``revision`` carries the physical fields, without loading any."""
    if sqlalchemy_inspect(revision, raiseerr=False) is not None:
        return True  # a mapped Saved row; an unloaded column is compared as actual
    return hasattr(revision, "payload_json")


def stored_column_sha256(model, column):
    """SHA-256 of one actual stored column of ``model``'s row in the current snapshot.

    For an ORM row that has not loaded ``column``: the physical reader of the
    current native read scope supplies the digest (an authenticated Saved v2
    ``StoredTextDigest`` or the hash of the actual text). None outside such a
    scope or for a row that is not persistent in a session.
    """
    state = sqlalchemy_inspect(model, raiseerr=False)
    session = getattr(state, "session", None)
    if session is None or _proofs.get() is None or column not in _LARGE_TEXT_FIELDS.values():
        return None
    cache = _physical_read_cache(session)
    if cache is None:
        return None
    identity = state.identity
    if not identity or identity[0] != model.__dict__.get("revision_id") or "run_id" not in model.__dict__:
        return None
    key = (model.__dict__["run_id"], identity[0])
    known = cache["revisions"].get(key) or cache.get("unreferenced_revisions", {}).get(key)
    if known is not None:
        row = known[0]
    else:
        rows = cache.setdefault("physical_rows", {})
        if key not in rows:
            rows[key] = read_physical_row(session, key[0], key[1], cache)
        row = rows[key]
    if row is None or row[1] != key[0] or row[0] != key[1]:
        return None
    index = next(i for i, name in _LARGE_TEXT_FIELDS.items() if name == column)
    value = row[index]
    if type(value) is StoredTextDigest:
        return value.digest
    if type(value) is str:
        return physical_text_sha256(cache, run_id=row[1], revision_id=row[0], column=column, text=value)
    return None


def row_matches_model(read_cache, row, model):
    """Exact equality of an actual physical row and an ORM row's fields.

    A ``StoredTextDigest`` matches only an ORM text of the same length whose own
    SHA-256 equals the authenticated stored digest.
    """
    from beta_engine.infrastructure.db.exact_text_digest import unloaded_column

    fields = _physical_revision_fields()
    if len(row) != len(fields):
        return False
    for index, field in enumerate(fields):
        actual = row[index]
        if index in _LARGE_TEXT_FIELDS and unloaded_column(model, field.key):
            # Not loaded into this ORM row: any access reads the actual stored
            # value, so no in-memory copy can differ from it.
            continue
        value = getattr(model, field.key)
        if type(actual) is StoredTextDigest:
            if (
                type(value) is not str
                or len(value) != actual.chars
                or physical_text_sha256(read_cache, run_id=row[1], revision_id=row[0],
                                        column=_LARGE_TEXT_FIELDS[index], text=value) != actual.digest
            ):
                return False
        elif actual != value:
            return False
    return True


# Indexes into _physical_revision_fields(): payload_json and change_summary_json.
_LARGE_TEXT_FIELDS = {9: "payload_json", 10: "change_summary_json"}


def _physical_revision_fields():
    return tuple(getattr(BranchSavedRevisionModel, key) for key in (
        "revision_id", "run_id", "branch_id", "sequence", "parent_revision_id",
        "kind", "payload_schema_version", "content_hash_algorithm", "content_hash",
        "payload_json", "change_summary_json",
    ))


@contextmanager
def native_read_proof_scope():
    from beta_engine.infrastructure.db.canonical_text import operation_proof_scope

    token = _proofs.set({}) if _proofs.get() is None else None
    try:
        # Canonical-text proofs of this operation's exact strings live exactly
        # as long as this outermost read scope (see canonical_text.py).
        with operation_proof_scope():
            yield _proofs.get()
    finally:
        if token is not None:
            _proofs.reset(token)


def _canonical_runtime_identity(raw):
    """Canonical component proof and state JSON, each large subtree encoded once.

    The component is REQUIRED to have exactly two keys: fingerprint and state.
    With sort_keys=True its original canonical JSON is precisely
    {"fingerprint":<json>,"state":<json>}. Hash the same UTF-8 bytes in
    pieces; do not re-encode the potentially multi-MB state a second time.
    SHA-256 identity, Unicode/float JSON semantics and cache byte limits
    remain identical to canonical_json(raw).encode("utf-8").
    """
    state_json = canonical_json(raw["state"]).encode("utf-8")
    prefix = (
        b'{"fingerprint":'
        + canonical_json(raw["fingerprint"]).encode("utf-8")
        + b',"state":'
    )
    digest = hashlib.sha256()
    digest.update(prefix)
    digest.update(state_json)
    digest.update(b"}")
    return digest.digest(), len(prefix) + len(state_json) + 1, state_json


def load_runtime(payload):
    raw = payload.get("content", {}).get(KEY)
    if not isinstance(raw, dict) or set(raw) != {"state", "fingerprint"}:
        raise ValueError("Malformed native fork runtime component")
    signature, size, state_json = _canonical_runtime_identity(raw)
    memo = _proofs.get()
    cache = memo.setdefault("parsed_native_runtimes", {}) if memo is not None else {}
    prior = cache.pop(signature, None)
    if prior is not None:
        cache[signature] = prior
        return prior[1]
    runtime = NativeForkRuntime.model_validate_json(state_json)
    if runtime.fingerprint != raw["fingerprint"]:
        raise ValueError("Native fork runtime fingerprint differs")
    if memo is not None and size <= _MAX_PARSED_RUNTIME_BYTES:
        cache[signature] = (size, runtime)
        while len(cache) > _MAX_PARSED_RUNTIMES or sum(item[0] for item in cache.values()) > _MAX_PARSED_RUNTIME_BYTES:
            cache.pop(next(iter(cache)))
    return runtime


def component(runtime):
    return {
        "state": runtime.model_dump(mode="json"),
        "fingerprint": runtime.fingerprint,
    }


def commit_prepared(previous, candidate, request, result, version):
    return NativeForkRuntime.model_validate_json(
        candidate.model_copy(
            update={
                "tour": candidate.tour.model_copy(
                    update={
                        "receipts": candidate.tour.receipts
                        + (
                            CalendarTourReceipt(
                                command_id=request.command.command_id,
                                request=request.model_dump(mode="json"),
                                result=result,
                            ),
                        )
                    }
                ),
                "journal": previous.journal
                + (
                    ForkRuntimeCommand(
                        draft_version_before=version,
                        request=request.model_dump(mode="json"),
                        result=result,
                    ),
                ),
            }
        ).model_dump_json()
    )


def verify_runtime(repository, session, *, runtime, revision, original, working=False):
    reachable = set()
    ancestors = []
    if working:
        reachable.add(revision.revision_id)
        ancestors.append(session.get(BranchSavedRevisionModel, revision.revision_id))
    parent, sequence = revision.parent_revision_id, revision.sequence
    while parent:
        if parent in reachable:
            raise ValueError("Native fork Saved ancestry contains a cycle")
        row = session.get(BranchSavedRevisionModel, parent)
        if row is None or row.run_id != runtime.run_id or row.sequence != sequence - 1:
            raise ValueError(
                "Native fork Saved ancestry is missing, foreign or discontinuous"
            )
        reachable.add(parent)
        ancestors.append(row)
        parent, sequence = row.parent_revision_id, row.sequence
    root_id = runtime.root_saved_revision_id
    if root_id != revision.revision_id:
        if root_id not in reachable:
            raise ValueError("Native fork root is unreachable")
        row = session.get(BranchSavedRevisionModel, root_id)
        if (row.run_id, row.branch_id, row.kind, row.payload_schema_version) != (
            runtime.run_id,
            runtime.branch_id,
            "branch_fork_materialized",
            SAVED_SCHEMA,
        ):
            raise ValueError("Native fork root is not its actual target installation")
        root = repository._validated_saved_revision_in_session(
            session=session, model=row
        )
        signed_root = load_runtime(root.payload)
        if signed_root.baseline != runtime.baseline or signed_root.journal:
            raise ValueError("Native fork root has another baseline/history")
    sources = source_inputs(original, repository, session)
    expected = initial_runtime(runtime.baseline, root_id, sources)
    cache = {}
    journal = [e.model_dump(mode="json") for e in runtime.journal]
    # Reuse a COMPLETE proof of an actual reachable Saved prefix, never a
    # self-declared fingerprint. Only the new suffix needs another MatchEngine run.
    for row in ancestors:
        if (
            row.branch_id != runtime.branch_id
            or row.payload_schema_version != SAVED_SCHEMA
        ):
            continue
        raw = (
            json.loads(row.payload_json)
            .get("content", {})
            .get(KEY, {})
            .get("state", {})
        )
        prefix = raw.get("journal")
        if (
            not isinstance(prefix, list)
            or len(prefix) > len(journal)
            or prefix != journal[: len(prefix)]
        ):
            continue
        record = repository._validated_saved_revision_in_session(
            session=session, model=row
        )
        signed = load_runtime(record.payload)
        if (
            signed.baseline != runtime.baseline
            or signed.root_saved_revision_id != root_id
        ):
            raise ValueError("Native fork Saved prefix has another root")
        expected = signed
        cache[row.revision_id] = (record, signed)
        break
    for event in runtime.journal[len(expected.journal) :]:
        request = CalendarTourCommit.model_validate_json(canonical_json(event.request))
        saved_id = request.command.expected_saved_head
        if saved_id not in reachable:
            raise ValueError("Fork command source is outside its actual Saved past")
        if saved_id not in cache:
            row = session.get(BranchSavedRevisionModel, saved_id)
            if row is None or (row.run_id, row.branch_id) != (
                runtime.run_id,
                runtime.branch_id,
            ):
                raise ValueError("Fork command source has a foreign owner")
            record = repository._validated_saved_revision_in_session(
                session=session, model=row
            )
            cache[saved_id] = (record, load_runtime(record.payload))
        record, signed = cache[saved_id]
        if (
            signed.baseline != runtime.baseline
            or len(signed.journal) > len(expected.journal)
            or signed.journal != expected.journal[: len(signed.journal)]
        ):
            raise ValueError("Fork command source is not its actual Saved prefix")
        per_command = type(sources)(**vars(sources))
        from beta_engine.domain.calendar.run_calendar import RunCalendar

        per_command.execution_calendar = RunCalendar.from_metadata(
            record.payload["run"]["run_calendar"]
        )
        per_command.prospects = load_saved_run_prospect_source(
            record.payload, run_id=runtime.run_id
        )
        from beta_engine.infrastructure.db.calendar_native_tour import (
            recorded_turn_pro_model,
        )

        # Re-run the exact recorded Master v87 model, if this command ran one.
        per_command.turn_pro_model = recorded_turn_pro_model(event.result)
        preview, candidate, result = prepare_command(
            expected,
            request.command,
            per_command,
            saved_head=saved_id,
            draft_version=event.draft_version_before,
            is_saved=signed == expected,
        )
        if (
            preview["preview_fingerprint"] != request.expected_preview_fingerprint
            or result != event.result
        ):
            raise ValueError("Native fork command differs from actual confirmed replay")
        expected = commit_prepared(
            expected, candidate, request, result, event.draft_version_before
        )
    if expected != runtime:
        raise ValueError(
            "Native fork current facts differ from its actual source and complete replay"
        )
    return runtime


def _proven_dependency_branches(row):
    """The same reference set, read from PROVEN canonical actual payload text.

    Only when these exact freshly read characters are proven to be their own
    canonical JSON encoding (canonical_text.py) are the two inputs taken from
    their exact spans: whether ``content`` has ``calendar_tour_authority`` and
    ``content.native_fork_baseline.state.selected_source_branch_id``. Any other
    shape or text returns None and the original parser decides.
    """
    import json as _json

    from beta_engine.infrastructure.db.canonical_text import PROOFS

    raw = row[9]
    if type(raw) is not str or len(raw) < 64 * 1024:
        return None  # small rows: the original projection parse is cheap
    proof = PROOFS.prove(raw, scope=row[1])
    if proof is None or proof.layout.keys is None:
        return None
    content = proof.layout.keys.get("content")
    if content is None or content.keys is None:
        return None
    branches = set()
    baseline = content.keys.get("native_fork_baseline")
    if baseline is not None:
        value = _json.loads(raw[baseline.start:baseline.end])
        if not isinstance(value, dict):
            return None
        state = value.get("state")
        if isinstance(state, dict):
            selected = state.get("selected_source_branch_id")
            if selected is not None and type(selected) is not str:
                return None
            branches.add(selected)
        elif state is not None:
            return None
    if "calendar_tour_authority" in content.keys:
        branches.add(row[2])
    return branches


def _seed_loaded_text_digest(session, read_cache, row):
    """Digest of an ORM-materialized v2 text of THIS snapshot via its envelope.

    Reads only the small stored envelope of the same row. When this process
    already hashed the text of that exact envelope and every reachable node
    re-hashes now, the ORM text (same snapshot, same immutable row) has that
    digest; otherwise the caller hashes the characters and the digest is then
    remembered for the envelope.
    """
    from sqlalchemy import select

    from beta_engine.infrastructure.db import saved_v2_store
    from beta_engine.infrastructure.db.exact_text_digest import DIGESTS

    known = read_cache.get(DIGESTS, {}).get((row[1], row[0], "payload_json"))
    if known is not None and known[0] is row[9]:
        return
    connection, state = _connection_and_state(session)
    if not saved_v2_store.run_is_v2(connection, row[1], saved_v2_store.snapshot_cache(connection, state)):
        return  # a v1 row's text IS its stored value; nothing to bind
    stored = session.execute(select(_raw_payload_column()).select_from(BranchSavedRevisionModel).where(
        BranchSavedRevisionModel.run_id == row[1],
        BranchSavedRevisionModel.revision_id == row[0],
    )).scalar()
    if type(stored) is not str or not stored.startswith(saved_v2_store.ENVELOPE_PREFIX):
        return
    digest = _stored_v2_digest(session, row[1], stored)
    if digest is not None and digest.chars == len(row[9]):
        read_cache.setdefault(DIGESTS, {})[(row[1], row[0], "payload_json")] = (row[9], digest.digest)
    else:
        _remember_stored_text(read_cache, row, stored)


def _dependency_references(repository, row, digest, materialize=None):
    """Bounded parse hints, never a validation proof or a stored hash shortcut.

    The caller just reread and hashed every actual physical field. Owners, heads
    and graph topology are still rebuilt from the current transaction below.
    Python's duplicate-key semantics must match the Saved JSON verifier; SQLite
    json_extract chooses a different value when duplicate keys are present.
    """
    if repository is not None:
        with repository._revision_validation_lock:
            hints = getattr(repository, "_native_dependency_reference_hints", {})
            if digest in hints:
                return hints[digest]
    transient = type(row[9]) is StoredTextDigest
    if transient:
        if materialize is None:
            raise ValueError("Native Saved row text is not available for its references")
        row = materialize()
    try:
        # A text read again only for this hint (a released or never-held row)
        # takes the original projection parser: proving it would retain it in
        # the operation's proofs and replace the scope's newest reference.
        branches = None if transient else _proven_dependency_branches(row)
        if branches is None:
            content = _dependency_content(row[9])
            baseline = content.get("native_fork_baseline", {}).get("state")
            branches = {baseline.get("selected_source_branch_id")} if isinstance(baseline, dict) else set()
            if "calendar_tour_authority" in content:
                branches.add(row[2])
        result = tuple(branches)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Native Saved row contains malformed JSON dependency data") from exc
    retain = all(branch is None or isinstance(branch, str) for branch in result)
    retain = retain and sum(len(branch.encode("utf-8")) for branch in result if branch is not None) <= _MAX_DEPENDENCY_REFERENCE_BYTES
    if repository is not None and retain:
        with repository._revision_validation_lock:
            hints = getattr(repository, "_native_dependency_reference_hints", None)
            if hints is None:
                hints = repository._native_dependency_reference_hints = {}
            hints[digest] = result
            while len(hints) > _MAX_DEPENDENCY_REFERENCE_HINTS:
                hints.pop(next(iter(hints)))
    return result


def _actual_branch_owner(session, run_id, branch_id):
    from sqlalchemy import select

    from beta_engine.infrastructure.db.models import RunBranchModel

    fields = (
        RunBranchModel.branch_id, RunBranchModel.run_id,
        RunBranchModel.forked_from_branch_id, RunBranchModel.forked_from_saved_revision_id,
        RunBranchModel.status, RunBranchModel.read_only, RunBranchModel.saved_head_revision_id,
    )
    row = session.execute(
        select(*fields).where(RunBranchModel.run_id == run_id, RunBranchModel.branch_id == branch_id)
    ).first()
    actual = tuple(row) if row is not None else None
    loaded = session.identity_map.get((RunBranchModel, (branch_id,), None))
    if loaded is not None and actual != tuple(getattr(loaded, field.key) for field in fields):
        raise ValueError("Native Branch owner differs from its actual stored bytes")
    return actual


def actual_dependency_signature(session, revision, *, repository=None):
    """Exact physical dependency graph, rebuilt before any cross-read proof reuse.

    A self-declared hash is insufficient. Include complete stored bytes, topology,
    actual owner origins, and current source-Branch reachability. Own later Saves
    need not invalidate an immutable prefix; a change to ANY dependency does.
    Only successfully completed proofs enter the bounded repository cache.
    """
    from sqlalchemy import select

    fields = _physical_revision_fields()
    memo = _proofs.get()
    if memo is not None:
        memo["native_actual_reads"] = True
    read_cache = _physical_read_cache(session)
    owners = read_cache["owners"] if read_cache is not None else {}
    revisions = read_cache["revisions"] if read_cache is not None else {}

    def actual_owner(branch_id):
        key = (revision.run_id, branch_id)
        if key not in owners:
            owners[key] = _actual_branch_owner(session, revision.run_id, branch_id)
        return owners[key]

    unreferenced = read_cache.setdefault("unreferenced_revisions", {}) if read_cache is not None else {}

    def read_revision(revision_id):
        """Actual row and signature; dependency references are added later."""
        key = (revision.run_id, revision_id)
        if key in unreferenced:
            return unreferenced[key]
        row = read_cache.get("loaded_rows", {}).get(key) if read_cache is not None else None
        if row is not None and read_cache is not None and type(row[9]) is str:
            # The ORM materialized this text in the same unchanged snapshot.
            # Bind its digest through the actual envelope and re-hashed nodes
            # when known instead of hashing every character again.
            _seed_loaded_text_digest(session, read_cache, row)
        if row is None and read_cache is not None and key in read_cache.get("physical_rows", {}):
            row = read_cache["physical_rows"][key]
        if row is None:
            row = read_physical_row(session, revision.run_id, revision_id, read_cache)
        if row is None:
            unreferenced[key] = (None, None)
        else:
            loaded = session.identity_map.get(
                (BranchSavedRevisionModel, (revision_id,), None))
            if loaded is not None and loaded.run_id == row[1]:
                # Share the identical text object with the loaded row so the
                # snapshot holds one copy and identity-keyed proof/digest
                # memos match. Only characters equal to the fresh SELECT are
                # shared; a different ORM value keeps the actual bytes.
                from beta_engine.infrastructure.db.exact_text_digest import unloaded_column

                def same_loaded_text(index, value):
                    if index not in _LARGE_TEXT_FIELDS or unloaded_column(loaded, _LARGE_TEXT_FIELDS[index]):
                        return False
                    text = getattr(loaded, _LARGE_TEXT_FIELDS[index])
                    if type(value) is str:
                        return text == value
                    # A row authenticated by its digest only (e.g. released by
                    # a bounded cold walk) while the ORM row holds a text of
                    # this snapshot: share it only when its OWN SHA-256 is the
                    # authenticated digest, so the proven text (and its
                    # canonical proof) serves the reference parse below.
                    return (type(value) is StoredTextDigest and type(text) is str
                            and len(text) == value.chars
                            and physical_text_sha256(read_cache, run_id=row[1], revision_id=row[0],
                                column=_LARGE_TEXT_FIELDS[index], text=text) == value.digest)

                row = tuple(
                    getattr(loaded, _LARGE_TEXT_FIELDS[index]) if same_loaded_text(index, value) else value
                    for index, value in enumerate(row)
                )
                retain_saved_model(session, loaded)
            digest = hashlib.sha256()
            for index, value in enumerate(row):
                if type(value) is StoredTextDigest and index in _LARGE_TEXT_FIELDS:
                    # The same SHA-256 of the same actual text, authenticated
                    # through its envelope and re-hashed nodes (see above).
                    digest.update(b"h")
                    digest.update(value.digest)
                    continue
                if type(value) is str and index in _LARGE_TEXT_FIELDS:
                    # Commit to the exact SHA-256 of these actual bytes. The
                    # same read scope hashes each physical text only once.
                    digest.update(b"h")
                    digest.update(physical_text_sha256(read_cache, run_id=row[1],
                        revision_id=row[0], column=_LARGE_TEXT_FIELDS[index], text=value))
                    continue
                raw = canonical_json(value).encode("utf-8") if not isinstance(value, str) else value.encode("utf-8")
                digest.update(b"s" if isinstance(value, str) else b"j")
                digest.update(len(raw).to_bytes(8, "big"))
                digest.update(raw)
            signature = digest.hexdigest()
            unreferenced[key] = (row, signature)
        return unreferenced[key]

    def actual_revision(revision_id):
        key = (revision.run_id, revision_id)
        if key not in revisions:
            # The walk discovers a Branch HEAD before its parents. Read the not
            # yet referenced parent chain first and derive references oldest
            # first, so each routing proof can compare with its predecessor's
            # proven text instead of re-encoding a whole HEAD (W9: 5.8 s for one
            # 122 M-character text). The same rows, signatures and references
            # result; the main walk below still visits every node itself.
            chain, current = [], revision_id
            while current and (revision.run_id, current) not in revisions and current not in chain:
                chain.append(current)
                row = read_revision(current)[0]
                current = row[4] if row is not None else None
            for member in reversed(chain):
                row, signature = read_revision(member)
                revisions[(revision.run_id, member)] = (
                    (None, None, ()) if row is None
                    else (row, signature, _dependency_references(repository, row, signature,
                        materialize=lambda row=row: _materialized_row(session, row, read_cache))))
                unreferenced.pop((revision.run_id, member), None)
        return revisions[key]

    # Within ONE unchanged SQLite read snapshot every row, owner and digest is
    # fixed, so the complete walk from a node is fixed as well. A later walk in
    # the same snapshot that reaches such a node merges its complete closure
    # instead of re-expanding it (exactly the nodes/entries the walk would add).
    # A snapshot change (any own write, savepoint rollback or new transaction)
    # discards this memo together with every cached row.
    closures = read_cache.setdefault("dependency_closures", {}) if read_cache is not None else {}
    pending, visited, graph, source_heads = [revision.revision_id], set(), [], {}
    while pending:
        revision_id = pending.pop()
        if revision_id in visited:
            continue
        known = closures.get((revision.run_id, revision_id)) if revision_id != revision.revision_id else None
        if known is not None:
            for entry in known[0]:
                if entry[0] not in visited:
                    visited.add(entry[0])
                    graph.append(entry)
            source_heads.update(known[1])
            continue
        visited.add(revision_id)
        row, digest, branch_ids = actual_revision(revision_id)
        if revision_id == revision.revision_id and _has_physical_fields(revision):
            if row is None or not row_matches_model(read_cache, row, revision):
                raise ValueError(
                    "Native Saved row differs from its actual stored bytes"
                )
        if row is None:
            graph.append((revision_id, None))
            continue
        owner = actual_owner(row[2])
        graph.append(
            (
                revision_id,
                digest,
                owner[:-1] if owner else None,
            )
        )
        if row[4]:
            pending.append(row[4])
        for branch_id in branch_ids:
            source = actual_owner(branch_id)
            source_heads[branch_id] = source
            if source and source[-1]:
                pending.append(source[-1])
    if read_cache is None:
        return (
            revision.revision_id,
            tuple(sorted(graph)),
            tuple(sorted(source_heads.items())),
        )
    closures[(revision.run_id, revision.revision_id)] = (tuple(graph), dict(source_heads))
    # Identical node sets OF THE SAME RUN in one snapshot have identical sorted
    # graph values (rows and owners are looked up by Run); share them and their
    # canonical JSON instead of re-sorting/re-encoding. Another Run's equal
    # revision-ID set is a different physical graph.
    shared = read_cache.setdefault("dependency_graphs", {})
    node_set = (revision.run_id, frozenset(visited))
    known_graph = shared.get(node_set)
    if known_graph is None:
        sorted_graph = tuple(sorted(graph))
        sorted_heads = tuple(sorted(source_heads.items()))
        known_graph = shared[node_set] = (
            sorted_graph, sorted_heads, canonical_json(sorted_graph), canonical_json(sorted_heads))
        if memo is not None:
            encoded = memo.setdefault("dependency_graph_json", {})
            encoded[id(sorted_graph)] = (sorted_graph, known_graph[2])
            encoded[id(sorted_heads)] = (sorted_heads, known_graph[3])
    return (revision.revision_id, known_graph[0], known_graph[1])


def install_verified_global_save_head(session, branch, revision, staged, staged_proofs, *, repository):
    """Install a staged HEAD and recheck its physical dependency graph.

    The staged graph already contains the new row and its prior HEAD parent.
    If actual SQLite reports a single statement and row change, and the row
    changed is exactly this Branch pointer, its only new graph edge targets the
    already verified new row. Any other statement, trigger, side effect, dirty
    input or snapshot change retains the ordinary complete physical reread.
    """
    memo = _proofs.get()
    snapshot_key = ("native_dependency_physical_rows", session)
    before = None
    verified_row = None
    if snapshot_proofs(session) is staged_proofs:
        before, rows = memo[snapshot_key]
        key = (revision.run_id, revision.revision_id)
        row = rows["revisions"].get(key)
        verified_row = row[0] if row is not None else None
        del rows

    branch.saved_head_revision_id = revision.revision_id
    session.flush()
    if before is not None and verified_row is not None and _physical_read_cache(session) is not None:
        after = memo[snapshot_key][0]
        if after[:3] == before[:3] and after[3:] == tuple(value + 1 for value in before[3:]):
            if not row_matches_model(_physical_read_cache(session), verified_row, revision):
                raise ValueError("Native Saved row differs from its actual stored bytes")
            heads = dict(staged[2])
            previous = heads.get(branch.branch_id)
            current = _actual_branch_owner(session, branch.run_id, branch.branch_id)
            if (
                previous
                and current == (*previous[:-1], revision.revision_id)
                and _physical_read_cache(session) is not None
                and memo[snapshot_key][0] == after
            ):
                heads[branch.branch_id] = current
                return (revision.revision_id, staged[1], tuple(sorted(heads.items())))
    return actual_dependency_signature(session, revision, repository=repository)


def has_actual_dependency_proof(repository, signature, *, run_id, branch_id):
    """A history walk must not evict the complete current-HEAD proof."""
    proof_key = _dependency_proof_key(signature)
    scoped = _append_ancestor_proofs.get()
    if scoped is not None and scoped[0] is repository and proof_key in scoped[1]:
        return True
    with repository._revision_validation_lock:
        heads = getattr(repository, "_native_head_dependency_proofs", {})
        key = (run_id, branch_id)
        if heads.get(key) == proof_key:
            heads[key] = heads.pop(key)  # bounded, recently used Branch heads
            return True
        proofs = getattr(repository, "_native_dependency_proofs", {})
        return proof_key in proofs


def _dependency_proof_key(signature):
    # Keep only a compact cryptographic digest of the COMPLETE actual graph,
    # never mutable payloads. Longer histories can retain their proven prefixes
    # without an unbounded collection of overlapping graph tuples.
    memo = _proofs.get()
    encoded = memo.get("dependency_graph_json") if memo is not None else None
    if encoded and type(signature) is tuple and len(signature) == 3 and type(signature[0]) is str:
        graph = encoded.get(id(signature[1]))
        heads = encoded.get(id(signature[2]))
        if graph is not None and heads is not None and graph[0] is signature[1] and heads[0] is signature[2]:
            # Exactly canonical_json(signature): a JSON array's encoding is its
            # elements' encodings joined by "," (same separators/sort_keys).
            text = "[" + canonical_json(signature[0]) + "," + graph[1] + "," + heads[1] + "]"
            return hashlib.sha256(text.encode("utf-8")).hexdigest()
    return hashlib.sha256(canonical_json(signature).encode("utf-8")).hexdigest()


def assert_global_save_append(before, after, *, run_id, branch_id, revision_id, installed):
    """Compare complete actual graphs around one already verified global Save.

    This is NOT component/origin validation. The Save coordinator must first
    authenticate the old complete lineage and independently verify the new row.
    No existing byte, owner, source HEAD or topology may change. Only the exact
    new row and, after installation, this Branch's HEAD may be added/advanced.
    """
    if after[0] != revision_id or before[0] == revision_id:
        raise ValueError("Global Save append has inconsistent revision identity")
    old = {row[0]: row[1:] for row in before[1]}
    new = {row[0]: row[1:] for row in after[1]}
    if set(new) != set(old) | {revision_id} or any(new[key] != value for key, value in old.items()):
        raise ValueError("Global Save changed an existing actual dependency")
    digest, owner = new[revision_id]
    if not digest or not owner or owner[:2] != (branch_id, run_id):
        raise ValueError("Global Save append has a foreign actual owner")
    old_heads, new_heads = dict(before[2]), dict(after[2])
    if set(old_heads) != set(new_heads) or branch_id not in old_heads:
        raise ValueError("Global Save changed its actual source owners")
    for source_id, previous in old_heads.items():
        current = new_heads[source_id]
        if source_id == branch_id and installed:
            if (not previous or not current or previous[:-1] != current[:-1]
                or previous[-1] != before[0] or current[-1] != revision_id):
                raise ValueError("Global Save did not install its exact actual HEAD")
        elif current != previous:
            raise ValueError("Global Save changed an actual source HEAD")
    return tuple(row_id for row_id, (_digest, actual_owner) in new.items()
        if actual_owner and actual_owner[:2] == (branch_id, run_id))


@contextmanager
def reuse_verified_append_ancestors(repository, before, after, *, run_id, branch_id):
    """Carry only already-proven ancestors across one exact uncommitted append."""
    try:
        owned = assert_global_save_append(
            before, after, run_id=run_id, branch_id=branch_id,
            revision_id=after[0], installed=True,
        )
    except ValueError:
        yield ()  # A non-equivalent graph keeps the ordinary validation path.
        return
    ancestors = tuple(
        revision_id
        for revision_id in owned
        if revision_id != after[0] and has_actual_dependency_proof(
            repository, (revision_id, before[1], before[2]),
            run_id=run_id, branch_id=branch_id,
        )
    )
    keys = {_dependency_proof_key((revision_id, after[1], after[2])) for revision_id in ancestors}
    token = _append_ancestor_proofs.set((repository, keys))
    try:
        yield ancestors
    finally:
        _append_ancestor_proofs.reset(token)


def remember_committed_global_append(repository, signature, revision_ids, *, run_id, branch_id):
    """Only after commit: retain proofs from the verified exact graph append.

    Every later lookup still rebuilds the COMPLETE actual graph. Different source
    bytes/heads/owners cannot match these keys. Shared foreign ancestry is never
    promoted: its ordinary independent source proof remains required.
    """
    keys = tuple(_dependency_proof_key((revision_id, signature[1], signature[2]))
        for revision_id in revision_ids)
    head = _dependency_proof_key(signature)
    with repository._revision_validation_lock:
        proofs = getattr(repository, "_native_dependency_proofs", None)
        if proofs is None:
            proofs = repository._native_dependency_proofs = {}
        for key in keys:
            proofs[key] = True
        while len(proofs) > _MAX_DEPENDENCY_PROOFS:
            proofs.pop(next(iter(proofs)))
        heads = getattr(repository, "_native_head_dependency_proofs", None)
        if heads is None:
            heads = repository._native_head_dependency_proofs = {}
        key = (run_id, branch_id)
        heads.pop(key, None)
        heads[key] = head
        while len(heads) > 16:
            heads.pop(next(iter(heads)))


def remember_committed_ancestor_proofs(repository, signature, revision_ids):
    """Only after commit: re-key proofs of already authenticated OLD revisions.

    Unlike remember_committed_global_append this never records a HEAD proof:
    the caller's newly appended revision has not passed the repository
    validator, so it must not gain the complete-graph shortcut. Each key still
    binds the COMPLETE actual graph; any later change makes it unusable.
    """
    keys = tuple(_dependency_proof_key((revision_id, signature[1], signature[2]))
        for revision_id in revision_ids)
    with repository._revision_validation_lock:
        proofs = getattr(repository, "_native_dependency_proofs", None)
        if proofs is None:
            proofs = repository._native_dependency_proofs = {}
        for key in keys:
            proofs.pop(key, None)
            proofs[key] = True
        while len(proofs) > _MAX_DEPENDENCY_PROOFS:
            proofs.pop(next(iter(proofs)))


def verify_with_actual_dependencies(repository, session, revision, verify):
    """Reuse a complete proof only when its entire actual dependency graph matches."""
    signature = actual_dependency_signature(session, revision, repository=repository)
    if has_actual_dependency_proof(repository, signature, run_id=revision.run_id, branch_id=revision.branch_id):
        return
    verify()
    proof_key = _dependency_proof_key(signature)
    from sqlalchemy import select

    from beta_engine.infrastructure.db.models import RunBranchModel

    actual_head = session.scalar(select(RunBranchModel.saved_head_revision_id).where(
        RunBranchModel.run_id == revision.run_id, RunBranchModel.branch_id == revision.branch_id,
    ))
    with repository._revision_validation_lock:
        proofs = getattr(repository, "_native_dependency_proofs", None)
        if proofs is None:
            proofs = repository._native_dependency_proofs = {}
        proofs[proof_key] = True
        while len(proofs) > _MAX_DEPENDENCY_PROOFS:
            proofs.pop(next(iter(proofs)))
        if actual_head == revision.revision_id:
            heads = getattr(repository, "_native_head_dependency_proofs", None)
            if heads is None:
                heads = repository._native_head_dependency_proofs = {}
            key = (revision.run_id, revision.branch_id)
            heads.pop(key, None)
            heads[key] = proof_key
            while len(heads) > 16:
                heads.pop(next(iter(heads)))
