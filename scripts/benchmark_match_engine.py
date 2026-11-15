"""Reproducible MatchEngine / knockout benchmark with result fingerprints.

Scenarios (each runs in its own fresh process for clean peak-memory numbers):

* ``single``    one real match, production input path (``MatchInputSnapshot`` +
                every effective snapshot, as Run/slot services call it), repeated.
* ``set``       a fixed set of matches with varied strength gaps, styles,
                archetypes, seeds and formats (BO5 and BO3), production path.
* ``lab``       the same set through the plain ``MatchEngine.simulate(context)``
                path that Tournament Lab uses.
* ``ko128``     a complete 128-player Tournament Lab knockout (127 real matches)
                through the shared draw/match kernels; engine time is measured
                separately from the tournament infrastructure around it.

Every scenario prints a JSON line with wall/CPU seconds, peak RSS and a
fingerprint over every complete ``MatchResult`` (``model_dump(mode="json")``),
so two source trees can be compared for byte-identical outputs.

    python scripts/benchmark_match_engine.py all --repeats 3
    python scripts/benchmark_match_engine.py single --profile /tmp/single.pstats
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

SCENARIOS = ("single", "set", "lab", "ko128")


def _player(player_id, base, *, style="tempo-controller", archetype="all-court tactician", spread=0):
    from beta_engine.domain.players import HiddenCareerTraits, Player

    def attr(offset):
        return max(1, min(99, base + offset))

    return Player(
        player_id=player_id, name=player_id, age=27, nationality="TST",
        technique=attr(spread), movement=attr(-spread), physical=attr(spread // 2),
        mental=attr(-spread // 2), consistency=attr(0), clutch=attr(spread),
        recovery=attr(-spread), play_style=style, archetype=archetype,
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90, growth_curve="balanced", professionalism=0.7,
            ambition=0.7, travel_tolerance=0.7, schedule_aggression=0.6,
            injury_proneness=0.2, resilience=0.8,
        ),
    )


STYLES = ("tempo-controller", "attacking", "retrieving", "counter-punching", "front-court")
ARCHETYPES = ("all-court tactician", "explosive shotmaker", "durable grinder",
              "quick interceptor", "late-blooming worker")


def match_set():
    """Fixed varied inputs: (match_id, player_a, player_b, best_of, seed)."""
    cases = []
    for index in range(24):
        gap = (0, 2, 5, 9, 14, 22)[index % 6]
        base = 88 - (index % 4) * 6
        a = _player(f"A{index}", base, style=STYLES[index % 5], archetype=ARCHETYPES[index % 5],
                    spread=index % 7)
        b = _player(f"B{index}", base - gap, style=STYLES[(index + 2) % 5],
                    archetype=ARCHETYPES[(index + 3) % 5], spread=(index * 3) % 5)
        cases.append((f"bench-{index}", a, b, 3 if index % 5 == 4 else 5, 1000 + index * 7919))
    return cases


def context_for(match_id, a, b, best_of):
    from beta_engine.domain.matches import MatchContext, MatchParticipantContext

    return MatchContext(match_id=match_id, player_a=MatchParticipantContext(player=a),
                        player_b=MatchParticipantContext(player=b), best_of=best_of)


def production_match(match_id, a, b, best_of, seed):
    """The Run/slot service input path: snapshot, every effective input, dump."""
    from beta_engine.core import DeterministicRng
    from beta_engine.domain.matches import MatchEngine
    from beta_engine.domain.matches.formats import (
        EffectiveMatchFormatSnapshot, MatchFormat, official_match_format_snapshot,
    )
    from beta_engine.domain.matches.inputs import MatchInputSnapshot
    from beta_engine.domain.matches.control import RallyCalibrationProfile

    context = context_for(match_id, a, b, best_of)
    snapshot = MatchInputSnapshot.create(
        context=context,
        effective_match_format=official_match_format_snapshot() if best_of == 5 else
        EffectiveMatchFormatSnapshot.create(
            format=MatchFormat(best_of=best_of, games_to=11, win_by=2),
            source_scope="tournament_edition_override", source_key="tournament-edition"),
        simulation_seed=seed, match_engine_version="benchmark",
        rally_calibration_profile=RallyCalibrationProfile(),
    )
    result = MatchEngine(rng=DeterministicRng(snapshot.simulation_seed)).simulate(
        snapshot.context, log_anchor_hash=snapshot.snapshot_hash,
        effective_match_timing=snapshot.effective_match_timing,
        effective_match_stamina=snapshot.effective_match_stamina,
        rally_calibration_profile=snapshot.rally_calibration_profile,
        effective_match_gameplans=snapshot.effective_match_gameplans,
        effective_rally_rules=snapshot.effective_rally_rules,
        effective_match_health=snapshot.effective_match_health,
    )
    return result.model_dump(mode="json")


def lab_match(match_id, a, b, best_of, seed):
    from beta_engine.core import DeterministicRng
    from beta_engine.domain.matches import MatchEngine

    return MatchEngine(rng=DeterministicRng(seed)).simulate(
        context_for(match_id, a, b, best_of)).model_dump(mode="json")


def digest(values):
    hasher = hashlib.sha256()
    for value in values:
        hasher.update(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
    return hasher.hexdigest()


def ko128(engine_seconds):
    from beta_engine.application.tournament_test_lab_service import (
        TournamentLabAssertions, TournamentLabRequest, TournamentLabScenario,
        TournamentTestLabService,
    )
    from beta_engine.domain.matches import MatchParticipantContext

    participants = tuple(
        MatchParticipantContext(player=_player(
            f"P{index:03d}", 95 - (index * 50) // 128, style=STYLES[index % 5],
            archetype=ARCHETYPES[(index * 3) % 5], spread=index % 6))
        for index in range(1, 129)
    )
    scenario = TournamentLabScenario(
        scenario_id="bench-ko128", display_name="Benchmark 128 knockout",
        format_kind="knockout", participants=participants, main_draw_size=128,
        seed_order_player_ids=tuple(p.player.player_id for p in participants),
        draw_seed=1701, match_seed=2701,
        assertions=TournamentLabAssertions(expected_played_match_count=127),
    )
    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))
    run = result.runs[0]
    if run.played_match_count != 127 or not run.tournament_complete:
        raise SystemExit(f"knockout incomplete: {run.played_match_count} matches")
    return result.model_dump(mode="json")


def run_scenario(name, repeats):
    from beta_engine.domain.matches import MatchEngine

    engine = {"seconds": 0.0, "calls": 0}
    original = MatchEngine.simulate

    def timed(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return original(self, *args, **kwargs)
        finally:
            engine["seconds"] += time.perf_counter() - started
            engine["calls"] += 1

    MatchEngine.simulate = timed
    walls, cpus, fingerprints = [], [], []
    for _ in range(repeats):
        engine["seconds"], engine["calls"] = 0.0, 0
        wall, cpu = time.perf_counter(), time.process_time()
        if name == "single":
            a = _player("SINGLE-A", 86, style="attacking", archetype="explosive shotmaker")
            b = _player("SINGLE-B", 84, style="retrieving", archetype="durable grinder")
            outputs = [production_match("bench-single", a, b, 5, 918273)]
        elif name in {"set", "lab"}:
            simulate = production_match if name == "set" else lab_match
            outputs = [simulate(*case) for case in match_set()]
        else:
            outputs = [ko128(engine)]
        walls.append(time.perf_counter() - wall)
        cpus.append(time.process_time() - cpu)
        fingerprints.append(digest(outputs))
    if len(set(fingerprints)) != 1:
        raise SystemExit("non-deterministic output across repeats")
    return {
        "scenario": name, "repeats": repeats,
        "wall_seconds": [round(v, 3) for v in walls],
        "cpu_seconds": [round(v, 3) for v in cpus],
        "engine_seconds_last": round(engine["seconds"], 3), "engine_calls_last": engine["calls"],
        "infrastructure_seconds_last": round(walls[-1] - engine["seconds"], 3),
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "fingerprint": fingerprints[0],
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=(*SCENARIOS, "all"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--in-process", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.scenario == "all":
        for name in SCENARIOS:
            command = [sys.executable, __file__, name, "--repeats", str(args.repeats), "--in-process"]
            subprocess.run(command, check=True, cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": "0"})
        return
    if args.profile:
        import cProfile

        profile = cProfile.Profile()
        profile.enable()
        report = run_scenario(args.scenario, args.repeats)
        profile.disable()
        profile.dump_stats(str(args.profile))
    else:
        report = run_scenario(args.scenario, args.repeats)
    report["source_root"] = str(ROOT)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
