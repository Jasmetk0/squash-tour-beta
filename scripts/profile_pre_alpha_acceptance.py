#!/usr/bin/env python3
"""Measure the mandatory Master §31.3 pre-alpha acceptance flows.

This is intentionally a measurement tool, not a performance gate. PAQ-006 still
requires a later explicit target for acceptable time and memory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest

from beta_engine.diagnostics.pre_alpha_performance import build_profile


DEFAULT_NODEIDS = (
    "tests/application/test_official_run_full_season_acceptance.py::"
    "test_official_run_completes_whole_season_reopens_and_rolls_to_next_season",
    "tests/application/test_standalone_match_acceptance.py::"
    "test_empty_run_two_manual_players_can_play_one_saved_standalone_match",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile the mandatory Master §31.3 pre-alpha acceptance flows."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output file. The report is always printed to stdout.",
    )
    parser.add_argument(
        "--label",
        default="master-31.3-pre-alpha-acceptance",
        help="Human-readable measurement label.",
    )
    parser.add_argument(
        "nodeids",
        nargs="*",
        help="Optional pytest nodeids. Defaults to both mandatory Master §31.3 flows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    nodeids = tuple(args.nodeids) or DEFAULT_NODEIDS

    tracemalloc.start()
    started = time.perf_counter()
    exit_code = int(pytest.main(["-q", *nodeids]))
    elapsed = time.perf_counter() - started
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    profile = build_profile(
        label=args.label,
        pytest_exit_code=exit_code,
        elapsed_seconds=elapsed,
        python_heap_current_bytes=current_bytes,
        python_heap_peak_bytes=peak_bytes,
        nodeids=nodeids,
    )
    rendered = json.dumps(profile.to_dict(), indent=2, sort_keys=True)
    print(rendered)

    if args.output is not None:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
