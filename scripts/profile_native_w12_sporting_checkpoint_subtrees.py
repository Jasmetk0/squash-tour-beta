"""Independent read-only sub-component accounting for the real W12 sporting checkpoint.

Never changes Saved bytes or asserts that mutable sporting state is append-only.
The input database is the original played 256-player/8-Edition 46-Saved artifact.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
import time

SOURCE_SHA256 = "17d8bae0e69e08457cb3ba2d76da813b6a2a684da76eb96ab39fb0ae51ab78e7"


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def run(source: Path, result_dir: Path):
    source = source.resolve(strict=True)
    with source.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    assert actual == SOURCE_SHA256, actual
    started = time.perf_counter()

    aggregates = defaultdict(lambda: {
        "revision_count": 0, "aggregate_bytes": 0,
        "last_bytes": 0, "identical_prior_bytes": 0,
        "identical_prior_count": 0, "distinct_hashes": set(),
        "first_bytes": None, "kind": None, "last_length": None,
    })
    previous_digest = {}
    sample_count = 0
    checkpoint_bytes = 0
    last_keys = {}
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as db:
        for seq, raw in db.execute(
            "SELECT sequence, payload_json FROM branch_saved_revisions "
            "ORDER BY sequence"
        ):
            doc = json.loads(raw)
            cp = doc.get("content", {}).get("calendar_player_sporting_checkpoint")
            if cp is None:
                continue
            if not isinstance(cp, dict) or not isinstance(cp.get("state"), dict):
                raise AssertionError((seq, "checkpoint state not a dictionary"))
            sample_count += 1
            checkpoint_bytes += len(_encoded(cp))
            state = cp["state"]

            # Compare top-level state fields only. Keys which change are NOT
            # assumed append-only even when their lengths are increasing.
            for key, value in state.items():
                b = _encoded(value)
                digest = hashlib.sha256(b).hexdigest()
                row = aggregates[key]
                row["revision_count"] += 1
                row["aggregate_bytes"] += len(b)
                row["last_bytes"] = len(b)
                if row["first_bytes"] is None:
                    row["first_bytes"] = len(b)
                row["kind"] = type(value).__name__
                row["last_length"] = len(value) if isinstance(value, (list, dict)) else None
                row["distinct_hashes"].add(digest)
                if previous_digest.get(key) == digest:
                    row["identical_prior_bytes"] += len(b)
                    row["identical_prior_count"] += 1
                previous_digest[key] = digest
            last_keys = {key: {"kind": type(v).__name__,
                               "length": len(v) if isinstance(v, (dict, list)) else None}
                         for key, v in state.items()}
            if sample_count % 10 == 0:
                print("W12_CHECKPOINT_SUBTREES " + json.dumps({
                    "phase": "scan", "revision_sequence": seq,
                    "checkpoints": sample_count, "keys": len(state),
                }), flush=True)

    assert sample_count == 42, sample_count
    summarized = {
        key: {
            **{k: v for k, v in data.items() if k != "distinct_hashes"},
            "distinct_exact_values": len(data["distinct_hashes"]),
        }
        for key, data in sorted(
            aggregates.items(), key=lambda item: item[1]["aggregate_bytes"],
            reverse=True,
        )
    }
    data = {
        "source_db_sha256": SOURCE_SHA256,
        "checkpoints": sample_count,
        "checkpoint_total_canonical_bytes": checkpoint_bytes,
        "state_fields": summarized,
        "last_snapshot_field_shapes": last_keys,
        "wall_s": round(time.perf_counter() - started, 3),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "warning": "Identical historic bytes are a potential dedup target, not "
                   "a safe storage implementation; authentic revision hashes "
                   "must reconstruct all original bytes and reject tampering",
    }
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "sporting-subtrees.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    print("W12_CHECKPOINT_SUBTREES " + json.dumps({
        "phase": "complete",
        "checkpoints": sample_count,
        "total_bytes": checkpoint_bytes,
        "top_fields": [
            {"key": key, **value} for key, value in list(summarized.items())[:18]
        ],
        "peak_rss_kib": data["peak_rss_kib"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.database, args.out)
