"""Deterministic standalone set-by-set professional squash match engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import exp, log
from typing import ClassVar

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.matches.control import RallyCalibrationProfile
from beta_engine.domain.matches.models import (
    MatchContext,
    MatchParticipantContext,
    MatchResult,
    MatchTerminationReason,
    RetirementTrigger,
    SetResult,
)
from beta_engine.domain.matches.rallies import (
    MatchRallyLog,
    PlayerControlSegmentWorkload,
    PlayerRallyControlWorkload,
    PlayerRallyEffort,
    PlayerRallyStaminaImpact,
    PostRallyStateSnapshot,
    RallyAnalyticalAttribution,
    RallyClosureReason,
    RallyControlSegment,
    RallyControlState,
    RallyControlTrace,
    RallyControlTransitionKind,
    RallyEffortChange,
    RallyEffortChangeReason,
    RallyEffortContext,
    RallyEffortDecisionFactor,
    RallyEffortLevel,
    RallyEvent,
    RallyPhasePace,
    RallyScoreMutation,
    RallyScoreSnapshot,
    RallyStaminaOutcomeContext,
    RallyTerminalTrigger,
)
from beta_engine.domain.matches.stamina import (
    EffectiveMatchStaminaSnapshot,
    MatchStaminaLog,
    PlayerStaminaState,
    StaminaDimension,
    StaminaTransitionCause,
)
from beta_engine.domain.matches.timeline import (
    BetweenRallyIntervalEvent,
    GameBreakEvent,
    MatchTimelineEvent,
    MatchTimelineLog,
    RallyTimelineEvent,
    ReadinessComponent,
)
from beta_engine.domain.matches.timing import (
    EffectiveMatchTimingSnapshot,
    RestartDecisionFactor,
    RestartIntent,
)


@dataclass(slots=True)
class MatchEngine:
    """Set-by-set BO5 simulation using deterministic RNG only."""

    rng: DeterministicRng

    STYLE_MATCHUP_EDGES: ClassVar[dict[tuple[str, str], float]] = {
        ("attacking", "retrieving"): 0.014,
        ("retrieving", "attacking"): -0.014,
        ("counter-punching", "attacking"): 0.012,
        ("attacking", "counter-punching"): -0.012,
        ("front-court", "counter-punching"): 0.011,
        ("counter-punching", "front-court"): -0.011,
        ("retrieving", "front-court"): 0.009,
        ("front-court", "retrieving"): -0.009,
        ("tempo-controller", "attacking"): 0.008,
        ("attacking", "tempo-controller"): -0.008,
        ("tempo-controller", "retrieving"): -0.006,
        ("retrieving", "tempo-controller"): 0.006,
    }

    ARCHETYPE_MATCHUP_EDGES: ClassVar[dict[tuple[str, str], float]] = {
        ("explosive shotmaker", "durable grinder"): 0.011,
        ("durable grinder", "explosive shotmaker"): -0.011,
        ("durable grinder", "late-blooming worker"): 0.007,
        ("late-blooming worker", "durable grinder"): -0.007,
        ("all-court tactician", "explosive shotmaker"): 0.01,
        ("explosive shotmaker", "all-court tactician"): -0.01,
        ("quick interceptor", "all-court tactician"): 0.009,
        ("all-court tactician", "quick interceptor"): -0.009,
        ("late-blooming worker", "quick interceptor"): 0.008,
        ("quick interceptor", "late-blooming worker"): -0.008,
    }

    CONTROL_VALUE: ClassVar[dict[RallyControlState, int]] = {
        RallyControlState.STRONG_CONTROL_A: 2,
        RallyControlState.SLIGHT_CONTROL_A: 1,
        RallyControlState.NEUTRAL: 0,
        RallyControlState.SLIGHT_CONTROL_B: -1,
        RallyControlState.STRONG_CONTROL_B: -2,
    }
    CONTROL_STATE: ClassVar[dict[int, RallyControlState]] = {
        2: RallyControlState.STRONG_CONTROL_A,
        1: RallyControlState.SLIGHT_CONTROL_A,
        0: RallyControlState.NEUTRAL,
        -1: RallyControlState.SLIGHT_CONTROL_B,
        -2: RallyControlState.STRONG_CONTROL_B,
    }
    EFFORT_LEVELS: ClassVar[tuple[RallyEffortLevel, ...]] = tuple(RallyEffortLevel)
    EFFORT_REQUESTED_INTENSITY: ClassVar[dict[RallyEffortLevel, float]] = {
        RallyEffortLevel.CONSERVE: 0.78,
        RallyEffortLevel.NORMAL: 1.00,
        RallyEffortLevel.INCREASED: 1.16,
        RallyEffortLevel.MAXIMUM: 1.32,
    }

    def simulate(
        self,
        context: MatchContext,
        *,
        log_anchor_hash: str | None = None,
        effective_match_timing: EffectiveMatchTimingSnapshot | None = None,
        effective_match_stamina: EffectiveMatchStaminaSnapshot | None = None,
        rally_calibration_profile: RallyCalibrationProfile | None = None,
    ) -> MatchResult:
        player_a = context.player_a.player
        player_b = context.player_b.player
        match_rng = self.rng.branch(
            SeedScope.MATCH, context.match_id, player_a.player_id, player_b.player_id
        )
        timing = effective_match_timing or EffectiveMatchTimingSnapshot.create(
            player_a_id=player_a.player_id,
            player_b_id=player_b.player_id,
        )
        stamina = effective_match_stamina or EffectiveMatchStaminaSnapshot.create(
            context=context
        )
        rally_calibration = rally_calibration_profile or RallyCalibrationProfile()
        if {profile.player_id for profile in timing.player_restart_profiles} != {
            player_a.player_id,
            player_b.player_id,
        }:
            raise ValueError(
                "effective match timing profiles must match both participants"
            )
        if tuple(profile.player_id for profile in stamina.player_profiles) != (
            player_a.player_id,
            player_b.player_id,
        ):
            raise ValueError("effective stamina profiles must match participant order")

        strength_a = self._base_strength(context.player_a)
        strength_b = self._base_strength(context.player_b)
        matchup_a, matchup_b = self._style_and_archetype_adjustment(
            player_a.play_style,
            player_b.play_style,
            player_a.archetype,
            player_b.archetype,
        )
        strength_a += matchup_a
        strength_b += matchup_b

        sets: list[SetResult] = []
        rally_events: list[RallyEvent] = []
        sets_won = {player_a.player_id: 0, player_b.player_id: 0}
        target_sets = context.best_of // 2 + 1
        momentum_owner: str | None = None
        rally_index = 1
        server_player_id = match_rng.branch(SeedScope.MATCH, "initial-server").choice(
            [player_a.player_id, player_b.player_id]
        )
        input_hash = log_anchor_hash or self._default_log_anchor(context)
        stamina_states = MatchStaminaLog.create_initial_states(
            effective=stamina,
            player_ids=(player_a.player_id, player_b.player_id),
        )
        timeline_rng = match_rng.branch(SeedScope.MATCH, "timeline-v1")

        for set_number in range(1, context.best_of + 1):
            retired_player_id = self._retirement_if_triggered(
                context, set_number, match_rng
            )
            if retired_player_id is not None:
                winner_id = (
                    player_b.player_id
                    if retired_player_id == player_a.player_id
                    else player_a.player_id
                )
                return self._build_result(
                    context=context,
                    winner_player_id=winner_id,
                    loser_player_id=retired_player_id,
                    sets=sets,
                    sets_won=sets_won,
                    termination_reason=MatchTerminationReason.RETIREMENT,
                    retired_player_id=retired_player_id,
                    retired_at_set_start=set_number,
                    rally_events=rally_events,
                    input_hash=input_hash,
                    match_rng=match_rng,
                    timing=timing,
                    stamina=stamina,
                    expected_final_stamina_states=stamina_states,
                )

            (
                set_winner,
                set_result,
                set_events,
                rally_index,
                server_player_id,
                stamina_states,
            ) = self._simulate_set(
                set_number=set_number,
                player_a_id=player_a.player_id,
                player_b_id=player_b.player_id,
                strength_a=strength_a,
                strength_b=strength_b,
                momentum_owner=momentum_owner,
                context=context,
                match_rng=match_rng,
                sets_won=sets_won,
                target_sets=target_sets,
                first_rally_index=rally_index,
                server_player_id=server_player_id,
                previous_event_hash=rally_events[-1].event_hash
                if rally_events
                else input_hash,
                timing=timing,
                stamina=stamina,
                stamina_states=stamina_states,
                timeline_rng=timeline_rng,
                rally_calibration=rally_calibration,
            )
            rally_events.extend(set_events)
            sets.append(set_result)
            sets_won[set_winner] += 1
            momentum_owner = set_winner
            if sets_won[set_winner] >= target_sets:
                loser_id = (
                    player_b.player_id
                    if set_winner == player_a.player_id
                    else player_a.player_id
                )
                return self._build_result(
                    context=context,
                    winner_player_id=set_winner,
                    loser_player_id=loser_id,
                    sets=sets,
                    sets_won=sets_won,
                    termination_reason=MatchTerminationReason.COMPLETED,
                    rally_events=rally_events,
                    input_hash=input_hash,
                    match_rng=match_rng,
                    timing=timing,
                    stamina=stamina,
                    expected_final_stamina_states=stamina_states,
                )
            _, stamina_states = MatchStaminaLog.advance_states(
                effective=stamina,
                states=stamina_states,
                cause=StaminaTransitionCause.GAME_BREAK_RECOVERY,
                elapsed_seconds=timing.nominal_game_break_seconds,
                workload_units=0.0,
            )

        winner_id = (
            player_a.player_id
            if sets_won[player_a.player_id] > sets_won[player_b.player_id]
            else player_b.player_id
        )
        loser_id = (
            player_b.player_id
            if winner_id == player_a.player_id
            else player_a.player_id
        )
        return self._build_result(
            context=context,
            winner_player_id=winner_id,
            loser_player_id=loser_id,
            sets=sets,
            sets_won=sets_won,
            termination_reason=MatchTerminationReason.COMPLETED,
            rally_events=rally_events,
            input_hash=input_hash,
            match_rng=match_rng,
            timing=timing,
            stamina=stamina,
            expected_final_stamina_states=stamina_states,
        )

    def _build_result(
        self,
        *,
        context: MatchContext,
        winner_player_id: str,
        loser_player_id: str,
        sets: list[SetResult],
        sets_won: dict[str, int],
        termination_reason: MatchTerminationReason,
        rally_events: list[RallyEvent],
        input_hash: str,
        match_rng: DeterministicRng,
        timing: EffectiveMatchTimingSnapshot,
        stamina: EffectiveMatchStaminaSnapshot,
        expected_final_stamina_states: tuple[PlayerStaminaState, PlayerStaminaState],
        retired_player_id: str | None = None,
        retired_at_set_start: int | None = None,
    ) -> MatchResult:
        rally_log = MatchRallyLog.create(
            match_id=context.match_id,
            input_snapshot_hash=input_hash,
            events=rally_events,
            schema_version=(
                "match_rally_log.v4"
                if stamina.within_rally_effort_applied
                else "match_rally_log.v3"
                if stamina.pre_rally_effort_applied
                else "match_rally_log.v2"
            ),
        )
        timeline_log = self._build_timeline(
            context=context,
            match_rng=match_rng,
            rally_log=rally_log,
            timing=timing,
            termination_reason=termination_reason,
            retired_at_set_start=retired_at_set_start,
        )
        stamina_log = MatchStaminaLog.build(
            context=context,
            timeline=timeline_log,
            rally_events=rally_log.events,
            effective=stamina,
        )
        if stamina_log.final_states != expected_final_stamina_states:
            raise ValueError("live stamina state diverged from authoritative timeline")
        return MatchResult(
            match_id=context.match_id,
            winner_player_id=winner_player_id,
            loser_player_id=loser_player_id,
            player_a_id=context.player_a.player.player_id,
            player_b_id=context.player_b.player.player_id,
            best_of=context.best_of,
            games_to=context.games_to,
            win_by=context.win_by,
            sets=sets,
            sets_won=sets_won,
            termination_reason=termination_reason,
            retired_player_id=retired_player_id,
            retired_at_set_start=retired_at_set_start,
            rally_log=rally_log,
            timeline_log=timeline_log,
            stamina_log=stamina_log,
        )

    def _simulate_set(
        self,
        *,
        set_number: int,
        player_a_id: str,
        player_b_id: str,
        strength_a: float,
        strength_b: float,
        momentum_owner: str | None,
        context: MatchContext,
        match_rng: DeterministicRng,
        sets_won: dict[str, int],
        target_sets: int,
        first_rally_index: int,
        server_player_id: str,
        previous_event_hash: str,
        timing: EffectiveMatchTimingSnapshot,
        stamina: EffectiveMatchStaminaSnapshot,
        stamina_states: tuple[PlayerStaminaState, PlayerStaminaState],
        timeline_rng: DeterministicRng,
        rally_calibration: RallyCalibrationProfile,
    ) -> tuple[
        str,
        SetResult,
        list[RallyEvent],
        int,
        str,
        tuple[PlayerStaminaState, PlayerStaminaState],
    ]:
        set_rng = match_rng.branch(SeedScope.MATCH, "set", set_number)
        momentum_adjustment = 0.035
        adjusted_a = strength_a + (
            momentum_adjustment if momentum_owner == player_a_id else 0.0
        )
        adjusted_b = strength_b + (
            momentum_adjustment if momentum_owner == player_b_id else 0.0
        )

        upset_roll = set_rng.uniform(-context.upset_variance, context.upset_variance)
        adjusted_a += upset_roll
        adjusted_b -= upset_roll

        games_a = 0
        games_b = 0
        was_close_endgame = False
        rally_events: list[RallyEvent] = []
        rally_index = first_rally_index
        rally_in_set = 1

        while not self._set_finished(
            games_a, games_b, context.games_to, context.win_by
        ):
            effort_rng = set_rng.branch(SeedScope.MATCH, "rally-effort", rally_in_set)
            efforts = (
                (
                    self._select_rally_effort(
                        participant=context.player_a,
                        state=stamina_states[0],
                        own_points=games_a,
                        opponent_points=games_b,
                        games_to=context.games_to,
                        rng=effort_rng.branch(SeedScope.MATCH, player_a_id),
                    ),
                    self._select_rally_effort(
                        participant=context.player_b,
                        state=stamina_states[1],
                        own_points=games_b,
                        opponent_points=games_a,
                        games_to=context.games_to,
                        rng=effort_rng.branch(SeedScope.MATCH, player_b_id),
                    ),
                )
                if stamina.pre_rally_effort_applied
                else None
            )
            game_prob_a, stamina_outcome = self._game_probability(
                adjusted_a=adjusted_a,
                adjusted_b=adjusted_b,
                context=context,
                games_a=games_a,
                games_b=games_b,
                stamina=stamina,
                stamina_states=stamina_states,
                efforts=efforts,
            )
            if games_a >= context.games_to - 2 and games_b >= context.games_to - 2:
                was_close_endgame = True

            score_before = RallyScoreSnapshot(
                player_a_id=player_a_id,
                player_b_id=player_b_id,
                sets_a=sets_won[player_a_id],
                sets_b=sets_won[player_b_id],
                points_a=games_a,
                points_b=games_b,
            )
            detail_rng = set_rng.branch(SeedScope.MATCH, "rally-detail", rally_in_set)
            terminal_roll = set_rng.random()
            control_trace = None
            if stamina.within_rally_effort_applied and efforts is not None:
                (
                    rally_winner,
                    trigger,
                    attribution,
                    control_trace,
                    completed_efforts,
                ) = self._simulate_hidden_control_rally(
                    context=context,
                    server_player_id=server_player_id,
                    base_probability_player_a=game_prob_a,
                    efforts=efforts,
                    stamina_states=stamina_states,
                    calibration=rally_calibration,
                    terminal_roll=terminal_roll,
                    rng=detail_rng.branch(SeedScope.MATCH, "hidden-control"),
                )
            else:
                rally_winner = (
                    player_a_id if terminal_roll < game_prob_a else player_b_id
                )
                trigger, attribution, segments, shots, elapsed = self._rally_detail(
                    rng=detail_rng,
                    server_player_id=server_player_id,
                    winner_player_id=rally_winner,
                )
                completed_efforts = (
                    tuple(
                        self._complete_rally_effort(
                            effort=effort,
                            base_workload=MatchStaminaLog.workload_from_detail(
                                elapsed_seconds=elapsed,
                                estimated_shot_count=shots,
                                abstract_segments=segments,
                            ),
                            won_rally=effort.player_id == rally_winner,
                            attribution=attribution,
                        )
                        for effort in efforts
                    )
                    if efforts is not None
                    else None
                )

            if rally_winner == player_a_id:
                games_a += 1
            else:
                games_b += 1

            if control_trace is not None:
                segments = control_trace.control_segment_count
                shots = control_trace.estimated_shot_count
                elapsed = control_trace.active_rally_duration

            set_complete = self._set_finished(
                games_a, games_b, context.games_to, context.win_by
            )
            projected_sets_a = sets_won[player_a_id] + (
                1 if set_complete and games_a > games_b else 0
            )
            projected_sets_b = sets_won[player_b_id] + (
                1 if set_complete and games_b > games_a else 0
            )
            score_after = RallyScoreSnapshot(
                player_a_id=player_a_id,
                player_b_id=player_b_id,
                sets_a=projected_sets_a,
                sets_b=projected_sets_b,
                points_a=games_a,
                points_b=games_b,
            )
            effort_context = None
            player_workloads = None
            if completed_efforts is not None:
                base_workload = MatchStaminaLog.workload_from_detail(
                    elapsed_seconds=elapsed,
                    estimated_shot_count=shots,
                    abstract_segments=segments,
                )
                effort_context = RallyEffortContext(
                    base_workload_units=base_workload,
                    probability_before_effort_player_a=(
                        stamina_outcome.adjusted_probability_player_a
                    ),
                    probability_after_effort_player_a=game_prob_a,
                    player_efforts=completed_efforts,
                )
                player_workloads = {
                    effort.player_id: effort.workload_units
                    for effort in completed_efforts
                }
            event = RallyEvent.create(
                schema_version=(
                    "rally_event.v4"
                    if control_trace is not None
                    else "rally_event.v3"
                    if effort_context is not None
                    else "rally_event.v2"
                ),
                match_id=context.match_id,
                rally_index=rally_index,
                set_number=set_number,
                rally_in_set=rally_in_set,
                serving_player_id=server_player_id,
                winner_player_id=rally_winner,
                primary_terminal_trigger=trigger,
                analytical_attribution=attribution,
                score_before=score_before,
                score_mutations=(RallyScoreMutation(player_id=rally_winner),),
                score_after=score_after,
                abstract_segments=segments,
                estimated_shot_count=shots,
                elapsed_seconds=elapsed,
                rally_seed=str(detail_rng.seed.value),
                post_rally_state=PostRallyStateSnapshot(
                    score=score_after,
                    next_server_player_id=rally_winner,
                    set_complete=set_complete,
                    match_complete=set_complete
                    and max(projected_sets_a, projected_sets_b) >= target_sets,
                    unsupported_dynamic_state=("mental_stamina",),
                ),
                stamina_outcome_context=stamina_outcome,
                effort_context=effort_context,
                control_trace=control_trace,
                previous_event_hash=previous_event_hash,
            )
            rally_events.append(event)
            _, stamina_states = MatchStaminaLog.advance_states(
                effective=stamina,
                states=stamina_states,
                cause=StaminaTransitionCause.RALLY_WORKLOAD,
                elapsed_seconds=event.elapsed_seconds,
                workload_units=MatchStaminaLog.rally_workload(event),
                player_workload_units=player_workloads,
            )
            if not set_complete:
                interval = self._between_rally_interval(
                    context=context,
                    timing=timing,
                    previous_rally=event,
                    interval_rng=timeline_rng.branch(
                        SeedScope.MATCH, "between-rally", event.rally_index
                    ),
                    timeline_index=event.rally_index * 2,
                    previous_event_hash="0" * 64,
                )
                _, stamina_states = MatchStaminaLog.advance_states(
                    effective=stamina,
                    states=stamina_states,
                    cause=StaminaTransitionCause.BETWEEN_RALLY_RECOVERY,
                    elapsed_seconds=interval.elapsed_seconds,
                    workload_units=0.0,
                )
            previous_event_hash = event.event_hash
            server_player_id = rally_winner
            rally_index += 1
            rally_in_set += 1

        winner_id = player_a_id if games_a > games_b else player_b_id
        loser_id = player_b_id if winner_id == player_a_id else player_a_id
        winner_games = games_a if winner_id == player_a_id else games_b
        loser_games = games_b if winner_id == player_a_id else games_a

        return (
            winner_id,
            SetResult(
                set_number=set_number,
                winner_player_id=winner_id,
                loser_player_id=loser_id,
                winner_games=winner_games,
                loser_games=loser_games,
                was_close_endgame=was_close_endgame,
                ended_by_retirement=False,
            ),
            rally_events,
            rally_index,
            server_player_id,
            stamina_states,
        )

    def _build_timeline(
        self,
        *,
        context: MatchContext,
        match_rng: DeterministicRng,
        rally_log: MatchRallyLog,
        timing: EffectiveMatchTimingSnapshot,
        termination_reason: MatchTerminationReason,
        retired_at_set_start: int | None,
    ) -> MatchTimelineLog:
        """Build time truth from an isolated RNG branch after scoring is complete."""

        timeline_events: list[MatchTimelineEvent] = []
        previous_hash = rally_log.input_snapshot_hash
        timeline_rng = match_rng.branch(SeedScope.MATCH, "timeline-v1")

        for position, rally in enumerate(rally_log.events):
            marker = RallyTimelineEvent.create(
                match_id=context.match_id,
                timeline_index=len(timeline_events) + 1,
                rally_index=rally.rally_index,
                set_number=rally.set_number,
                rally_event_hash=rally.event_hash,
                elapsed_seconds=rally.elapsed_seconds,
                previous_event_hash=previous_hash,
            )
            timeline_events.append(marker)
            previous_hash = marker.event_hash

            next_rally = (
                rally_log.events[position + 1]
                if position + 1 < len(rally_log.events)
                else None
            )
            if next_rally is not None and next_rally.set_number == rally.set_number:
                interval = self._between_rally_interval(
                    context=context,
                    timing=timing,
                    previous_rally=rally,
                    interval_rng=timeline_rng.branch(
                        SeedScope.MATCH, "between-rally", rally.rally_index
                    ),
                    timeline_index=len(timeline_events) + 1,
                    previous_event_hash=previous_hash,
                )
                timeline_events.append(interval)
                previous_hash = interval.event_hash
            elif next_rally is not None or (
                termination_reason == MatchTerminationReason.RETIREMENT
                and retired_at_set_start is not None
                and retired_at_set_start > rally.set_number
            ):
                game_break = self._game_break_event(
                    context=context,
                    timing=timing,
                    previous_rally=rally,
                    timeline_index=len(timeline_events) + 1,
                    previous_event_hash=previous_hash,
                )
                timeline_events.append(game_break)
                previous_hash = game_break.event_hash

        return MatchTimelineLog.create(
            match_id=context.match_id,
            input_snapshot_hash=rally_log.input_snapshot_hash,
            events=timeline_events,
            dynamic_stamina_recovery=True,
        )

    def _between_rally_interval(
        self,
        *,
        context: MatchContext,
        timing: EffectiveMatchTimingSnapshot,
        previous_rally: RallyEvent,
        interval_rng: DeterministicRng,
        timeline_index: int,
        previous_event_hash: str,
    ) -> BetweenRallyIntervalEvent:
        player_a_id = context.player_a.player.player_id
        player_b_id = context.player_b.player.player_id
        server_player_id = previous_rally.winner_player_id
        receiver_player_id = (
            player_b_id if server_player_id == player_a_id else player_a_id
        )
        server_profile = timing.profile_for(server_player_id)
        receiver_profile = timing.profile_for(receiver_player_id)
        server_intent, server_factors = self._sample_restart_intent(
            rng=interval_rng.branch(SeedScope.MATCH, "server-intent"),
            tendency=server_profile.serve_tendency,
            previous_rally=previous_rally,
            games_to=context.games_to,
        )
        receiver_intent, receiver_factors = self._sample_restart_intent(
            rng=interval_rng.branch(SeedScope.MATCH, "receiver-intent"),
            tendency=receiver_profile.return_tendency,
            previous_rally=previous_rally,
            games_to=context.games_to,
        )
        server_ready = self._player_ready_seconds(
            rng=interval_rng.branch(SeedScope.MATCH, "server-ready"),
            intent=server_intent,
            previous_rally=previous_rally,
            role="server",
        )
        receiver_ready = self._player_ready_seconds(
            rng=interval_rng.branch(SeedScope.MATCH, "receiver-ready"),
            intent=receiver_intent,
            previous_rally=previous_rally,
            role="receiver",
        )
        official_ready = round(
            interval_rng.branch(SeedScope.MATCH, "official-ready").uniform(5.5, 9.5),
            3,
        )
        court_ready = round(
            interval_rng.branch(SeedScope.MATCH, "court-ready").uniform(4.0, 8.5),
            3,
        )
        readiness = {
            ReadinessComponent.SERVER: server_ready,
            ReadinessComponent.RECEIVER: receiver_ready,
            ReadinessComponent.OFFICIAL: official_ready,
            ReadinessComponent.COURT: court_ready,
        }
        dominant = max(readiness, key=readiness.__getitem__)
        return BetweenRallyIntervalEvent.create(
            match_id=context.match_id,
            timeline_index=timeline_index,
            after_rally_index=previous_rally.rally_index,
            set_number=previous_rally.set_number,
            server_player_id=server_player_id,
            receiver_player_id=receiver_player_id,
            server_intent=server_intent,
            receiver_intent=receiver_intent,
            server_decision_factors=server_factors,
            receiver_decision_factors=receiver_factors,
            server_ready_seconds=server_ready,
            receiver_ready_seconds=receiver_ready,
            official_ready_seconds=official_ready,
            court_ready_seconds=court_ready,
            dominant_readiness=dominant,
            elapsed_seconds=round(max(readiness.values()), 3),
            interval_seed=str(interval_rng.seed.value),
            previous_event_hash=previous_event_hash,
        )

    @staticmethod
    def _game_break_event(
        *,
        context: MatchContext,
        timing: EffectiveMatchTimingSnapshot,
        previous_rally: RallyEvent,
        timeline_index: int,
        previous_event_hash: str,
    ) -> GameBreakEvent:
        return GameBreakEvent.create(
            match_id=context.match_id,
            timeline_index=timeline_index,
            after_rally_index=previous_rally.rally_index,
            completed_set_number=previous_rally.set_number,
            nominal_seconds=timing.nominal_game_break_seconds,
            elapsed_seconds=timing.nominal_game_break_seconds,
            dynamic_recovery_applied=True,
            previous_event_hash=previous_event_hash,
        )

    @staticmethod
    def _sample_restart_intent(
        *,
        rng: DeterministicRng,
        tendency: RestartIntent,
        previous_rally: RallyEvent,
        games_to: int,
    ) -> tuple[RestartIntent, tuple[RestartDecisionFactor, ...]]:
        factors = [RestartDecisionFactor.NATURAL_TENDENCY]
        weights = {
            RestartIntent.ACCELERATE: 0.18,
            RestartIntent.NATURAL: 0.64,
            RestartIntent.DELAY: 0.18,
        }
        weights[tendency] += 0.32
        weights[RestartIntent.NATURAL] -= 0.16
        opposite = (
            RestartIntent.DELAY
            if tendency == RestartIntent.ACCELERATE
            else RestartIntent.ACCELERATE
        )
        if tendency != RestartIntent.NATURAL:
            weights[opposite] -= 0.16

        physically_demanding = (
            previous_rally.elapsed_seconds >= 16
            or previous_rally.estimated_shot_count >= 24
        )
        score = previous_rally.score_after
        close_endgame = (
            max(score.points_a, score.points_b) >= games_to - 2
            and abs(score.points_a - score.points_b) <= 2
        )
        recovery_shift = 0.0
        if physically_demanding:
            recovery_shift += 0.12
            factors.append(RestartDecisionFactor.PREVIOUS_RALLY_LOAD)
        if close_endgame:
            recovery_shift += 0.05
            factors.append(RestartDecisionFactor.CLOSE_ENDGAME)
        if recovery_shift:
            weights[RestartIntent.DELAY] += recovery_shift
            weights[RestartIntent.NATURAL] -= recovery_shift

        roll = rng.random()
        total = sum(weights.values())
        cumulative = 0.0
        for intent in (
            RestartIntent.ACCELERATE,
            RestartIntent.NATURAL,
            RestartIntent.DELAY,
        ):
            cumulative += weights[intent] / total
            if roll < cumulative:
                return intent, tuple(factors)
        return RestartIntent.DELAY, tuple(factors)

    @staticmethod
    def _player_ready_seconds(
        *,
        rng: DeterministicRng,
        intent: RestartIntent,
        previous_rally: RallyEvent,
        role: str,
    ) -> float:
        lower, upper = (7.5, 13.0) if role == "server" else (8.0, 13.5)
        base = rng.uniform(lower, upper)
        workload_delay = min(
            3.0,
            max(0.0, previous_rally.elapsed_seconds - 8.0) * 0.06
            + max(0, previous_rally.estimated_shot_count - 12) * 0.045,
        )
        intent_adjustment = {
            RestartIntent.ACCELERATE: -1.8,
            RestartIntent.NATURAL: 0.0,
            RestartIntent.DELAY: 2.4,
        }[intent]
        return round(
            MatchEngine._clamp(
                base + workload_delay + intent_adjustment,
                5.0,
                22.0,
            ),
            3,
        )

    @staticmethod
    def _base_strength(participant: MatchParticipantContext) -> float:
        p = participant.player
        weighted = (
            p.technique * 0.21
            + p.movement * 0.18
            + p.physical * 0.14
            + p.mental * 0.14
            + p.consistency * 0.12
            + p.clutch * 0.11
            + p.recovery * 0.10
        ) / 99.0
        modifiers = (
            participant.form_modifier * 0.35
            + participant.fatigue_modifier * 0.3
            + participant.health_modifier * 0.25
            + participant.travel_modifier * 0.1
        )
        return weighted + modifiers

    @staticmethod
    def _style_and_archetype_adjustment(
        style_a: str,
        style_b: str,
        archetype_a: str,
        archetype_b: str,
    ) -> tuple[float, float]:
        adj_a = MatchEngine.STYLE_MATCHUP_EDGES.get(
            (style_a, style_b), 0.0
        ) + MatchEngine.ARCHETYPE_MATCHUP_EDGES.get(
            (archetype_a, archetype_b),
            0.0,
        )
        return adj_a, -adj_a

    @staticmethod
    def _set_finished(games_a: int, games_b: int, games_to: int, win_by: int) -> bool:
        return (games_a >= games_to or games_b >= games_to) and abs(
            games_a - games_b
        ) >= win_by

    @staticmethod
    def _clamp(value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    @classmethod
    def _select_rally_effort(
        cls,
        *,
        participant: MatchParticipantContext,
        state: PlayerStaminaState,
        own_points: int,
        opponent_points: int,
        games_to: int,
        rng: DeterministicRng,
    ) -> PlayerRallyEffort:
        """Choose an imperfect pre-rally effort intent from information the player has."""

        player = participant.player
        # Explicit pre-alpha calibration only: the Master fixes the four choices and
        # limited perception, while leaving their exact decision mathematics open.
        actual_reserve = (
            state.current(StaminaDimension.EXPLOSIVE)
            / next(
                bar.capacity
                for bar in state.bars
                if bar.dimension == StaminaDimension.EXPLOSIVE
            )
            * 0.45
            + state.current(StaminaDimension.RALLY)
            / next(
                bar.capacity
                for bar in state.bars
                if bar.dimension == StaminaDimension.RALLY
            )
            * 0.35
            + state.current(StaminaDimension.MATCH)
            / next(
                bar.capacity
                for bar in state.bars
                if bar.dimension == StaminaDimension.MATCH
            )
            * 0.20
        )
        perception_error = 0.085 - player.mental / 99.0 * 0.045
        perceived_reserve = round(
            cls._clamp(
                actual_reserve + rng.uniform(-perception_error, perception_error),
                0.0,
                1.0,
            ),
            8,
        )

        factors = [RallyEffortDecisionFactor.NATURAL_STYLE]
        score = {
            "attacking": 0.35,
            "retrieving": 0.20,
            "front-court": 0.20,
            "counter-punching": 0.05,
            "tempo-controller": -0.10,
        }.get(player.play_style, 0.0)
        if perceived_reserve < 0.38:
            score -= 0.85
            factors.append(RallyEffortDecisionFactor.PERCEIVED_LOW_RESERVE)
        elif perceived_reserve < 0.58:
            score -= 0.35
            factors.append(RallyEffortDecisionFactor.PERCEIVED_LOW_RESERVE)

        close_endgame = (
            own_points >= games_to - 2
            and opponent_points >= games_to - 2
            and abs(own_points - opponent_points) <= 2
        )
        if close_endgame:
            score += 0.65
            factors.append(RallyEffortDecisionFactor.CLOSE_ENDGAME)
        elif own_points <= opponent_points - 3:
            score += 0.35
            factors.append(RallyEffortDecisionFactor.TRAILING_SCORE)
        elif own_points >= opponent_points + 4:
            score -= 0.25
            factors.append(RallyEffortDecisionFactor.LEADING_SCORE)

        tactical_noise = rng.uniform(-0.38, 0.38)
        score += tactical_noise
        if abs(tactical_noise) >= 0.25:
            factors.append(RallyEffortDecisionFactor.TACTICAL_VARIATION)

        if score < -0.45:
            level = RallyEffortLevel.CONSERVE
        elif score < 0.45:
            level = RallyEffortLevel.NORMAL
        elif score < 0.95:
            level = RallyEffortLevel.INCREASED
        else:
            level = RallyEffortLevel.MAXIMUM

        requested = {
            RallyEffortLevel.CONSERVE: 0.78,
            RallyEffortLevel.NORMAL: 1.00,
            RallyEffortLevel.INCREASED: 1.16,
            RallyEffortLevel.MAXIMUM: 1.32,
        }[level]
        physical_execution = cls._clamp(
            0.45 + actual_reserve * 0.40 + player.physical / 99.0 * 0.15,
            0.45,
            1.0,
        )
        executed = (
            1.0 + (requested - 1.0) * physical_execution
            if requested > 1.0
            else requested
        )
        movement_efficiency = cls._clamp(
            1.12 - player.movement / 450.0 - player.physical / 900.0,
            0.82,
            1.12,
        )
        style_workload = {
            "attacking": 1.05,
            "retrieving": 1.10,
            "front-court": 1.02,
            "counter-punching": 0.98,
            "tempo-controller": 0.94,
        }.get(player.play_style, 1.0)
        outcome_adjustment = (executed - 1.0) * 0.10
        return PlayerRallyEffort(
            player_id=player.player_id,
            intended_level=level,
            decision_factors=tuple(factors),
            perceived_reserve=perceived_reserve,
            requested_intensity_multiplier=round(requested, 8),
            executed_intensity_multiplier=round(executed, 8),
            outcome_strength_adjustment=round(outcome_adjustment, 8),
            movement_efficiency_factor=round(movement_efficiency, 8),
            style_workload_factor=round(style_workload, 8),
            pressure_workload_factor=1.0,
            workload_units=0.0,
        )

    @staticmethod
    def _complete_rally_effort(
        *,
        effort: PlayerRallyEffort,
        base_workload: float,
        won_rally: bool,
        attribution: RallyAnalyticalAttribution,
    ) -> PlayerRallyEffort:
        # Until hidden control states are active, the terminal result is a bounded
        # proxy for who carried more pressure load; it is logged and replaceable.
        pressure_factor = 0.96 if won_rally else 1.08
        if not won_rally and attribution == RallyAnalyticalAttribution.FORCED_ERROR:
            pressure_factor += 0.05
        workload = (
            base_workload
            * effort.executed_intensity_multiplier
            * effort.movement_efficiency_factor
            * effort.style_workload_factor
            * pressure_factor
        )
        return effort.model_copy(
            update={
                "pressure_workload_factor": round(pressure_factor, 8),
                "workload_units": round(workload, 4),
            }
        )

    @classmethod
    def _simulate_hidden_control_rally(
        cls,
        *,
        context: MatchContext,
        server_player_id: str,
        base_probability_player_a: float,
        efforts: tuple[PlayerRallyEffort, PlayerRallyEffort],
        stamina_states: tuple[PlayerStaminaState, PlayerStaminaState],
        calibration: RallyCalibrationProfile,
        terminal_roll: float,
        rng: DeterministicRng,
    ) -> tuple[
        str,
        RallyTerminalTrigger,
        RallyAnalyticalAttribution,
        RallyControlTrace,
        tuple[PlayerRallyEffort, PlayerRallyEffort],
    ]:
        """Create one causal opening -> control -> terminal rally truth."""

        participants = (context.player_a, context.player_b)
        player_ids = tuple(participant.player.player_id for participant in participants)
        if tuple(effort.player_id for effort in efforts) != player_ids:
            raise ValueError("rally efforts must use match participant order")
        if tuple(state.player_id for state in stamina_states) != player_ids:
            raise ValueError("rally stamina must use match participant order")
        if server_player_id not in player_ids:
            raise ValueError("rally server must be a match participant")

        opening_rng = rng.branch(SeedScope.MATCH, "opening")
        opening_state = cls._opening_control_state(
            context=context,
            server_player_id=server_player_id,
            base_probability_player_a=base_probability_player_a,
            rng=opening_rng.branch(SeedScope.MATCH, "control"),
        )
        current_levels = [effort.intended_level for effort in efforts]
        actual_reserves = [cls._stamina_reserve(state) for state in stamina_states]
        opening_terminal_probability = round(
            cls._clamp(
                calibration.opening_terminal_probability
                * (
                    0.92
                    + 0.08
                    * sum(effort.executed_intensity_multiplier for effort in efforts)
                    / 2.0
                ),
                0.03,
                0.16,
            ),
            8,
        )
        opening_terminal_roll = opening_rng.branch(SeedScope.MATCH, "closure").random()

        opening_shots = 2
        opening_duration_range = calibration.opening_elapsed_seconds_range
        opening_elapsed = round(
            opening_rng.branch(SeedScope.MATCH, "duration").uniform(
                *opening_duration_range
            ),
            3,
        )
        opening_base_workload = 0.22 + opening_elapsed * 0.04 + opening_shots * 0.025
        opening_workloads: list[float] = []
        pressure_samples: list[list[tuple[float, float]]] = [[], []]
        for player_index, effort in enumerate(efforts):
            pressure_factor = cls._control_pressure_factor(
                state_value=float(cls.CONTROL_VALUE[opening_state]),
                player_index=player_index,
                calibration=calibration,
            )
            opening_workload = round(
                opening_base_workload
                * effort.executed_intensity_multiplier
                * effort.movement_efficiency_factor
                * effort.style_workload_factor
                * pressure_factor,
                4,
            )
            opening_workloads.append(opening_workload)
            pressure_samples[player_index].append(
                (pressure_factor, opening_base_workload)
            )

        if opening_terminal_roll < opening_terminal_probability:
            terminal_probability = cls._terminal_control_probability(
                base_probability_player_a=base_probability_player_a,
                final_state=opening_state,
                mean_control_value=float(cls.CONTROL_VALUE[opening_state]),
                calibration=calibration,
            )
            winner_player_id = (
                player_ids[0] if terminal_roll < terminal_probability else player_ids[1]
            )
            cause_rng = rng.branch(SeedScope.MATCH, "terminal", "cause")
            if winner_player_id != server_player_id and cause_rng.random() < 0.22:
                trigger = RallyTerminalTrigger.SERVE_FAULT
                attribution = RallyAnalyticalAttribution.UNFORCED_ERROR
                opening_shots = 1
                serve_fault_duration_range = (
                    calibration.serve_fault_elapsed_seconds_range
                )
                opening_elapsed = round(
                    opening_rng.branch(SeedScope.MATCH, "serve-fault-duration").uniform(
                        *serve_fault_duration_range
                    ),
                    3,
                )
                opening_base_workload = (
                    0.22 + opening_elapsed * 0.04 + opening_shots * 0.025
                )
                opening_workloads = []
                pressure_samples = [[], []]
                for player_index, effort in enumerate(efforts):
                    pressure_factor = cls._control_pressure_factor(
                        state_value=float(cls.CONTROL_VALUE[opening_state]),
                        player_index=player_index,
                        calibration=calibration,
                    )
                    opening_workloads.append(
                        round(
                            opening_base_workload
                            * effort.executed_intensity_multiplier
                            * effort.movement_efficiency_factor
                            * effort.style_workload_factor
                            * pressure_factor,
                            4,
                        )
                    )
                    pressure_samples[player_index].append(
                        (pressure_factor, opening_base_workload)
                    )
            else:
                trigger = RallyTerminalTrigger.GOOD_RETURN_UNANSWERED
                attribution = RallyAnalyticalAttribution.CLEAN_WINNER

            control_workloads, completed_efforts = cls._complete_control_workloads(
                efforts=efforts,
                opening_workloads=tuple(opening_workloads),
                segments=(),
                terminal_workloads=(0.0, 0.0),
                pressure_samples=pressure_samples,
            )
            trace = RallyControlTrace(
                calibration_version=calibration.calibration_version,
                trace_seed=str(rng.seed.value),
                opening_state=opening_state,
                opening_terminal_probability=opening_terminal_probability,
                opening_terminal_roll=opening_terminal_roll,
                segments=(),
                final_state=opening_state,
                closure_reason=RallyClosureReason.OPENING_TERMINAL,
                control_segment_count=0,
                opening_shot_count=opening_shots,
                terminal_shot_count=0,
                estimated_shot_count=opening_shots,
                opening_elapsed_seconds=opening_elapsed,
                terminal_elapsed_seconds=0.0,
                active_rally_duration=opening_elapsed,
                probability_before_control_player_a=base_probability_player_a,
                terminal_probability_player_a=terminal_probability,
                terminal_roll=terminal_roll,
                player_workloads=control_workloads,
            )
            return (
                winner_player_id,
                trigger,
                attribution,
                trace,
                completed_efforts,
            )

        segments: list[RallyControlSegment] = []
        cumulative_workloads = list(opening_workloads)
        current_state = opening_state
        for segment_index in range(1, calibration.maximum_control_segments + 1):
            segment_rng = rng.branch(SeedScope.MATCH, "segment", segment_index)
            effort_changes: list[RallyEffortChange] = []
            for player_index, participant in enumerate(participants):
                perceived_reserve = cls._clamp(
                    efforts[player_index].perceived_reserve
                    - cumulative_workloads[player_index] * 0.018,
                    0.0,
                    1.0,
                )
                next_level, change = cls._within_rally_effort_change(
                    participant=participant,
                    player_index=player_index,
                    control_state=current_state,
                    current_level=current_levels[player_index],
                    perceived_reserve=perceived_reserve,
                    calibration=calibration,
                    rng=segment_rng.branch(
                        SeedScope.MATCH,
                        "effort",
                        participant.player.player_id,
                    ),
                )
                current_levels[player_index] = next_level
                if change is not None:
                    effort_changes.append(change)

            intensities = tuple(
                cls._executed_effort_intensity(
                    level=current_levels[player_index],
                    actual_reserve=cls._clamp(
                        actual_reserves[player_index]
                        - cumulative_workloads[player_index] * 0.012,
                        0.0,
                        1.0,
                    ),
                    physical=participants[player_index].player.physical,
                )
                for player_index in range(2)
            )
            next_state = cls._next_control_state(
                current_state=current_state,
                base_probability_player_a=base_probability_player_a,
                intensity_a=intensities[0],
                intensity_b=intensities[1],
                calibration=calibration,
                rng=segment_rng.branch(SeedScope.MATCH, "transition"),
            )
            transition_distance = abs(
                cls.CONTROL_VALUE[next_state] - cls.CONTROL_VALUE[current_state]
            )
            transition_kind = (
                RallyControlTransitionKind.STAY
                if transition_distance == 0
                else RallyControlTransitionKind.LOCAL_SHIFT
                if transition_distance == 1
                else RallyControlTransitionKind.DIRECT_REVERSAL
                if transition_distance == 4
                else RallyControlTransitionKind.SIGNIFICANT_BREAK
            )
            pace = cls._rally_phase_pace(
                participants=participants,
                intensities=intensities,
                rng=segment_rng.branch(SeedScope.MATCH, "pace"),
            )
            segment_shots = cls._segment_shot_count(
                pace=pace,
                calibration=calibration,
                rng=segment_rng.branch(SeedScope.MATCH, "shots"),
            )
            segment_elapsed = cls._segment_elapsed_seconds(
                pace=pace,
                estimated_shot_count=segment_shots,
                calibration=calibration,
                rng=segment_rng.branch(SeedScope.MATCH, "duration"),
            )
            segment_base_workload = (
                0.055 + segment_elapsed * 0.045 + segment_shots * 0.022
            )
            mean_state_value = (
                cls.CONTROL_VALUE[current_state] + cls.CONTROL_VALUE[next_state]
            ) / 2.0
            segment_player_workloads: list[PlayerControlSegmentWorkload] = []
            for player_index, effort in enumerate(efforts):
                pressure_factor = cls._control_pressure_factor(
                    state_value=mean_state_value,
                    player_index=player_index,
                    calibration=calibration,
                )
                workload_units = round(
                    segment_base_workload
                    * intensities[player_index]
                    * effort.movement_efficiency_factor
                    * effort.style_workload_factor
                    * pressure_factor,
                    4,
                )
                cumulative_workloads[player_index] += workload_units
                pressure_samples[player_index].append(
                    (pressure_factor, segment_base_workload)
                )
                segment_player_workloads.append(
                    PlayerControlSegmentWorkload(
                        player_id=player_ids[player_index],
                        effort_level=current_levels[player_index],
                        intensity_multiplier=intensities[player_index],
                        control_pressure_factor=round(pressure_factor, 8),
                        workload_units=workload_units,
                    )
                )

            closure_probability = cls._segment_closure_probability(
                segment_index=segment_index,
                control_state=next_state,
                pace=pace,
                mean_intensity=sum(intensities) / 2.0,
                calibration=calibration,
            )
            closure_roll = segment_rng.branch(SeedScope.MATCH, "closure").random()
            closed_rally = closure_roll < closure_probability
            segment = RallyControlSegment(
                segment_index=segment_index,
                state_before=current_state,
                state_after=next_state,
                transition_kind=transition_kind,
                phase_pace=pace,
                estimated_shot_count=segment_shots,
                elapsed_seconds=segment_elapsed,
                closure_probability=closure_probability,
                closure_roll=closure_roll,
                closed_rally=closed_rally,
                effort_changes=tuple(effort_changes),
                player_workloads=tuple(segment_player_workloads),
            )
            segments.append(segment)
            current_state = next_state
            if closed_rally:
                closure_reason = (
                    RallyClosureReason.HARD_SEGMENT_CAP
                    if segment_index == calibration.maximum_control_segments
                    else RallyClosureReason.NATURAL_TERMINAL
                )
                break
        else:  # pragma: no cover - segment 24 is forced closed by calibration logic.
            raise RuntimeError("hidden rally control exceeded its hard segment cap")

        control_weight = opening_shots + sum(
            segment.estimated_shot_count for segment in segments
        )
        mean_control_value = (
            cls.CONTROL_VALUE[opening_state] * opening_shots
            + sum(
                cls.CONTROL_VALUE[segment.state_after] * segment.estimated_shot_count
                for segment in segments
            )
        ) / control_weight
        terminal_probability = cls._terminal_control_probability(
            base_probability_player_a=base_probability_player_a,
            final_state=current_state,
            mean_control_value=mean_control_value,
            calibration=calibration,
        )
        terminal_rng = rng.branch(SeedScope.MATCH, "terminal")
        winner_player_id = (
            player_ids[0] if terminal_roll < terminal_probability else player_ids[1]
        )
        trigger, attribution = cls._control_terminal_detail(
            final_state=current_state,
            winner_player_id=winner_player_id,
            player_a_id=player_ids[0],
            rng=terminal_rng.branch(SeedScope.MATCH, "cause"),
        )
        terminal_shots = 1
        terminal_duration_range = calibration.terminal_elapsed_seconds_range
        terminal_elapsed = round(
            terminal_rng.branch(SeedScope.MATCH, "duration").uniform(
                *terminal_duration_range
            ),
            3,
        )
        terminal_base_workload = 0.075 + terminal_elapsed * 0.04 + 0.025
        terminal_workloads: list[float] = []
        for player_index, effort in enumerate(efforts):
            pressure_factor = cls._control_pressure_factor(
                state_value=float(cls.CONTROL_VALUE[current_state]),
                player_index=player_index,
                calibration=calibration,
            )
            terminal_workload = round(
                terminal_base_workload
                * cls._executed_effort_intensity(
                    level=current_levels[player_index],
                    actual_reserve=cls._clamp(
                        actual_reserves[player_index]
                        - cumulative_workloads[player_index] * 0.012,
                        0.0,
                        1.0,
                    ),
                    physical=participants[player_index].player.physical,
                )
                * effort.movement_efficiency_factor
                * effort.style_workload_factor
                * pressure_factor,
                4,
            )
            terminal_workloads.append(terminal_workload)
            pressure_samples[player_index].append(
                (pressure_factor, terminal_base_workload)
            )

        control_workloads, completed_efforts = cls._complete_control_workloads(
            efforts=efforts,
            opening_workloads=tuple(opening_workloads),
            segments=tuple(segments),
            terminal_workloads=tuple(terminal_workloads),
            pressure_samples=pressure_samples,
        )
        estimated_shots = (
            opening_shots
            + sum(segment.estimated_shot_count for segment in segments)
            + terminal_shots
        )
        active_duration = round(
            opening_elapsed
            + sum(segment.elapsed_seconds for segment in segments)
            + terminal_elapsed,
            3,
        )
        trace = RallyControlTrace(
            calibration_version=calibration.calibration_version,
            trace_seed=str(rng.seed.value),
            opening_state=opening_state,
            opening_terminal_probability=opening_terminal_probability,
            opening_terminal_roll=opening_terminal_roll,
            segments=tuple(segments),
            final_state=current_state,
            closure_reason=closure_reason,
            control_segment_count=len(segments),
            opening_shot_count=opening_shots,
            terminal_shot_count=terminal_shots,
            estimated_shot_count=estimated_shots,
            opening_elapsed_seconds=opening_elapsed,
            terminal_elapsed_seconds=terminal_elapsed,
            active_rally_duration=active_duration,
            probability_before_control_player_a=base_probability_player_a,
            terminal_probability_player_a=terminal_probability,
            terminal_roll=terminal_roll,
            player_workloads=control_workloads,
        )
        return (
            winner_player_id,
            trigger,
            attribution,
            trace,
            completed_efforts,
        )

    @classmethod
    def _opening_control_state(
        cls,
        *,
        context: MatchContext,
        server_player_id: str,
        base_probability_player_a: float,
        rng: DeterministicRng,
    ) -> RallyControlState:
        player_a = context.player_a.player
        player_b = context.player_b.player
        server = player_a if server_player_id == player_a.player_id else player_b
        receiver = player_b if server is player_a else player_a
        serve_execution = (
            server.technique * 0.62 + server.consistency * 0.23 + server.mental * 0.15
        ) / 99.0
        return_execution = (
            receiver.technique * 0.48
            + receiver.movement * 0.32
            + receiver.consistency * 0.20
        ) / 99.0
        role_edge_for_a = serve_execution - return_execution
        if server.player_id != player_a.player_id:
            role_edge_for_a *= -1
        base_edge = cls._probability_logit(base_probability_player_a) / 5.0
        signal = base_edge + role_edge_for_a * 0.90 + rng.uniform(-0.68, 0.68)
        if signal >= 0.76:
            return RallyControlState.STRONG_CONTROL_A
        if signal >= 0.20:
            return RallyControlState.SLIGHT_CONTROL_A
        if signal > -0.20:
            return RallyControlState.NEUTRAL
        if signal > -0.76:
            return RallyControlState.SLIGHT_CONTROL_B
        return RallyControlState.STRONG_CONTROL_B

    @classmethod
    def _within_rally_effort_change(
        cls,
        *,
        participant: MatchParticipantContext,
        player_index: int,
        control_state: RallyControlState,
        current_level: RallyEffortLevel,
        perceived_reserve: float,
        calibration: RallyCalibrationProfile,
        rng: DeterministicRng,
    ) -> tuple[RallyEffortLevel, RallyEffortChange | None]:
        state_value = cls.CONTROL_VALUE[control_state]
        own_control = state_value if player_index == 0 else -state_value
        pressure = max(0, -own_control)
        level_index = cls.EFFORT_LEVELS.index(current_level)
        direction = 0
        reason: RallyEffortChangeReason | None = None
        decision_roll = rng.random()

        if perceived_reserve < 0.40 and level_index > 0:
            probability = calibration.low_reserve_effort_change_probability * (
                1.0 if perceived_reserve < 0.25 else 0.68
            )
            if decision_roll < probability:
                direction = -1
                reason = RallyEffortChangeReason.CONSERVE_LOW_RESERVE
        elif pressure > 0 and level_index < len(cls.EFFORT_LEVELS) - 1:
            probability = calibration.strong_pressure_effort_change_probability * (
                1.0 if pressure == 2 else 0.52
            )
            if decision_roll < probability:
                direction = 1
                reason = RallyEffortChangeReason.RESPOND_TO_PRESSURE
        elif own_control > 0 and level_index < len(cls.EFFORT_LEVELS) - 1:
            style_factor = (
                1.0
                if participant.player.play_style in {"attacking", "front-court"}
                else 0.48
            )
            probability = 0.13 * style_factor * (1.0 if own_control == 2 else 0.58)
            if decision_roll < probability:
                direction = 1
                reason = RallyEffortChangeReason.PRESS_CONTROL_ADVANTAGE

        if reason is None:
            tactical_probability = calibration.tactical_effort_change_probability * (
                0.72 + participant.player.mental / 99.0 * 0.56
            )
            if decision_roll < tactical_probability:
                prefer_up = pressure > 0 or participant.player.play_style in {
                    "attacking",
                    "front-court",
                }
                if perceived_reserve < 0.48:
                    prefer_up = False
                direction = 1 if prefer_up else -1
                if 0 <= level_index + direction < len(cls.EFFORT_LEVELS):
                    reason = RallyEffortChangeReason.TACTICAL_VARIATION

        if reason is None or direction == 0:
            return current_level, None
        next_level = cls.EFFORT_LEVELS[level_index + direction]
        return next_level, RallyEffortChange(
            player_id=participant.player.player_id,
            from_level=current_level,
            to_level=next_level,
            reason=reason,
        )

    @classmethod
    def _next_control_state(
        cls,
        *,
        current_state: RallyControlState,
        base_probability_player_a: float,
        intensity_a: float,
        intensity_b: float,
        calibration: RallyCalibrationProfile,
        rng: DeterministicRng,
    ) -> RallyControlState:
        current_value = cls.CONTROL_VALUE[current_state]
        base_drive = cls._probability_logit(base_probability_player_a) / 3.5
        effort_drive = (intensity_a - intensity_b) * 1.15
        direction_drive = cls._clamp(base_drive + effort_drive, -1.5, 1.5)
        weighted_states: list[tuple[RallyControlState, float]] = []
        for candidate_value in range(-2, 3):
            distance = abs(candidate_value - current_value)
            if distance == 0:
                weight = calibration.stay_transition_weight
            elif distance == 1:
                weight = calibration.local_transition_weight
            elif distance == 4:
                weight = calibration.direct_reversal_weight
            else:
                weight = calibration.significant_break_weight / ((distance - 1) ** 2)
            weight *= exp(
                candidate_value
                * direction_drive
                * calibration.transition_direction_log_weight
            )
            if candidate_value == current_value:
                weight *= 1.0 + abs(current_value) * 0.12
            weighted_states.append((cls.CONTROL_STATE[candidate_value], weight))
        return cls._weighted_control_state(rng=rng, weighted_states=weighted_states)

    @staticmethod
    def _weighted_control_state(
        *,
        rng: DeterministicRng,
        weighted_states: list[tuple[RallyControlState, float]],
    ) -> RallyControlState:
        total = sum(weight for _, weight in weighted_states)
        roll = rng.random() * total
        cumulative = 0.0
        for state, weight in weighted_states:
            cumulative += weight
            if roll < cumulative:
                return state
        return weighted_states[-1][0]

    @staticmethod
    def _rally_phase_pace(
        *,
        participants: tuple[MatchParticipantContext, MatchParticipantContext],
        intensities: tuple[float, float],
        rng: DeterministicRng,
    ) -> RallyPhasePace:
        style_pace = {
            "attacking": 0.10,
            "front-court": 0.08,
            "counter-punching": 0.00,
            "retrieving": -0.04,
            "tempo-controller": -0.08,
        }
        signal = (
            sum(intensities) / 2.0
            - 1.0
            + sum(
                style_pace.get(participant.player.play_style, 0.0)
                for participant in participants
            )
            / 2.0
            + rng.uniform(-0.15, 0.15)
        )
        if signal > 0.08:
            return RallyPhasePace.FAST
        if signal < -0.07:
            return RallyPhasePace.PATIENT
        return RallyPhasePace.BALANCED

    @staticmethod
    def _segment_shot_count(
        *,
        pace: RallyPhasePace,
        calibration: RallyCalibrationProfile,
        rng: DeterministicRng,
    ) -> int:
        thresholds = {
            RallyPhasePace.FAST: calibration.fast_segment_shot_cdf,
            RallyPhasePace.BALANCED: calibration.balanced_segment_shot_cdf,
            RallyPhasePace.PATIENT: calibration.patient_segment_shot_cdf,
        }[pace]
        roll = rng.random()
        for shots, threshold in enumerate(thresholds, start=1):
            if roll < threshold:
                return shots
        return 5

    @staticmethod
    def _segment_elapsed_seconds(
        *,
        pace: RallyPhasePace,
        estimated_shot_count: int,
        calibration: RallyCalibrationProfile,
        rng: DeterministicRng,
    ) -> float:
        lower, upper = {
            RallyPhasePace.FAST: calibration.fast_seconds_per_shot_range,
            RallyPhasePace.BALANCED: calibration.balanced_seconds_per_shot_range,
            RallyPhasePace.PATIENT: calibration.patient_seconds_per_shot_range,
        }[pace]
        seconds_per_shot = rng.uniform(lower, upper)
        return round(0.16 + estimated_shot_count * seconds_per_shot, 3)

    @classmethod
    def _segment_closure_probability(
        cls,
        *,
        segment_index: int,
        control_state: RallyControlState,
        pace: RallyPhasePace,
        mean_intensity: float,
        calibration: RallyCalibrationProfile,
    ) -> float:
        if segment_index == calibration.maximum_control_segments:
            return 1.0
        probability = (
            calibration.base_segment_closure_probability
            + (segment_index - 1) * calibration.early_closure_growth_per_segment
            + max(0, segment_index - calibration.late_closure_starts_after_segment)
            * calibration.late_closure_growth_per_segment
            + abs(cls.CONTROL_VALUE[control_state]) * 0.01
            - (0.008 if pace == RallyPhasePace.PATIENT else 0.0)
            + (mean_intensity - 1.0) * 0.035
        )
        return round(cls._clamp(probability, 0.035, 0.96), 8)

    @classmethod
    def _terminal_control_probability(
        cls,
        *,
        base_probability_player_a: float,
        final_state: RallyControlState,
        mean_control_value: float,
        calibration: RallyCalibrationProfile,
    ) -> float:
        base_logit = cls._probability_logit(base_probability_player_a)
        terminal_logit = (
            base_logit
            + cls.CONTROL_VALUE[final_state] * calibration.final_control_logit_weight
            + mean_control_value * calibration.mean_control_logit_weight
        )
        return round(cls._clamp(1.0 / (1.0 + exp(-terminal_logit)), 0.02, 0.98), 8)

    @classmethod
    def _control_terminal_detail(
        cls,
        *,
        final_state: RallyControlState,
        winner_player_id: str,
        player_a_id: str,
        rng: DeterministicRng,
    ) -> tuple[RallyTerminalTrigger, RallyAnalyticalAttribution]:
        winner_control = cls.CONTROL_VALUE[final_state]
        if winner_player_id != player_a_id:
            winner_control *= -1
        roll = rng.random()
        if winner_control >= 1 and roll < 0.30:
            return (
                RallyTerminalTrigger.GOOD_RETURN_UNANSWERED,
                RallyAnalyticalAttribution.CLEAN_WINNER,
            )
        trigger = rng.choice(
            [
                RallyTerminalTrigger.RETURN_DOWN,
                RallyTerminalTrigger.RETURN_OUT,
                RallyTerminalTrigger.RETURN_NOT_UP,
            ]
        )
        forced_probability = 0.70 if winner_control >= 1 else 0.48
        attribution = (
            RallyAnalyticalAttribution.FORCED_ERROR
            if rng.random() < forced_probability
            else RallyAnalyticalAttribution.UNFORCED_ERROR
        )
        return trigger, attribution

    @classmethod
    def _control_pressure_factor(
        cls,
        *,
        state_value: float,
        player_index: int,
        calibration: RallyCalibrationProfile,
    ) -> float:
        own_control = state_value if player_index == 0 else -state_value
        factor = (
            1.0
            + max(0.0, -own_control) * calibration.pressure_workload_per_control_step
            - max(0.0, own_control) * calibration.controlled_workload_relief_per_step
        )
        return cls._clamp(factor, 0.5, 1.5)

    @staticmethod
    def _stamina_reserve(state: PlayerStaminaState) -> float:
        fills = {bar.dimension: bar.current / bar.capacity for bar in state.bars}
        return (
            fills[StaminaDimension.EXPLOSIVE] * 0.45
            + fills[StaminaDimension.RALLY] * 0.35
            + fills[StaminaDimension.MATCH] * 0.20
        )

    @classmethod
    def _probability_logit(cls, probability: float) -> float:
        safe_probability = cls._clamp(probability, 0.00000001, 0.99999999)
        return log(safe_probability / (1.0 - safe_probability))

    @classmethod
    def _executed_effort_intensity(
        cls,
        *,
        level: RallyEffortLevel,
        actual_reserve: float,
        physical: int,
    ) -> float:
        requested = cls.EFFORT_REQUESTED_INTENSITY[level]
        physical_execution = cls._clamp(
            0.45 + actual_reserve * 0.40 + physical / 99.0 * 0.15,
            0.45,
            1.0,
        )
        executed = (
            1.0 + (requested - 1.0) * physical_execution
            if requested > 1.0
            else requested
        )
        return round(executed, 8)

    @staticmethod
    def _complete_control_workloads(
        *,
        efforts: tuple[PlayerRallyEffort, PlayerRallyEffort],
        opening_workloads: tuple[float, float],
        segments: tuple[RallyControlSegment, ...],
        terminal_workloads: tuple[float, float],
        pressure_samples: list[list[tuple[float, float]]],
    ) -> tuple[
        tuple[PlayerRallyControlWorkload, PlayerRallyControlWorkload],
        tuple[PlayerRallyEffort, PlayerRallyEffort],
    ]:
        control_workloads: list[PlayerRallyControlWorkload] = []
        completed_efforts: list[PlayerRallyEffort] = []
        for player_index, effort in enumerate(efforts):
            segment_workload = round(
                sum(
                    segment.player_workloads[player_index].workload_units
                    for segment in segments
                ),
                4,
            )
            sample_weight = sum(weight for _, weight in pressure_samples[player_index])
            mean_pressure = (
                sum(
                    pressure * weight
                    for pressure, weight in pressure_samples[player_index]
                )
                / sample_weight
                if sample_weight
                else 1.0
            )
            total_workload = round(
                opening_workloads[player_index]
                + segment_workload
                + terminal_workloads[player_index],
                4,
            )
            control_workloads.append(
                PlayerRallyControlWorkload(
                    player_id=effort.player_id,
                    opening_workload_units=opening_workloads[player_index],
                    segment_workload_units=segment_workload,
                    terminal_workload_units=terminal_workloads[player_index],
                    mean_control_pressure_factor=round(mean_pressure, 8),
                    total_workload_units=total_workload,
                )
            )
            completed_efforts.append(
                effort.model_copy(
                    update={
                        "pressure_workload_factor": round(mean_pressure, 8),
                        "workload_units": total_workload,
                    }
                )
            )
        return tuple(control_workloads), tuple(completed_efforts)

    def _game_probability(
        self,
        *,
        adjusted_a: float,
        adjusted_b: float,
        context: MatchContext,
        games_a: int,
        games_b: int,
        stamina: EffectiveMatchStaminaSnapshot,
        stamina_states: tuple[PlayerStaminaState, PlayerStaminaState],
        efforts: tuple[PlayerRallyEffort, PlayerRallyEffort] | None = None,
    ) -> tuple[float, RallyStaminaOutcomeContext]:
        strength_delta = adjusted_a - adjusted_b
        base_probability = 1.0 / (1.0 + exp(-(strength_delta * 5.1)))
        impact_a = self._stamina_impact(
            stamina_states[0], enabled=stamina.outcome_effect_applied
        )
        impact_b = self._stamina_impact(
            stamina_states[1], enabled=stamina.outcome_effect_applied
        )
        adjusted_probability = 1.0 / (
            1.0
            + exp(
                -(
                    (
                        strength_delta
                        - impact_a.strength_penalty
                        + impact_b.strength_penalty
                    )
                    * 5.1
                )
            )
        )

        close_phase = (
            games_a >= context.games_to - 2 and games_b >= context.games_to - 2
        )
        if close_phase:
            clutch_a = context.player_a.player.clutch / 99.0
            clutch_b = context.player_b.player.clutch / 99.0
            mental_a = context.player_a.player.mental / 99.0
            mental_b = context.player_b.player.mental / 99.0
            pressure_shift = ((clutch_a + mental_a) - (clutch_b + mental_b)) * 0.18
            base_probability += pressure_shift
            adjusted_probability += pressure_shift

        consistency_delta = (
            context.player_a.player.consistency - context.player_b.player.consistency
        ) / 99.0
        base_probability += consistency_delta * 0.06
        adjusted_probability += consistency_delta * 0.06

        base_probability = round(self._clamp(base_probability, 0.05, 0.95), 8)
        adjusted_probability = round(self._clamp(adjusted_probability, 0.05, 0.95), 8)
        stamina_outcome = RallyStaminaOutcomeContext(
            base_probability_player_a=base_probability,
            adjusted_probability_player_a=adjusted_probability,
            player_impacts=(impact_a, impact_b),
        )
        if efforts is not None:
            adjusted_probability = round(
                self._clamp(
                    adjusted_probability
                    + efforts[0].outcome_strength_adjustment
                    - efforts[1].outcome_strength_adjustment,
                    0.05,
                    0.95,
                ),
                8,
            )
        return adjusted_probability, stamina_outcome

    @staticmethod
    def _stamina_impact(
        state: PlayerStaminaState, *, enabled: bool
    ) -> PlayerRallyStaminaImpact:
        fills = {
            bar.dimension: round(bar.current / bar.capacity, 8) for bar in state.bars
        }
        nonlinear = {
            dimension: (1.0 - fills[dimension]) ** 2.2 for dimension in StaminaDimension
        }
        weighted_deficit = (
            nonlinear[StaminaDimension.EXPLOSIVE] * 0.45
            + nonlinear[StaminaDimension.RALLY] * 0.35
            + nonlinear[StaminaDimension.MATCH] * 0.20
        )
        weighted_deficit = round(weighted_deficit, 8)
        penalty = 0.18 * weighted_deficit if enabled else 0.0
        return PlayerRallyStaminaImpact(
            player_id=state.player_id,
            explosive_fill_ratio=fills[StaminaDimension.EXPLOSIVE],
            rally_fill_ratio=fills[StaminaDimension.RALLY],
            match_fill_ratio=fills[StaminaDimension.MATCH],
            weighted_nonlinear_deficit=weighted_deficit,
            strength_penalty=round(penalty, 8),
        )

    @staticmethod
    def _rally_detail(
        *,
        rng: DeterministicRng,
        server_player_id: str,
        winner_player_id: str,
    ) -> tuple[
        RallyTerminalTrigger,
        RallyAnalyticalAttribution,
        int,
        int,
        float,
    ]:
        """Create correlated compact detail without changing the scoring RNG stream."""

        roll = rng.random()
        if server_player_id != winner_player_id and roll < 0.035:
            trigger = RallyTerminalTrigger.SERVE_FAULT
            attribution = RallyAnalyticalAttribution.UNFORCED_ERROR
            segments = 0
            shots = 1
        elif roll < 0.32:
            trigger = RallyTerminalTrigger.GOOD_RETURN_UNANSWERED
            attribution = RallyAnalyticalAttribution.CLEAN_WINNER
            segments = rng.randint(0, 8)
            shots = max(1, 2 + segments * 2 + rng.randint(-1, 2))
        else:
            trigger = rng.choice(
                [
                    RallyTerminalTrigger.RETURN_DOWN,
                    RallyTerminalTrigger.RETURN_OUT,
                    RallyTerminalTrigger.RETURN_NOT_UP,
                ]
            )
            attribution = (
                RallyAnalyticalAttribution.FORCED_ERROR
                if rng.random() < 0.62
                else RallyAnalyticalAttribution.UNFORCED_ERROR
            )
            segments = rng.randint(0, 24)
            shots = max(1, 2 + segments * 2 + rng.randint(-1, 3))
        elapsed = round(max(0.5, 0.7 + shots * 0.72 + segments * 0.18), 3)
        return trigger, attribution, segments, shots, elapsed

    @staticmethod
    def _default_log_anchor(context: MatchContext) -> str:
        encoded = json.dumps(
            context.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _retirement_if_triggered(
        context: MatchContext, set_number: int, match_rng: DeterministicRng
    ) -> str | None:
        rule = context.retirement_rule
        if not rule.enabled or rule.retired_player_id is None:
            return None
        if rule.trigger == RetirementTrigger.EXPLICIT_SET_START:
            if rule.set_number == set_number:
                return rule.retired_player_id
            return None

        if rule.set_number is not None and set_number < rule.set_number:
            return None
        return rule.retired_player_id if match_rng.random() < rule.probability else None
