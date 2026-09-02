from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    EffectiveMatchStaminaSnapshot,
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchStaminaLog,
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
    assert profile_a.bar(StaminaDimension.EXPLOSIVE).capacity > profile_b.bar(
        StaminaDimension.EXPLOSIVE
    ).capacity
    assert profile_a.bar(StaminaDimension.MATCH).recovery_per_second > profile_b.bar(
        StaminaDimension.MATCH
    ).recovery_per_second
    assert effective.calibration_version == "pre_alpha_physical_v1"
    assert effective.outcome_effect_applied is False


def test_negative_carried_modifiers_reduce_initial_fill_without_changing_capacity() -> None:
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
            for before_bar, after_bar in zip(
                before.bars, after.bars, strict=True
            ):
                assert before_bar.current <= after_bar.current <= after_bar.capacity
        assert any(
            after_bar.current < after_bar.capacity
            for state in transition.states_after
            for after_bar in state.bars
        )


def test_calibration_changes_stamina_log_but_not_sporting_or_timing_truth() -> None:
    default = _result()
    alternate_context = MatchContext(
        match_id="alternate-calibration-source",
        player_a=MatchParticipantContext(
            player=_player("A", physical=55, movement=52, recovery=50)
        ),
        player_b=MatchParticipantContext(
            player=_player("B", physical=96, movement=95, recovery=97)
        ),
    )
    alternate = EffectiveMatchStaminaSnapshot.create(context=alternate_context)
    changed = _result(stamina=alternate)

    assert changed.winner_player_id == default.winner_player_id
    assert changed.sets == default.sets
    assert changed.rally_log == default.rally_log
    assert changed.timeline_log == default.timeline_log
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
