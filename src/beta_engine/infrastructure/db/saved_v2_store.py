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

Text digests (``stored_text_sha256``)
-------------------------------------
Physical-row signatures need only SHA-256 of a row's logical text. After a
verified materialization was hashed, ``TEXT_DIGESTS`` remembers that digest for
the exact (Run, root, size). A later snapshot may return it without
materializing the text again, but only after re-fetching and re-hashing EVERY
node reachable from that root in its own transaction, as the reader would; a
missing, foreign or changed node fails closed, and any other envelope is a
different key. Content addressing makes those identical bodies determine the
same text.

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

from sqlalchemy import Text, case, func, literal_column, or_, select, type_coerce
from sqlalchemy import table as sql_table
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
# Writer limit, enforced on every emitted node (well below the reader limit).
WRITE_MAX_CHILDREN = 2 * 64
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
    if len(children) > WRITE_MAX_CHILDREN:
        raise SavedV2IntegrityError(
            f"v2 node would hold {len(children)} references (limit {WRITE_MAX_CHILDREN})")
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


MAX_FLAT_PIECES = 1 << 24


def materialize(fetch, *, run_id, root, expected_chars, on_value_node=None, verified=None):
    """Authenticate the complete DAG from ACTUAL bytes and return its exact text.

    ``fetch(run_id, digests)`` returns {digest: body} of rows that physically exist
    for this Run only. Every body fetched is hashed here. ``verified`` may hold
    nodes of this Run already fetched AND hashed in the SAME SQLite transaction
    snapshot (see ``SnapshotCache``) together with values derived from them in that
    snapshot (subtree size and the flattened tuple of its piece strings); newly
    verified nodes and derived values are added to it.
    """
    derived = getattr(verified, "derived", None)
    known_root = derived.get(root) if derived is not None else None
    if known_root is not None and on_value_node is None:
        # The complete subtree was authenticated, size-checked and flattened in
        # this unchanged snapshot: only the size binding to this envelope remains.
        if known_root[0] != expected_chars:
            raise SavedV2IntegrityError("v2 Saved size differs from its envelope")
        return "".join(known_root[1])
    nodes = authenticated_nodes(fetch, run_id=run_id, root=root, verified=verified)
    return _materialize_nodes(nodes, root=root, expected_chars=expected_chars,
                              on_value_node=on_value_node, derived=derived)


def authenticated_nodes(fetch, *, run_id, root, verified=None):
    """Fetch every node reachable from ``root`` and authenticate its ACTUAL body.

    Each body returned by ``fetch`` (rows of this Run only) must hash to its own
    digest; a missing, foreign or changed node raises. ``verified`` has the
    meaning described in ``materialize``. Returns {digest: parsed node}; a node
    whose subtree has a derived value of the same snapshot is not descended.
    """
    derived = getattr(verified, "derived", None)
    nodes, pending = {}, [root]
    while pending:
        batch, following = [], []
        for digest in dict.fromkeys(pending):
            if digest in nodes:
                continue
            known = verified.get(digest) if verified is not None else None
            if known is not None:
                nodes[digest] = known
                if derived is None or derived.get(digest) is None:
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
                parsed = BODIES.parsed_if_identical(run_id, digest, body)
                if parsed is None:
                    if sha256_hex(body) != digest:
                        raise SavedV2IntegrityError(f"v2 node {digest[:12]} does not match its digest")
                    parsed = parse_node(body)
                    BODIES.remember(run_id, digest, body, parsed)
                nodes[digest] = parsed
                if verified is not None:
                    verified[digest] = nodes[digest]
                following.extend(nodes[digest][1])
        if len(nodes) > MAX_NODES:
            raise SavedV2IntegrityError("v2 node graph is too large")
        pending = following
    return nodes


def _materialize_nodes(nodes, *, root, expected_chars, on_value_node, derived):
    # Sizes and piece counts bottom-up with cycle and depth detection (iterative
    # post-order). A node with a derived value of this snapshot is a closed leaf.
    sizes, counts, state = {}, {}, {}
    for digest in nodes:
        known = derived.get(digest) if derived is not None else None
        if known is not None:
            sizes[digest], counts[digest], state[digest] = known[0], len(known[1]), 2
    order = []
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
        count = sum(1 for p in pieces if p) + sum(counts[c] for c in children)
        if count > MAX_FLAT_PIECES:
            raise SavedV2IntegrityError("v2 node graph expands beyond the piece limit")
        sizes[digest], counts[digest] = total, count
        state[digest] = 2
        order.append(digest)
    if sizes[root] != expected_chars:
        raise SavedV2IntegrityError("v2 Saved size differs from its envelope")
    if on_value_node is None:
        # Flatten bottom-up (children before parents in ``order``), reusing the
        # flattened tuples of this snapshot; join once at C speed.
        flat = {}
        for digest in order:
            _, children, pieces = nodes[digest]
            parts = [pieces[0]] if pieces[0] else []
            for child, piece in zip(children, pieces[1:]):
                child_flat = flat.get(child)
                if child_flat is None:
                    child_flat = derived.get(child)[1]
                parts.extend(child_flat)
                if piece:
                    parts.append(piece)
            flat[digest] = tuple(parts)
            if derived is not None:
                derived[digest] = (sizes[digest], flat[digest])
        root_flat = flat.get(root)
        if root_flat is None:
            root_flat = derived.get(root)[1]
        text = "".join(root_flat)
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


class VerifiedBodies:
    """Bounded process cache: node body text known to hash to its digest.

    Not an authority: every transaction still fetches the ACTUAL body. Only a body
    that is byte-for-byte equal (``==`` of the exact strings) to text that already
    hashed to this digest reuses that SHA-256 result and its parse, as
    ``exact_text_digest`` does for whole rows. Different bytes are hashed again.
    """

    def __init__(self, max_chars=64 * 1024 * 1024):
        # Each entry holds the body and its parsed pieces (copies): ~2x chars.
        self._lock = threading.Lock()
        self._entries = OrderedDict()   # (run_id, digest) -> (body, parsed)
        self._chars = 0
        self._max = max_chars

    def parsed_if_identical(self, run_id, digest, body):
        with self._lock:
            entry = self._entries.get((run_id, digest))
            if entry is not None:
                self._entries.move_to_end((run_id, digest))
        if entry is not None and (entry[0] is body or entry[0] == body):
            return entry[1]
        return None

    def remember(self, run_id, digest, body, parsed):
        if len(body) > self._max:
            return
        with self._lock:
            old = self._entries.pop((run_id, digest), None)
            if old is not None:
                self._chars -= len(old[0])
            self._entries[(run_id, digest)] = (body, parsed)
            self._chars += len(body)
            while self._chars > self._max and self._entries:
                _, (old_body, _parsed) = self._entries.popitem(last=False)
                self._chars -= len(old_body)

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._chars = 0


BODIES = VerifiedBodies()


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
            chunks, current, size, refs_in_chunk = [], [], 0, 0
            for member in members:
                current.append(member)
                size += len(member[0])
                refs_in_chunk += len(member) == 2
                boundary = (zlib.crc32(member[1].encode()) if len(member) == 2 else _crc(member[0])) & CHUNK_MASK
                # Content-defined cut, plus hard cuts by size AND by reference
                # count: identical large members share one digest/CRC, so the
                # content rule alone never cuts a run of repeated items.
                if boundary == 0 or size >= MAX_CHUNK or refs_in_chunk >= FANOUT:
                    chunks.append(current)
                    current, size, refs_in_chunk = [], 0, 0
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
    """Per-DBAPI-connection snapshot bookkeeping (owned by the pool record).

    ``guarded`` is True only while this connection's TEMP guard triggers exist:
    they call ``saved_v2_invalidate()`` for every INSERT/UPDATE/DELETE of a node or
    format row executed on this connection (also raw driver SQL), so no
    authentication from before such a change can be reused afterwards.
    """

    __slots__ = ("epoch", "cache", "guard_epoch", "guarded")

    def __init__(self):
        self.epoch = 0
        self.cache = None
        self.guard_epoch = -1
        self.guarded = False


# Data-volume budgets per connection (Python characters of retained text).
SNAPSHOT_TEXT_CHARS = 128 * 1024 * 1024
SNAPSHOT_NODE_CHARS = 128 * 1024 * 1024


def bump_snapshot(state):
    """Transaction/savepoint boundary, DDL, failed statement or a guarded write."""
    if state is not None:
        state.epoch += 1
        state.cache = None


class SnapshotCache:
    """Bytes already authenticated inside ONE unchanged SQLite read snapshot.

    Valid only while the connection stays inside the same explicit transaction
    and no node/format row was written on it (guard triggers bump the epoch);
    every transaction/savepoint boundary and DDL bumps it as well. Outside a
    transaction, or without verified guards, nothing is cached. Retained text is
    bounded by ``SNAPSHOT_TEXT_CHARS`` and ``SNAPSHOT_NODE_CHARS``. It never
    outlives the snapshot, is never persisted and is not a proof for any later
    request.
    """

    __slots__ = ("key", "formats", "nodes", "node_chars", "derived", "texts", "chars")

    def __init__(self, key):
        self.key = key
        self.formats = {}
        self.nodes = {}               # (run_id, digest) -> parsed verified node
        self.node_chars = 0
        self.derived = {}             # (run_id, digest) -> (size, flattened pieces)
        self.texts = OrderedDict()    # (run_id, root, chars) -> text
        self.chars = 0

    def remember_node(self, key, parsed):
        size = sum(len(piece) for piece in parsed[2]) + 80 * len(parsed[1])
        if self.node_chars + size > SNAPSHOT_NODE_CHARS:
            return
        self.nodes[key] = parsed
        self.node_chars += size

    def remember_derived(self, key, value):
        # References to piece strings already held by verified nodes: charge
        # 8 characters per reference against the same data-volume budget.
        size = 8 * len(value[1]) + 64
        if self.node_chars + size > SNAPSHOT_NODE_CHARS:
            return
        self.derived[key] = value
        self.node_chars += size

    def remember_text(self, key, text):
        if len(text) > SNAPSHOT_TEXT_CHARS:
            return
        self.texts[key] = text
        self.chars += len(text)
        while self.chars > SNAPSHOT_TEXT_CHARS and self.texts:
            _, old = self.texts.popitem(last=False)
            self.chars -= len(old)


GUARD_TRIGGERS = tuple(
    (f"saved_v2_guard_{table}_{event.lower()}", table, event)
    for table in (NODES_TABLE, FORMATS_TABLE)
    for event in ("INSERT", "UPDATE", "DELETE")
)
_GUARD_SQL = {
    name: f"CREATE TEMP TRIGGER IF NOT EXISTS {name} AFTER {event} ON main.{table} "
          "BEGIN SELECT saved_v2_invalidate(); END"
    for name, table, event in GUARD_TRIGGERS
}
_GUARD_NAMES = tuple(name for name, _table, _event in GUARD_TRIGGERS)
_GUARD_EXISTING_SQL = (
    "SELECT name FROM sqlite_temp_master WHERE type = 'trigger' AND name IN (?, ?, ?, ?, ?, ?)"
)
_GUARD_COUNT_SQL = (
    "SELECT COUNT(*) FROM sqlite_temp_master WHERE type = 'trigger' AND name IN ("
    + ",".join("?" * len(_GUARD_NAMES)) + ")"
)


def install_guards(dbapi_connection):
    """Create the TEMP guard triggers when both tables exist (outside a transaction)."""
    if getattr(dbapi_connection, "in_transaction", True):
        return False
    cursor = dbapi_connection.cursor()
    try:
        present = {name for (name,) in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (?, ?)",
            (NODES_TABLE, FORMATS_TABLE))}
        if present != {NODES_TABLE, FORMATS_TABLE}:
            return False
        # Issue DDL only when a guard is actually missing: other read caches of
        # this connection treat any non-SELECT statement as a snapshot change.
        existing = {name for (name,) in cursor.execute(_GUARD_EXISTING_SQL, _GUARD_NAMES)}
        for name in _GUARD_NAMES:
            if name not in existing:
                cursor.execute(_GUARD_SQL[name])
    finally:
        cursor.close()
    return True


def _guards_present(dbapi_connection):
    cursor = dbapi_connection.cursor()
    try:
        return cursor.execute(_GUARD_COUNT_SQL, _GUARD_NAMES).fetchone()[0] == len(_GUARD_NAMES)
    finally:
        cursor.close()


def snapshot_cache(dbapi_connection, state):
    if state is None or not getattr(dbapi_connection, "in_transaction", False):
        return None
    if state.guard_epoch != state.epoch:
        state.guarded = _guards_present(dbapi_connection)
        state.guard_epoch = state.epoch
    if not state.guarded:
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
        self.derived = _DerivedView(cache, run_id)

    def get(self, digest, default=None):
        return self._cache.nodes.get((self._run, digest), default)

    def __setitem__(self, digest, value):
        self._cache.remember_node((self._run, digest), value)


class _DerivedView:
    __slots__ = ("_cache", "_run")

    def __init__(self, cache, run_id):
        self._cache, self._run = cache, run_id

    def get(self, digest, default=None):
        return self._cache.derived.get((self._run, digest), default)

    def __setitem__(self, digest, value):
        self._cache.remember_derived((self._run, digest), value)


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


def forget_snapshot_text(dbapi_connection, run_id, stored, *, state=None):
    """Drop the snapshot cache's materialized text of one stored v2 envelope.

    The verified nodes stay cached, so a later read of the same row in the same
    snapshot re-assembles the text without fetching or re-hashing them again.
    Returns True when a text was dropped.
    """
    cache = snapshot_cache(dbapi_connection, state)
    if cache is None or type(stored) is not str or not stored.startswith(ENVELOPE_PREFIX):
        return False
    root, chars = parse_envelope(stored, run_id=run_id)
    text = cache.texts.pop((run_id, root, chars), None)
    if text is None:
        return False
    cache.chars -= len(text)
    return True


class TextDigestIndex:
    """Bounded process memo: (Run, root, chars) -> SHA-256 of the materialized text.

    Not an authority. An entry only records which digest the exact text had when
    it was materialized from nodes that ALL hashed to their own digests. It is
    used only after ``stored_text_sha256`` has fetched and re-hashed every node
    reachable from that root from actual SQLite bytes in the CURRENT snapshot:
    a node is content-addressed (its digest commits to its body and therefore to
    its children), so those identical authenticated bodies determine the same
    text. Any missing, foreign or changed node fails closed; a different root,
    size or Run is a different key. Nothing else is retained.
    """

    def __init__(self, max_entries=8192):
        self._lock = threading.Lock()
        self._entries = OrderedDict()
        self._max = max_entries

    def get(self, run_id, root, chars):
        with self._lock:
            digest = self._entries.get((run_id, root, chars))
            if digest is not None:
                self._entries.move_to_end((run_id, root, chars))
            return digest

    def remember(self, run_id, root, chars, digest):
        if type(digest) is not bytes or len(digest) != 32:
            return
        with self._lock:
            self._entries.pop((run_id, root, chars), None)
            self._entries[(run_id, root, chars)] = digest
            while len(self._entries) > self._max:
                self._entries.popitem(last=False)

    def clear(self):
        with self._lock:
            self._entries.clear()


TEXT_DIGESTS = TextDigestIndex()


def stored_envelope(dbapi_connection, run_id, stored, *, state=None):
    """(root, chars) of a v2 envelope row, None for a v1 row of a v1 Run.

    The same routing and fail-closed rules as ``read_payload``: an inline row of
    a v2 Run or an envelope in a v1 Run raises.
    """
    if type(run_id) is not str:
        raise SavedV2IntegrityError("Saved row has no Run identity")
    is_envelope = type(stored) is str and stored.startswith(ENVELOPE_PREFIX)
    v2 = run_is_v2(dbapi_connection, run_id, snapshot_cache(dbapi_connection, state))
    if not is_envelope:
        if v2:
            raise SavedV2IntegrityError("v2 Run contains an inline (downgraded) Saved payload")
        return None
    if not v2:
        raise SavedV2IntegrityError("v1 Run contains a v2 Saved storage envelope")
    return parse_envelope(stored, run_id=run_id)


def stored_text_sha256(dbapi_connection, run_id, stored, *, state=None):
    """SHA-256 of the exact logical text of one stored v2 row, or None.

    Returns a digest only when this process already hashed the text of the same
    (Run, root, size) AND every node reachable from that root is present in
    this Run now, in this connection's current snapshot, with a body that hashes
    to its digest (re-fetched; shared with the snapshot's verified node cache).
    None means: materialize and hash the text the ordinary way.
    """
    envelope = stored_envelope(dbapi_connection, run_id, stored, state=state)
    if envelope is None:
        return None
    root, chars = envelope
    digest = TEXT_DIGESTS.get(run_id, root, chars)
    if digest is None:
        return None
    cache = snapshot_cache(dbapi_connection, state)
    try:
        authenticated_nodes(connection_fetch(dbapi_connection), run_id=run_id, root=root,
                            verified=_RunView(cache, run_id) if cache is not None else None)
    except Exception:
        bump_snapshot(state)
        raise
    return digest


def remember_text_sha256(run_id, stored, text, digest):
    """Record sha256(text) for a v2 envelope ``stored`` whose verified read gave ``text``.

    The caller must have obtained ``text`` from the verified reader for exactly
    this ``stored`` envelope inside one unchanged snapshot, and ``digest`` must be
    the SHA-256 it computed of that text. A non-envelope or size mismatch is not
    recorded.
    """
    if type(stored) is not str or not stored.startswith(ENVELOPE_PREFIX) or type(text) is not str:
        return
    root, chars = parse_envelope(stored, run_id=run_id)
    if len(text) == chars:
        TEXT_DIGESTS.remember(run_id, root, chars, digest)


def _sql_saved_v2_payload(dbapi_connection, state):
    def saved_v2_payload(run_id, stored):
        # The verified text is returned to SQLite like any column value: nothing
        # is retained outside the bounded snapshot cache, whether or not the
        # caller consumes or finishes the result.
        try:
            return read_payload(dbapi_connection, run_id, stored, state=state)
        except Exception as exc:  # reported through the engine's handle_error hook
            bump_snapshot(state)
            _remember_error(exc if isinstance(exc, SavedV2IntegrityError)
                            else SavedV2IntegrityError(f"v2 Saved read failed: {exc}"))
            raise
    return saved_v2_payload


def register_sqlite_functions(dbapi_connection, state=None):
    create = getattr(dbapi_connection, "create_function", None)
    if create is None:
        return
    create("saved_v2_payload", 2, _sql_saved_v2_payload(dbapi_connection, state))
    create("saved_v2_invalidate", 0, lambda: bump_snapshot(state))


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
        # Pure SQL routing: a v1 row of a v1 Run never calls Python and issues no
        # extra query (the uncorrelated format subquery is evaluated once per
        # statement). Envelope rows and every row of a v2 Run go to the verified
        # reader, which also rejects an envelope in a v1 Run and an inline
        # (downgraded) row in a v2 Run.
        routed = or_(
            func.substr(column, 1, len(ENVELOPE_PREFIX)) == ENVELOPE_PREFIX,
            run_id.in_(select(literal_column("run_id")).select_from(sql_table(FORMATS_TABLE))),
        )
        return type_coerce(case((routed, func.saved_v2_payload(run_id, column)), else_=column), Text())
