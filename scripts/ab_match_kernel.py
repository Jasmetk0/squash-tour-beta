"""Pinned A/B (or A/A) of two commits' MatchEngine with one harness.

Both commits are checked out as detached Git worktrees under ``--out``. The
harness is always THIS checkout's ``scripts/benchmark_match_engine.py``; it
imports ``src/beta_engine`` from the worktree named by
``MATCH_BENCH_SOURCE_ROOT`` and reports the imported file, so both sides run the
same deterministic inputs and the report proves which source was measured.

1. Equality pass: one ``--chains`` process per side and scenario. Every digest
   (complete ``model_dump_json`` bytes and sorted JSON of each real
   ``MatchResult``; rally, timeline and stamina chains; gameplan, rules and
   control contexts; rally numbers/times; bracket/HTTP output; step and restart
   states) must be identical, or the run stops with exit 1.
2. Timing pass: ``--rounds`` rounds in fresh processes with ``PYTHONHASHSEED=0``
   and no instrumentation, A B B A in even and B A A B in odd rounds so that a
   position effect cancels. Each child's peak RSS and CPU come from
   ``os.wait4``; the output fingerprint must equal the equality pass. Besides
   medians, the summary gives per-round paired ratios (sum of the round's two B
   samples over its two A samples), which are robust to slow host drift.

    a=$(git rev-parse origin/buuk); b=$(git rev-parse HEAD)
    python scripts/ab_match_kernel.py --a "$a" --b "$a" --out work/aa --rounds 3 ko64 ko128
    python scripts/ab_match_kernel.py --a "$a" --b "$b" --out work/ab --rounds 3 ko32 ko64 ko128

The worktrees are removed at the end unless ``--keep``. Reports:
``manifest.json``, ``equality.json``, ``samples.jsonl`` and ``summary.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "benchmark_match_engine.py"
METRICS = {
    "wall": "wall_seconds", "cpu": "cpu_seconds", "engine": "engine_seconds_last",
    "infrastructure": "infrastructure_seconds_last",
}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout.strip()


def _cpu_model() -> str | None:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return platform.processor() or None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _child(python: str, source: Path, args: list[str]) -> tuple[dict, dict]:
    """Run the harness in a fresh process; return (report, rusage)."""
    env = {**os.environ, "PYTHONHASHSEED": "0", "MATCH_BENCH_SOURCE_ROOT": str(source)}
    env.pop("PYTHONPATH", None)
    started = time.perf_counter()
    process = subprocess.Popen([python, str(HARNESS), *args], cwd=ROOT, env=env,
                               stdout=subprocess.PIPE, text=True)
    stdout = process.stdout.read()
    _, status, usage = os.wait4(process.pid, 0)
    process.returncode = os.waitstatus_to_exitcode(status)
    if process.returncode != 0:
        raise SystemExit(f"harness failed ({process.returncode}): {' '.join(args)}")
    report = json.loads(stdout.strip().splitlines()[-1])
    if Path(report["source_root"]).resolve() != source.resolve() or not Path(
        report["beta_engine_file"]
    ).resolve().is_relative_to(source.resolve()):
        raise SystemExit(f"harness imported the wrong source tree: {report['beta_engine_file']}")
    return report, {
        "process_wall_seconds": round(time.perf_counter() - started, 3),
        "process_cpu_seconds": round(usage.ru_utime + usage.ru_stime, 3),
        "process_peak_rss_mb": round(usage.ru_maxrss / 1024, 1),
    }


def _summary(values: list[float]) -> dict:
    return {
        "n": len(values), "median": round(statistics.median(values), 4),
        "mean": round(statistics.fmean(values), 4),
        "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4), "max": round(max(values), 4),
        "values": values,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenarios", nargs="+")
    parser.add_argument("--a", required=True, help="full commit hash of the reference")
    parser.add_argument("--b", required=True, help="full commit hash of the candidate")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--keep", action="store_true", help="keep the worktrees")
    parser.add_argument("--skip-equality", action="store_true",
                        help="timing only (equality already proven for the same pins)")
    args = parser.parse_args(argv)
    for name in ("a", "b"):
        if not re.fullmatch(r"[0-9a-f]{40}", getattr(args, name)):
            parser.error(f"--{name} must be a full lowercase commit hash")
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error(f"{out} must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    sides = {"A": args.a, "B": args.b}
    trees = {side: out / f"tree-{side}" for side in sides}
    for side, commit in sides.items():
        _git("worktree", "add", "--detach", str(trees[side]), commit)
    try:
        python_info = subprocess.run(
            [args.python, "-c", ("import sys, pydantic, platform; print(sys.version.split()[0],"
                                 " pydantic.VERSION, platform.platform())")],
            check=True, capture_output=True, text=True).stdout.split(maxsplit=2)
        manifest = {
            "schema": "ab_match_kernel.v1",
            "sides": {side: {"commit": commit,
                             "src_tree": _git("rev-parse", f"{commit}:src"),
                             "matches_tree": _git("rev-parse",
                                                  f"{commit}:src/beta_engine/domain/matches"),
                             "rng_blob": _git("rev-parse", f"{commit}:src/beta_engine/core/rng.py")}
                      for side, commit in sides.items()},
            "harness": {"path": str(HARNESS), "sha256": _sha256(HARNESS),
                        "driver_head": _git("rev-parse", "HEAD"),
                        "driver_dirty": bool(_git("status", "--porcelain", "--",
                                                  "scripts/benchmark_match_engine.py"))},
            "python": {"executable": args.python, "version": python_info[0],
                       "pydantic": python_info[1], "platform": python_info[2].strip()},
            "machine": {"cpu_model": _cpu_model(), "logical_cpus": os.cpu_count(),
                        "affinity": len(os.sched_getaffinity(0))
                        if hasattr(os, "sched_getaffinity") else None},
            "scenarios": args.scenarios, "rounds": args.rounds,
            "order": "A B B A in even rounds, B A A B in odd rounds",
            "pythonhashseed": "0",
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
        fingerprints: dict[str, str] = {}
        equality: dict[str, dict] = {}
        if not args.skip_equality:
            for scenario in args.scenarios:
                emitted = {}
                for side in sides:
                    path = out / f"chains-{scenario}-{side}.json"
                    _child(args.python, trees[side],
                           [scenario, "--repeats", "1", "--chains", "--emit", str(path)])
                    emitted[side] = json.loads(path.read_text())
                a, b = emitted["A"], emitted["B"]
                differences = []
                if a["fingerprint"] != b["fingerprint"]:
                    differences.append("complete scenario output")
                if len(a["chains"]) != len(b["chains"]):
                    differences.append("number of engine results")
                for index, (left, right) in enumerate(zip(a["chains"], b["chains"])):
                    for key in sorted(set(left) | set(right)):
                        if left.get(key) != right.get(key):
                            differences.append(f"result {index} ({left.get('match_id')}): {key}")
                equality[scenario] = {
                    "equal": not differences, "differences": differences[:50],
                    "fingerprint": a["fingerprint"], "engine_results": len(a["chains"]),
                    "rallies": sum(c["rallies"] for c in a["chains"]),
                    "components_per_result": len(a["chains"][0]) if a["chains"] else 0,
                }
                fingerprints[scenario] = a["fingerprint"]
                print(json.dumps({"equality": scenario, **equality[scenario]}), flush=True)
            (out / "equality.json").write_text(json.dumps(equality, indent=1))
            if not all(item["equal"] for item in equality.values()):
                print("A and B outputs differ", file=sys.stderr)
                return 1
        samples: dict[str, dict[str, list[dict]]] = {}
        with (out / "samples.jsonl").open("w") as log:
            for round_index in range(args.rounds):
                for scenario in args.scenarios:
                    for side in ("A", "B", "B", "A") if round_index % 2 == 0 else ("B", "A", "A", "B"):
                        report, usage = _child(args.python, trees[side],
                                               [scenario, "--repeats", "1", "--in-process"])
                        expected = fingerprints.setdefault(scenario, report["fingerprint"])
                        if report["fingerprint"] != expected:
                            raise SystemExit(f"{scenario}/{side}: fingerprint changed in timing")
                        row = {"round": round_index, "scenario": scenario, "side": side,
                               **report, **usage}
                        log.write(json.dumps(row) + "\n")
                        log.flush()
                        samples.setdefault(scenario, {"A": [], "B": []})[side].append(row)
        summary = {}
        for scenario, by_side in samples.items():
            row: dict[str, object] = {
                "fingerprint": fingerprints[scenario],
                "engine_calls": by_side["A"][0]["engine_calls_last"],
                "engine_rallies": by_side["A"][0]["engine_rallies_last"],
            }
            for metric, key in {**METRICS, "peak_rss_mb": "process_peak_rss_mb",
                                "process_cpu": "process_cpu_seconds"}.items():
                stats = {}
                for side in ("A", "B"):
                    values = [s[key][0] if isinstance(s[key], list) else s[key]
                              for s in by_side[side]]
                    stats[side] = _summary(values)
                a_med, b_med = stats["A"]["median"], stats["B"]["median"]
                stats["change_of_medians"] = round(b_med / a_med - 1, 4) if a_med else None
                stats["ranges_overlap"] = not (stats["B"]["max"] < stats["A"]["min"]
                                               or stats["A"]["max"] < stats["B"]["min"])
                ratios = []
                for round_index in range(args.rounds):
                    pair = {side: sum(
                        s[key][0] if isinstance(s[key], list) else s[key]
                        for s in by_side[side] if s["round"] == round_index) for side in ("A", "B")}
                    if pair["A"]:
                        ratios.append(round(pair["B"] / pair["A"] - 1, 4))
                stats["paired_round_change"] = {
                    "values": ratios, "median": round(statistics.median(ratios), 4),
                    "min": min(ratios), "max": max(ratios)} if ratios else None
                row[metric] = stats
            summary[scenario] = row
            print(json.dumps({"scenario": scenario,
                              **{m: {"A": row[m]["A"]["median"], "B": row[m]["B"]["median"],
                                     "change": row[m]["change_of_medians"],
                                     "paired": row[m]["paired_round_change"]["median"],
                                     "overlap": row[m]["ranges_overlap"]}
                                 for m in (*METRICS, "peak_rss_mb")}}), flush=True)
        (out / "summary.json").write_text(json.dumps(summary, indent=1))
        return 0
    finally:
        if not args.keep:
            for tree in trees.values():
                subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT,
                               check=False, capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
