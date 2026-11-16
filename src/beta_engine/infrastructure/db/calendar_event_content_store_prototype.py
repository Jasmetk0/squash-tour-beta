"""PROTOTYPE ONLY: scoped, tamper-evident storage of Saved sporting events.

Not imported by any production path. No Run/Branch Saved storage format changes.
This deliberately handles the original calendar_sporting_checkpoint.v13
`state.events` problem measured in the real W12/256-player acceptance.

The *caller* must independently validate the source immutable Saved row and its
source_content_hash with ordinary production validators. A self-described SHA-256
is not an authorization or a cryptographic signature. The manifest includes
that independently supplied identity so reconstruction can be cross-checked
against the original canonical Saved event array.

A non-prefix historical edit is rejected, not silently converted to an append.
Owner isolation, SQLite savepoints, physical-node hashing on each read and
per-revision original-array commitments are deliberately enforced.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3


_SCHEMA = "sporting_event_manifest.experimental.v1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class SportingEventStoreError(ValueError):
    """An untrusted source, changed immutable event or physical store corruption."""


def _canonical(value):
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise SportingEventStoreError("Invalid original JSON value") from exc


def _sha(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _identity(value, name):
    if type(value) is not str or not value or len(value) > 256:
        raise SportingEventStoreError(f"Invalid {name}")
    return value


def _digest(value, name):
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise SportingEventStoreError(f"Invalid {name}")
    return value


def create_schema(db: sqlite3.Connection):
    """Create experiment tables only; caller owns the outer SQLite transaction."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS experimental_sporting_event_nodes (
            run_id TEXT NOT NULL,
            branch_id TEXT NOT NULL,
            event_sha256 TEXT NOT NULL,
            canonical_event_json TEXT NOT NULL,
            PRIMARY KEY(run_id, branch_id, event_sha256)
        ) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS experimental_sporting_event_manifests (
            run_id TEXT NOT NULL,
            branch_id TEXT NOT NULL,
            revision_id TEXT NOT NULL,
            manifest_json TEXT NOT NULL,
            manifest_sha256 TEXT NOT NULL,
            PRIMARY KEY(run_id, branch_id, revision_id)
        ) WITHOUT ROWID;
    """)


def _read_manifest(db, run_id, branch_id, revision_id):
    row = db.execute(
        "SELECT manifest_json, manifest_sha256 "
        "FROM experimental_sporting_event_manifests "
        "WHERE run_id=? AND branch_id=? AND revision_id=?",
        (run_id, branch_id, revision_id),
    ).fetchone()
    if row is None:
        raise SportingEventStoreError("Missing physical Saved event manifest")
    raw, expected_sha = row
    _digest(expected_sha, "manifest digest")
    if type(raw) is not str or _sha(raw) != expected_sha:
        raise SportingEventStoreError("Saved event manifest physical bytes changed")
    try:
        manifest = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise SportingEventStoreError("Malformed Saved event manifest") from exc
    if (
        type(manifest) is not dict
        or set(manifest) != {
            "schema", "run_id", "branch_id", "revision_id",
            "parent_manifest_revision_id", "source_content_hash",
            "event_sha256", "events",
        }
        or manifest["schema"] != _SCHEMA
        or manifest["run_id"] != run_id
        or manifest["branch_id"] != branch_id
        or manifest["revision_id"] != revision_id
        or type(manifest["events"]) is not list
        or any(_SHA.fullmatch(value) is None for value in manifest["events"]
               if type(value) is str)
        or any(type(value) is not str for value in manifest["events"])
        or _canonical(manifest) != raw
    ):
        raise SportingEventStoreError("Malformed or foreign Saved event manifest")
    _digest(manifest["source_content_hash"], "Saved content hash")
    _digest(manifest["event_sha256"], "canonical events digest")
    parent = manifest["parent_manifest_revision_id"]
    if parent is not None:
        _identity(parent, "parent manifest revision")
    return manifest


def _verified_manifest_chain(db, run_id, branch_id, revision_id):
    """Every actually stored ancestor manifest is rehashed and prefix-checked."""
    reverse = []
    seen = set()
    while revision_id is not None:
        if revision_id in seen:
            raise SportingEventStoreError("Cyclic physical manifest history")
        seen.add(revision_id)
        manifest = _read_manifest(db, run_id, branch_id, revision_id)
        reverse.append(manifest)
        revision_id = manifest["parent_manifest_revision_id"]
    chain = list(reversed(reverse))
    previous = []
    for row in chain:
        current = row["events"]
        if current[:len(previous)] != previous or len(current) < len(previous):
            raise SportingEventStoreError("Retroactive mutation of Saved event history")
        previous = current
    return chain


def _physical_event(db, run_id, branch_id, digest):
    row = db.execute(
        "SELECT canonical_event_json FROM experimental_sporting_event_nodes "
        "WHERE run_id=? AND branch_id=? AND event_sha256=?",
        (run_id, branch_id, digest),
    ).fetchone()
    if row is None:
        raise SportingEventStoreError("Missing physical sporting event node")
    raw = row[0]
    if type(raw) is not str or _sha(raw) != digest:
        raise SportingEventStoreError("Tampered sporting event node bytes")
    try:
        value = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise SportingEventStoreError("Malformed physical event JSON") from exc
    if type(value) is not dict or _canonical(value) != raw:
        raise SportingEventStoreError("Non-canonical or invalid physical sporting event")
    return raw


def restore(
    db: sqlite3.Connection, *, run_id: str, branch_id: str,
    revision_id: str, independently_verified_source_hash: str,
):
    """Rebuild exact canonical array from verified PHYSICAL SQLite bytes.

    The expected Saved hash must come from the caller's independent validation
    of the actual immutable row, not from this store's own manifest.
    """
    _identity(run_id, "Run")
    _identity(branch_id, "Branch")
    _identity(revision_id, "Saved revision")
    _digest(independently_verified_source_hash, "independently verified Saved hash")
    chain = _verified_manifest_chain(db, run_id, branch_id, revision_id)
    result = chain[-1]
    if result["source_content_hash"] != independently_verified_source_hash:
        raise SportingEventStoreError("Saved source binding changed")
    verified_blobs = {}
    ordered = []
    for digest in result["events"]:
        if digest not in verified_blobs:
            verified_blobs[digest] = _physical_event(db, run_id, branch_id, digest)
        ordered.append(verified_blobs[digest])
    canonical_json = "[" + ",".join(ordered) + "]"
    if _sha(canonical_json) != result["event_sha256"]:
        raise SportingEventStoreError("Original event ordering or contents changed")
    return json.loads(canonical_json)


def append(
    db: sqlite3.Connection, *, run_id: str, branch_id: str,
    revision_id: str, independently_verified_source_hash: str, events: list,
    preceding_manifest_revision_id: str | None = None,
):
    """One SQLite-savepoint append, with exact original-prefix proof.

    It may be called inside a caller-owned transaction. On failure neither new
    node rows nor a half-created manifest remain. No implicit global cache.
    """
    _identity(run_id, "Run")
    _identity(branch_id, "Branch")
    _identity(revision_id, "Saved revision")
    _digest(independently_verified_source_hash, "Saved source content hash")
    if preceding_manifest_revision_id is not None:
        _identity(preceding_manifest_revision_id, "preceding Saved revision")
        if preceding_manifest_revision_id == revision_id:
            raise SportingEventStoreError("Self-referential Saved event manifest")
    if type(events) is not list:
        raise SportingEventStoreError("Expected genuine Saved event array")

    frozen = json.loads(_canonical(events))
    encoded = []
    hashes = []
    for event in frozen:
        if type(event) is not dict or type(event.get("schema_version")) is not str:
            raise SportingEventStoreError("Malformed Saved sporting event object")
        raw = _canonical(event)
        hashes.append(_sha(raw))
        encoded.append(raw)

    if preceding_manifest_revision_id is not None:
        previous = restore(
            db, run_id=run_id, branch_id=branch_id,
            revision_id=preceding_manifest_revision_id,
            independently_verified_source_hash=_read_manifest(
                db, run_id, branch_id, preceding_manifest_revision_id,
            )["source_content_hash"],
        )
        previous_hashes = [_sha(_canonical(item)) for item in previous]
        if len(hashes) < len(previous_hashes) or hashes[:len(previous_hashes)] != previous_hashes:
            raise SportingEventStoreError("Non-append-only Saved sporting history")

    manifest = {
        "schema": _SCHEMA, "run_id": run_id, "branch_id": branch_id,
        "revision_id": revision_id,
        "parent_manifest_revision_id": preceding_manifest_revision_id,
        "source_content_hash": independently_verified_source_hash,
        "event_sha256": _sha(_canonical(frozen)),
        "events": hashes,
    }
    manifest_text = _canonical(manifest)

    # Savepoint is safe within a larger authoritative Save transaction; never
    # returns a partially written manifest when nodes fail to insert.
    db.execute("SAVEPOINT experimental_sporting_event_append")
    try:
        if db.execute(
            "SELECT 1 FROM experimental_sporting_event_manifests "
            "WHERE run_id=? AND branch_id=? AND revision_id=?",
            (run_id, branch_id, revision_id),
        ).fetchone():
            raise SportingEventStoreError("Duplicate immutable Saved event manifest")
        for digest, body in zip(hashes, encoded):
            old = db.execute(
                "SELECT canonical_event_json FROM experimental_sporting_event_nodes "
                "WHERE run_id=? AND branch_id=? AND event_sha256=?",
                (run_id, branch_id, digest),
            ).fetchone()
            if old is None:
                db.execute(
                    "INSERT INTO experimental_sporting_event_nodes "
                    "(run_id, branch_id, event_sha256, canonical_event_json) "
                    "VALUES (?, ?, ?, ?)",
                    (run_id, branch_id, digest, body),
                )
            elif old[0] != body:
                raise SportingEventStoreError("Existing physical event node corrupted")
        db.execute(
            "INSERT INTO experimental_sporting_event_manifests "
            "(run_id, branch_id, revision_id, manifest_json, manifest_sha256) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, branch_id, revision_id, manifest_text, _sha(manifest_text)),
        )
        db.execute("RELEASE SAVEPOINT experimental_sporting_event_append")
    except BaseException:
        db.execute("ROLLBACK TO SAVEPOINT experimental_sporting_event_append")
        db.execute("RELEASE SAVEPOINT experimental_sporting_event_append")
        raise

    return {
        "revision_id": revision_id,
        "event_count": len(frozen),
        "new_nodes_possible": len(set(hashes)),
        "original_array_sha256": manifest["event_sha256"],
        "manifest_sha256": _sha(manifest_text),
    }


def stats(db: sqlite3.Connection):
    node_count, node_bytes = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(canonical_event_json AS BLOB))),0) "
        "FROM experimental_sporting_event_nodes"
    ).fetchone()
    manifest_count, manifest_bytes = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(manifest_json AS BLOB))),0) "
        "FROM experimental_sporting_event_manifests"
    ).fetchone()
    return {
        "nodes": node_count, "node_bytes": node_bytes,
        "manifests": manifest_count, "manifest_bytes": manifest_bytes,
        "total_payload_bytes": node_bytes + manifest_bytes,
    }
