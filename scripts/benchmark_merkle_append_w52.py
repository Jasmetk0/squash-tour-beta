"""Read-only actual-W52 benchmark of append-only Merkle history deltas.

Example:
    PYTHONPATH=src python scripts/benchmark_merkle_append_w52.py /path/to/matrix.db

The SOURCE_DB is opened SQLite mode=ro; prototype nodes are only an in-memory
dict. No source writes or changes to native Saved authority. Every historical
journal and advances list is reconstructed exactly at *every* W52 revision.
This does NOT benchmark an integrated storage writer or full season runtime.
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


def run(source_db):
    db = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    store, heads = {}, {"journal": None, "advances": None}
    previous = {name: [] for name in heads}
    history = []
    total_bytes = 0
    new_events = 0
    append_cpu = 0.0
    external_prefix_cpu = 0.0
    try:
        sql = db.execute(
            "SELECT sequence,payload_json FROM branch_saved_revisions "
            "WHERE payload_schema_version='native_fork_saved_root.v2' "
            "ORDER BY sequence"
        )
        for sequence, raw in sql:
            state = json.loads(raw)["content"]["native_fork_runtime"]["state"]
            original_hashes = {}
            for name in heads:
                current = state.get(name, [])
                if type(current) is not list:
                    raise AssertionError((sequence, name, "not list"))
                total_bytes += len(canonical(current))
                original_hashes[name] = hashlib.sha256(canonical(current).encode()).hexdigest()
                t = time.process_time()
                same = current[:len(previous[name])] == previous[name]
                external_prefix_cpu += time.process_time() - t
                if not same:
                    raise AssertionError((sequence, name, "NOT APPEND ONLY"))
                delta = current[len(previous[name]):]
                if delta:
                    t = time.process_time()
                    heads[name] = append(store, heads[name], delta, previous_count=len(previous[name]))
                    append_cpu += time.process_time() - t
                    new_events += len(delta)
                previous[name] = current
            history.append((sequence, dict(heads), original_hashes))
    finally:
        db.close()

    t = time.process_time()
    for sequence, roots, hashes in history:
        for name in roots:
            reconstructed = AppendReader(store).history(roots[name])
            actual = hashlib.sha256(canonical(reconstructed).encode()).hexdigest()
            if actual != hashes[name]:
                raise AssertionError((sequence, name, "reconstruction differs"))
    reconstruct_cpu = time.process_time() - t

    t = time.process_time()
    for name in heads:
        AppendReader(store).history(heads[name])
    cold_head_cpu = time.process_time() - t

    if store:
        damaged = next(iter(store))
        old = store[damaged]
        store[damaged] = old + " "
        try:
            for name in heads:
                AppendReader(store).history(heads[name])
        except MerkleAppendError:
            pass
        else:
            raise AssertionError("Physical corruption accepted")
        store[damaged] = old

    return {
        "snapshots": len(history),
        "fields": list(heads),
        "new_events": new_events,
        "total_original_list_snapshot_bytes": total_bytes,
        "unique_merkle_node_bytes": sum(len(v) for v in store.values()),
        "unique_nodes": len(store),
        "writer_cpu_s_including_full_prior_chain_authentication": round(append_cpu, 3),
        "external_full_prefix_comparison_cpu_s": round(external_prefix_cpu, 3),
        "all_revision_exact_reconstruction_cpu_s": round(reconstruct_cpu, 3),
        "cold_final_reconstruction_cpu_s": round(cold_head_cpu, 3),
        "physical_corruption_rejected": True,
        "scope": "prototype append-only arrays only, NOT whole Saved or simulation speed",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_db")
    args = parser.parse_args()
    print(json.dumps(run(args.source_db), indent=2, sort_keys=True))
