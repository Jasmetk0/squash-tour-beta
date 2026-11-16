"""Measure a discarded native Saved subtree copy, without bypassing any verifier.

By default the fixture is synthetic. For an actual previously prepared database,
pass --database work/<fixture>.db; it is opened read-only and never modified.
Neither result is a complete Save / season benchmark.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import gc
import json
import resource
import sqlite3
import statistics
import time
import tracemalloc
from pathlib import Path

from beta_engine.application.native_fork_runtime_service import (
    _copy_append_payload_without_replaced_runtime,
)
from beta_engine.domain.run_revisions import canonical_json
from beta_engine.infrastructure.db.native_fork_runtime_state import KEY


def synthetic_source(player_count: int):
    players = [
        {
            "player_id": f"p-{i:05d}",
            "attributes": {f"attribute-{j:02d}": (i * 37 + j * 71) % 201 for j in range(57)},
            "health": [{"week": week, "state": week % 4} for week in range(4)],
        }
        for i in range(player_count)
    ]
    return {
        "run": {"run_id": "r", "run_calendar": {"weeks_per_year": 61, "season_count": 50}},
        "branch": {"branch_id": "b", "status": "active"},
        "content": {
            KEY: {"state": {"players": players, "history": [{"week": n, "audit": n} for n in range(100)]}},
            "source": {"original_source": True},
        },
    }


def database_source(path: Path, run_id: str | None, branch_id: str | None):
    # No mutation and no trusted verification claim: an input for timing only.
    conditions = ["payload_schema_version = 'native_fork_saved_root.v2'"]
    params = []
    if run_id is not None:
        conditions.append("run_id = ?")
        params.append(run_id)
    if branch_id is not None:
        conditions.append("branch_id = ?")
        params.append(branch_id)
    query = (
        "SELECT payload_json FROM branch_saved_revisions WHERE "
        + " AND ".join(conditions)
        + " ORDER BY sequence DESC LIMIT 1"
    )
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        row = db.execute(query, params).fetchone()
    if row is None:
        raise ValueError("No native v2 Saved Revision matches the selected Run/Branch")
    return json.loads(row[0])


def baseline(source):
    # Original writer behavior: clone everything, then overwrite the prior runtime.
    return deepcopy(source)


def candidate(source):
    return _copy_append_payload_without_replaced_runtime(source)


def once(action, source, replacement):
    start = time.perf_counter()
    payload = action(source)
    payload["content"][KEY] = replacement
    encoded = canonical_json(payload)
    return time.perf_counter() - start, encoded


def memory(action, source, replacement):
    gc.collect()
    tracemalloc.start()
    _duration, _encoded = once(action, source, replacement)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return peak


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--branch-id")
    parser.add_argument("--players", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=8)
    args = parser.parse_args()
    if args.repeats < 2 or args.players < 1:
        parser.error("--repeats >= 2 and --players >= 1 are required")
    source = (
        database_source(args.database, args.run_id, args.branch_id)
        if args.database else synthetic_source(args.players)
    )
    if not isinstance(source, dict) or not isinstance(source.get("content"), dict):
        raise ValueError("Input payload lacks a Saved content object")
    if KEY not in source["content"]:
        raise ValueError("Input has no previous native runtime to replace")
    # Component creation and hash validation are identical and OUTSIDE this
    # isolated copy+encode experiment. Reuse the same new component each time.
    replacement = source["content"][KEY]
    base_json = once(baseline, source, replacement)[1]
    cand_json = once(candidate, source, replacement)[1]
    if base_json != cand_json:
        raise AssertionError("Copy candidate differs in canonical Saved JSON")
    results = {"baseline": [], "candidate": []}
    for _ in range(args.repeats):
        for label, action in (
            ("baseline", baseline), ("candidate", candidate),
            ("candidate", candidate), ("baseline", baseline),
        ):
            duration, encoded = once(action, source, replacement)
            if encoded != base_json:
                raise AssertionError("Repeated copy mutated Saved content")
            results[label].append(duration)
    report = {
        "input": "real_sqlite_unverified_read_only" if args.database else "synthetic",
        "input_bytes": len(canonical_json(source).encode("utf-8")),
        "saved_output_bytes": len(base_json.encode("utf-8")),
        "repeats_per_variant": 2 * args.repeats,
        "baseline_median_s": statistics.median(results["baseline"]),
        "candidate_median_s": statistics.median(results["candidate"]),
        "baseline_traced_peak_bytes": memory(baseline, source, replacement),
        "candidate_traced_peak_bytes": memory(candidate, source, replacement),
        "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "byte_equal": True,
        "scope": "copy_plus_canonical_encode_only; not complete Save, not a season",
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
