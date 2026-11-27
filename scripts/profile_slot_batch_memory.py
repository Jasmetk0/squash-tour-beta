"""Temporary memory and wrapper overhead of the batched slot replay memo.

Lab measurement (not a Run): one wide frozen slot of ``--matches`` ko128
first-round matches inside a private replay memo scope.

* ``original``: the exact ``buuk`` 29784d5 one-by-one ``_simulate_slot_match``
  (inlined below), the reference;
* ``batch``: the candidate ``_simulate_slot_matches`` without a pool;
* ``batch-pool-N``: the same with an N-worker spawn pool;
* ``concurrent-pool-N``: two threads, each its own scope and slot, one pool.

Timing (median of ``--repeats``, wall and process CPU) runs without
instrumentation. A separate pass under ``tracemalloc`` reports the Python heap
peak during the call above the heap after it ("temporary", i.e. held outside
the memo and the returned results) and what the call retained. RSS is the
process high-water mark (Linux ``ru_maxrss``) after each variant, informative
only because it never decreases.

    PYTHONPATH=src python scripts/profile_slot_batch_memory.py --matches 32 --workers 2,3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import statistics
import sys
import threading
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import benchmark_match_engine as bench  # noqa: E402

from beta_engine.domain.matches import MatchContext, MatchParticipantContext, slot_batch  # noqa: E402
from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot  # noqa: E402
from beta_engine.domain.matches.models import MatchResult  # noqa: E402
from beta_engine.domain.players.health import PlayerHealthProfile  # noqa: E402
from beta_engine.domain.tournaments import calendar_global_slots as slots  # noqa: E402
from beta_engine.infrastructure.match_workers import ProcessMatchExecutor  # noqa: E402


def wide_slot(count):
    players = [bench._player(f"P{i:03d}", 95 - (i * 50) // 128, style=bench.STYLES[i % 5],
                             archetype=bench.ARCHETYPES[(i * 3) % 5], spread=i % 6)
               for i in range(1, 129)]
    items = []
    for k in range(count):
        context = MatchContext(match_id=f"ko128-r1-m{k + 1:02d}",
                               player_a=MatchParticipantContext(player=players[k % 64]),
                               player_b=MatchParticipantContext(player=players[127 - k % 64]))
        health = EffectiveMatchHealthSnapshot.from_profiles(
            player_a=PlayerHealthProfile(player_id=context.player_a.player.player_id),
            player_b=PlayerHealthProfile(player_id=context.player_b.player.player_id))
        items.append((context, 2701 + k * 7919, f"{k + 1:064x}", health))
    return items


def _original(items):
    """``buuk`` 29784d5 ``_simulate_slot_match`` applied one by one."""
    scope = slots._replay_projections.get()
    cache = scope["match_results"]
    out = []
    for context, seed, anchor, health in items:
        key = (seed, anchor, context.model_dump_json().encode(), health.model_dump_json().encode())
        previous = cache.pop(key, None)
        if previous is not None:
            cache[key] = previous
            out.append(MatchResult.model_validate_json(previous[1]))
            continue
        result = slot_batch.simulate_frozen(context, seed=seed, anchor=anchor, health=health)
        encoded = result.model_dump_json().encode()
        size = 128 + len(anchor) + len(key[2]) + len(key[3]) + len(encoded)
        if size <= slots._MATCH_REPLAY_BYTES:
            while scope["match_result_bytes"] + size > slots._MATCH_REPLAY_BYTES:
                removed_size, _ = cache.pop(next(iter(cache)))
                scope["match_result_bytes"] -= removed_size
            cache[key] = (size, encoded)
            scope["match_result_bytes"] += size
        out.append(result)
    return out


def _in_scope(function, items):
    token = slots._replay_projections.set(
        {"fingerprints": {}, "tournaments": {}, "match_results": {}, "match_result_bytes": 0})
    try:
        results = function(items)
        return results, slots._replay_projections.get()
    finally:
        slots._replay_projections.reset(token)


def _digest(results):
    h = hashlib.sha256()
    for r in results:
        h.update(r.model_dump_json().encode())
    return h.hexdigest()


def variant(name, executor):
    if name == "original":
        return lambda items: _in_scope(_original, items)
    previous = slot_batch.installed_executor()

    def run(items):
        slot_batch.install_executor(executor)
        try:
            return _in_scope(slots._simulate_slot_matches, items)
        finally:
            slot_batch.install_executor(previous)
    return run


def concurrent(executor, items):
    """Two request threads, each with its own memo scope, sharing one pool."""
    outputs, threads = {}, []
    barrier = threading.Barrier(2)
    previous = slot_batch.install_executor(executor)

    def one(i):
        barrier.wait()
        outputs[i] = _in_scope(slots._simulate_slot_matches, items)

    try:
        for i in range(2):
            threads.append(threading.Thread(target=one, args=(i,)))
            threads[-1].start()
        for t in threads:
            t.join()
    finally:
        slot_batch.install_executor(previous)
    assert _digest(outputs[0][0]) == _digest(outputs[1][0])
    return outputs[0]


def measure(label, call, items, repeats):
    walls, cpus, digest = [], [], None
    for _ in range(repeats):
        w, c = time.perf_counter(), time.process_time()
        results, scope = call(items)
        walls.append(time.perf_counter() - w)
        cpus.append(time.process_time() - c)
        digest = _digest(results)
        del results, scope
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    tracemalloc.reset_peak()
    results, scope = call(items)
    after, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    memo = scope.get("match_result_bytes", 0) if isinstance(scope, dict) else 0
    del results, scope
    return {"variant": label, "wall_median_s": round(statistics.median(walls), 3),
            "wall_max_s": round(max(walls), 3), "cpu_median_s": round(statistics.median(cpus), 3),
            "heap_peak_above_start_mib": round((peak - base) / 2 ** 20, 1),
            "heap_retained_mib": round((after - base) / 2 ** 20, 1),
            "temporary_peak_mib": round((peak - after) / 2 ** 20, 1),
            "memo_accounted_mib": round(memo / 2 ** 20, 1),
            "max_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "digest": digest}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--matches", type=int, default=32)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--workers", default="2,3")
    args = parser.parse_args(argv)
    items = wide_slot(args.matches)
    rows = [measure("original", variant("original", None), items, args.repeats),
            measure("batch", variant("batch", None), items, args.repeats)]
    for workers in [int(w) for w in args.workers.split(",") if w.strip()]:
        executor = ProcessMatchExecutor(workers)
        try:
            executor.start()
            rows.append(measure(f"batch-pool-{workers}", variant("batch", executor), items, args.repeats))
            rows.append(measure(f"concurrent-pool-{workers}", lambda values: concurrent(executor, values),
                                items, args.repeats))
            rows[-1]["executor"] = executor.stats()
        finally:
            executor.close()
    assert len({row["digest"] for row in rows}) == 1, "results differ"
    print(json.dumps({"schema_version": "slot_batch_memory.v1", "matches": args.matches,
                      "python": sys.version.split()[0], "cpu_count": os.cpu_count(),
                      "counters": slot_batch.batch_counters(), "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
