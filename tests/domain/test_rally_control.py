from __future__ import annotations

import copy
from collections import Counter
from statistics import median

import pytest
from pydantic import ValidationError

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.matches import (
    EffectiveMatchStaminaSnapshot,
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchStaminaLog,
    MatchTerminationReason,
    RallyCalibrationProfile,
    RallyClosureReason,
    RallyControlState,
    RallyEffortChangeReason,
    RallyEffortLevel,
    RallyEvent,
    RallyPhasePace,
    RetirementRule,
)
from beta_engine.domain.players import HiddenCareerTraits, Player


def _player(player_id: str, *, strength: int, style: str) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
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
            potential_ceiling=90,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
    )


def _context(*, equal: bool = False) -> MatchContext:
    return MatchContext(
        match_id="control-match",
        player_a=MatchParticipantContext(
            player=_player(
                "A",
                strength=84,
                style="tempo-controller" if equal else "attacking",
            )
        ),
        player_b=MatchParticipantContext(
            player=_player(
                "B",
                strength=84 if equal else 82,
                style="tempo-controller" if equal else "retrieving",
            )
        ),
    )


def _one_control_rally(
    *,
    seed: int,
    context: MatchContext | None = None,
    base_probability_player_a: float = 0.53,
):
    context = context or _context()
    engine = MatchEngine(rng=DeterministicRng(seed))
    effective = EffectiveMatchStaminaSnapshot.create(context=context)
    player_ids = (
        context.player_a.player.player_id,
        context.player_b.player.player_id,
    )
    states = MatchStaminaLog.create_initial_states(
        effective=effective, player_ids=player_ids
    )
    rally_rng = DeterministicRng(seed)
    effort_rng = rally_rng.branch(SeedScope.MATCH, "effort")
    efforts = (
        engine._select_rally_effort(
            participant=context.player_a,
            state=states[0],
            own_points=4,
            opponent_points=4,
            games_to=11,
            rng=effort_rng.branch(SeedScope.MATCH, player_ids[0]),
        ),
        engine._select_rally_effort(
            participant=context.player_b,
            state=states[1],
            own_points=4,
            opponent_points=4,
            games_to=11,
            rng=effort_rng.branch(SeedScope.MATCH, player_ids[1]),
        ),
    )
    return engine._simulate_hidden_control_rally(
        context=context,
        server_player_id=player_ids[seed % 2],
        base_probability_player_a=base_probability_player_a,
        efforts=efforts,
        stamina_states=states,
        calibration=RallyCalibrationProfile(),
        terminal_roll=rally_rng.random(),
        rng=rally_rng.branch(SeedScope.MATCH, "hidden-control"),
    )


def test_active_match_records_one_causal_control_trace_per_rally() -> None:
    result = MatchEngine(rng=DeterministicRng(777)).simulate(
        _context(), log_anchor_hash="b" * 64
    )
    assert result.rally_log is not None
    assert result.stamina_log is not None

    for event in result.rally_log.events:
        assert event.schema_version == "rally_event.v4"
        assert event.control_trace is not None
        trace = event.control_trace
        expected_winner = (
            event.score_before.player_a_id
            if trace.terminal_roll < trace.terminal_probability_player_a
            else event.score_before.player_b_id
        )
        assert event.winner_player_id == expected_winner
        assert event.abstract_segments == len(trace.segments)
        assert event.estimated_shot_count == trace.estimated_shot_count
        assert event.elapsed_seconds == trace.active_rally_duration
        assert event.effort_context is not None
        assert tuple(
            effort.workload_units for effort in event.effort_context.player_efforts
        ) == tuple(workload.total_workload_units for workload in trace.player_workloads)


def test_first_set_retirement_keeps_current_empty_log_schemas() -> None:
    context = _context().model_copy(
        update={
            "match_id": "control-retirement",
            "retirement_rule": RetirementRule(
                enabled=True,
                retired_player_id="A",
                set_number=1,
            ),
        }
    )

    result = MatchEngine(rng=DeterministicRng(777)).simulate(context)

    assert result.termination_reason == MatchTerminationReason.RETIREMENT
    assert result.rally_log is not None
    assert result.rally_log.schema_version == "match_rally_log.v4"
    assert result.rally_log.events == ()
    assert result.stamina_log is not None
    assert result.stamina_log.schema_version == "match_stamina_log.v3"


def test_rally_calibration_profile_is_frozen_match_input() -> None:
    profile = RallyCalibrationProfile()

    with pytest.raises(ValidationError, match="frozen"):
        profile.stay_transition_weight = 0.9
    with pytest.raises(ValidationError, match="shot CDF"):
        RallyCalibrationProfile(fast_segment_shot_cdf=(0.2, 0.8, 0.7, 0.9))
    with pytest.raises(ValidationError, match="local inertia"):
        RallyCalibrationProfile(local_transition_weight=0.7)


def test_control_trace_tampering_is_rejected_before_replay() -> None:
    result = MatchEngine(rng=DeterministicRng(777)).simulate(_context())
    assert result.rally_log is not None
    event = next(
        event
        for event in result.rally_log.events
        if event.control_trace is not None and event.control_trace.segments
    )
    payload = copy.deepcopy(event.model_dump(mode="json"))
    payload["control_trace"]["segments"][0]["state_before"] = (
        RallyControlState.STRONG_CONTROL_B.value
    )

    with pytest.raises(
        ValidationError, match="transition kind|continuity|hash mismatch"
    ):
        RallyEvent.model_validate(payload)

    payload = copy.deepcopy(event.model_dump(mode="json"))
    payload["control_trace"]["player_workloads"].reverse()
    for segment in payload["control_trace"]["segments"]:
        segment["player_workloads"].reverse()

    with pytest.raises(ValidationError, match="participant order"):
        RallyEvent.model_validate(payload)


def test_pre_alpha_control_calibration_hits_shot_corridor_and_local_inertia() -> None:
    shots: list[int] = []
    transition_counts: Counter[str] = Counter()
    opening_terminals = 0
    effort_changes = 0

    for seed in range(1200):
        _, _, _, trace, _ = _one_control_rally(seed=seed)
        shots.append(trace.estimated_shot_count)
        opening_terminals += trace.closure_reason == RallyClosureReason.OPENING_TERMINAL
        for segment in trace.segments:
            transition_counts[segment.transition_kind.value] += 1
            effort_changes += len(segment.effort_changes)

    sorted_shots = sorted(shots)
    percentile_75 = sorted_shots[int((len(sorted_shots) - 1) * 0.75)]
    local_share = (transition_counts["STAY"] + transition_counts["LOCAL_SHIFT"]) / sum(
        transition_counts.values()
    )
    direct_reversal_share = transition_counts["DIRECT_REVERSAL"] / sum(
        transition_counts.values()
    )

    assert 11 <= median(shots) <= 13
    assert 19 <= percentile_75 <= 23
    assert local_share >= 0.93
    assert direct_reversal_share <= 0.005
    assert 0 < opening_terminals < len(shots)
    assert effort_changes > 0


def test_equal_players_receive_no_structural_server_control_bonus() -> None:
    context = _context(equal=True)
    for seed in range(80):
        rng = DeterministicRng(seed).branch(SeedScope.MATCH, "opening")
        serving_a = MatchEngine._opening_control_state(
            context=context,
            server_player_id="A",
            base_probability_player_a=0.5,
            rng=rng,
        )
        serving_b = MatchEngine._opening_control_state(
            context=context,
            server_player_id="B",
            base_probability_player_a=0.5,
            rng=DeterministicRng(seed).branch(SeedScope.MATCH, "opening"),
        )

        assert serving_a == serving_b


def test_equal_player_control_model_is_symmetric_across_seed_sample() -> None:
    context = _context(equal=True)
    player_a_wins = 0
    terminal_probabilities: list[float] = []

    for seed in range(600):
        winner, _, _, trace, _ = _one_control_rally(
            seed=seed,
            context=context,
            base_probability_player_a=0.5,
        )
        player_a_wins += winner == "A"
        terminal_probabilities.append(trace.terminal_probability_player_a)

    assert 0.47 <= sum(terminal_probabilities) / len(terminal_probabilities) <= 0.53
    assert 0.45 <= player_a_wins / len(terminal_probabilities) <= 0.55


def test_within_rally_effort_responds_to_pressure_but_low_reserve_conserves() -> None:
    context = _context()
    pressure_profile = RallyCalibrationProfile(
        strong_pressure_effort_change_probability=1.0,
        tactical_effort_change_probability=0.0,
    )
    pressured_level, pressured_change = MatchEngine._within_rally_effort_change(
        participant=context.player_a,
        player_index=0,
        control_state=RallyControlState.STRONG_CONTROL_B,
        current_level=RallyEffortLevel.NORMAL,
        perceived_reserve=0.8,
        calibration=pressure_profile,
        rng=DeterministicRng(10),
    )
    conserve_profile = RallyCalibrationProfile(
        low_reserve_effort_change_probability=1.0,
        tactical_effort_change_probability=0.0,
    )
    conserved_level, conserved_change = MatchEngine._within_rally_effort_change(
        participant=context.player_a,
        player_index=0,
        control_state=RallyControlState.STRONG_CONTROL_B,
        current_level=RallyEffortLevel.MAXIMUM,
        perceived_reserve=0.1,
        calibration=conserve_profile,
        rng=DeterministicRng(10),
    )

    assert pressured_level == RallyEffortLevel.INCREASED
    assert pressured_change is not None
    assert pressured_change.reason == RallyEffortChangeReason.RESPOND_TO_PRESSURE
    assert conserved_level == RallyEffortLevel.INCREASED
    assert conserved_change is not None
    assert conserved_change.reason == RallyEffortChangeReason.CONSERVE_LOW_RESERVE


def test_segment_24_is_a_contextual_forced_terminal() -> None:
    calibration = RallyCalibrationProfile()
    probability = MatchEngine._segment_closure_probability(
        segment_index=24,
        control_state=RallyControlState.STRONG_CONTROL_A,
        pace=RallyPhasePace.FAST,
        mean_intensity=1.0,
        calibration=calibration,
    )
    strong_a_probability = MatchEngine._terminal_control_probability(
        base_probability_player_a=0.5,
        final_state=RallyControlState.STRONG_CONTROL_A,
        mean_control_value=1.5,
        calibration=calibration,
    )
    strong_b_probability = MatchEngine._terminal_control_probability(
        base_probability_player_a=0.5,
        final_state=RallyControlState.STRONG_CONTROL_B,
        mean_control_value=-1.5,
        calibration=calibration,
    )

    assert probability == 1.0
    assert strong_a_probability > 0.5 > strong_b_probability
