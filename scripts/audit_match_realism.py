"""Reproducible synthetic-cohort audit of the real Match Engine; no tuning writes.

Run with PYTHONPATH=src python scripts/audit_match_realism.py --output DIR.
Each match starts fresh. These ratings are synthetic, not mapped to PSA rankings.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from statistics import mean, median

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
)
from beta_engine.domain.players import HiddenCareerTraits, Player

SCENARIOS = (
    ("equal_84", 84, 84, "tempo-controller", "tempo-controller"),
    ("gap_6", 90, 84, "tempo-controller", "tempo-controller"),
    ("gap_22", 90, 68, "tempo-controller", "tempo-controller"),
    ("attack_retrieve", 84, 84, "attacking", "retrieving"),
    ("front_counter", 84, 84, "front-court", "counter-punching"),
    ("equal_60", 60, 60, "tempo-controller", "tempo-controller"),
)


def player(pid, strength, style):
    return Player(
        player_id=pid,
        name=f"Synthetic {pid}",
        age=27,
        nationality="TST",
        technique=strength,
        movement=strength,
        physical=strength,
        mental=strength,
        consistency=strength,
        clutch=strength,
        recovery=strength,
        play_style=style,
        archetype="all-court tactician",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=99,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
    )


def run_match(task):
    scenario, i, seed_base = task
    name, a_strength, b_strength, a_style, b_style = scenario
    a, b = player("A", a_strength, a_style), player("B", b_strength, b_style)
    left, right = (a, b) if i % 2 == 0 else (b, a)
    seed = seed_base + i
    context = MatchContext(
        match_id=f"audit:{name}:{i}",
        player_a=MatchParticipantContext(player=left),
        player_b=MatchParticipantContext(player=right),
    )
    start = time.perf_counter()
    result = MatchEngine(rng=DeterministicRng(seed)).simulate(context)
    runtime = time.perf_counter() - start
    rallies = result.rally_log.events
    timeline = result.timeline_log
    durations = [r.elapsed_seconds for r in rallies]
    scored = [r for r in rallies if r.winner_player_id is not None]
    serving_wins = sum(r.winner_player_id == r.serving_player_id for r in scored)
    intervals = [
        e.elapsed_seconds
        for e in timeline.events
        if e.event_type == "BETWEEN_RALLY_INTERVAL"
    ]
    return {
        "scenario": name,
        "sample": i,
        "seed": seed,
        "left_player": left.player_id,
        "a_won": int(result.winner_player_id == "A"),
        "first_server_won": int(
            result.winner_player_id == rallies[0].serving_player_id
        ),
        "games": len(result.sets),
        "minutes": timeline.total_elapsed_seconds / 60,
        "rallies": len(rallies),
        "rally_seconds": sum(durations),
        "rally_mean": mean(durations),
        "rally_median": median(durations),
        "rally_max": max(durations),
        "under_10": sum(d < 10 for d in durations),
        "over_21": sum(d > 21 for d in durations),
        "over_60": sum(d > 60 for d in durations),
        "scored_rallies": len(scored),
        "server_points": serving_wins,
        "intervals": len(intervals),
        "interval_seconds": sum(intervals),
        "deuce_games": sum(s.loser_games >= 10 for s in result.sets),
        "runtime_seconds": runtime,
        "log_hash": result.rally_log.match_log_hash,
    }


def wilson(wins, n):
    z = 1.96
    p = wins / n
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [center - margin, center + margin]


def summarize(rows):
    output = {}
    for scenario in SCENARIOS:
        subset = [r for r in rows if r["scenario"] == scenario[0]]
        n = len(subset)
        rallies = sum(r["rallies"] for r in subset)
        durations = sorted(r["minutes"] for r in subset)
        wins = sum(r["a_won"] for r in subset)
        intervals = sum(r["intervals"] for r in subset)
        output[scenario[0]] = {
            "matches": n,
            "a_win_rate": wins / n,
            "a_win_wilson_95": wilson(wins, n),
            "a_win_rate_by_side": {
                side: mean(r["a_won"] for r in subset if r["left_player"] == side)
                for side in ("A", "B")
                if any(r["left_player"] == side for r in subset)
            },
            "mean_minutes": mean(durations),
            "median_minutes": median(durations),
            "p10_minutes": durations[int((n - 1) * 0.1)],
            "p90_minutes": durations[int((n - 1) * 0.9)],
            "game_counts": dict(Counter(r["games"] for r in subset)),
            "rallies": rallies,
            "mean_rally_seconds": sum(r["rally_seconds"] for r in subset) / rallies,
            "mean_match_rally_seconds": mean(r["rally_mean"] for r in subset),
            "max_rally_seconds": max(r["rally_max"] for r in subset),
            "rally_under_10_fraction": sum(r["under_10"] for r in subset) / rallies,
            "rally_over_21_fraction": sum(r["over_21"] for r in subset) / rallies,
            "rally_over_60_fraction": sum(r["over_60"] for r in subset) / rallies,
            "mean_interval_seconds": sum(r["interval_seconds"] for r in subset)
            / intervals
            if intervals
            else None,
            "server_point_fraction": sum(r["server_points"] for r in subset)
            / sum(r["scored_rallies"] for r in subset),
            "first_server_match_win_fraction": mean(
                r["first_server_won"] for r in subset
            ),
            "deuce_game_fraction": sum(r["deuce_games"] for r in subset)
            / sum(r["games"] for r in subset),
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=500, help="Matches per scenario")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed-base", type=int, default=20260908)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1 or args.workers < 1:
        parser.error("samples and workers must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    tasks = [
        (scenario, i, args.seed_base)
        for scenario in SCENARIOS
        for i in range(args.samples)
    ]
    rows = []
    start = time.perf_counter()
    with (
        (args.output / "matches.csv").open("w", newline="", encoding="utf-8") as stream,
        ProcessPoolExecutor(max_workers=args.workers) as pool,
    ):
        writer = None
        for row in pool.map(run_match, tasks, chunksize=5):
            if writer is None:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
            writer.writerow(row)
            rows.append(row)
            if len(rows) % 100 == 0:
                stream.flush()
                print(f"Completed {len(rows)}/{len(tasks)}", flush=True)
    summary = {
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "samples_per_scenario": args.samples,
        "seed_base": args.seed_base,
        "elapsed_seconds": time.perf_counter() - start,
        "scenarios": SCENARIOS,
        "summary": summarize(rows),
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["summary"], indent=2))


if __name__ == "__main__":
    main()
