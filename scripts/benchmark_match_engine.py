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
* ``http16``    a short real pass: a real uvicorn HTTP server on a disposable
                SQLite database runs a 16-player knockout (15 real matches)
                through ``POST /admin/labs/tournament/run``; the fingerprint is
                the complete HTTP response body.
* ``cases``     the equality corpus of abnormal and edge states: forced deuce
                (equal players, every set checked for 10-10), explicit and
                probabilistic retirement, an injured/ill participant with
                Health input and negative modifiers, BO1/BO3/PAR-15 formats, and
                the step-wise ``Simulate Next Rally`` path whose every persisted
                working state and step outcome is part of the fingerprint.

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

SCENARIOS = ("single", "set", "lab", "ko128", "http16", "cases")


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
    from beta_engine.domain.matches.control import RallyCalibrationProfile
    from beta_engine.domain.matches.formats import (
        EffectiveMatchFormatSnapshot,
        MatchFormat,
        official_match_format_snapshot,
    )
    from beta_engine.domain.matches.inputs import MatchInputSnapshot

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
        TournamentLabAssertions,
        TournamentLabRequest,
        TournamentLabScenario,
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


def _health(player_a_id, player_b_id):
    from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
    from beta_engine.domain.players.health import (
        PermanentHealthConsequence,
        PlayerHealthProfile,
        PlayerHealthRecord,
    )
    from beta_engine.domain.rankings.official import RankingWeek

    injured = PlayerHealthProfile(
        player_id=player_a_id,
        records=(PlayerHealthRecord(
            record_id="ankle-active", kind="Injury", condition_key="ankle",
            lifecycle="Active", severity=42, affected_domains=("movement", "stamina"),
            onset_week=RankingWeek(season_index=0, week=5), recovery_window_min_weeks=2,
            recovery_window_max_weeks=6, provenance="benchmark active ankle"),
            PlayerHealthRecord(
            record_id="knee-old", kind="Injury", condition_key="knee", lifecycle="Recovered",
            severity=0, affected_domains=("movement",),
            onset_week=RankingWeek(season_index=0, week=1),
            recovered_week=RankingWeek(season_index=0, week=3),
            provenance="benchmark recovered knee")),
        permanent_consequences=(PermanentHealthConsequence(
            consequence_id="knee-limitation", source_record_id="knee-old",
            affected_domains=("movement",), limitation_severity=12,
            provenance="benchmark permanent consequence"),),
    )
    return EffectiveMatchHealthSnapshot.from_profiles(
        player_a=injured, player_b=PlayerHealthProfile(player_id=player_b_id))


def edge_cases():
    """(label, context, seed, health, path) for every abnormal/edge state."""
    from beta_engine.domain.matches import MatchContext, MatchParticipantContext
    from beta_engine.domain.matches.models import RetirementRule, RetirementTrigger

    def ctx(match_id, a, b, **kwargs):
        participant_a = kwargs.pop("participant_a", {})
        return MatchContext(match_id=match_id,
                            player_a=MatchParticipantContext(player=a, **participant_a),
                            player_b=MatchParticipantContext(player=b), **kwargs)

    even_a = _player("DEUCE-A", 85, style="retrieving", archetype="durable grinder")
    even_b = _player("DEUCE-B", 85, style="retrieving", archetype="durable grinder")
    strong = _player("RET-A", 88, style="attacking", archetype="explosive shotmaker")
    weak = _player("RET-B", 79, style="counter-punching", archetype="quick interceptor")
    cases = [
        ("deuce-bo5", ctx("edge-deuce", even_a, even_b, upset_variance=0.0), 515, None, "production"),
        ("deuce-par15-bo3", ctx("edge-par15", even_a, even_b, best_of=3, games_to=15), 616, None, "production"),
        ("bo1", ctx("edge-bo1", strong, weak, best_of=1), 717, None, "production"),
        ("retire-explicit-set1", ctx("edge-ret1", strong, weak, retirement_rule=RetirementRule(
            enabled=True, retired_player_id="RET-B", set_number=1)), 818, None, "production"),
        ("retire-explicit-set3", ctx("edge-ret3", strong, weak, retirement_rule=RetirementRule(
            enabled=True, retired_player_id="RET-A", set_number=3)), 919, None, "production"),
        ("retire-probabilistic", ctx("edge-retp", strong, weak, retirement_rule=RetirementRule(
            enabled=True, retired_player_id="RET-A", trigger=RetirementTrigger.PROBABILISTIC_SET_START,
            set_number=2, probability=0.55)), 1020, None, "production"),
        ("injured-health-input", ctx("edge-injury", strong, weak, participant_a={
            "health_modifier": -0.2, "fatigue_modifier": -0.15, "form_modifier": -0.05}),
         1121, "injured", "production"),
        ("lab-retire-explicit", ctx("edge-lab-ret", weak, strong, retirement_rule=RetirementRule(
            enabled=True, retired_player_id="RET-B", set_number=2)), 1222, None, "lab"),
        ("step-deuce-bo3", ctx("edge-step", even_a, even_b, best_of=3), 1357, None, "step"),
        ("step-retire-probabilistic", ctx("edge-step-ret", strong, weak, best_of=3,
            retirement_rule=RetirementRule(enabled=True, retired_player_id="RET-B",
            trigger=RetirementTrigger.PROBABILISTIC_SET_START, set_number=2, probability=0.7)),
         1424, None, "step"),
    ]
    return cases


def _snapshot(context, seed, health):
    from beta_engine.domain.matches.control import RallyCalibrationProfile
    from beta_engine.domain.matches.formats import (
        EffectiveMatchFormatSnapshot,
        MatchFormat,
        official_match_format_snapshot,
    )
    from beta_engine.domain.matches.inputs import MatchInputSnapshot

    official = (context.best_of, context.games_to, context.win_by) == (5, 11, 2)
    return MatchInputSnapshot.create(
        context=context,
        effective_match_format=official_match_format_snapshot() if official else
        EffectiveMatchFormatSnapshot.create(
            format=MatchFormat(best_of=context.best_of, games_to=context.games_to,
                               win_by=context.win_by),
            source_scope="tournament_edition_override", source_key="tournament-edition"),
        simulation_seed=seed, match_engine_version="benchmark",
        rally_calibration_profile=RallyCalibrationProfile(),
        effective_match_health=_health(context.player_a.player.player_id,
                                       context.player_b.player.player_id)
        if health == "injured" else None,
    )


def _effective(snapshot):
    return dict(
        log_anchor_hash=snapshot.snapshot_hash,
        effective_match_timing=snapshot.effective_match_timing,
        effective_match_stamina=snapshot.effective_match_stamina,
        rally_calibration_profile=snapshot.rally_calibration_profile,
        effective_match_gameplans=snapshot.effective_match_gameplans,
        effective_rally_rules=snapshot.effective_rally_rules,
        effective_match_health=snapshot.effective_match_health,
    )


def edge_case_outputs():
    """Complete serialized outputs of every edge case (and step-wise states)."""
    from beta_engine.core import DeterministicRng
    from beta_engine.domain.matches import MatchEngine

    outputs = []
    for label, context, seed, health, path in edge_cases():
        if path == "lab":
            result = MatchEngine(rng=DeterministicRng(seed)).simulate(context)
            outputs.append({"case": label, "result": result.model_dump(mode="json")})
            continue
        snapshot = _snapshot(context, seed, health)
        engine = MatchEngine(rng=DeterministicRng(snapshot.simulation_seed))
        if path == "production":
            result = engine.simulate(snapshot.context, **_effective(snapshot))
            outputs.append({"case": label, "input": snapshot.snapshot_hash,
                            "result": result.model_dump(mode="json")})
            continue
        effective = _effective(snapshot)
        working_input, state = engine.start_working_match(snapshot.context, **effective)
        steps = [hashlib.sha256(working_input.model_dump_json().encode()).hexdigest(),
                 hashlib.sha256(state.model_dump_json().encode()).hexdigest()]
        final = None
        for _ in range(10_000):
            outcome = engine.simulate_next_rally(working_input, state)
            # The persisted working state and step outcome must be byte-identical.
            steps.append(hashlib.sha256(json.dumps(
                outcome.model_dump(mode="json", exclude={"state"}), sort_keys=True).encode()).hexdigest())
            if outcome.final_result is not None:
                final = outcome.final_result
                break
            state = outcome.state
            steps.append(hashlib.sha256(state.model_dump_json().encode()).hexdigest())
        full = MatchEngine(rng=DeterministicRng(snapshot.simulation_seed)).simulate(
            snapshot.context, **effective)
        if final is None or final.model_dump(mode="json") != full.model_dump(mode="json"):
            raise SystemExit(f"step path diverged from full simulation in {label}")
        outputs.append({"case": label, "steps": steps, "result": final.model_dump(mode="json")})
    return outputs


def http16():
    import socket
    import tempfile
    import threading
    from urllib import request as urlrequest

    import uvicorn

    from beta_engine.application.tournament_test_lab_service import (
        TournamentLabAssertions,
        TournamentLabScenario,
    )
    from beta_engine.domain.matches import MatchParticipantContext
    from beta_engine.main import create_app

    participants = tuple(
        MatchParticipantContext(player=_player(
            f"H{index:02d}", 92 - index, style=STYLES[index % 5],
            archetype=ARCHETYPES[(index * 2) % 5], spread=index % 4))
        for index in range(1, 17)
    )
    scenario = TournamentLabScenario(
        scenario_id="bench-http16", display_name="Benchmark HTTP 16 knockout",
        format_kind="knockout", participants=participants, main_draw_size=16,
        seed_order_player_ids=tuple(p.player.player_id for p in participants),
        draw_seed=1616, match_seed=2616,
        assertions=TournamentLabAssertions(expected_played_match_count=15),
    )
    body = json.dumps({"scenario": scenario.model_dump(mode="json")}).encode()
    with tempfile.TemporaryDirectory() as root, socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        app = create_app(database_url=f"sqlite:///{Path(root) / 'bench.db'}")
        server = uvicorn.Server(uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for _ in range(200):
                try:
                    urlrequest.urlopen(f"http://127.0.0.1:{port}/health", timeout=5).read()
                    break
                except OSError:
                    time.sleep(0.05)
            req = urlrequest.Request(f"http://127.0.0.1:{port}/admin/labs/tournament/run",
                                     data=body, method="POST",
                                     headers={"content-type": "application/json"})
            with urlrequest.urlopen(req, timeout=600) as response:
                payload = json.loads(response.read().decode())
        finally:
            server.should_exit = True
            thread.join(timeout=10)
    run = payload["runs"][0]
    if run["played_match_count"] != 15 or not run["tournament_complete"]:
        raise SystemExit(f"http16 incomplete: {run['played_match_count']} matches")
    return payload


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
        elif name == "http16":
            outputs = [http16()]
        elif name == "cases":
            outputs = edge_case_outputs()
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
