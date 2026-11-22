"""SHA-256 of exact stored Saved Revision text, computed once per read snapshot.

One Saved read walks the complete lineage and needs the digest of every physical
``payload_json``/``change_summary_json`` in several independent gates (routing,
validation signature, actual dependency graph, origin projections). Those gates
re-encoded and re-hashed the same multi-megabyte strings three or more times per
revision per request.

This is a pure function cache, never an authority:

* every returned value is ``sha256(text.encode('utf-8')).digest()`` of the text
  passed in;
* the only stored digests belong to texts that the native physical read cache
  of the current SQLite snapshot already holds (the actual row it just read).
  A caller's text reuses such a digest only when it is that same ``str`` object
  or byte-for-byte equal to it (``==`` of two exact ``str`` values). A different,
  stale or tampered text is hashed on its own;
* nothing is stored for any other text (besides the text of an ORM row that the
  same snapshot cache already retains), so no additional string is kept alive,
  and the memo disappears with its read snapshot/proof scope. No identifier,
  declared hash or earlier request can supply a digest for different bytes.
"""

import hashlib

DIGESTS = "exact_text_sha256"


def physical_text_sha256(cache, *, run_id, revision_id, column, text):
    """Digest one text of an ACTUAL row the physical read cache now retains."""
    known = cache.get(DIGESTS, {}).get((run_id, revision_id, column)) if cache is not None else None
    if known is not None and known[0] is text:
        return known[1]  # this exact string object was hashed in this snapshot
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    if cache is not None and type(text) is str:
        cache.setdefault(DIGESTS, {})[(run_id, revision_id, column)] = (text, digest)
    return digest


def unloaded_column(row, column):
    """True when an ORM row has not loaded ``column`` (e.g. a deferred payload).

    Reading such an attribute would load it from SQLite; its value IS the
    actual stored value, not an in-memory copy that could differ from it.
    """
    from sqlalchemy import inspect

    state = inspect(row, raiseerr=False)
    return state is not None and column in state.unloaded


def row_text_sha256(row, column):
    """``sha256`` of one Saved Revision column of an ORM row, without rehashing.

    Looks up the current native read scope's physical row cache for the same
    session without touching the session (no autobegin, flush or query).
    A column the ORM row has not loaded is the actual stored text itself: its
    digest is taken from the physical reader of the current snapshot (which
    may authenticate a Saved v2 text by envelope and re-hashed nodes) instead
    of materializing the text into the row.
    """
    if unloaded_column(row, column):
        from beta_engine.infrastructure.db.native_fork_runtime_state import stored_column_sha256

        digest = stored_column_sha256(row, column)
        if digest is not None:
            return digest
    text = getattr(row, column)
    known = entry = None
    if type(text) is str:
        from sqlalchemy import inspect

        from beta_engine.infrastructure.db.native_fork_runtime_state import _proofs

        memo = _proofs.get()
        state = inspect(row, raiseerr=False) if memo is not None else None
        session = getattr(state, "session", None)
        entry = memo.get(("native_dependency_physical_rows", session)) if session is not None else None
        if entry is not None:
            known = entry[1].get(DIGESTS, {}).get(
                (getattr(row, "run_id", None), getattr(row, "revision_id", None), column))
    if known is not None and type(known[0]) is str and (known[0] is text or known[0] == text):
        return known[1]
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    if entry is not None and type(text) is str and entry[1].get("retained_models", {}).get(
            (getattr(row, "run_id", None), getattr(row, "revision_id", None))) is row:
        # A row this snapshot retains (native_fork_runtime_state.retain_saved_model)
        # already keeps its string alive; remember the digest of that exact object
        # so the physical reader does not hash the same characters again.
        entry[1].setdefault(DIGESTS, {})[(row.run_id, row.revision_id, column)] = (text, digest)
    return digest
