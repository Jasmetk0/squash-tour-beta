"""PROTOTYPE benchmark: re-store a real v1 Saved history as Merkle JSON nodes.

Reads an existing Saved history (read-only), writes every revision's payload into
a fresh SQLite node table revision by revision, then measures a cold
authentication of all revisions and an exact reconstruction check:

    python scripts/prototype_merkle_saved_history.py SOURCE.db --work /tmp/merkle

Nothing in production reads this format. The source database is opened read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from beta_engine.infrastructure.db import merkle_json_prototype as mj  # noqa: E402


class SqliteNodes:
    """Insert-only node table; reads return the ACTUAL stored text."""

    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS merkle_nodes (digest TEXT PRIMARY KEY, body TEXT NOT NULL) WITHOUT ROWID")
        self.reads = 0

    def __contains__(self, digest):
        return self.db.execute("SELECT 1 FROM merkle_nodes WHERE digest = ?", (digest,)).fetchone() is not None

    def __setitem__(self, digest, body):
        self.db.execute("INSERT INTO merkle_nodes (digest, body) VALUES (?, ?)", (digest, body))

    def get(self, digest):
        self.reads += 1
        row = self.db.execute("SELECT body FROM merkle_nodes WHERE digest = ?", (digest,)).fetchone()
        return row[0] if row else None


def build(source, work):
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    rows = src.execute("SELECT revision_id, sequence, payload_json FROM branch_saved_revisions ORDER BY sequence").fetchall()
    nodes_path = work / "nodes.db"
    nodes_path.unlink(missing_ok=True)
    store = SqliteNodes(str(nodes_path))
    roots, per_revision, encode_seconds = [], [], 0.0
    for revision_id, sequence, text in rows:
        payload = json.loads(text)
        started = time.perf_counter()
        root, stats = mj.encode(payload, store)
        store.db.commit()
        encode_seconds += time.perf_counter() - started
        roots.append({"revision_id": revision_id, "sequence": sequence, "root": root,
                      "original_chars": len(text)})
        per_revision.append(stats["new_bytes"])
    (work / "roots.json").write_text(json.dumps(roots))
    store.db.execute("VACUUM")
    store.db.close()
    return {
        "revisions": len(rows),
        "v1_payload_mb": round(sum(r["original_chars"] for r in roots) / 1e6, 1),
        "v1_file_mb": round(os.path.getsize(source) / 1e6, 1),
        "merkle_nodes_file_mb": round(os.path.getsize(nodes_path) / 1e6, 1),
        "encode_seconds_total": round(encode_seconds, 1),
        "new_bytes_per_revision_last10_kb": round(sum(per_revision[-10:]) / 10 / 1e3, 1),
        "new_bytes_per_revision_first10_kb": round(sum(per_revision[:10]) / 10 / 1e3, 1),
    }


def cold(source, work):
    """Fresh process: authenticate every revision, then exact reconstruction."""
    store = SqliteNodes(str(work / "nodes.db"))
    roots = json.loads((work / "roots.json").read_text())
    reader = mj.Reader(store)
    started = time.perf_counter()
    for item in roots:
        if "digest" in item["root"]:
            reader.verify(item["root"]["digest"])
    verify_seconds = time.perf_counter() - started
    started = time.perf_counter()
    head = mj.decode_root(roots[-1]["root"], reader)
    head_seconds = time.perf_counter() - started
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    exact = 0
    for item in roots:
        (text,) = src.execute("SELECT payload_json FROM branch_saved_revisions WHERE revision_id = ?",
                              (item["revision_id"],)).fetchone()
        if mj.canonical(mj.decode_root(item["root"], mj.Reader(store))) == text:
            exact += 1
    return {
        "cold_verify_all_revisions_seconds": round(verify_seconds, 2),
        "cold_verify_hashed_mb": round(reader.hashed_bytes / 1e6, 1),
        "node_reads": store.reads,
        "head_reconstruct_seconds": round(head_seconds, 2),
        "head_is_dict": isinstance(head, dict),
        "exact_reconstruction": f"{exact}/{len(roots)}",
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--cold-only", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    if args.cold_only:
        print(json.dumps(cold(args.source, args.work)))
        return
    report = build(args.source, args.work)
    out = subprocess.run([sys.executable, __file__, str(args.source), "--work", str(args.work), "--cold-only"],
                         check=True, capture_output=True, text=True)
    report.update(json.loads(out.stdout))
    report["source"] = args.source.name
    print(json.dumps(report))


if __name__ == "__main__":
    main()
