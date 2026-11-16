"""Actual SQLite disk-index/IO granularity of Claude's *unchanged* Merkle nodes.

Distinct from earlier in-memory 15-event test: each threshold is persisted to
a separate WAL-mode SQLite file, page checkpointed, then checked with a new
cold SQLite connection. Every genuine original 256-player 15-event body must
be reconstructed exactly; a physically tampered node must fail closed.

No production Saved storage, v1 source or running giant #1820 is modified.
No claim that these numbers include 46 fully signed Saved envelopes/semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sqlite3
import time

EXPECTED_SOURCE_SHA = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"
RUN = "run"


def _module(path):
    spec = importlib.util.spec_from_file_location(
        "claude_original_merkle_physical", path.resolve(strict=True),
    )
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class SqliteNodeStore:
    """Same insert-only Run-scoped node body concept as #1805 spec."""

    def __init__(self, path, *, read_only=False):
        if read_only:
            self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        else:
            self.db = sqlite3.connect(str(path))
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute(
                "CREATE TABLE merkle_nodes "
                "(run_id TEXT NOT NULL,digest TEXT NOT NULL,body TEXT NOT NULL,"
                "PRIMARY KEY(run_id,digest)) WITHOUT ROWID"
            )
            self.db.commit()
        self.select_queries = 0
        self.inserted = 0
        self.inserted_raw_bytes = 0

    def __contains__(self, digest):
        self.select_queries += 1
        return self.db.execute(
            "SELECT 1 FROM merkle_nodes WHERE run_id=? AND digest=?",
            (RUN, digest)
        ).fetchone() is not None

    def __setitem__(self, digest, body):
        self.db.execute(
            "INSERT INTO merkle_nodes (run_id,digest,body) VALUES (?,?,?)",
            (RUN, digest, body)
        )
        self.inserted += 1
        self.inserted_raw_bytes += len(body.encode())

    def get(self, digest):
        self.select_queries += 1
        found = self.db.execute(
            "SELECT body FROM merkle_nodes WHERE run_id=? AND digest=?",
            (RUN, digest),
        ).fetchone()
        return found[0] if found else None

    def close(self):
        self.db.close()


def _rss():
    with open("/proc/self/status", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return None


def _physical(source):
    source = source.resolve(strict=True)
    with source.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == EXPECTED_SOURCE_SHA
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        value = db.execute(
            "SELECT payload_json FROM branch_saved_revisions ORDER BY sequence DESC LIMIT 1"
        ).fetchone()[0]
    events = json.loads(value)["content"]["calendar_player_sporting_checkpoint"]["state"]["events"]
    if not (len(events) == 15 and all(isinstance(x, dict) for x in events)):
        raise AssertionError("Expected exact original authentic 15 W12 sporting events")
    return events


def _one(mj, events, threshold, directory):
    db_path = directory / f"nodes-{threshold}.db"
    if db_path.exists():
        raise RuntimeError("Refusing to reuse previous benchmark database")
    store = SqliteNodeStore(db_path)
    roots = []
    wall = time.perf_counter()
    cpu = time.process_time()
    for entry in events:
        root, _ = mj.encode(entry, store, threshold=threshold)
        assert "digest" in root
        roots.append(root)
    store.db.commit()
    writer_wall_s = time.perf_counter() - wall
    writer_cpu_s = time.process_time() - cpu
    wal_path = Path(str(db_path) + "-wal")
    wal_peak_bytes_at_commit = wal_path.stat().st_size if wal_path.exists() else 0
    store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    physical_before_close = db_path.stat().st_size
    unique_nodes = store.inserted
    raw_nodes = store.inserted_raw_bytes
    insert_lookup_count = store.select_queries
    store.close()
    actual_bytes = db_path.stat().st_size

    cold = SqliteNodeStore(db_path, read_only=True)
    start = time.perf_counter()
    cpu = time.process_time()
    verifier = mj.Reader(cold)
    for root in roots:
        verifier.verify(root["digest"])
    auth_wall_s = time.perf_counter() - start
    auth_cpu_s = time.process_time() - cpu
    started = time.perf_counter()
    originals = [mj.canonical(e) for e in events]
    for root, original in zip(roots, originals):
        value = mj.decode_root(root, mj.Reader(cold))
        assert mj.canonical(value) == original
    reconstruction_wall_s = time.perf_counter() - started
    read_lookup_count = cold.select_queries

    # Mutate actual SQLite body after a successful read; a fresh reader must
    # not trust previously observed original content or cached digests.
    cold.close()
    writable = sqlite3.connect(db_path)
    digest = roots[0]["digest"]
    original_body = writable.execute(
        "SELECT body FROM merkle_nodes WHERE run_id=? AND digest=?",
        (RUN, digest)
    ).fetchone()[0]
    writable.execute(
        "UPDATE merkle_nodes SET body=? WHERE run_id=? AND digest=?",
        (original_body + " ", RUN, digest)
    )
    writable.commit()
    writable.close()
    tampered = SqliteNodeStore(db_path, read_only=True)
    try:
        mj.Reader(tampered).verify(digest)
    except mj.MerkleError:
        physical_tamper_rejected = True
    else:
        raise AssertionError("Tampered physical SQLite node accepted")
    finally:
        tampered.close()

    return {
        "threshold": threshold,
        "inserted_nodes": unique_nodes,
        "raw_node_text_bytes": raw_nodes,
        "sqlite_file_bytes_after_checkpoint": actual_bytes,
        "sqlite_overhead_bytes": actual_bytes - raw_nodes,
        "file_bytes_before_close": physical_before_close,
        "wal_bytes_just_after_writer_commit": wal_peak_bytes_at_commit,
        "writer_wall_s": round(writer_wall_s, 3),
        "writer_process_cpu_s": round(writer_cpu_s, 3),
        "cold_physical_node_verify_wall_s": round(auth_wall_s, 3),
        "cold_physical_node_verify_cpu_s": round(auth_cpu_s, 3),
        "exact_15_events_restore_wall_s": round(reconstruction_wall_s, 3),
        "verified_exact_event_count": len(events),
        "verified_node_bytes": verifier.hashed_bytes,
        "writer_lookup_queries": insert_lookup_count,
        "read_lookup_queries": read_lookup_count,
        "current_rss_kib": _rss(),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "tampered_sqlite_body_rejected": physical_tamper_rejected,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--claude-module", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = args.database.resolve(strict=True)
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    events = _physical(source)
    mj = _module(args.claude_module)
    original_bytes = sum(len(mj.canonical(event).encode()) for event in events)
    report = {
        "source_sha256": EXPECTED_SOURCE_SHA,
        "source_run": 43919075227,
        "original_15_unique_event_text_bytes": original_bytes,
        "using_claude_original_generic_merkle_sha": "4c7271144e02580d8d33a9b2bfb56f12d9ad2156",
        "production_code_changed": False,
        "physical_sqlite_thresholds": [],
    }
    for threshold in (4096, 2048, 1024, 512):
        case = _one(mj, events, threshold, out)
        case["sqlite_file_percent_vs_original_event_bytes"] = round(
            100 * case["sqlite_file_bytes_after_checkpoint"] / original_bytes, 3
        )
        report["physical_sqlite_thresholds"].append(case)
        print("W12_PHYSICAL_MERKLE " + json.dumps(
            {"phase": "case", **case}, sort_keys=True
        ), flush=True)
    (out / "physical-sqlite-merkle-thresholds.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print("W12_PHYSICAL_MERKLE " + json.dumps(
        {"phase": "complete", "cases": report["physical_sqlite_thresholds"],
         "source_run": report["source_run"]}, sort_keys=True
    ), flush=True)


if __name__ == "__main__":
    main()
