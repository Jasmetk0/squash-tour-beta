"""Reuse the strict decode of byte-identical v13 sporting checkpoint parts.

A v13 checkpoint is ``competition_root`` plus an append-mostly tuple of event
parts (global slots, sporting weeks, follow-up knockouts). Between two Saves
almost every part is byte-identical, yet every Admin read, Preview, Execute and
Save strictly decoded the complete history again (about 15 s for the 162 MB
checkpoint of the 1,000-player W12 snapshot), because the whole value exceeds
the 64 MiB value caches.

``decode`` is the ONLY entry: it runs the caller's original strict parser on
exactly the text the original path parses (``json.dumps(part)``). The key is
the SHA-256 of that complete text, its length and the parser identity, so a hit
means the parser would receive the same characters and return the same value.
The stored form is the pickled validated model, never a model: every use
unpickles a fresh, private object graph, so no caller can observe or mutate a
value another caller holds, and nothing here needs an ownership protocol.

The parsers must be pure functions of their text. The only validation context
in this code base, the engine's deferred event-hash check, bypasses reuse.

Nothing here is a physical, lineage, source or ownership proof. It never
replaces a row read, a byte comparison, a declared-hash check or a replay; it
only avoids repeating the pure strict decode of identical text. A part that is
new, changed, unknown, oversized or not picklable takes the original parse.
"""

from __future__ import annotations

import hashlib
import pickle
import threading
from collections import OrderedDict

MAX_CACHE_BYTES = 256 * 1024 * 1024
MAX_PART_BYTES = 64 * 1024 * 1024

_lock = threading.Lock()
_entries: OrderedDict = OrderedDict()
_state = {"bytes": 0}
_stats = {"hits": 0, "misses": 0, "uncached": 0, "evictions": 0, "pickle_errors": 0,
          "parsed_bytes": 0, "reused_bytes": 0}


def parser_identity(parse):
    """A stable name for ``parse``: the model class of a bound validator, or the function."""
    owner = getattr(parse, "__self__", None)
    target = owner if isinstance(owner, type) else parse
    return f"{target.__module__}.{target.__qualname__}:{getattr(parse, '__name__', '')}"


def decode(text, parse):
    """``(parse(text), key)``; a hit unpickles a fresh copy of the identical decode."""
    data = text.encode("utf-8")
    from beta_engine.domain.matches import content_hash
    if len(data) > MAX_PART_BYTES or content_hash._deferred.get() is not None:
        # Oversized, or inside an engine factory whose deferred hash check
        # makes validation context dependent: the original parse, not retained.
        with _lock:
            _stats["uncached"] += 1
            _stats["parsed_bytes"] += len(data)
        return parse(text), None
    key = (parser_identity(parse), len(data), hashlib.sha256(data).digest())
    with _lock:
        blob = _entries.get(key)
        if blob is not None:
            _entries.move_to_end(key)
    if blob is not None:
        try:
            value = pickle.loads(blob)
        except Exception:  # noqa: BLE001 - never trust a damaged entry; parse again
            with _lock:
                if _entries.pop(key, None) is not None:
                    _state["bytes"] -= len(blob)
                _stats["pickle_errors"] += 1
        else:
            with _lock:
                _stats["hits"] += 1
                _stats["reused_bytes"] += len(data)
            return value, key
    value = parse(text)
    try:
        blob = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:  # noqa: BLE001 - an unpicklable value is simply not reused
        with _lock:
            _stats["pickle_errors"] += 1
        return value, key
    with _lock:
        _stats["misses"] += 1
        _stats["parsed_bytes"] += len(data)
        if len(blob) <= MAX_CACHE_BYTES:
            previous = _entries.pop(key, None)
            if previous is not None:
                _state["bytes"] -= len(previous)
            _entries[key] = blob
            _state["bytes"] += len(blob)
            while _state["bytes"] > MAX_CACHE_BYTES:
                _, removed = _entries.popitem(last=False)
                _state["bytes"] -= len(removed)
                _stats["evictions"] += 1
    return value, key


def stats():
    with _lock:
        return {**_stats, "entries": len(_entries), "bytes": _state["bytes"]}


def clear():
    with _lock:
        _entries.clear()
        _state["bytes"] = 0
        for name in _stats:
            _stats[name] = 0
