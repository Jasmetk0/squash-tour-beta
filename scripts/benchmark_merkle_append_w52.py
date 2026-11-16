"""Read-only six-stream Merkle append benchmark on genuine native Saved W52.

Usage:
    PYTHONPATH=src python scripts/benchmark_merkle_append_w52.py source.db

SOURCE_DB is opened SQLite mode=ro. Prototype nodes exist in memory ONLY.
Every field's complete prefix is compared to the preceding actual snapshot
before any delta is accepted. Every actual historical value is then rebuilt
from physical Merkle-node text (not cached proofs) and checked against SHA-256
of its original canonical JSON. This is NOT a native Save integration,
a semantic validation, nor a season-throughput benchmark.

Important: these SIX streams happened to be strictly append-only on the
original #1803 W52 reference; other runs may revise tour rankings or related
evidence. Such changes MUST fail the prefix check, not silently coerce them
into append operations. Fields like tour.editions are knowingly mutable and
are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time

from beta_engine.infrastructure.db.merkle_append_prototype import (
    AppendReader, MerkleAppendError, append, canonical,
)

# Historically observed append-only on one genuine 4-player W52 Run.
# This is NOT a promise of a global production schema guarantee.
HISTORICAL_PATHS = {
    "journal": ("journal",),
    "advances": ("advances",),
    "tournaments": ("tournaments",),
    "tour.receipts": ("tour", "receipts"),
    "tour.transitions": ("tour", "transitions"),
    "tour.rankings": ("tour", "rankings"),
}


def _at_path(state, path, *, sequence, name):
    value = state
    for key in path:
        if type(value) is not dict or key not in value:
            raise AssertionError((sequence, name, "missing field"))
        value = value[key]
    if type(value) is not list:
        raise AssertionError((sequence, name, "not a list"))
    return value


def run(source_db):
    db = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    store = {}
    heads = {name: None for name in HISTORICAL_PATHS}
    previous = {name: [] for name in heads}
    history = []
    total_bytes = 0
    new_events = {name: 0 for name in heads}
    append_cpu = 0.0
    external_prefix_cpu = 0.0
    try:
        cursor = db.execute(
            "SELECT sequence,payload_json FROM branch_saved_revisions "
            "WHERE payload_schema_version='native_fork_saved_root.v2' "
            "ORDER BY sequence"
        )
        for sequence, raw in cursor:
            state = json.loads(raw)["content"]["native_fork_runtime"]["state"]
            original_hashes = {}
            for name, path in HISTORICAL_PATHS.items():
                current = _at_path(state, path, sequence=sequence, name=name)
                serialized = canonical(current).encode("utf-8")
                total_bytes += len(serialized)
                original_hashes[name] = hashlib.sha256(serialized).hexdigest()
                start = time.process_time()
                same_prefix = current[:len(previous[name])] == previous[name]
                external_prefix_cpu += time.process_time() - start
                if not same_prefix:
                    raise AssertionError((sequence, name, "NOT APPEND ONLY"))
                delta = current[len(previous[name]):]
                if delta:
                    start = time.process_time()
                    heads[name] = append(
                        store, heads[name], delta, previous_count=len(previous[name]),
                    )
                    append_cpu += time.process_time() - start
                    new_events[name] += len(delta)
                previous[name] = current
            history.append((sequence, dict(heads), original_hashes))
    finally:
        db.close()

    if not history:
        raise AssertionError("No native Saved runtime snapshots found")

    start = time.process_time()
    for sequence, roots, original_hashes in history:
        for name, root in roots.items():
            reconstructed = AppendReader(store).history(root)
            actual_hash = hashlib.sha256(
                canonical(reconstructed).encode("utf-8")
            ).hexdigest()
            if actual_hash != original_hashes[name]:
                raise AssertionError((sequence, name, "reconstruction differs"))
    reconstruct_cpu = time.process_time() - start

    start = time.process_time()
    for root in heads.values():
        AppendReader(store).history(root)
    cold_head_cpu = time.process_time() - start

    if store:
        damaged = next(iter(store))
        old = store[damaged]
        store[damaged] = old + " "
        try:
            for root in heads.values():
                AppendReader(store).history(root)
        except MerkleAppendError:
            pass
        else:
            raise AssertionError("Physical corruption accepted after warm read")
        finally:
            store[damaged] = old

    return {
        "snapshots": len(history),
        "fields": list(heads),
        "new_events_by_field": new_events,
        "total_original_list_snapshot_bytes": total_bytes,
        "unique_merkle_node_bytes": sum(len(v.encode("utf-8")) for v in store.values()),
        "unique_nodes": len(store),
        "writer_cpu_s_including_full_prior_chain_authentication": round(append_cpu, 3),
        "external_full_prefix_comparison_cpu_s": round(external_prefix_cpu, 3),
        "all_revision_exact_reconstruction_cpu_s": round(reconstruct_cpu, 3),
        "cold_final_reconstruction_cpu_s": round(cold_head_cpu, 3),
        "exact_reconstructions": len(history) * len(heads),
        "physical_corruption_rejected": True,
        "scope": "six append-only arrays in one Run only; NOT full Saved or season speed",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_db")
    args = parser.parse_args()
    print(json.dumps(run(args.source_db), indent=2, sort_keys=True))
