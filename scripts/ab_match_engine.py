"""Interleaved A/B of two source trees with ``benchmark_match_engine.py``.

Every sample is a fresh process (``PYTHONHASHSEED=0``) running one scenario
once; the order per round is A B B A so that drift on a shared host affects
both sides alike. Both trees must contain ``scripts/benchmark_match_engine.py``
(copy this branch's script into a clean baseline worktree). The result
fingerprints of A and B must be identical or the run aborts.

    git worktree add /tmp/base origin/buuk
    cp scripts/benchmark_match_engine.py /tmp/base/scripts/
    python scripts/ab_match_engine.py --a /tmp/base --b . --rounds 3 single set lab ko128 http16
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path


def _sample(root: Path, scenario: str) -> dict:
    output = subprocess.run(
        [sys.executable, str(root / "scripts" / "benchmark_match_engine.py"), scenario,
         "--repeats", "1", "--in-process"],
        check=True, cwd=root, capture_output=True, text=True,
        env={**os.environ, "PYTHONHASHSEED": "0"},
    ).stdout
    return json.loads(output.strip().splitlines()[-1])


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("scenarios", nargs="+")
    parser.add_argument("--a", type=Path, required=True, help="baseline source root")
    parser.add_argument("--b", type=Path, required=True, help="candidate source root")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--json", type=Path, help="write every raw sample here")
    args = parser.parse_args(argv)
    raw: dict[str, dict[str, list[dict]]] = {}
    for scenario in args.scenarios:
        samples = raw.setdefault(scenario, {"A": [], "B": []})
        for _ in range(args.rounds):
            for side in ("A", "B", "B", "A"):
                samples[side].append(_sample(args.a if side == "A" else args.b, scenario))
        fingerprints = {sample["fingerprint"] for side in samples.values() for sample in side}
        if len(fingerprints) != 1:
            raise SystemExit(f"{scenario}: A and B outputs differ: {sorted(fingerprints)}")
        row = {"scenario": scenario, "fingerprint": fingerprints.pop(), "n": len(samples["A"])}
        for metric in ("wall", "cpu", "engine", "infrastructure", "peak_rss_mb"):
            key = {"wall": "wall_seconds", "cpu": "cpu_seconds", "engine": "engine_seconds_last",
                   "infrastructure": "infrastructure_seconds_last", "peak_rss_mb": "peak_rss_mb"}[metric]
            values = {
                side: [s[key][0] if isinstance(s[key], list) else s[key] for s in samples[side]]
                for side in ("A", "B")
            }
            a, b = statistics.median(values["A"]), statistics.median(values["B"])
            row[metric] = {"A_median": round(a, 3), "B_median": round(b, 3),
                           "change": round((b - a) / a, 4) if a else None,
                           "A": values["A"], "B": values["B"]}
        print(json.dumps(row), flush=True)
    if args.json:
        args.json.write_text(json.dumps(raw, indent=1))


if __name__ == "__main__":
    main()
