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
* nothing is stored for any other text, so no additional string is kept alive,
  and the memo disappears with its read snapshot/proof scope. No identifier,
  declared hash or earlier request can supply a digest for different bytes.
"""

import hashlib

DIGESTS = "exact_text_sha256"


def physical_text_sha256(cache, *, run_id, revision_id, column, text):
    """Digest one text of an ACTUAL row the physical read cache now retains."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    if cache is not None and type(text) is str:
        cache.setdefault(DIGESTS, {})[(run_id, revision_id, column)] = (text, digest)
    return digest


def row_text_sha256(row, column):
    """``sha256`` of one Saved Revision column of an ORM row, without rehashing.

    Looks up the current native read scope's physical row cache for the same
    session without touching the session (no autobegin, flush or query).
    """
    text = getattr(row, column)
    known = None
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
    return hashlib.sha256(text.encode("utf-8")).digest()
