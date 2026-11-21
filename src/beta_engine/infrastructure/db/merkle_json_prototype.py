"""PROTOTYPE ONLY: content-addressed (Merkle) storage of canonical JSON values.

Not imported by any production code path. It exists to measure, on real Saved
histories, whether storing each large JSON subtree once makes long Runs linear in
the data actually added (see docs/SAVED_HISTORY_MERKLE_STORAGE_SPEC.md).

Model
-----
* A value is split into NODES. Every dict/list whose canonical encoding is at
  least ``threshold`` characters becomes its own node; smaller values stay inline.
* A node is stored as the canonical JSON text of
  ``{"mj": 1, "r": [[path, digest], ...], "v": <value>}``. Each referenced child is
  ``null`` in ``v`` at its ``path`` (a list of keys/indexes relative to the node),
  so an ordinary value can never be mistaken for a reference.
* ``digest = sha256(node_text)``. A parent commits to its children's digests, so the
  root digest commits to the complete value (Merkle property).
* Reading verifies sha256 of every node's ACTUAL stored text before use; a digest
  verified in one read is not re-hashed within that read. Any changed, missing,
  malformed or cyclic node fails closed.
* Reconstruction is exact: ``canonical(decode(root)) == canonical(original)``.
"""

from __future__ import annotations

import hashlib
import json

FORMAT = 1
DEFAULT_THRESHOLD = 4096


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class MerkleError(ValueError):
    pass


def _length(value) -> int:
    return len(canonical(value))


class _Encoder:
    def __init__(self, store, threshold):
        self.store = store
        self.threshold = threshold
        self.new_nodes = 0
        self.new_bytes = 0

    def encode(self, value):
        """Return (inline_value_or_None, digest_or_None, canonical_length)."""
        if isinstance(value, dict):
            items = sorted(value.items())
            if any(type(k) is not str for k, _ in items):
                raise MerkleError("canonical JSON objects need string keys")
            body, refs, length = {}, [], 2 + max(0, len(items) - 1)
            for key, item in items:
                inline, digest, child_length = self.encode(item)
                length += len(json.dumps(key)) + 1 + child_length
                if digest is None:
                    body[key] = inline
                else:
                    body[key] = None
                    refs.append(([key], digest))
        elif isinstance(value, list):
            body, refs, length = [], [], 2 + max(0, len(value) - 1)
            for index, item in enumerate(value):
                inline, digest, child_length = self.encode(item)
                length += child_length
                if digest is None:
                    body.append(inline)
                else:
                    body.append(None)
                    refs.append(([index], digest))
        else:
            return value, None, _length(value)
        if length < self.threshold:
            # Small container: inline with its (small) children expanded again.
            return _expand(body, refs, self.store), None, length
        node_text = canonical({"mj": FORMAT, "r": [[path, digest] for path, digest in refs], "v": body})
        digest = hashlib.sha256(node_text.encode("utf-8")).hexdigest()
        if digest not in self.store:
            self.store[digest] = node_text
            self.new_nodes += 1
            self.new_bytes += len(node_text)
        return None, digest, length


def _expand(body, refs, store):
    """Inline small containers whose children were themselves nodes (rare)."""
    if not refs:
        return body
    reader = Reader(store)
    for path, digest in refs:
        body[path[0]] = reader.decode(digest)
    return body


def encode(value, store, *, threshold=DEFAULT_THRESHOLD):
    """Store ``value``; return (root, stats). ``root`` is a digest or inline value."""
    encoder = _Encoder(store, threshold)
    inline, digest, length = encoder.encode(value)
    root = {"digest": digest} if digest is not None else {"inline": inline}
    return root, {"new_nodes": encoder.new_nodes, "new_bytes": encoder.new_bytes, "length": length}


class Reader:
    """One read snapshot: every node's actual text is hashed once before use."""

    def __init__(self, store):
        self.store = store
        self.verified = {}  # digest -> parsed node (only after hashing actual text)
        self.hashed_bytes = 0

    def node(self, digest):
        known = self.verified.get(digest)
        if known is not None:
            return known
        if type(digest) is not str or len(digest) != 64:
            raise MerkleError("malformed node digest")
        text = self.store.get(digest)
        if text is None:
            raise MerkleError(f"missing node {digest[:12]}")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != digest:
            raise MerkleError(f"node {digest[:12]} does not match its digest")
        self.hashed_bytes += len(text)
        try:
            node = json.loads(text)
        except ValueError as exc:
            raise MerkleError("node is not JSON") from exc
        if (not isinstance(node, dict) or set(node) != {"mj", "r", "v"} or node["mj"] != FORMAT
                or not isinstance(node["r"], list) or canonical(node) != text):
            raise MerkleError("node is not a canonical format-1 node")
        seen_paths = set()
        for ref in node["r"]:
            if (not isinstance(ref, list) or len(ref) != 2 or not isinstance(ref[0], list)
                    or len(ref[0]) != 1 or type(ref[1]) is not str):
                raise MerkleError("malformed node reference")
            key = ref[0][0]
            container = node["v"]
            if isinstance(container, dict):
                if type(key) is not str or key not in container or container[key] is not None:
                    raise MerkleError("reference does not point at a null placeholder")
            elif isinstance(container, list):
                if type(key) is not int or not 0 <= key < len(container) or container[key] is not None:
                    raise MerkleError("reference does not point at a null placeholder")
            else:
                raise MerkleError("references need a container node")
            if repr(key) in seen_paths:
                raise MerkleError("duplicate reference path")
            seen_paths.add(repr(key))
        self.verified[digest] = node
        return node

    def decode(self, digest, _stack=()):
        if digest in _stack:
            raise MerkleError("reference cycle")
        node = self.node(digest)
        value = json.loads(canonical(node["v"]))  # fresh containers for every caller
        for (key,), child in node["r"]:
            value[key] = self.decode(child, _stack + (digest,))
        return value

    def verify(self, digest, _stack=()):
        """Authenticate a complete DAG without materializing it (each node once)."""
        if digest in _stack:
            raise MerkleError("reference cycle")
        node = self.node(digest)
        for _, child in node["r"]:
            if child not in self.verified:
                self.verify(child, _stack + (digest,))
        return True


def decode_root(root, reader):
    if set(root) == {"inline"}:
        return root["inline"]
    if set(root) != {"digest"}:
        raise MerkleError("malformed root")
    return reader.decode(root["digest"])
