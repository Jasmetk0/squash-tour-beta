"""Non-production, content-addressed append-only Merkle history prototype.

Every new Save delta stores only its new items and the digest of its predecessor.
No production Saved schema, writer, reader, or sporting code imports this module.

The writer checks the complete ACTUAL predecessor chain before extending it;
the reader always re-hashes all reachable physical node bytes on each read.
Neither warm proof reuse nor declared digests authorize any stored value.

An authoritative integration must prove append-only semantics from reviewed
sporting commands. This API receives a *delta*, not a full snapshot, and does
not claim to detect edits to an unprovided external snapshot.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


class MerkleAppendError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class AppendReader:
    store: object

    def node(self, digest):
        if (type(digest) is not str or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise MerkleAppendError("Invalid Merkle digest")
        raw = self.store.get(digest)
        if type(raw) is not str or digest_text(raw) != digest:
            raise MerkleAppendError("Missing or corrupted actual node bytes")
        try:
            node = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise MerkleAppendError("Malformed append node") from exc
        if (type(node) is not dict or set(node) != {"v", "prev", "count", "items"}
                or type(node["v"]) is not int or node["v"] != 1
                or type(node["count"]) is not int or node["count"] < 1
                or type(node["items"]) is not list or not node["items"]
                or (node["prev"] is not None and
                    (type(node["prev"]) is not str or len(node["prev"]) != 64))
                or canonical(node) != raw):
            raise MerkleAppendError("Non-canonical or malformed append node")
        return node

    def history(self, root, *, reconstruct=True):
        """Verify each actual ancestor, iteratively; optionally reconstruct values."""
        if root is None:
            return [] if reconstruct else 0
        seen, chunks, expected_count, head_count = set(), [], None, None
        while root is not None:
            if root in seen:
                raise MerkleAppendError("Cyclic append chain")
            seen.add(root)
            node = self.node(root)
            if head_count is None:
                head_count = node["count"]
            if expected_count is not None and node["count"] != expected_count:
                raise MerkleAppendError("Append history is not contiguous")
            expected_count = node["count"] - len(node["items"])
            if expected_count < 0:
                raise MerkleAppendError("Invalid append count")
            if expected_count == 0 and node["prev"] is not None:
                raise MerkleAppendError("Unexpected append ancestor")
            if expected_count > 0 and node["prev"] is None:
                raise MerkleAppendError("Missing append ancestor")
            if reconstruct:
                chunks.append(node["items"])
            root = node["prev"]
        if expected_count != 0:
            raise MerkleAppendError("Chain did not terminate at zero")
        if not reconstruct:
            return head_count
        result = []
        for chunk in reversed(chunks):
            result.extend(chunk)
        return result


def append(store, previous_root, new_items, *, previous_count):
    """Append reviewed JSON deltas; authenticate all old physical bytes first."""
    if type(new_items) is not list or not new_items:
        raise MerkleAppendError("At least one actual appended event is required")
    if type(previous_count) is not int or previous_count < 0:
        raise MerkleAppendError("Invalid previous count")
    if previous_root is None:
        if previous_count:
            raise MerkleAppendError("Nonempty previous history is missing")
    elif AppendReader(store).history(previous_root, reconstruct=False) != previous_count:
        raise MerkleAppendError("Previous append count has changed")
    try:
        # Round-trip to own immutable JSON values; no caller's mutable object is
        # retained. Canonical JSON matches the existing Merkle prototype.
        frozen = json.loads(canonical(new_items))
    except (TypeError, ValueError) as exc:
        raise MerkleAppendError("Appended values are not JSON") from exc
    node = {"v": 1, "prev": previous_root,
            "count": previous_count + len(frozen), "items": frozen}
    raw = canonical(node)
    digest = digest_text(raw)
    existing = store.get(digest)
    if existing is not None and existing != raw:
        raise MerkleAppendError("Digest collision or modified stored node")
    store[digest] = raw
    return digest
