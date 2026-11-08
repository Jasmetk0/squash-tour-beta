#!/usr/bin/env python3
"""Paired, replay-checked observations of the real MatchEngine (not calibration).

Each paired block uses the *same explicit match ID and derived RNG seed* in
three arms. Both left/right seat orientations are inspected independently.
All matches start with fresh synthetic player state. This is NOT an in-Run
career, fatigue, ranking, Entry or long-term realism experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from beta_engine.core import (
    DeterministicRng,
    derive_match_seed,
    derive_season_seed,
    derive_week_seed,
)
from beta_engine.domain.matches import MatchContext, MatchEngine, MatchParticipantContext
from beta_engine.domain.players import HiddenCareerTraits, Player

SCHEMA = "match_paired_seed_validation.v1"
ARMS = ("equal", "x_stronger", "y_stronger")
SEATS = ("x_left", "y_left")
STRENGTHS = {"equal": (84, 84), "x_stronger": (90, 84), "y_stronger": (84, 90)}
MAX_BLOCKS = 500  # bounded evidence size; not a statistical power claim


def _require_config(*, blocks: int, root_seed: int) -> None:
    if type(blocks) is not int or not 1 <= blocks <= MAX_BLOCKS:
        raise ValueError(f"blocks must be an integer between 1 and {MAX_BLOCKS}")
    if type(root_seed) is not int or not 0 <= root_seed < 2**63:
        raise ValueError("root seed must be a non-negative 63-bit integer")


def _player(identity: str, strength: int) -> Player:
    """Synthetic adult; do not interpret an OVR as a real-world ranking."""
    return Player(
        player_id=identity, name=f"Validation {identity}", age=27, nationality="TST",
        technique=strength, movement=strength, physical=strength,
        mental=strength, consistency=strength, clutch=strength,
        recovery=strength, play_style="tempo-controller",
        archetype="all-court tactician",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=99, growth_curve="balanced",
            professionalism=0.7, ambition=0.7, travel_tolerance=0.7,
            schedule_aggression=0.6, injury_proneness=0.2, resilience=0.8,
        ),
    )


def _seed(root_seed: int, block: int, seat: str) -> int:
    """One stable seed per (block, orientation), shared across all arms."""
    season = derive_season_seed(root_seed, 1)
    week = derive_week_seed(season, 1)
    return derive_match_seed(week, f"paired-validation-v1:{block}:{seat}").value


def _context(block: int, seat: str, arm: str) -> MatchContext:
    if seat not in SEATS or arm not in ARMS or type(block) is not int or block < 0:
        raise ValueError("invalid validation cell")
    x, y = (_player("X", STRENGTHS[arm][0]),
            _player("Y", STRENGTHS[arm][1]))
    left, right = (x, y) if seat == "x_left" else (y, x)
    return MatchContext(
        match_id=f"paired-validation-v1:{block}:{seat}",
        player_a=MatchParticipantContext(player=left),
        player_b=MatchParticipantContext(player=right),
    )


def _digest(value: object) -> str:
    """Version-independent canonicalization of JSON-serializable result values."""
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _simulate_cell(block: int, seat: str, arm: str, root_seed: int) -> dict:
    context = _context(block, seat, arm)
    seed = _seed(root_seed, block, seat)
    result = MatchEngine(rng=DeterministicRng(seed)).simulate(context)
    if result.rally_log is None or result.timeline_log is None:
        raise ValueError("MatchEngine omitted authoritative rally/timeline logs")
    if result.termination_reason.value != "COMPLETED":
        raise ValueError("Unexpected non-completed match in healthy synthetic cohort")
    seconds = result.timeline_log.total_elapsed_seconds
    rallies = len(result.rally_log.events)
    if not math.isfinite(seconds) or seconds <= 0 or not rallies:
        raise ValueError("Invalid MatchEngine time or rally evidence")
    if result.winner_player_id not in ("X", "Y") or not 3 <= len(result.sets) <= 5:
        raise ValueError("Invalid synthetic match winner or BO5 set count")
    result_json = result.model_dump(mode="json")
    return {
        "block": block, "seat": seat, "arm": arm, "match_id": context.match_id,
        "seed": seed, "player_a": context.player_a.player.player_id,
        "winner": result.winner_player_id,
        "sets": len(result.sets), "rallies": rallies,
        "duration_seconds": seconds,
        "rally_log_hash": result.rally_log.match_log_hash,
        "result_sha256": _digest(result_json),
    }


def _validate_rows(rows: list[dict], *, blocks: int, root_seed: int) -> dict:
    """Full paired factorial closure, not a sample of whichever rows succeeded."""
    _require_config(blocks=blocks, root_seed=root_seed)
    if not isinstance(rows, list) or len(rows) != blocks * len(SEATS) * len(ARMS):
        raise ValueError("Expected exactly six observations per block")
    keyed: dict[tuple[int, str, str], dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid observation")
        block, seat, arm = row.get("block"), row.get("seat"), row.get("arm")
        if type(block) is not int or block not in range(blocks) or seat not in SEATS or arm not in ARMS:
            raise ValueError("Observation is outside declared seed blocks")
        key = (block, seat, arm)
        if key in keyed:
            raise ValueError("Duplicate observation cell")
        if (
            row.get("seed") != _seed(root_seed, block, seat)
            or row.get("match_id") != f"paired-validation-v1:{block}:{seat}"
            or row.get("player_a") != ("X" if seat == "x_left" else "Y")
        ):
            raise ValueError("Observed seed, identity or orientation disagrees with design")
        if row.get("winner") not in ("X", "Y"):
            raise ValueError("Unknown match winner")
        for field in ("sets", "rallies", "duration_seconds"):
            value = row.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid observed {field}")
        if row["sets"] not in (3, 4, 5):
            raise ValueError("Invalid BO5 match length")
        for name in ("result_sha256", "rally_log_hash"):
            if not isinstance(row.get(name), str) or not row[name]:
                raise ValueError(f"Missing {name}")
        keyed[key] = row
    for block in range(blocks):
        for seat in SEATS:
            for arm in ARMS:
                if (block, seat, arm) not in keyed:
                    raise ValueError("Missing paired observation")
    return keyed


def _wilson(wins: int, count: int) -> list[float]:
    if count <= 0 or not 0 <= wins <= count:
        raise ValueError("Invalid binomial sample")
    z = 1.959963984540054
    p = wins / count
    denom = 1 + z*z / count
    middle = (p + z*z / (2*count)) / denom
    radius = z * math.sqrt(p*(1-p)/count + z*z/(4*count*count)) / denom
    return [max(0.0, middle-radius), min(1.0, middle+radius)]


def summarize(rows: list[dict], *, blocks: int, root_seed: int) -> dict:
    keyed = _validate_rows(rows, blocks=blocks, root_seed=root_seed)
    n = blocks * len(SEATS)
    outcomes = {}
    for arm in ARMS:
        samples = [keyed[(block, seat, arm)] for block in range(blocks) for seat in SEATS]
        wins = sum(row["winner"] == "X" for row in samples)
        outcomes[arm] = {
            "matches": n, "x_wins": wins, "x_win_fraction": wins/n,
            "x_win_wilson95_observational": _wilson(wins, n),
            "mean_duration_seconds": sum(r["duration_seconds"] for r in samples)/n,
            "mean_rallies": sum(r["rallies"] for r in samples)/n,
            "x_win_fraction_by_orientation": {
                seat: sum(keyed[(block, seat, arm)]["winner"] == "X" for block in range(blocks))/blocks
                for seat in SEATS
            },
        }
    contrasts = {}
    for arm in ("x_stronger", "y_stronger"):
        groups = [(keyed[(block, seat, "equal")], keyed[(block, seat, arm)])
                  for block in range(blocks) for seat in SEATS]
        contrasts[f"{arm}_minus_equal"] = {
            "matched_pairs": n,
            "mean_x_win_change": sum(
                (b["winner"] == "X") - (a["winner"] == "X") for a, b in groups
            ) / n,
            "mean_duration_seconds_change": sum(
                b["duration_seconds"] - a["duration_seconds"] for a, b in groups
            ) / n,
            "mean_rallies_change": sum(b["rallies"] - a["rallies"] for a, b in groups)/n,
            "x_loses_to_wins": sum(a["winner"] != "X" and b["winner"] == "X" for a, b in groups),
            "x_wins_to_loses": sum(a["winner"] == "X" and b["winner"] != "X" for a, b in groups),
        }
    return {"arms": outcomes, "paired_contrasts": contrasts}


def collect(*, blocks: int = 8, root_seed: int = 20261101) -> dict:
    """Execute real matches twice in reversed order to detect replay/order drift."""
    _require_config(blocks=blocks, root_seed=root_seed)
    cells = [(i, seat, arm) for i in range(blocks) for seat in SEATS for arm in ARMS]
    first = {cell: _simulate_cell(*cell, root_seed) for cell in cells}
    # Each simulation creates a fresh RNG. Any global state/order dependency
    # that changes authoritative results is treated as a hard failure.
    for cell in reversed(cells):
        repeat = _simulate_cell(*cell, root_seed)
        if first[cell] != repeat:
            raise ValueError(f"Replay/order mismatch at cell {cell}")
    rows = [first[cell] for cell in cells]
    return {
        "schema_version": SCHEMA, "root_seed": root_seed, "blocks": blocks,
        "seats": list(SEATS), "arms": list(ARMS),
        "attribute_settings": {"equal": {"X": 84, "Y": 84},
                               "x_stronger": {"X": 90, "Y": 84},
                               "y_stronger": {"X": 84, "Y": 90}},
        "replay_checked": True, "replay_mismatches": 0,
        "observations": rows, "summary": summarize(rows, blocks=blocks, root_seed=root_seed),
        "observations_sha256": _digest(rows),
        "limitations": [
            "Standalone fresh-state MatchEngine calls, not a full production HTTP/SQLite Saved Run.",
            "Same explicit seed and match_id per paired block/seat; RNG draws can diverge after an input changes.",
            "These are synthetic attributes, not empirically calibrated player strengths, causal estimates or real PSA data.",
            "Wilson intervals describe observed independent-looking outcomes; paired orientation/block observations may be correlated.",
            "No game-rule, strength, travel, mental-state or player progression tuning is authorized by this report.",
            "No pre-alpha release, 80-Edition, 50-season or cross-version replay certification.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blocks", type=int, default=8)
    parser.add_argument("--root-seed", type=int, default=20261101)
    parser.add_argument("--output", type=Path, help="Write a NEW JSON report (no overwrites)")
    args = parser.parse_args(argv)
    try:
        if args.output and (args.output.exists() or args.output.is_symlink()):
            raise ValueError("Output already exists; previous evidence is immutable")
        payload = collect(blocks=args.blocks, root_seed=args.root_seed)
        rendered = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        else:
            print(rendered, end="")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Paired MatchEngine audit failed (no pass claimed): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
