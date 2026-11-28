"""Exclusive CPU and allocation pressure of MatchEngine work, by phase.

A CPU-time sampling profiler (``ITIMER_PROF`` signal, default every 0.5 ms of
process CPU) classifies each sample by the innermost Squash Engine frame on the
stack. Library frames (json, hashlib, pydantic, random, enum) are charged to the
domain frame that called them, so e.g. JSON encoding inside a rally event
validator is "rally event: hash". Samples are exclusive: each lands in exactly
one phase. Because sampling is statistical, phases below ~1 % are noise.

Allocation pressure uses an approximate sampled heap-rise proxy. In a separate
``tracemalloc`` pass, the rise from each interval's starting live heap to its
peak is charged to the phase observed at the sampling point. Short-lived
allocations can be missed, and phase changes between samples are approximate.
The CPU pass separately measures GC runs and their time.

    python scripts/profile_match_engine_phases.py set
    python scripts/profile_match_engine_phases.py ko128 --no-alloc

Unix only. The HTTP scenarios run MatchEngine on a server worker thread, and
``restart`` finishes its matches in child processes.
Use the A/B timer for those scenarios. Python delivers the signal callback on
the main thread, so its stack cannot attribute server-side work.
"""

from __future__ import annotations

import argparse
import collections
import gc
import json
import linecache
import signal
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

PACKAGE = "beta_engine" + "/"

# (file suffix, function names or None for "any") -> phase, checked in order.
_RULES: tuple[tuple[str, frozenset[str] | None, str], ...] = (
    ("core/rng.py", frozenset({"derive", "branch", "derive_child_seed", "__init__", "_random"}), "rng: derive + seed"),
    ("core/rng.py", None, "rng: draws"),
    ("matches/rallies.py", frozenset({"_json_value", "_hash_payload", "_content_hash", "_event_hash"}), "rally event: hash"),
    ("matches/rallies.py", frozenset({"validate_event", "create", "_create_from_engine"}), "rally event: validate/construct"),
    ("matches/rallies.py", frozenset({"validate_chain", "validate_rules_timeline"}), "rally log: validate"),
    ("matches/rallies.py", None, "rally event: nested models"),
    ("matches/timeline.py", frozenset({"_content_hash", "_event_hash"}), "timeline event: hash"),
    ("matches/timeline.py", frozenset({"validate_event_hash", "create", "_create_from_engine"}), "timeline event: validate/construct"),
    ("matches/timeline.py", frozenset({"validate_chain_and_totals"}), "timeline log: validate"),
    ("matches/timeline.py", None, "timeline event: validate/construct"),
    ("matches/stamina.py", frozenset({"_hash_payload", "_content_hash", "_transition_hash"}), "stamina transition: hash"),
    ("matches/stamina.py", frozenset({"validate_transition", "create", "_create_from_engine"}), "stamina transition: validate/construct"),
    ("matches/stamina.py", frozenset({"validate_chain", "validate_timeline", "validate_effective_snapshot", "validate_rally_outcomes"}), "stamina log: validate"),
    ("matches/stamina.py", frozenset({"build"}), "stamina log: rebuild from timeline"),
    ("matches/stamina.py", None, "stamina: state math"),
    ("matches/match_engine.py", frozenset({"_base_strength", "_style_and_archetype_adjustment", "_game_probability", "_stamina_impact", "_control_pressure_factor", "_stamina_reserve", "_probability_logit", "_clamp"}), "attributes + probabilities"),
    ("matches/match_engine.py", frozenset({"_prepare_rally_gameplans", "_review_player_gameplan", "_record_gameplan_outcome"}), "gameplans"),
    ("matches/match_engine.py", frozenset({"_resolve_rally_situation"}), "rally rules"),
    ("matches/match_engine.py", frozenset({"_build_timeline", "_between_rally_interval", "_sample_between_rally_interval", "_game_break_event", "_sample_restart_intent", "_player_ready_seconds"}), "timeline construction"),
    ("matches/match_engine.py", frozenset({"_build_result"}), "result assembly"),
    ("matches/match_engine.py", None, "rally loop + control"),
    ("matches/gameplans.py", None, "gameplans"),
    ("matches/rally_rules.py", None, "rally rules"),
    ("matches/models.py", None, "result assembly"),
    ("matches/inputs.py", None, "match input snapshot"),
    ("matches/formats.py", None, "match input snapshot"),
    ("matches/health.py", None, "match input snapshot"),
    ("matches/timing.py", None, "match input snapshot"),
    ("matches/control.py", None, "match input snapshot"),
    ("domain/players", None, "players"),
    ("application/", None, "tournament infrastructure"),
    ("domain/", None, "tournament infrastructure"),
    ("scripts/", None, "benchmark harness"),
)

_HASH_HINTS = ("model_dump", "_content_hash", "_hash_payload", "json.dumps")


def _classify(frame) -> str:
    while frame is not None:
        filename = frame.f_code.co_filename.replace("\\", "/")
        if PACKAGE in filename or "/scripts/" in filename:
            if filename.endswith("/matches/content_hash.py"):
                frame = frame.f_back
                continue
            name = frame.f_code.co_name
            for suffix, names, phase in _RULES:
                if suffix in filename and (names is None or name in names):
                    if phase.endswith("validate/construct"):
                        line = linecache.getline(filename, frame.f_lineno)
                        if any(hint in line for hint in _HASH_HINTS):
                            return phase.split(":")[0] + ": hash"
                    return phase
            return "other engine"
        frame = frame.f_back
    return "outside engine (import/startup)"


class PhaseSampler:
    def __init__(self, interval: float, allocations: bool):
        self.interval = interval
        self.allocations = allocations
        self.samples: collections.Counter[str] = collections.Counter()
        self.heap_rise: collections.Counter[str] = collections.Counter()
        self.gc_runs: collections.Counter[str] = collections.Counter()
        self.gc_seconds: collections.Counter[str] = collections.Counter()
        self._last_traced = 0
        self._gc_started = 0.0
        self._gc_phase = ""

    def _on_sample(self, _signum, frame):
        phase = _classify(frame)
        self.samples[phase] += 1
        if self.allocations:
            current, peak = tracemalloc.get_traced_memory()
            self.heap_rise[phase] += max(0, peak - self._last_traced)
            tracemalloc.reset_peak()
            self._last_traced = current

    def _on_gc(self, stage, info):
        if stage == "start":
            self._gc_phase = _classify(sys._getframe(2))
            self._gc_started = time.process_time()
        else:
            self.gc_runs[self._gc_phase] += 1
            self.gc_seconds[self._gc_phase] += time.process_time() - self._gc_started

    def __enter__(self):
        if self.allocations:
            tracemalloc.start()
            self._last_traced = tracemalloc.get_traced_memory()[0]
        gc.callbacks.append(self._on_gc)
        signal.signal(signal.SIGPROF, self._on_sample)
        signal.setitimer(signal.ITIMER_PROF, self.interval, self.interval)
        return self

    def __exit__(self, *_exc):
        signal.setitimer(signal.ITIMER_PROF, 0, 0)
        gc.callbacks.remove(self._on_gc)
        if self.allocations:
            tracemalloc.stop()


def main(argv=None):
    from scripts import benchmark_match_engine as bench

    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=tuple(name for name in bench.SCENARIOS
                                                if not name.startswith("http") and name != "restart"))
    parser.add_argument("--interval", type=float, default=0.0005)
    parser.add_argument("--no-alloc", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.interval <= 0:
        parser.error("--interval must be positive")
    bench.run_scenario(args.scenario, 1)  # warm imports/schemas outside the sample
    # Pass 1: CPU and GC without tracemalloc (which would distort CPU shares).
    cpu = time.process_time()
    with PhaseSampler(args.interval, False) as sampler:
        report = bench.run_scenario(args.scenario, 1)
    cpu = time.process_time() - cpu
    if not args.no_alloc:
        # Pass 2: identical work again, for the sampled heap-rise proxy.
        with PhaseSampler(args.interval, True) as alloc_sampler:
            bench.run_scenario(args.scenario, 1)
        sampler.heap_rise = alloc_sampler.heap_rise
    total = sum(sampler.samples.values()) or 1
    phases = sorted(sampler.samples, key=sampler.samples.__getitem__, reverse=True)
    rows = [
        {
            "phase": phase,
            "cpu_share": round(sampler.samples[phase] / total, 4),
            "cpu_seconds": round(cpu * sampler.samples[phase] / total, 3),
            "sampled_heap_rise_mib": (
                None if args.no_alloc else round(sampler.heap_rise[phase] / 2**20, 1)
            ),
            "gc_runs": sampler.gc_runs[phase],
            "gc_seconds": round(sampler.gc_seconds[phase], 3),
        }
        for phase in phases
    ]
    summary = {
        "scenario": args.scenario, "cpu_seconds": round(cpu, 3), "samples": total,
        "fingerprint": report["fingerprint"], "phases": rows,
    }
    if args.json:
        print(json.dumps(summary))
        return
    print(f"{args.scenario}: {cpu:.2f} s CPU, {total} samples, fingerprint {report['fingerprint'][:12]}")
    print(f"{'phase':42} {'CPU %':>6} {'CPU s':>7} {'rise MiB':>9} {'GC n':>5} {'GC s':>6}")
    for row in rows:
        rise = row["sampled_heap_rise_mib"]
        formatted_rise = "-" if rise is None else f"{rise:.1f}"
        print(f"{row['phase']:42} {100 * row['cpu_share']:6.1f} {row['cpu_seconds']:7.2f} "
              f"{formatted_rise:>9} {row['gc_runs']:5d} {row['gc_seconds']:6.3f}")


if __name__ == "__main__":
    main()
