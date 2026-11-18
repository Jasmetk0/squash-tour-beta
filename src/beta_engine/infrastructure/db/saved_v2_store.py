"""Saved v2: Run-scoped content-addressed storage of Saved Revision payload text.

Scope and invariants
--------------------
* Only Runs whose immutable ``run_saved_storage_formats`` row names
  ``saved_v2.rope.1`` use this store. Every other Run (all existing history) keeps
  the v1 inline ``payload_json`` bytes and code path unchanged.
* The LOGICAL payload is unchanged: the materialized text of a v2 row is exactly
  the text the writer supplied (verified in the same transaction before commit),
  so the Saved ``content_hash``, revision IDs, fingerprints, readers and every
  existing physical/source/replay gate see exactly the v1 bytes.
* Physically, ``payload_json`` of a v2 row holds a small canonical envelope
  ``{"saved_v2":{"chars":N,"format":"saved_v2.rope.1","root":D,"run_id":R}}`` and
  the text lives in insert-only ``saved_revision_nodes(run_id, digest, body)``.

Node format ``saved_v2.rope.1``
-------------------------------
``body = header + "\\n" + data`` where ``header`` is the canonical JSON
``{"c":[child digests],"k":"v"|"s","n":[piece lengths]}`` with
``len(n) == len(c) + 1`` and ``sum(n) == len(data)``. Splitting ``data`` by ``n``
gives pieces ``p0..pk``; the node materializes to ``p0 + M(c1) + p1 + ... + pk``.
``digest = sha256(body as UTF-8)``. References are out of band, so no JSON
literal can alias a reference. ``k == "v"`` marks a node whose text is one
complete JSON value (a large container), ``"s"`` a segment (chunk/group).

Reading (fail closed)
---------------------
Each SELECT of ``payload_json`` is compiled to call ``saved_v2_payload(run_id,
payload_json)`` for envelope rows and rows of v2 Runs. That SQLite function runs
on the SAME connection, i.e. inside the reader's own transaction snapshot. It
re-fetches every reachable node of that row's Run, re-hashes the ACTUAL bytes,
validates headers, rejects missing/foreign/cyclic/oversized graphs and a size that
differs from the envelope, and only then returns the text. Nothing is trusted
from an earlier read, a declared digest or a persisted proof; corruption after
any successful (warm) read fails the next read.

Writing (incremental)
---------------------
The encoder splits the exact text at JSON container boundaries. Containers of at
least ``THRESHOLD`` characters become value nodes; large containers with many
members are chunked at content-defined boundaries, so an append or a local edit
changes only nearby chunks plus the path to the root. A process-local index of
already verified value nodes of the same Run lets the writer reuse an unchanged
subtree after an exact SHA-256 comparison of the candidate text instead of
rescanning it. The index is a pure cache: a stale entry can only cost a rescan,
and the writer verifies the stored result from actual bytes before commit.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import zlib
from collections import OrderedDict
from json.decoder import scanstring

from sqlalchemy import Text, case, func, or_, type_coerce
from sqlalchemy.types import TypeDecorator

FORMAT = "saved_v2.rope.1"
FORMATS_TABLE = "run_saved_storage_formats"
NODES_TABLE = "saved_revision_nodes"
ENVELOPE_KEY = "saved_v2"
ENVELOPE_PREFIX = '{"saved_v2":'

# Writer parameters are part of the format version: changing them changes digests
# of new nodes only (old nodes stay readable), never the materialized text.
THRESHOLD = 4096          # container values at least this long become nodes
MAX_INLINE = 32 * 1024    # chunk a container whose own literal text is larger
CHUNK_MASK = 0x7          # content-defined member chunk boundary (≈ 8 members)
MAX_CHUNK = 64 * 1024     # forced chunk cut (bounded node size)
FANOUT = 64               # group child lists larger than this
GROUP_MASK = 0xF
INDEX_PREFIX = 64
INDEX_TAIL = 64

# Reader limits (forged size / expansion / depth defences).
MAX_CHILDREN = 4096
MAX_DEPTH = 256
MAX_CHARS = (1 << 31) - 1
MAX_NODES = 1_000_000

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SCALAR = re.compile(
    r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?|true|false|null|NaN|-?Infinity"
)
_decoder = json.JSONDecoder()


class SavedV2IntegrityError(ValueError):
    """Physical v2 Saved storage is missing, foreign, malformed or changed."""


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- envelope

def envelope_text(*, run_id: str, root: str, chars: int) -> str:
    return canonical({ENVELOPE_KEY: {"chars": chars, "format": FORMAT, "root": root, "run_id": run_id}})


def parse_envelope(text, *, run_id):
    if type(text) is not str or not text.startswith(ENVELOPE_PREFIX) or len(text) > 512:
        raise SavedV2IntegrityError("v2 Saved row has no valid storage envelope")
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise SavedV2IntegrityError("v2 Saved envelope is not JSON") from exc
    if type(value) is not dict or set(value) != {ENVELOPE_KEY} or canonical(value) != text:
        raise SavedV2IntegrityError("v2 Saved envelope is not canonical")
    inner = value[ENVELOPE_KEY]
    if (type(inner) is not dict or set(inner) != {"chars", "format", "root", "run_id"}
            or inner["format"] != FORMAT or type(inner["chars"]) is not int
            or not 0 <= inner["chars"] <= MAX_CHARS or type(inner["root"]) is not str
            or not _HEX64.match(inner["root"])):
        raise SavedV2IntegrityError("v2 Saved envelope is malformed")
    if inner["run_id"] != run_id:
        raise SavedV2IntegrityError("v2 Saved envelope belongs to a different Run")
    return inner["root"], inner["chars"]


# --------------------------------------------------------------------------- nodes

def node_body(kind, parts):
    """``parts``: sequence of str and ('ref', digest). Returns canonical body text."""
    pieces, children, current = [], [], []
    for part in parts:
        if type(part) is str:
            current.append(part)
        else:
            pieces.append("".join(current))
            current = []
            children.append(part[1])
    pieces.append("".join(current))
    header = canonical({"c": children, "k": kind, "n": [len(p) for p in pieces]})
    return header + "\n" + "".join(pieces)


def parse_node(body: str):
    """Strict header validation of one verified body; returns (kind, children, pieces)."""
    header, separator, data = body.partition("\n")
    if separator != "\n" or len(header) > 64 + MAX_CHILDREN * 80:
        raise SavedV2IntegrityError("v2 node has no valid header")
    try:
        value = json.loads(header)
    except ValueError as exc:
        raise SavedV2IntegrityError("v2 node header is not JSON") from exc
    if type(value) is not dict or set(value) != {"c", "k", "n"} or canonical(value) != header:
        raise SavedV2IntegrityError("v2 node header is not canonical")
    kind, children, lengths = value["k"], value["c"], value["n"]
    if (kind not in ("v", "s") or type(children) is not list or type(lengths) is not list
            or len(children) > MAX_CHILDREN or len(lengths) != len(children) + 1):
        raise SavedV2IntegrityError("v2 node header is malformed")
    for child in children:
        if type(child) is not str or not _HEX64.match(child):
            raise SavedV2IntegrityError("v2 node child reference is malformed")
    pieces, offset = [], 0
    for length in lengths:
        if type(length) is not int or length < 0:
            raise SavedV2IntegrityError("v2 node piece length is malformed")
        pieces.append(data[offset:offset + length])
        offset += length
    if offset != len(data):
        raise SavedV2IntegrityError("v2 node piece lengths do not cover its data")
    return kind, tuple(children), tuple(pieces)


def materialize(fetch, *, run_id, root, expected_chars, on_value_node=None, verified=None):
    """Authenticate the complete DAG from ACTUAL bytes and return its exact text.

    ``fetch(run_id, digests)`` returns {digest: body} of rows that physically exist
    for this Run only. Every body fetched is hashed here. ``verified`` may hold
    nodes of this Run already fetched AND hashed in the SAME SQLite transaction
    snapshot (see ``SnapshotCache``); newly verified nodes are added to it.
    """
    nodes, pending = {}, [root]
    while pending:
        batch, following = [], []
        for digest in dict.fromkeys(pending):
            if digest in nodes:
                continue
            known = verified.get(digest) if verified is not None else None
            if known is not None:
                nodes[digest] = known
                following.extend(known[1])
            else:
                batch.append(digest)
        for start in range(0, len(batch), 500):
            chunk = batch[start:start + 500]
            found = fetch(run_id, chunk)
            for digest in chunk:
                body = found.get(digest)
                if type(body) is not str:
                    raise SavedV2IntegrityError(f"v2 node {digest[:12]} is missing for this Run")
                if sha256_hex(body) != digest:
                    raise SavedV2IntegrityError(f"v2 node {digest[:12]} does not match its digest")
                nodes[digest] = parse_node(body)
                if verified is not None:
                    verified[digest] = nodes[digest]
                following.extend(nodes[digest][1])
        if len(nodes) > MAX_NODES:
            raise SavedV2IntegrityError("v2 node graph is too large")
        pending = following
    # Sizes bottom-up with cycle and depth detection (iterative post-order).
    sizes, state = {}, {}
    stack = [(root, 0, 0)]
    while stack:
        digest, index, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise SavedV2IntegrityError("v2 node graph is too deep")
        _, children, pieces = nodes[digest]
        if index == 0:
            if state.get(digest) == 2:
                continue
            if state.get(digest) == 1:
                raise SavedV2IntegrityError("v2 node graph contains a cycle")
            state[digest] = 1
        if index < len(children):
            stack.append((digest, index + 1, depth))
            child = children[index]
            if state.get(child) == 1:
                raise SavedV2IntegrityError("v2 node graph contains a cycle")
            if state.get(child) != 2:
                stack.append((child, 0, depth + 1))
            continue
        total = sum(len(p) for p in pieces) + sum(sizes[c] for c in children)
        if total > MAX_CHARS:
            raise SavedV2IntegrityError("v2 node graph expands beyond the size limit")
        sizes[digest] = total
        state[digest] = 2
    if sizes[root] != expected_chars:
        raise SavedV2IntegrityError("v2 Saved size differs from its envelope")
    subtrees = getattr(verified, "subtrees", None) if on_value_node is None else None
    if subtrees is not None:
        text = _assemble_shared(nodes, sizes, root, subtrees)
        if len(text) != expected_chars:
            raise SavedV2IntegrityError("v2 Saved text differs from its envelope size")
        return text
    out, marks = [], []
    position = 0
    work = [("n", root)]
    while work:
        tag, item = work.pop()
        if tag == "p":
            out.append(item)
            position += len(item)
            continue
        kind, children, pieces = nodes[item]
        if on_value_node is not None and kind == "v":
            marks.append((item, position, sizes[item]))
        sequence = [("p", pieces[0])]
        for child, piece in zip(children, pieces[1:]):
            sequence.append(("n", child))
            sequence.append(("p", piece))
        work.extend(reversed(sequence))
    text = "".join(out)
    if len(text) != expected_chars:
        raise SavedV2IntegrityError("v2 Saved text differs from its envelope size")
    if on_value_node is not None:
        for digest, start, size in marks:
            on_value_node(digest, text, start, start + size)
    return text


MEMO_NODE_CHARS = 4 * 1024 * 1024


def _assemble_shared(nodes, sizes, root, subtrees):
    """Assemble from authenticated nodes, reusing subtree texts of this snapshot.

    ``subtrees`` holds texts assembled earlier in the SAME snapshot from nodes
    that were authenticated in it; a shared history prefix is joined once.
    """
    def build(digest):
        known = subtrees.get(digest)
        if known is not None:
            return known
        _kind, children, pieces = nodes[digest]
        if not children:
            text = pieces[0]
        else:
            parts = [pieces[0]]
            for child, piece in zip(children, pieces[1:]):
                parts.append(build(child))
                parts.append(piece)
            text = "".join(parts)
        if sizes[digest] <= MEMO_NODE_CHARS:
            subtrees[digest] = text
        return text
    return build(root)


# Static SQL only; digests are bound as one JSON array parameter.
_FETCH_NODES_SQL = (
    "SELECT digest, body FROM saved_revision_nodes "
    "WHERE run_id = ? AND digest IN (SELECT value FROM json_each(?))"
)
_RUN_FORMAT_SQL = "SELECT storage_format FROM run_saved_storage_formats WHERE run_id = ?"


def connection_fetch(dbapi_connection):
    def fetch(run_id, digests):
        if not digests:
            return {}
        cursor = dbapi_connection.cursor()
        try:
            rows = cursor.execute(_FETCH_NODES_SQL, (run_id, json.dumps(list(digests)))).fetchall()
        finally:
            cursor.close()
        return {digest: body for digest, body in rows}
    return fetch


# --------------------------------------------------------------------------- index

class KnownValueIndex:
    """Bounded process-local cache: (Run, exact value text) -> verified node digest.

    An entry only lets the encoder SKIP rescanning a region whose exact text has
    the recorded SHA-256; it never authorizes bytes. Entries come from texts this
    process encoded or materialized from authenticated nodes of the same Run.
    """

    def __init__(self, max_entries=60_000):
        self._lock = threading.Lock()
        self._entries = OrderedDict()   # (run_id, digest) -> (prefix, length, tail, sha)
        self._by_prefix = {}            # (run_id, prefix) -> {digest: (length, tail, sha)}
        self._roots = OrderedDict()     # (run_id, root) -> True
        self._max = max_entries

    def add(self, run_id, digest, text, start, end):
        if end - start < THRESHOLD:
            return
        key = (run_id, digest)
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return
        prefix = text[start:start + INDEX_PREFIX]
        tail = text[end - INDEX_TAIL:end]
        sha = hashlib.sha256(text[start:end].encode("utf-8")).digest()
        with self._lock:
            self._entries[key] = (prefix, end - start, tail, sha)
            self._by_prefix.setdefault((run_id, prefix), {})[digest] = (end - start, tail, sha)
            while len(self._entries) > self._max:
                (old_run, old_digest), (old_prefix, *_rest) = self._entries.popitem(last=False)
                bucket = self._by_prefix.get((old_run, old_prefix))
                if bucket is not None:
                    bucket.pop(old_digest, None)
                    if not bucket:
                        del self._by_prefix[(old_run, old_prefix)]

    def remember_root(self, run_id, root):
        with self._lock:
            self._roots[(run_id, root)] = True
            self._roots.move_to_end((run_id, root))
            while len(self._roots) > 256:
                self._roots.popitem(last=False)

    def knows_root(self, run_id, root):
        with self._lock:
            return (run_id, root) in self._roots

    def match(self, run_id, text, start):
        """``(end, digest)`` of an exactly equal known value, ``False`` when only
        the prefix is known (a changed version of a large value), else ``None``."""
        with self._lock:
            bucket = self._by_prefix.get((run_id, text[start:start + INDEX_PREFIX]))
            candidates = sorted(bucket.items(), key=lambda item: -item[1][0]) if bucket else ()
        size = len(text)
        for digest, (length, tail, sha) in candidates:
            end = start + length
            if end > size or text[end - INDEX_TAIL:end] != tail:
                continue
            if end < size and text[end] not in ",]}":
                continue
            if hashlib.sha256(text[start:end].encode("utf-8")).digest() == sha:
                return end, digest
        return False if candidates else None

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._by_prefix.clear()
            self._roots.clear()


KNOWN = KnownValueIndex()


# --------------------------------------------------------------------------- encoder

class _Bail(Exception):
    pass


def _crc(text):
    return zlib.crc32(text.encode("utf-8"))


class Encoder:
    """Split one exact text into rope nodes; deterministic given the text."""

    def __init__(self, run_id, index=KNOWN):
        self.run_id = run_id
        self.index = index
        self.nodes = {}          # digest -> body (new or recomputed this call)
        self.value_nodes = []    # (digest, start, end) for indexing
        self.reused = 0
        self.text = ""

    def _emit(self, kind, parts):
        body = node_body(kind, parts)
        digest = sha256_hex(body)
        self.nodes.setdefault(digest, body)
        return digest

    def encode(self, text):
        if type(text) is not str:
            raise SavedV2IntegrityError("Saved payload text must be a string")
        self.text = text
        root = None
        if len(text) >= THRESHOLD and text[:1] in ("{", "["):
            try:
                end, root = self._value(0)
                if end != len(text):
                    raise _Bail
            except (_Bail, ValueError, IndexError, RecursionError):
                self.nodes, self.value_nodes, root = {}, [], None
        if root is None:
            root = self._raw(text)
        return root

    def _raw(self, text):
        # Not compact JSON: exact text in bounded segments (still content-addressed).
        parts = []
        for start in range(0, len(text), MAX_CHUNK):
            segment = text[start:start + MAX_CHUNK]
            parts.append(("ref", self._emit("s", [segment])))
        return self._emit("s", self._group(parts)) if len(parts) != 1 else parts[0][1]

    def _value_end(self, position):
        text = self.text
        char = text[position]
        if char == '"':
            return scanstring(text, position + 1, True)[1], None
        if char in "{[":
            known = self.index.match(self.run_id, text, position) if self.index else None
            if known:
                self.reused += 1
                return known
            if known is False:
                # A changed version of a known large value: scan its members
                # directly instead of decoding the whole value first.
                return self._value(position, matched=True)
            return _decoder.raw_decode(text, position)[1], None
        match = _SCALAR.match(text, position)
        if match is None:
            raise _Bail
        return match.end(), None

    def _value(self, start, matched=False):
        """Encode the container at ``start``; (end, digest), digest None if small."""
        text = self.text
        known = self.index.match(self.run_id, text, start) if self.index and not matched else None
        if known:
            self.reused += 1
            return known
        opening = text[start]
        closing = "}" if opening == "{" else "]"
        members = []
        position = start + 1
        if text[position] == closing:
            raise _Bail  # an empty container is never large; callers inline it
        while True:
            member_start = position
            if opening == "{":
                if text[position] != '"':
                    raise _Bail
                key_end = scanstring(text, position + 1, True)[1]
                if text[key_end] != ":":
                    raise _Bail
                value_start = key_end + 1
            else:
                value_start = position
            value_end, digest = self._value_end(value_start)
            if digest is None and value_end - value_start >= THRESHOLD and text[value_start] in "{[":
                value_end, digest = self._value(value_start, matched=True)
            if digest is None:
                members.append((text[member_start:value_end],))
            else:
                members.append((text[member_start:value_start], digest))
            following = text[value_end]
            if following == ",":
                position = value_end + 1
                continue
            if following != closing:
                raise _Bail
            end = value_end + 1
            break
        if end - start < THRESHOLD and start != 0:
            return end, None
        inline = sum(len(member[0]) for member in members)
        refs = sum(len(member) == 2 for member in members)
        if inline <= MAX_INLINE and refs <= FANOUT:
            parts = [opening]
            for index, member in enumerate(members):
                if index:
                    parts.append(",")
                parts.append(member[0])
                if len(member) == 2:
                    parts.append(("ref", member[1]))
            parts.append(closing)
        else:
            chunks, current, size = [], [], 0
            for member in members:
                current.append(member)
                size += len(member[0])
                boundary = (zlib.crc32(member[1].encode()) if len(member) == 2 else _crc(member[0])) & CHUNK_MASK
                if boundary == 0 or size >= MAX_CHUNK:
                    chunks.append(current)
                    current, size = [], 0
            if current:
                chunks.append(current)
            chunk_refs = []
            for chunk in chunks:
                parts = []
                for index, member in enumerate(chunk):
                    if index:
                        parts.append(",")
                    parts.append(member[0])
                    if len(member) == 2:
                        parts.append(("ref", member[1]))
                chunk_refs.append(("ref", self._emit("s", parts)))
            parts = [opening, *self._group(chunk_refs, separator=","), closing]
        digest = self._emit("v", parts)
        self.value_nodes.append((digest, start, end))
        return end, digest

    def _group(self, refs, separator=""):
        """Join child refs with ``separator``; group into a tree when too wide."""
        while len(refs) > FANOUT:
            groups, current = [], []
            for ref in refs:
                current.append(ref)
                if (int(ref[1][:8], 16) & GROUP_MASK) == 0 or len(current) >= 2 * FANOUT:
                    groups.append(current)
                    current = []
            if current:
                groups.append(current)
            if len(groups) == len(refs):   # degenerate: force pairs
                groups = [refs[i:i + 2] for i in range(0, len(refs), 2)]
            refs = [("ref", self._emit("s", _joined(group, separator))) for group in groups]
        return _joined(refs, separator)


def _joined(refs, separator):
    parts = []
    for index, ref in enumerate(refs):
        if index and separator:
            parts.append(separator)
        parts.append(ref)
    return parts


# --------------------------------------------------------------------------- SQL glue

_errors = threading.local()


def _remember_error(exc):
    _errors.last = exc


def take_error():
    exc = getattr(_errors, "last", None)
    _errors.last = None
    return exc


# --------------------------------------------------------------------------- snapshot cache

class ConnectionState:
    """Per-DBAPI-connection snapshot bookkeeping (owned by the pool record)."""

    __slots__ = ("epoch", "cache")

    def __init__(self):
        self.epoch = 0
        self.cache = None


SNAPSHOT_TEXT_CHARS = 384 * 1024 * 1024


def bump_snapshot(state):
    """Transaction boundary, savepoint operation or DDL: forget everything."""
    if state is not None:
        state.epoch += 1
        state.cache = None


def note_own_write(state):
    """Own INSERT/UPDATE/DELETE inside the same transaction.

    Nodes are insert-only (ORM guard plus SQLite triggers that only DDL can drop,
    and DDL is a full boundary), so bytes authenticated earlier in this
    transaction stay exactly as they were: keep verified nodes and texts. A new
    format row may appear, so the per-Run format answers are recomputed.
    """
    if state is not None and state.cache is not None:
        state.cache.formats.clear()


class SnapshotCache:
    """Bytes already authenticated inside ONE unchanged SQLite read snapshot.

    Valid only while the connection stays inside the same explicit transaction:
    the key is an epoch bumped at every transaction/savepoint boundary and DDL.
    Outside a transaction nothing is cached. It never outlives the snapshot, is
    never persisted and is not a proof for any later request.
    """

    __slots__ = ("key", "formats", "nodes", "texts", "chars", "subtrees", "subtree_chars")

    def __init__(self, key):
        self.key = key
        self.formats = {}
        self.subtrees = {}            # (run_id, digest) -> assembled subtree text
        self.subtree_chars = 0
        self.nodes = {}               # (run_id, digest) -> parsed verified node
        self.texts = OrderedDict()    # (run_id, root, chars) -> text
        self.chars = 0

    def remember_text(self, key, text):
        if len(text) > SNAPSHOT_TEXT_CHARS:
            return
        self.texts[key] = text
        self.chars += len(text)
        while self.chars > SNAPSHOT_TEXT_CHARS and self.texts:
            _, old = self.texts.popitem(last=False)
            self.chars -= len(old)


def snapshot_cache(dbapi_connection, state):
    if state is None or not getattr(dbapi_connection, "in_transaction", False):
        return None
    key = state.epoch
    cache = state.cache
    if cache is None or cache.key != key:
        cache = state.cache = SnapshotCache(key)
    return cache


class _RunView(dict):
    """``verified`` mapping of one Run inside a SnapshotCache (no cross-Run keys)."""

    def __init__(self, cache, run_id):
        super().__init__()
        self._cache, self._run = cache, run_id
        self.subtrees = _SubtreeView(cache, run_id)

    def get(self, digest, default=None):
        return self._cache.nodes.get((self._run, digest), default)

    def __setitem__(self, digest, value):
        self._cache.nodes[(self._run, digest)] = value


SNAPSHOT_SUBTREE_CHARS = 256 * 1024 * 1024


class _SubtreeView:
    __slots__ = ("_cache", "_run")

    def __init__(self, cache, run_id):
        self._cache, self._run = cache, run_id

    def get(self, digest):
        return self._cache.subtrees.get((self._run, digest))

    def __setitem__(self, digest, text):
        cache = self._cache
        if cache.subtree_chars + len(text) > SNAPSHOT_SUBTREE_CHARS:
            return
        cache.subtrees[(self._run, digest)] = text
        cache.subtree_chars += len(text)


def run_is_v2(dbapi_connection, run_id, cache=None) -> bool:
    if cache is not None and run_id in cache.formats:
        return cache.formats[run_id]
    result = _run_is_v2(dbapi_connection, run_id)
    if cache is not None:
        cache.formats[run_id] = result
    return result


def _run_is_v2(dbapi_connection, run_id) -> bool:
    cursor = dbapi_connection.cursor()
    try:
        exists = cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (FORMATS_TABLE,)
        ).fetchone()
        if exists is None:
            return False
        row = cursor.execute(
            _RUN_FORMAT_SQL, (run_id,)
        ).fetchone()
    finally:
        cursor.close()
    if row is None:
        return False
    if row[0] != FORMAT:
        raise SavedV2IntegrityError("Run has an unknown Saved storage format")
    return True


def read_payload(dbapi_connection, run_id, stored, *, on_value_node=None, state=None):
    """The exact logical payload text of one stored row, or a fail-closed error."""
    if type(run_id) is not str:
        raise SavedV2IntegrityError("Saved row has no Run identity")
    is_envelope = type(stored) is str and stored.startswith(ENVELOPE_PREFIX)
    cache = snapshot_cache(dbapi_connection, state)
    v2 = run_is_v2(dbapi_connection, run_id, cache)
    if not is_envelope:
        if v2:
            raise SavedV2IntegrityError("v2 Run contains an inline (downgraded) Saved payload")
        return stored
    if not v2:
        raise SavedV2IntegrityError("v1 Run contains a v2 Saved storage envelope")
    root, chars = parse_envelope(stored, run_id=run_id)
    key = (run_id, root, chars)
    if cache is not None and on_value_node is None:
        known = cache.texts.get(key)
        if known is not None:
            cache.texts.move_to_end(key)
            return known
    text = materialize(connection_fetch(dbapi_connection), run_id=run_id, root=root,
                       expected_chars=chars, on_value_node=on_value_node,
                       verified=_RunView(cache, run_id) if cache is not None else None)
    if cache is not None:
        cache.remember_text(key, text)
    return text


# Hand the verified text to the result processor of the SAME Python process by a
# short token instead of copying it through SQLite (str -> UTF-8 -> str) on every
# repeated SELECT. A token is single use; stored row text can never be a token
# (the reader rejects any stored value starting with NUL).
_TOKEN = "\x00saved_v2_text:"
_handoff = OrderedDict()
_handoff_lock = threading.Lock()
_token_counter = __import__("itertools").count(1)
MAX_HANDOFF = 100_000


def _hand_off(text):
    token = _TOKEN + str(next(_token_counter))
    with _handoff_lock:
        _handoff[token] = text
        while len(_handoff) > MAX_HANDOFF:
            _handoff.popitem(last=False)
    return token


def take_handed_off(value):
    if type(value) is not str or not value.startswith(_TOKEN):
        return value
    with _handoff_lock:
        text = _handoff.pop(value, None)
    if text is None:
        raise SavedV2IntegrityError("v2 Saved text hand-off is unavailable")
    return text


def _sql_saved_v2_payload(dbapi_connection, state):
    def saved_v2_payload(run_id, stored):
        try:
            if type(stored) is str and stored.startswith("\x00"):
                raise SavedV2IntegrityError("Stored Saved payload text is malformed")
            text = read_payload(dbapi_connection, run_id, stored, state=state)
            return _hand_off(text)
        except Exception as exc:  # reported through the engine's handle_error hook
            _remember_error(exc if isinstance(exc, SavedV2IntegrityError)
                            else SavedV2IntegrityError(f"v2 Saved read failed: {exc}"))
            raise
    return saved_v2_payload


def _sql_saved_v2_run(dbapi_connection, state):
    def saved_v2_run(run_id):
        try:
            return 1 if type(run_id) is str and run_is_v2(
                dbapi_connection, run_id, snapshot_cache(dbapi_connection, state)) else 0
        except Exception as exc:
            _remember_error(exc if isinstance(exc, SavedV2IntegrityError)
                            else SavedV2IntegrityError(f"v2 Saved format read failed: {exc}"))
            raise
    return saved_v2_run


def register_sqlite_functions(dbapi_connection, state=None):
    create = getattr(dbapi_connection, "create_function", None)
    if create is None:
        return
    create("saved_v2_payload", 2, _sql_saved_v2_payload(dbapi_connection, state))
    create("saved_v2_run", 1, _sql_saved_v2_run(dbapi_connection, state))


class _HandedOffText(TypeDecorator):
    """Result type of the routed expression: resolves a hand-off token."""

    impl = Text
    cache_ok = True

    def process_result_value(self, value, dialect):
        return take_handed_off(value)


class SavedPayloadText(TypeDecorator):
    """TEXT column whose SELECT returns the exact logical (materialized) payload.

    v1 rows pass through untouched in SQL (no Python call). The DDL type is TEXT.
    """

    impl = Text
    cache_ok = True

    def column_expression(self, column):
        table = getattr(column, "table", None)
        run_id = table.c.run_id if table is not None and "run_id" in table.c else None
        if run_id is None:
            return column
        routed = or_(
            func.substr(column, 1, len(ENVELOPE_PREFIX)) == ENVELOPE_PREFIX,
            func.substr(column, 1, 1) == func.char(0),
            func.saved_v2_run(run_id) == 1,
        )
        return type_coerce(case((routed, func.saved_v2_payload(run_id, column)), else_=column), _HandedOffText())
