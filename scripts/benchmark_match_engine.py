"""Reproducible MatchEngine / knockout benchmark with result fingerprints.

Scenarios (each runs in its own fresh process for clean peak-memory numbers):

* ``single``    one real match, production input path (``MatchInputSnapshot`` +
                every effective snapshot, as Run/slot services call it), repeated.
* ``set``       a fixed set of matches with varied strength gaps, styles,
                archetypes, seeds and formats (BO5 and BO3), production path.
* ``lab``       the same set through the plain ``MatchEngine.simulate(context)``
                path that Tournament Lab uses.
* ``ko32`` / ``ko64`` / ``ko128``
                a complete 32/64/128-player Tournament Lab knockout (31/63/127
                real matches) through the shared draw/match kernels; engine time
                is measured separately from the tournament infrastructure.
* ``http16`` / ``http64``
                a real pass: a real uvicorn HTTP server on a disposable SQLite
                database runs a 16/64-player knockout (15/63 real matches)
                through ``POST /admin/labs/tournament/run``; the fingerprint is
                the complete HTTP response body.
* ``corpus``    a small production-input corpus with human Admin inputs (form,
                sharpness, fatigue, health and travel modifiers, upset variance),
                Health snapshots (active Injury, Illness, permanent consequence),
                gameplans, forced tie-breaks (10-10 and PAR-15), long retriever
                rallies, BO1/BO3/BO5 and retirements.
* ``restart``   live-match restart: ``Simulate Next Rally`` for N rallies, the
                working input and state are serialized to JSON, a NEW process
                loads them through full validation and finishes the match; the
                final result must equal the uninterrupted step path and the
                bulk simulation byte for byte.
* ``cases``     the equality corpus of abnormal and edge states: forced deuce
                (equal players, every set checked for 10-10), explicit and
                probabilistic retirement, an injured/ill participant with
                Health input and negative modifiers, BO1/BO3/PAR-15 formats, and
                the step-wise ``Simulate Next Rally`` path whose every persisted
                working state and step outcome is part of the fingerprint.

Every scenario prints a JSON line with wall/CPU seconds, peak RSS and a
fingerprint over every complete ``MatchResult`` (``model_dump(mode="json")``),
so two source trees can be compared for byte-identical outputs.

``--chains`` additionally records, for every real ``MatchResult`` the engine
returns, separate digests of the complete result, the rally, timeline and
stamina chains, gameplan and rules contexts and rally numbers/times
(``model_dump_json`` and sorted-key JSON). It runs inside the engine wrapper, so
a ``--chains`` run is an equality run, never a timing run. ``--emit PATH``
writes the report and every digest as JSON. ``MATCH_BENCH_SOURCE_ROOT`` selects
the source tree whose ``src/beta_engine`` is imported (default: this checkout),
so one harness can measure two pinned commits (``scripts/ab_match_kernel.py``).

    python scripts/benchmark_match_engine.py all --repeats 3
    python scripts/benchmark_match_engine.py single --profile /tmp/single.pstats
    python scripts/benchmark_match_engine.py ko64 --repeats 1 --chains --emit /tmp/ko64.json
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
SOURCE_ROOT = Path(os.environ.get("MATCH_BENCH_SOURCE_ROOT") or ROOT).resolve()
sys.path[:0] = [str(SOURCE_ROOT / "src"), str(ROOT)]

SCENARIOS = ("single", "set", "lab", "ko32", "ko64", "ko128", "http16", "http64",
             "cases", "corpus", "restart")
KNOCKOUT_SIZES = {"ko32": 32, "ko64": 64, "ko128": 128}
HTTP_SIZES = {"http16": 16, "http64": 64}


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


def knockout(size):
    """A complete ``size``-player Tournament Lab knockout (``size - 1`` matches)."""
    from beta_engine.application.tournament_test_lab_service import (
        TournamentLabAssertions,
        TournamentLabRequest,
        TournamentLabScenario,
        TournamentTestLabService,
    )
    from beta_engine.domain.matches import MatchParticipantContext

    participants = tuple(
        MatchParticipantContext(player=_player(
            f"P{index:03d}", 95 - (index * 50) // size, style=STYLES[index % 5],
            archetype=ARCHETYPES[(index * 3) % 5], spread=index % 6))
        for index in range(1, size + 1)
    )
    scenario = TournamentLabScenario(
        scenario_id=f"bench-ko{size}", display_name=f"Benchmark {size} knockout",
        format_kind="knockout", participants=participants, main_draw_size=size,
        seed_order_player_ids=tuple(p.player.player_id for p in participants),
        draw_seed=1701, match_seed=2701,
        assertions=TournamentLabAssertions(expected_played_match_count=size - 1),
    )
    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))
    run = result.runs[0]
    if run.played_match_count != size - 1 or not run.tournament_complete:
        raise SystemExit(f"knockout incomplete: {run.played_match_count} matches")
    return result.model_dump(mode="json")


def ko128(_engine_seconds=None):
    return knockout(128)


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


def _corpus_health(kind, player_a_id, player_b_id):
    """Health snapshots for the corpus: the edge-case injury or an Illness."""
    from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
    from beta_engine.domain.players.health import (
        PlayerHealthProfile,
        PlayerHealthRecord,
    )
    from beta_engine.domain.rankings.official import RankingWeek

    if kind == "injured":
        return _health(player_a_id, player_b_id)
    ill = PlayerHealthProfile(
        player_id=player_b_id,
        records=(PlayerHealthRecord(
            record_id="flu-recovering", kind="Illness", condition_key="influenza",
            lifecycle="Recovering", severity=25, affected_domains=("stamina",),
            onset_week=RankingWeek(season_index=0, week=7), recovery_window_min_weeks=1,
            recovery_window_max_weeks=2, provenance="benchmark recovering illness"),),
    )
    return EffectiveMatchHealthSnapshot.from_profiles(
        player_a=PlayerHealthProfile(player_id=player_a_id), player_b=ill)


def corpus_cases():
    """(label, context, seed, health kind) of the production-input corpus.

    Human Admin inputs are the participant modifiers and upset variance; Health
    enters through the effective Health snapshot; every production snapshot
    carries effective gameplans and rally rules.
    """
    from beta_engine.domain.matches import MatchContext, MatchParticipantContext
    from beta_engine.domain.matches.models import RetirementRule, RetirementTrigger

    def ctx(match_id, a, b, mods_a=None, mods_b=None, **kwargs):
        return MatchContext(
            match_id=match_id,
            player_a=MatchParticipantContext(player=a, **(mods_a or {})),
            player_b=MatchParticipantContext(player=b, **(mods_b or {})), **kwargs)

    grinder_a = _player("LONG-A", 90, style="retrieving", archetype="durable grinder", spread=1)
    grinder_b = _player("LONG-B", 90, style="retrieving", archetype="durable grinder", spread=2)
    even_a = _player("TIE-A", 84, style="tempo-controller", archetype="all-court tactician")
    even_b = _player("TIE-B", 84, style="tempo-controller", archetype="all-court tactician")
    shot = _player("HUM-A", 87, style="attacking", archetype="explosive shotmaker", spread=4)
    wall = _player("HUM-B", 85, style="counter-punching", archetype="quick interceptor", spread=3)
    front = _player("FRONT-A", 80, style="front-court", archetype="late-blooming worker", spread=5)
    tempo = _player("FRONT-B", 78, style="tempo-controller", archetype="quick interceptor", spread=6)
    return [
        ("long-retrievers-bo5", ctx("corpus-long", grinder_a, grinder_b, upset_variance=0.0), 30001, None),
        ("long-retrievers-par15", ctx("corpus-long15", grinder_a, grinder_b, best_of=3, games_to=15,
                                      upset_variance=0.05), 30002, None),
        ("tiebreak-even-bo5", ctx("corpus-tie", even_a, even_b, upset_variance=0.0), 30003, None),
        ("tiebreak-even-bo3", ctx("corpus-tie3", even_a, even_b, best_of=3, upset_variance=0.0), 30004, None),
        ("human-form-sharpness", ctx("corpus-form", shot, wall,
                                     {"form_modifier": 0.2, "sharpness_modifier": 0.15},
                                     {"form_modifier": -0.1, "travel_modifier": -0.12}), 30005, None),
        ("human-fatigue-travel", ctx("corpus-fatigue", shot, wall,
                                     {"fatigue_modifier": -0.3, "travel_modifier": -0.2},
                                     {"sharpness_modifier": 0.3}, upset_variance=0.3), 30006, None),
        ("health-injury-modifiers", ctx("corpus-injury", shot, wall,
                                        {"health_modifier": -0.25, "fatigue_modifier": -0.1}),
         30007, "injured"),
        ("health-illness", ctx("corpus-illness", front, tempo, None,
                               {"health_modifier": -0.15}), 30008, "ill"),
        ("health-injury-bo3", ctx("corpus-injury3", front, tempo, {"health_modifier": -0.35},
                                  best_of=3), 30009, "injured"),
        ("mismatch-bo1", ctx("corpus-bo1", shot, tempo, best_of=1), 30010, None),
        ("retire-explicit-health", ctx("corpus-ret", shot, wall, {"health_modifier": -0.2},
                                       retirement_rule=RetirementRule(
                                           enabled=True, retired_player_id="HUM-A", set_number=2)),
         30011, "injured"),
        ("retire-probabilistic", ctx("corpus-retp", grinder_a, wall, retirement_rule=RetirementRule(
            enabled=True, retired_player_id="HUM-B", trigger=RetirementTrigger.PROBABILISTIC_SET_START,
            set_number=3, probability=0.9)), 30012, None),
    ]


def corpus_outputs(capture=None):
    """Complete serialized outputs of the production-input corpus."""
    from beta_engine.core import DeterministicRng
    from beta_engine.domain.matches import MatchEngine

    outputs = []
    for label, context, seed, health in corpus_cases():
        snapshot = _corpus_snapshot(context, seed, health)
        result = MatchEngine(rng=DeterministicRng(snapshot.simulation_seed)).simulate(
            snapshot.context, **_effective(snapshot))
        outputs.append({"case": label, "input": snapshot.snapshot_hash,
                        "health": snapshot.effective_match_health.fingerprint
                        if snapshot.effective_match_health is not None else None,
                        "result": result.model_dump(mode="json")})
    return outputs


def _corpus_snapshot(context, seed, health):
    from beta_engine.domain.matches.control import RallyCalibrationProfile
    from beta_engine.domain.matches.formats import (
        EffectiveMatchFormatSnapshot,
        MatchFormat,
        official_match_format_snapshot,
    )
    from beta_engine.domain.matches.inputs import MatchInputSnapshot

    official = (context.best_of, context.games_to, context.win_by) == (5, 11, 2)
    a_id = context.player_a.player.player_id
    b_id = context.player_b.player.player_id
    return MatchInputSnapshot.create(
        context=context,
        effective_match_format=official_match_format_snapshot() if official else
        EffectiveMatchFormatSnapshot.create(
            format=MatchFormat(best_of=context.best_of, games_to=context.games_to,
                               win_by=context.win_by),
            source_scope="tournament_edition_override", source_key="tournament-edition"),
        simulation_seed=seed, match_engine_version="benchmark",
        rally_calibration_profile=RallyCalibrationProfile(),
        effective_match_health=_corpus_health(health, a_id, b_id) if health else None,
    )


RESTART_CASES = (
    # (corpus label, rallies played before the process restart)
    ("tiebreak-even-bo5", 23),
    ("health-injury-modifiers", 1),
    ("long-retrievers-par15", 40),
    ("retire-probabilistic", 15),
)


def _step_digest(model):
    return hashlib.sha256(model.model_dump_json().encode()).hexdigest()


def _continue_steps(engine, working_input, state, limit=None):
    """Advance one rally at a time; returns (final result or None, state, digests)."""
    steps = []
    played = 0
    while limit is None or played < limit:
        outcome = engine.simulate_next_rally(working_input, state)
        played += 1
        steps.append(_step_digest(outcome))
        if outcome.final_result is not None:
            return outcome.final_result, None, steps
        state = outcome.state
    return None, state, steps


def restart_continue(path):
    """Child process: load a serialized live match and finish it."""
    from beta_engine.core import DeterministicRng
    from beta_engine.domain.matches import MatchEngine
    from beta_engine.domain.matches.working_state import (
        MatchRallyWorkingState,
        MatchWorkingInput,
    )

    saved = json.loads(Path(path).read_text())
    working_input = MatchWorkingInput.model_validate_json(saved["working_input"])
    state = MatchRallyWorkingState.model_validate_json(saved["state"])
    if _step_digest(state) != saved["state_digest"]:
        raise SystemExit("reloaded working state is not byte-identical")
    engine = MatchEngine(rng=DeterministicRng(working_input.simulation_seed))
    final, _, steps = _continue_steps(engine, working_input, state)
    Path(path).with_suffix(".out.json").write_text(json.dumps(
        {"steps": steps, "result": final.model_dump_json()}))


def restart_outputs():
    """Live-match restart through a new process for every ``RESTART_CASES`` entry."""
    import tempfile

    from beta_engine.core import DeterministicRng
    from beta_engine.domain.matches import MatchEngine

    cases = {label: (context, seed, health) for label, context, seed, health in corpus_cases()}
    outputs = []
    with tempfile.TemporaryDirectory() as root:
        for label, before in RESTART_CASES:
            context, seed, health = cases[label]
            snapshot = _corpus_snapshot(context, seed, health)
            effective = _effective(snapshot)
            bulk = MatchEngine(rng=DeterministicRng(seed)).simulate(snapshot.context, **effective)
            engine = MatchEngine(rng=DeterministicRng(seed))
            working_input, state = engine.start_working_match(snapshot.context, **effective)
            uninterrupted, _, all_steps = _continue_steps(engine, working_input, state)
            first = MatchEngine(rng=DeterministicRng(seed))
            working_input, state = first.start_working_match(snapshot.context, **effective)
            final, state, steps = _continue_steps(first, working_input, state, limit=before)
            if final is not None or state is None:
                raise SystemExit(f"{label}: match ended before the restart point")
            saved = Path(root) / f"{label}.json"
            saved.write_text(json.dumps({
                "working_input": working_input.model_dump_json(),
                "state": state.model_dump_json(), "state_digest": _step_digest(state)}))
            subprocess.run([sys.executable, __file__, "restart", "--continue-from", str(saved)],
                           check=True, cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": "0"})
            child = json.loads(saved.with_suffix(".out.json").read_text())
            if steps + child["steps"] != all_steps:
                raise SystemExit(f"{label}: restarted step outcomes differ from uninterrupted steps")
            if not (child["result"] == uninterrupted.model_dump_json() == bulk.model_dump_json()):
                raise SystemExit(f"{label}: restarted result differs from step/bulk simulation")
            outputs.append({"case": label, "restart_after": before,
                            "state": _step_digest(state), "steps": all_steps,
                            "result": bulk.model_dump(mode="json")})
    return outputs


def http_knockout(size):
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

    # The 16-player inputs are the historical ``http16`` pass, unchanged.
    participants = tuple(
        MatchParticipantContext(player=_player(
            f"H{index:02d}" if size == 16 else f"H{index:03d}",
            92 - index if size == 16 else 92 - (index * 40) // size,
            style=STYLES[index % 5],
            archetype=ARCHETYPES[(index * 2) % 5], spread=index % 4))
        for index in range(1, size + 1)
    )
    scenario = TournamentLabScenario(
        scenario_id=f"bench-http{size}", display_name=f"Benchmark HTTP {size} knockout",
        format_kind="knockout", participants=participants, main_draw_size=size,
        seed_order_player_ids=tuple(p.player.player_id for p in participants),
        draw_seed=1600 + size, match_seed=2600 + size,
        assertions=TournamentLabAssertions(expected_played_match_count=size - 1),
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
    if run["played_match_count"] != size - 1 or not run["tournament_complete"]:
        raise SystemExit(f"http{size} incomplete: {run['played_match_count']} matches")
    return payload


def http16():
    return http_knockout(16)


_LOGS = ("rally_log", "timeline_log", "stamina_log")


def _sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def result_components(result):
    """Separate digests of one real ``MatchResult`` (model object)."""
    dump = result.model_dump(mode="json")
    rally = (dump.get("rally_log") or {}).get("events", [])
    timeline = (dump.get("timeline_log") or {}).get("events", [])
    transitions = (dump.get("stamina_log") or {}).get("transitions", [])
    return {
        "match_id": dump["match_id"],
        "model_dump_json": hashlib.sha256(result.model_dump_json().encode()).hexdigest(),
        "sorted_json": _sha(dump),
        "result_core": _sha({k: v for k, v in dump.items() if k not in _LOGS}),
        **{name: _sha(dump.get(name)) for name in _LOGS},
        "rally_event_hashes": _sha([e["event_hash"] for e in rally]),
        "timeline_event_hashes": _sha([e["event_hash"] for e in timeline]),
        "stamina_transition_hashes": _sha([t["transition_hash"] for t in transitions]),
        "gameplan_contexts": _sha([e.get("gameplan_context") for e in rally]),
        "rules_resolutions": _sha([e.get("rules_resolution") for e in rally]),
        "control_traces": _sha([e.get("control_trace") for e in rally]),
        "rally_numbers_times": _sha([
            (e["rally_index"], e["set_number"], e["rally_in_set"], e["elapsed_seconds"],
             e["estimated_shot_count"], e["abstract_segments"], e["winner_player_id"])
            for e in rally]),
        "timeline_times": _sha([(e["timeline_index"], e["event_type"], e["elapsed_seconds"])
                                for e in timeline]),
        "stamina_states": _sha([(t["states_before"], t["deltas"], t["states_after"])
                                for t in transitions]),
        "rallies": len(rally),
        "max_segments": max((e["abstract_segments"] for e in rally), default=0),
        "deuce_rallies": sum(1 for e in rally if e["score_before"]["points_a"] >= 10
                             and e["score_before"]["points_a"] == e["score_before"]["points_b"]),
    }


def _run_outputs(name):
    if name == "single":
        a = _player("SINGLE-A", 86, style="attacking", archetype="explosive shotmaker")
        b = _player("SINGLE-B", 84, style="retrieving", archetype="durable grinder")
        return [production_match("bench-single", a, b, 5, 918273)]
    if name in {"set", "lab"}:
        simulate = production_match if name == "set" else lab_match
        return [simulate(*case) for case in match_set()]
    if name in HTTP_SIZES:
        return [http_knockout(HTTP_SIZES[name])]
    if name == "cases":
        return edge_case_outputs()
    if name == "corpus":
        return corpus_outputs()
    if name == "restart":
        return restart_outputs()
    return [knockout(KNOCKOUT_SIZES[name])]


def run_scenario(name, repeats, chains=None):
    import pydantic

    import beta_engine
    from beta_engine.domain.matches import MatchEngine

    engine = {"seconds": 0.0, "calls": 0, "rallies": 0}
    original = MatchEngine.simulate

    def timed(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            result = original(self, *args, **kwargs)
        finally:
            engine["seconds"] += time.perf_counter() - started
            engine["calls"] += 1
        if result.rally_log is not None:
            engine["rallies"] += len(result.rally_log.events)
        if chains is not None:
            chains.append(result_components(result))
        return result

    MatchEngine.simulate = timed
    walls, cpus, fingerprints = [], [], []
    try:
        for _ in range(repeats):
            engine["seconds"], engine["calls"], engine["rallies"] = 0.0, 0, 0
            if chains is not None:
                chains.clear()
            wall, cpu = time.perf_counter(), time.process_time()
            outputs = _run_outputs(name)
            walls.append(time.perf_counter() - wall)
            cpus.append(time.process_time() - cpu)
            fingerprints.append(digest(outputs))
    finally:
        MatchEngine.simulate = original
    if len(set(fingerprints)) != 1:
        raise SystemExit("non-deterministic output across repeats")
    calls, rallies = engine["calls"], engine["rallies"]
    return {
        "scenario": name, "repeats": repeats,
        "wall_seconds": [round(v, 3) for v in walls],
        "cpu_seconds": [round(v, 3) for v in cpus],
        "engine_seconds_last": round(engine["seconds"], 3), "engine_calls_last": calls,
        "engine_rallies_last": rallies,
        "engine_ms_per_match_last": round(1000 * engine["seconds"] / calls, 3) if calls else None,
        "engine_us_per_rally_last": round(1e6 * engine["seconds"] / rallies, 1) if rallies else None,
        "infrastructure_seconds_last": round(walls[-1] - engine["seconds"], 3),
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "fingerprint": fingerprints[0],
        "beta_engine_file": beta_engine.__file__,
        "python": sys.version.split()[0], "pydantic": pydantic.VERSION,
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=(*SCENARIOS, "all"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--chains", action="store_true",
                        help="equality run: separate digests of every engine result")
    parser.add_argument("--emit", type=Path, help="write the report and digests here")
    parser.add_argument("--in-process", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--continue-from", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.continue_from:
        restart_continue(args.continue_from)
        return
    if args.scenario == "all":
        for name in SCENARIOS:
            command = [sys.executable, __file__, name, "--repeats", str(args.repeats), "--in-process"]
            subprocess.run(command, check=True, cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": "0"})
        return
    chains = [] if args.chains else None
    if args.profile:
        import cProfile

        profile = cProfile.Profile()
        profile.enable()
        report = run_scenario(args.scenario, args.repeats, chains)
        profile.disable()
        profile.dump_stats(str(args.profile))
    else:
        report = run_scenario(args.scenario, args.repeats, chains)
    report["source_root"] = str(SOURCE_ROOT)
    report["harness"] = str(Path(__file__).resolve())
    if args.emit:
        args.emit.write_text(json.dumps({**report, "chains": chains}, sort_keys=True))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
