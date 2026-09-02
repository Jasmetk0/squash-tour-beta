"""Deterministic standalone set-by-set professional squash match engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import exp
from typing import ClassVar

from beta_engine.core import DeterministicRng, SeedScope
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
    PlayerRallyEffort,
    PlayerRallyStaminaImpact,
    PostRallyStateSnapshot,
    RallyAnalyticalAttribution,
    RallyEffortContext,
    RallyEffortDecisionFactor,
    RallyEffortLevel,
    RallyEvent,
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

    def simulate(
        self,
        context: MatchContext,
        *,
        log_anchor_hash: str | None = None,
        effective_match_timing: EffectiveMatchTimingSnapshot | None = None,
        effective_match_stamina: EffectiveMatchStaminaSnapshot | None = None,
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
            raise ValueError(
                "effective stamina profiles must match participant order"
            )

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
            ) = (
                self._simulate_set(
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
                )
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
        expected_final_stamina_states: tuple[
            PlayerStaminaState, PlayerStaminaState
        ],
        retired_player_id: str | None = None,
        retired_at_set_start: int | None = None,
    ) -> MatchResult:
        rally_log = MatchRallyLog.create(
            match_id=context.match_id,
            input_snapshot_hash=input_hash,
            events=rally_events,
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
            effort_rng = set_rng.branch(
                SeedScope.MATCH, "rally-effort", rally_in_set
            )
            efforts = (
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
            ) if stamina.pre_rally_effort_applied else None
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
            if set_rng.random() < game_prob_a:
                games_a += 1
                rally_winner = player_a_id
            else:
                games_b += 1
                rally_winner = player_b_id

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
            detail_rng = set_rng.branch(SeedScope.MATCH, "rally-detail", rally_in_set)
            trigger, attribution, segments, shots, elapsed = self._rally_detail(
                rng=detail_rng,
                server_player_id=server_player_id,
                winner_player_id=rally_winner,
            )
            effort_context = None
            player_workloads = None
            if efforts is not None:
                base_workload = MatchStaminaLog.workload_from_detail(
                    elapsed_seconds=elapsed,
                    estimated_shot_count=shots,
                    abstract_segments=segments,
                )
                completed_efforts = tuple(
                    self._complete_rally_effort(
                        effort=effort,
                        base_workload=base_workload,
                        won_rally=effort.player_id == rally_winner,
                        attribution=attribution,
                    )
                    for effort in efforts
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
                    "rally_event.v3" if effort_context is not None else "rally_event.v2"
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
        impact_a = self._stamina_impact(stamina_states[0], enabled=stamina.outcome_effect_applied)
        impact_b = self._stamina_impact(stamina_states[1], enabled=stamina.outcome_effect_applied)
        adjusted_probability = 1.0 / (
            1.0
            + exp(
                -(
                    (strength_delta - impact_a.strength_penalty + impact_b.strength_penalty)
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
        adjusted_probability = round(
            self._clamp(adjusted_probability, 0.05, 0.95), 8
        )
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
            bar.dimension: round(bar.current / bar.capacity, 8)
            for bar in state.bars
        }
        nonlinear = {
            dimension: (1.0 - fills[dimension]) ** 2.2
            for dimension in StaminaDimension
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
