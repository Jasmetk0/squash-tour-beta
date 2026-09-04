from __future__ import annotations

from collections import defaultdict

import pytest
from pydantic import ValidationError

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    EffectiveMatchGameplanSnapshot,
    EffectiveMatchStaminaSnapshot,
    GameplanDecisionAction,
    GameplanDecisionReason,
    GameplanStrategy,
    GameplanTimeHorizon,
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchStaminaLog,
    PlayerActiveGameplan,
    PlayerGameplanState,
    RallyCalibrationProfile,
    RallyControlState,
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
            potential_ceiling=92,
            growth_curve="balanced",
            professionalism=0.75,
            ambition=0.72,
            travel_tolerance=0.66,
            schedule_aggression=0.58,
            injury_proneness=0.18,
            resilience=0.82,
        ),
    )


def _context() -> MatchContext:
    return MatchContext(
        match_id="gameplan-match",
        player_a=MatchParticipantContext(
            player=_player("A", strength=86, style="attacking")
        ),
        player_b=MatchParticipantContext(
            player=_player("B", strength=78, style="retrieving")
        ),
    )


def _runtime_states(
    effective: EffectiveMatchGameplanSnapshot,
) -> tuple[PlayerGameplanState, PlayerGameplanState]:
    return tuple(
        PlayerGameplanState(
            player_id=plan.player_id,
            active_plan=plan,
            rallies_since_reassessment=0,
            points_won_since_reassessment=0,
            points_lost_since_reassessment=0,
        )
        for plan in effective.initial_gameplans
    )


def _replace_plan(
    plan: PlayerActiveGameplan, **updates: object
) -> PlayerActiveGameplan:
    payload = plan.model_dump(mode="json")
    payload.update(updates)
    return PlayerActiveGameplan.model_validate(payload)


def test_effective_gameplans_materialize_distinct_four_axis_player_truth() -> None:
    context = _context()
    first = EffectiveMatchGameplanSnapshot.create(context=context, simulation_seed=777)
    replayed = EffectiveMatchGameplanSnapshot.create(
        context=context, simulation_seed=777
    )
    another_match_seed = EffectiveMatchGameplanSnapshot.create(
        context=context, simulation_seed=778
    )

    assert first == replayed
    assert first.natural_style_profiles == another_match_seed.natural_style_profiles
    assert first.initial_gameplans != another_match_seed.initial_gameplans
    assert tuple(profile.player_id for profile in first.natural_style_profiles) == (
        "A",
        "B",
    )
    assert first.natural_style_profiles[0].axes != first.natural_style_profiles[1].axes
    assert all(
        set(profile.axes.model_dump())
        == {"risk", "tempo", "court_positioning", "variation"}
        for profile in first.natural_style_profiles
    )
    assert all(
        plan.opponent_estimate.mean_absolute_error > 0
        for plan in first.initial_gameplans
    )
    assert all(
        3 <= plan.reassessment_after_rallies <= 16
        and plan.selection_seed
        and plan.intended_mechanism
        and plan.time_horizon
        for plan in first.initial_gameplans
    )

    with pytest.raises(ValidationError, match="frozen"):
        first.initial_gameplans[0].confidence = 0.1


def test_every_current_rally_logs_plan_decision_and_causal_effects() -> None:
    result = MatchEngine(rng=DeterministicRng(777)).simulate(
        _context(), log_anchor_hash="c" * 64
    )
    assert result.rally_log is not None
    assert result.rally_log.schema_version == "match_rally_log.v5"
    assert result.rally_log.events

    first_context = result.rally_log.events[0].gameplan_context
    assert first_context is not None
    assert all(
        decision.action == GameplanDecisionAction.START
        and decision.reason == GameplanDecisionReason.INITIAL_SELECTION
        for decision in first_context.player_decisions
    )

    revisions: dict[str, list[int]] = defaultdict(list)
    actions: set[GameplanDecisionAction] = set()
    reviewed_reasons: set[GameplanDecisionReason] = set()
    closure_verified = False
    for event in result.rally_log.events:
        assert event.schema_version == "rally_event.v5"
        assert event.gameplan_context is not None
        gameplan = event.gameplan_context
        assert tuple(effect.player_id for effect in gameplan.player_effects) == (
            event.score_before.player_a_id,
            event.score_before.player_b_id,
        )
        for decision in gameplan.player_decisions:
            revisions[decision.player_id].append(decision.active_plan.revision)
            actions.add(decision.action)
            if decision.reason != GameplanDecisionReason.REVIEW_NOT_DUE:
                reviewed_reasons.add(decision.reason)

        trace = event.control_trace
        assert trace is not None
        if trace.segments and not closure_verified:
            segment = trace.segments[0]
            expected_closure = MatchEngine._segment_closure_probability(
                segment_index=segment.segment_index,
                control_state=segment.state_after,
                pace=segment.phase_pace,
                mean_intensity=sum(
                    workload.intensity_multiplier
                    for workload in segment.player_workloads
                )
                / 2.0,
                calibration=RallyCalibrationProfile(),
                gameplan_closure_adjustment=(
                    gameplan.shared_closure_probability_adjustment
                ),
            )
            assert segment.closure_probability == expected_closure
            closure_verified = True

    assert GameplanDecisionAction.ADAPT in actions
    assert GameplanDecisionReason.NEGATIVE_REASSESSMENT in reviewed_reasons
    assert all(values == sorted(values) for values in revisions.values())
    assert closure_verified is True


def test_ai_can_deliberately_stick_or_adapt_after_the_same_bad_score_signal() -> None:
    context = _context()
    effective = EffectiveMatchGameplanSnapshot.create(
        context=context, simulation_seed=991
    )
    opponent_plan = effective.initial_gameplans[1]
    original = effective.initial_gameplans[0]
    delayed = _replace_plan(
        original,
        strategy=GameplanStrategy.DELAYED_PAYOFF,
        time_horizon=GameplanTimeHorizon.MATCH_LONG,
        confidence=0.96,
        reassessment_after_rallies=3,
        anticipated_payoff_after_rallies=20,
    )
    low_confidence = _replace_plan(
        original,
        strategy=GameplanStrategy.OWN_STRENGTH,
        time_horizon=GameplanTimeHorizon.IMMEDIATE,
        confidence=0.28,
        reassessment_after_rallies=3,
        anticipated_payoff_after_rallies=0,
    )

    def losing_state(plan: PlayerActiveGameplan) -> PlayerGameplanState:
        return PlayerGameplanState(
            player_id="A",
            active_plan=plan,
            rallies_since_reassessment=3,
            points_won_since_reassessment=0,
            points_lost_since_reassessment=3,
        )

    stuck, stuck_state = MatchEngine._review_player_gameplan(
        participant=context.player_a,
        opponent_active_plan=opponent_plan,
        effective=effective,
        state=losing_state(delayed),
        rally_index=4,
        rng=DeterministicRng(10),
    )
    adapted, adapted_state = MatchEngine._review_player_gameplan(
        participant=context.player_a,
        opponent_active_plan=opponent_plan,
        effective=effective,
        state=losing_state(low_confidence),
        rally_index=4,
        rng=DeterministicRng(10),
    )

    assert stuck.action == GameplanDecisionAction.STICK
    assert stuck.reason == GameplanDecisionReason.EXPECTED_LATER_PAYOFF
    assert stuck_state.active_plan.revision == delayed.revision
    assert adapted.action == GameplanDecisionAction.ADAPT
    assert adapted.reason == GameplanDecisionReason.NEGATIVE_REASSESSMENT
    assert adapted_state.active_plan.revision == low_confidence.revision + 1


def test_gameplan_effects_use_current_stamina_without_exposing_future_result() -> None:
    context = _context()
    effective = EffectiveMatchGameplanSnapshot.create(
        context=context, simulation_seed=222
    )
    stamina = EffectiveMatchStaminaSnapshot.create(context=context)
    stamina_states = MatchStaminaLog.create_initial_states(
        effective=stamina,
        player_ids=("A", "B"),
    )

    rally_context, _ = MatchEngine._prepare_rally_gameplans(
        context=context,
        effective=effective,
        states=_runtime_states(effective),
        stamina_states=stamina_states,
        rally_index=1,
        rng=DeterministicRng(333),
    )

    assert all(
        decision.observed_rallies == 0 for decision in rally_context.player_decisions
    )
    assert all(
        -0.25 <= effect.control_execution_signal <= 0.25
        and 0.75 <= effect.workload_factor <= 1.35
        for effect in rally_context.player_effects
    )
    assert rally_context.control_drive_adjustment_player_a == round(
        rally_context.player_effects[0].control_execution_signal
        - rally_context.player_effects[1].control_execution_signal,
        8,
    )


def test_gameplan_control_drive_changes_control_distribution_without_direct_point_bonus() -> (
    None
):
    calibration = RallyCalibrationProfile()

    def mean_next_control(drive: float) -> float:
        values = []
        for seed in range(600):
            state = MatchEngine._next_control_state(
                current_state=RallyControlState.NEUTRAL,
                base_probability_player_a=0.5,
                intensity_a=1.0,
                intensity_b=1.0,
                calibration=calibration,
                rng=DeterministicRng(seed),
                gameplan_control_drive=drive,
            )
            values.append(MatchEngine.CONTROL_VALUE[state])
        return sum(values) / len(values)

    favorable_to_a = mean_next_control(0.12)
    favorable_to_b = mean_next_control(-0.12)

    assert favorable_to_a > favorable_to_b + 0.10
