from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.matches import (
    EffectiveMatchStaminaSnapshot,
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchStaminaLog,
    PlayerStaminaState,
    RallyCalibrationProfile,
    StaminaBarState,
    StaminaDimension,
    StaminaTransitionCause,
)
from beta_engine.domain.players import HiddenCareerTraits, Player


def _player(player_id: str, *, physical: int, movement: int, recovery: int) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="TST",
        technique=82,
        movement=movement,
        physical=physical,
        mental=82,
        consistency=82,
        clutch=82,
        recovery=recovery,
        play_style="tempo-controller",
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


def _context(*, fatigue_a: float = 0.0) -> MatchContext:
    return MatchContext(
        match_id="stamina-match",
        player_a=MatchParticipantContext(
            player=_player("A", physical=88, movement=91, recovery=86),
            fatigue_modifier=fatigue_a,
        ),
        player_b=MatchParticipantContext(
            player=_player("B", physical=76, movement=79, recovery=71)
        ),
    )


def _result(*, stamina: EffectiveMatchStaminaSnapshot | None = None):
    return MatchEngine(rng=DeterministicRng(919)).simulate(
        _context(),
        log_anchor_hash="c" * 64,
        effective_match_stamina=stamina,
    )


def test_effective_profile_derives_three_distinct_bars_from_player_inputs() -> None:
    effective = EffectiveMatchStaminaSnapshot.create(context=_context())
    profile_a = effective.profile_for("A")
    profile_b = effective.profile_for("B")

    assert {bar.dimension for bar in profile_a.bars} == set(StaminaDimension)
    assert (
        profile_a.bar(StaminaDimension.EXPLOSIVE).capacity
        > profile_b.bar(StaminaDimension.EXPLOSIVE).capacity
    )
    assert (
        profile_a.bar(StaminaDimension.MATCH).recovery_per_second
        > profile_b.bar(StaminaDimension.MATCH).recovery_per_second
    )
    assert effective.calibration_version == "pre_alpha_physical_v4"
    assert effective.outcome_effect_applied is True
    assert effective.pre_rally_effort_applied is True
    assert effective.within_rally_effort_applied is True
    assert "stamina_outcome_coupling" not in effective.unsupported_components
    assert "within_rally_effort_changes" not in effective.unsupported_components


def test_negative_carried_modifiers_reduce_initial_fill_without_changing_capacity() -> (
    None
):
    rested = EffectiveMatchStaminaSnapshot.create(context=_context())
    tired = EffectiveMatchStaminaSnapshot.create(context=_context(fatigue_a=-0.30))
    rested_result = _result(stamina=rested)
    tired_result = _result(stamina=tired)
    assert rested_result.stamina_log is not None
    assert tired_result.stamina_log is not None

    rested_state = rested_result.stamina_log.initial_states[0]
    tired_state = tired_result.stamina_log.initial_states[0]
    assert [bar.capacity for bar in rested_state.bars] == [
        bar.capacity for bar in tired_state.bars
    ]
    assert all(
        tired_bar.current < rested_bar.current
        for rested_bar, tired_bar in zip(
            rested_state.bars, tired_state.bars, strict=True
        )
    )


def test_stamina_log_covers_timeline_and_applies_time_exactly_once() -> None:
    result = _result()
    assert result.timeline_log is not None
    assert result.stamina_log is not None
    stamina = result.stamina_log

    stamina.validate_timeline(result.timeline_log)
    assert stamina.total_transitions == result.timeline_log.total_timeline_events
    assert stamina.timeline_log_hash == result.timeline_log.match_log_hash
    assert stamina.match_log_hash == stamina.transitions[-1].transition_hash
    assert "dynamic_stamina_recovery" not in (
        result.timeline_log.unsupported_timeline_components
    )

    for transition, source in zip(
        stamina.transitions, result.timeline_log.events, strict=True
    ):
        assert transition.elapsed_seconds == source.elapsed_seconds
        assert transition.source_timeline_event_hash == source.event_hash
        if source.event_type == "RALLY":
            assert transition.cause == StaminaTransitionCause.RALLY_WORKLOAD
            assert all(delta.explosive < 0 for delta in transition.deltas)
        else:
            assert transition.workload_units == 0
            assert all(delta.explosive >= 0 for delta in transition.deltas)


def test_longer_harder_rallies_produce_more_workload() -> None:
    result = _result()
    assert result.rally_log is not None
    assert result.stamina_log is not None
    rally_transitions = [
        transition
        for transition in result.stamina_log.transitions
        if transition.cause == StaminaTransitionCause.RALLY_WORKLOAD
    ]
    paired = list(zip(result.rally_log.events, rally_transitions, strict=True))
    low = min(paired, key=lambda pair: pair[1].workload_units)
    high = max(paired, key=lambda pair: pair[1].workload_units)

    assert high[1].workload_units > low[1].workload_units
    assert (
        high[0].elapsed_seconds > low[0].elapsed_seconds
        or high[0].estimated_shot_count > low[0].estimated_shot_count
        or high[0].abstract_segments > low[0].abstract_segments
    )


def test_game_break_recovers_both_players_without_resetting_bars() -> None:
    result = _result()
    assert result.stamina_log is not None
    breaks = [
        transition
        for transition in result.stamina_log.transitions
        if transition.cause == StaminaTransitionCause.GAME_BREAK_RECOVERY
    ]
    assert breaks

    for transition in breaks:
        assert transition.elapsed_seconds == 120
        for before, after in zip(
            transition.states_before, transition.states_after, strict=True
        ):
            for before_bar, after_bar in zip(before.bars, after.bars, strict=True):
                assert before_bar.current <= after_bar.current <= after_bar.capacity
        assert any(
            after_bar.current < after_bar.capacity
            for state in transition.states_after
            for after_bar in state.bars
        )


def test_legacy_inactive_calibration_does_not_change_sporting_or_timing_truth() -> None:
    default_stamina = EffectiveMatchStaminaSnapshot.create(
        context=_context(), outcome_effect_applied=False
    )
    default = _result(stamina=default_stamina)
    alternate_context = MatchContext(
        match_id="alternate-calibration-source",
        player_a=MatchParticipantContext(
            player=_player("A", physical=55, movement=52, recovery=50)
        ),
        player_b=MatchParticipantContext(
            player=_player("B", physical=96, movement=95, recovery=97)
        ),
    )
    alternate = EffectiveMatchStaminaSnapshot.create(
        context=alternate_context, outcome_effect_applied=False
    )
    changed = _result(stamina=alternate)

    assert changed.winner_player_id == default.winner_player_id
    assert changed.sets == default.sets
    assert changed.rally_log is not None and default.rally_log is not None
    assert [event.winner_player_id for event in changed.rally_log.events] == [
        event.winner_player_id for event in default.rally_log.events
    ]
    assert [event.elapsed_seconds for event in changed.rally_log.events] == [
        event.elapsed_seconds for event in default.rally_log.events
    ]
    assert changed.stamina_log != default.stamina_log


def test_stamina_log_rejects_hash_and_state_tampering() -> None:
    result = _result()
    assert result.stamina_log is not None
    payload = result.stamina_log.model_dump(mode="json")
    payload["transitions"][2]["deltas"][0]["explosive"] += 0.5

    with pytest.raises(ValidationError, match="delta does not match|hash mismatch"):
        MatchStaminaLog.model_validate(payload)

    payload = copy.deepcopy(result.stamina_log.model_dump(mode="json"))
    payload["transitions"][1]["previous_transition_hash"] = "0" * 64
    with pytest.raises(ValidationError, match="hash mismatch|chain is broken"):
        MatchStaminaLog.model_validate(payload)


def test_v1_stamina_transition_remains_hash_compatible_without_player_workloads() -> (
    None
):
    inactive = EffectiveMatchStaminaSnapshot.create(
        context=_context(), outcome_effect_applied=False
    )
    result = _result(stamina=inactive)
    assert result.stamina_log is not None
    payload = result.stamina_log.model_dump(mode="json")
    payload["schema_version"] = "match_stamina_log.v1"
    payload.pop("pre_rally_effort_applied")
    payload.pop("within_rally_effort_applied")
    for transition in payload["transitions"]:
        transition.pop("player_workloads")

    restored = MatchStaminaLog.model_validate(payload)

    assert restored.schema_version == "match_stamina_log.v1"
    assert restored.pre_rally_effort_applied is False


def test_every_rally_records_the_live_nonlinear_stamina_effect() -> None:
    result = _result()
    assert result.rally_log is not None
    assert result.stamina_log is not None
    assert result.stamina_log.outcome_effect_applied is True

    contexts = [event.stamina_outcome_context for event in result.rally_log.events]
    assert all(
        event.schema_version == "rally_event.v5" for event in result.rally_log.events
    )
    assert all(context is not None for context in contexts)
    assert any(
        impact.strength_penalty > 0
        for context in contexts
        if context is not None
        for impact in context.player_impacts
    )
    result.stamina_log.validate_rally_outcomes(result.rally_log.events)


def test_each_rally_records_asymmetric_player_effort_and_workload() -> None:
    result = _result()
    assert result.rally_log is not None
    assert result.stamina_log is not None

    rally_transitions = [
        transition
        for transition in result.stamina_log.transitions
        if transition.cause == StaminaTransitionCause.RALLY_WORKLOAD
    ]
    observed_levels = set()
    for rally, transition in zip(
        result.rally_log.events, rally_transitions, strict=True
    ):
        assert rally.effort_context is not None
        efforts = rally.effort_context.player_efforts
        observed_levels.update(effort.intended_level for effort in efforts)
        assert rally.effort_context.base_workload_units == transition.workload_units
        assert tuple(
            (workload.player_id, workload.workload_units)
            for workload in transition.player_workloads
        ) == tuple((effort.player_id, effort.workload_units) for effort in efforts)
        assert efforts[0].workload_units != efforts[1].workload_units

    assert len(observed_levels) >= 3


def test_effort_ai_conserves_low_reserve_and_movement_changes_energy_cost() -> None:
    context = _context()
    effective = EffectiveMatchStaminaSnapshot.create(context=context)
    rested = MatchStaminaLog.create_initial_states(
        effective=effective, player_ids=("A", "B")
    )[0]
    depleted = PlayerStaminaState(
        player_id="A",
        bars=tuple(
            bar.model_copy(update={"current": bar.capacity * 0.10})
            for bar in rested.bars
        ),
    )
    conserve = MatchEngine._select_rally_effort(
        participant=context.player_a,
        state=depleted,
        own_points=4,
        opponent_points=4,
        games_to=11,
        rng=DeterministicRng(55),
    )
    less_efficient_player = context.player_a.player.model_copy(update={"movement": 45})
    less_efficient = MatchEngine._select_rally_effort(
        participant=context.player_a.model_copy(
            update={"player": less_efficient_player}
        ),
        state=rested,
        own_points=4,
        opponent_points=4,
        games_to=11,
        rng=DeterministicRng(55),
    )
    efficient = MatchEngine._select_rally_effort(
        participant=context.player_a,
        state=rested,
        own_points=4,
        opponent_points=4,
        games_to=11,
        rng=DeterministicRng(55),
    )

    assert conserve.intended_level.value == "CONSERVE"
    assert (
        conserve.executed_intensity_multiplier
        == conserve.requested_intensity_multiplier
    )
    assert (
        efficient.movement_efficiency_factor < less_efficient.movement_efficiency_factor
    )


def test_replay_rejects_individual_workload_tampering() -> None:
    result = _result()
    assert result.rally_log is not None
    assert result.stamina_log is not None
    payload = result.stamina_log.model_dump(mode="json")
    first_rally = next(
        transition
        for transition in payload["transitions"]
        if transition["cause"] == "RALLY_WORKLOAD"
    )
    first_rally["player_workloads"][0]["workload_units"] += 0.25

    with pytest.raises(ValidationError, match="hash mismatch"):
        MatchStaminaLog.model_validate(payload)


def test_stamina_penalty_is_continuous_and_steepens_near_empty() -> None:
    def state(fill: float) -> PlayerStaminaState:
        return PlayerStaminaState(
            player_id="A",
            bars=tuple(
                StaminaBarState(
                    dimension=dimension,
                    capacity=100,
                    current=100 * fill,
                )
                for dimension in StaminaDimension
            ),
        )

    full = MatchEngine._stamina_impact(state(1.0), enabled=True)
    medium = MatchEngine._stamina_impact(state(0.5), enabled=True)
    low = MatchEngine._stamina_impact(state(0.1), enabled=True)

    assert full.strength_penalty == 0
    assert 0 < medium.strength_penalty < low.strength_penalty < 0.18
    assert low.strength_penalty - medium.strength_penalty > medium.strength_penalty


def test_more_exhausted_player_gets_lower_rally_probability() -> None:
    engine = MatchEngine(rng=DeterministicRng(1))
    context = MatchContext(
        match_id="equal-players",
        player_a=MatchParticipantContext(
            player=_player("A", physical=82, movement=82, recovery=82)
        ),
        player_b=MatchParticipantContext(
            player=_player("B", physical=82, movement=82, recovery=82)
        ),
        upset_variance=0,
    )
    effective = EffectiveMatchStaminaSnapshot.create(context=context)
    states = MatchStaminaLog.create_initial_states(
        effective=effective, player_ids=("A", "B")
    )
    tired_a = PlayerStaminaState(
        player_id="A",
        bars=tuple(
            bar.model_copy(update={"current": bar.capacity * 0.15})
            for bar in states[0].bars
        ),
    )

    probability, outcome = engine._game_probability(
        adjusted_a=0.8,
        adjusted_b=0.8,
        context=context,
        games_a=5,
        games_b=5,
        stamina=effective,
        stamina_states=(tired_a, states[1]),
    )

    assert outcome.base_probability_player_a == 0.5
    assert probability == outcome.adjusted_probability_player_a
    assert probability < 0.5
    assert (
        outcome.player_impacts[0].strength_penalty
        > outcome.player_impacts[1].strength_penalty
    )


def test_hidden_control_changes_some_but_not_all_shared_terminal_rolls() -> None:
    context = _context()
    engine = MatchEngine(rng=DeterministicRng(1))
    effective = EffectiveMatchStaminaSnapshot.create(context=context)
    states = MatchStaminaLog.create_initial_states(
        effective=effective, player_ids=("A", "B")
    )
    changed_points = 0
    samples = 160
    base_probability = 0.52

    for seed in range(1000, 1000 + samples):
        rally_rng = DeterministicRng(seed)
        effort_rng = rally_rng.branch(SeedScope.MATCH, "effort")
        efforts = (
            engine._select_rally_effort(
                participant=context.player_a,
                state=states[0],
                own_points=4,
                opponent_points=4,
                games_to=11,
                rng=effort_rng.branch(SeedScope.MATCH, "A"),
            ),
            engine._select_rally_effort(
                participant=context.player_b,
                state=states[1],
                own_points=4,
                opponent_points=4,
                games_to=11,
                rng=effort_rng.branch(SeedScope.MATCH, "B"),
            ),
        )
        terminal_roll = rally_rng.random()
        winner, _, _, _, _ = engine._simulate_hidden_control_rally(
            context=context,
            server_player_id="A" if seed % 2 else "B",
            base_probability_player_a=base_probability,
            efforts=efforts,
            stamina_states=states,
            calibration=RallyCalibrationProfile(),
            terminal_roll=terminal_roll,
            rng=rally_rng.branch(SeedScope.MATCH, "hidden-control"),
        )
        baseline_winner = "A" if terminal_roll < base_probability else "B"
        changed_points += winner != baseline_winner

    assert 0 < changed_points < samples
