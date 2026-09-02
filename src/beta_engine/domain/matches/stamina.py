"""Versioned physical-stamina calibration and authoritative transition log."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import TYPE_CHECKING, Literal, Self

from pydantic import BaseModel, Field, model_validator

from beta_engine.domain.matches.rallies import RallyEvent
from beta_engine.domain.matches.timeline import MatchTimelineLog

if TYPE_CHECKING:
    from beta_engine.domain.matches.models import MatchContext, MatchParticipantContext


def _round(value: float) -> float:
    return round(value, 4)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


class StaminaDimension(str, Enum):
    EXPLOSIVE = "EXPLOSIVE"
    RALLY = "RALLY"
    MATCH = "MATCH"


class StaminaTransitionCause(str, Enum):
    RALLY_WORKLOAD = "RALLY_WORKLOAD"
    BETWEEN_RALLY_RECOVERY = "BETWEEN_RALLY_RECOVERY"
    GAME_BREAK_RECOVERY = "GAME_BREAK_RECOVERY"


class StaminaBarProfile(BaseModel):
    dimension: StaminaDimension
    capacity: float = Field(gt=0, le=100)
    workload_cost_factor: float = Field(gt=0)
    recovery_per_second: float = Field(ge=0)


class PlayerStaminaProfile(BaseModel):
    player_id: str = Field(min_length=1)
    initial_readiness_factor: float = Field(gt=0, le=1.2)
    bars: tuple[StaminaBarProfile, ...]

    @model_validator(mode="after")
    def validate_dimensions(self) -> PlayerStaminaProfile:
        if {bar.dimension for bar in self.bars} != set(StaminaDimension):
            raise ValueError("stamina profile requires every physical dimension once")
        if len(self.bars) != len(StaminaDimension):
            raise ValueError("stamina profile contains duplicate dimensions")
        return self

    def bar(self, dimension: StaminaDimension) -> StaminaBarProfile:
        return next(bar for bar in self.bars if bar.dimension == dimension)


class EffectiveMatchStaminaSnapshot(BaseModel):
    """Hash-protected, replaceable pre-alpha calibration used by one match."""

    schema_version: Literal["effective_match_stamina.v1"] = (
        "effective_match_stamina.v1"
    )
    calibration_version: Literal[
        "pre_alpha_physical_v1", "pre_alpha_physical_v2"
    ] = "pre_alpha_physical_v2"
    player_profiles: tuple[PlayerStaminaProfile, PlayerStaminaProfile]
    outcome_effect_applied: bool = True
    unsupported_components: tuple[
        Literal[
            "stamina_outcome_coupling",
            "within_rally_effort_changes",
            "within_rally_explosive_recovery",
            "carried_reserves_between_matches",
            "injury_specific_cost_profiles",
        ],
        ...,
    ] = (
        "within_rally_effort_changes",
        "within_rally_explosive_recovery",
        "carried_reserves_between_matches",
        "injury_specific_cost_profiles",
    )

    @classmethod
    def create(
        cls,
        *,
        context: MatchContext,
        outcome_effect_applied: bool = True,
    ) -> EffectiveMatchStaminaSnapshot:
        unsupported = list(cls.model_fields["unsupported_components"].default)
        calibration_version = (
            "pre_alpha_physical_v2"
            if outcome_effect_applied
            else "pre_alpha_physical_v1"
        )
        if not outcome_effect_applied:
            unsupported.insert(0, "stamina_outcome_coupling")
        return cls(
            calibration_version=calibration_version,
            player_profiles=(
                cls._profile(context.player_a),
                cls._profile(context.player_b),
            ),
            outcome_effect_applied=outcome_effect_applied,
            unsupported_components=tuple(unsupported),
        )

    @classmethod
    def _profile(cls, participant: MatchParticipantContext) -> PlayerStaminaProfile:
        player = participant.player
        readiness = _clamp(
            1.0
            + participant.fatigue_modifier * 0.55
            + participant.health_modifier * 0.35
            + participant.travel_modifier * 0.10,
            0.45,
            1.10,
        )
        # These formulas are an explicit, versioned calibration rather than canon.
        # They use only existing physical inputs and can be replaced without
        # reinterpreting historical matches.
        capacities = {
            StaminaDimension.EXPLOSIVE: 55 + player.physical * 0.25 + player.movement * 0.20,
            StaminaDimension.RALLY: 55 + player.physical * 0.30 + player.movement * 0.15,
            StaminaDimension.MATCH: 55 + player.physical * 0.25 + player.recovery * 0.20,
        }
        cost_factors = {
            StaminaDimension.EXPLOSIVE: 1.18 - player.movement * 0.0025,
            StaminaDimension.RALLY: 1.12 - player.physical * 0.0020,
            StaminaDimension.MATCH: 0.58 - player.physical * 0.0012,
        }
        recovery_rates = {
            StaminaDimension.EXPLOSIVE: 0.028 + player.recovery * 0.00022 + player.physical * 0.00010,
            StaminaDimension.RALLY: 0.018 + player.recovery * 0.00017 + player.physical * 0.00008,
            StaminaDimension.MATCH: 0.008 + player.recovery * 0.00010 + player.physical * 0.00005,
        }
        return PlayerStaminaProfile(
            player_id=player.player_id,
            initial_readiness_factor=_round(readiness),
            bars=tuple(
                StaminaBarProfile(
                    dimension=dimension,
                    capacity=_round(capacities[dimension]),
                    workload_cost_factor=_round(cost_factors[dimension]),
                    recovery_per_second=_round(recovery_rates[dimension]),
                )
                for dimension in StaminaDimension
            ),
        )

    @model_validator(mode="after")
    def validate_players(self) -> EffectiveMatchStaminaSnapshot:
        if len({profile.player_id for profile in self.player_profiles}) != 2:
            raise ValueError("effective stamina requires two distinct players")
        return self

    def profile_for(self, player_id: str) -> PlayerStaminaProfile:
        try:
            return next(
                profile
                for profile in self.player_profiles
                if profile.player_id == player_id
            )
        except StopIteration as exc:
            raise ValueError(f"no stamina profile for player '{player_id}'") from exc


class StaminaBarState(BaseModel):
    dimension: StaminaDimension
    capacity: float = Field(gt=0, le=100)
    current: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_current(self) -> StaminaBarState:
        if self.current > self.capacity:
            raise ValueError("stamina current value cannot exceed capacity")
        return self


class PlayerStaminaState(BaseModel):
    player_id: str = Field(min_length=1)
    bars: tuple[StaminaBarState, ...]

    @model_validator(mode="after")
    def validate_dimensions(self) -> PlayerStaminaState:
        if len(self.bars) != len(StaminaDimension) or {
            bar.dimension for bar in self.bars
        } != set(StaminaDimension):
            raise ValueError("stamina state requires every physical dimension once")
        return self

    def current(self, dimension: StaminaDimension) -> float:
        return next(bar.current for bar in self.bars if bar.dimension == dimension)


class PlayerStaminaDelta(BaseModel):
    player_id: str = Field(min_length=1)
    explosive: float
    rally: float
    match: float

    def for_dimension(self, dimension: StaminaDimension) -> float:
        return {
            StaminaDimension.EXPLOSIVE: self.explosive,
            StaminaDimension.RALLY: self.rally,
            StaminaDimension.MATCH: self.match,
        }[dimension]


class StaminaTransition(BaseModel):
    schema_version: Literal["stamina_transition.v1"] = "stamina_transition.v1"
    match_id: str = Field(min_length=1)
    transition_index: int = Field(ge=1)
    source_timeline_index: int = Field(ge=1)
    source_timeline_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cause: StaminaTransitionCause
    elapsed_seconds: float = Field(gt=0)
    workload_units: float = Field(ge=0)
    states_before: tuple[PlayerStaminaState, PlayerStaminaState]
    deltas: tuple[PlayerStaminaDelta, PlayerStaminaDelta]
    states_after: tuple[PlayerStaminaState, PlayerStaminaState]
    previous_transition_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    transition_hash_algorithm: Literal["sha256"] = "sha256"
    transition_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: object) -> Self:
        draft = cls.model_construct(**values, transition_hash="0" * 64)
        payload = draft.model_dump(
            mode="json", exclude={"transition_hash", "transition_hash_algorithm"}
        )
        return cls(**values, transition_hash=cls._content_hash(payload))

    @model_validator(mode="after")
    def validate_transition(self) -> StaminaTransition:
        before_ids = [state.player_id for state in self.states_before]
        after_ids = [state.player_id for state in self.states_after]
        delta_ids = [delta.player_id for delta in self.deltas]
        if before_ids != after_ids or before_ids != delta_ids or len(set(before_ids)) != 2:
            raise ValueError("stamina transition participants do not agree")
        expected_cause = (
            StaminaTransitionCause.RALLY_WORKLOAD
            if self.workload_units > 0
            else self.cause
        )
        if self.cause != expected_cause:
            raise ValueError("only rally workload transitions may carry workload")
        for before, delta, after in zip(
            self.states_before, self.deltas, self.states_after, strict=True
        ):
            for dimension in StaminaDimension:
                expected = _round(
                    _clamp(
                        before.current(dimension) + delta.for_dimension(dimension),
                        0,
                        next(
                            bar.capacity
                            for bar in before.bars
                            if bar.dimension == dimension
                        ),
                    )
                )
                if after.current(dimension) != expected:
                    raise ValueError("stamina transition delta does not match state")
        payload = self.model_dump(
            mode="json", exclude={"transition_hash", "transition_hash_algorithm"}
        )
        if self.transition_hash != self._content_hash(payload):
            raise ValueError("stamina transition hash mismatch")
        return self

    @staticmethod
    def _content_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class MatchStaminaLog(BaseModel):
    schema_version: Literal["match_stamina_log.v1"] = "match_stamina_log.v1"
    match_id: str = Field(min_length=1)
    timeline_log_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    calibration_version: Literal["pre_alpha_physical_v1", "pre_alpha_physical_v2"]
    initial_states: tuple[PlayerStaminaState, PlayerStaminaState]
    transitions: tuple[StaminaTransition, ...]
    final_states: tuple[PlayerStaminaState, PlayerStaminaState]
    total_transitions: int = Field(ge=0)
    outcome_effect_applied: bool = False
    unsupported_components: tuple[
        Literal[
            "stamina_outcome_coupling",
            "within_rally_effort_changes",
            "within_rally_explosive_recovery",
            "carried_reserves_between_matches",
            "injury_specific_cost_profiles",
        ],
        ...,
    ]
    match_log_hash_algorithm: Literal["sha256"] = "sha256"
    match_log_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def build(
        cls,
        *,
        context: MatchContext,
        timeline: MatchTimelineLog,
        rally_events: tuple[RallyEvent, ...],
        effective: EffectiveMatchStaminaSnapshot,
    ) -> MatchStaminaLog:
        player_ids = (
            context.player_a.player.player_id,
            context.player_b.player.player_id,
        )
        rally_by_hash = {event.event_hash: event for event in rally_events}
        initial = cls.create_initial_states(effective=effective, player_ids=player_ids)
        current = initial
        transitions: list[StaminaTransition] = []
        previous_hash = timeline.match_log_hash
        for source in timeline.events:
            if source.event_type == "RALLY":
                rally = rally_by_hash[source.rally_event_hash]
                workload = cls.rally_workload(rally)
                cause = StaminaTransitionCause.RALLY_WORKLOAD
            elif source.event_type == "BETWEEN_RALLY_INTERVAL":
                workload = 0.0
                cause = StaminaTransitionCause.BETWEEN_RALLY_RECOVERY
            else:
                workload = 0.0
                cause = StaminaTransitionCause.GAME_BREAK_RECOVERY
            deltas, after = cls.advance_states(
                effective=effective,
                states=current,
                cause=cause,
                elapsed_seconds=source.elapsed_seconds,
                workload_units=workload,
            )
            transition = StaminaTransition.create(
                match_id=context.match_id,
                transition_index=len(transitions) + 1,
                source_timeline_index=source.timeline_index,
                source_timeline_event_hash=source.event_hash,
                cause=cause,
                elapsed_seconds=source.elapsed_seconds,
                workload_units=workload,
                states_before=current,
                deltas=deltas,
                states_after=after,
                previous_transition_hash=previous_hash,
            )
            transitions.append(transition)
            current = after
            previous_hash = transition.transition_hash
        return cls(
            match_id=context.match_id,
            timeline_log_hash=timeline.match_log_hash,
            calibration_version=effective.calibration_version,
            initial_states=initial,
            transitions=tuple(transitions),
            final_states=current,
            total_transitions=len(transitions),
            outcome_effect_applied=effective.outcome_effect_applied,
            unsupported_components=effective.unsupported_components,
            match_log_hash=previous_hash,
        )

    @staticmethod
    def _initial_state(profile: PlayerStaminaProfile) -> PlayerStaminaState:
        return PlayerStaminaState(
            player_id=profile.player_id,
            bars=tuple(
                StaminaBarState(
                    dimension=bar.dimension,
                    capacity=bar.capacity,
                    current=_round(
                        min(
                            bar.capacity,
                            bar.capacity * profile.initial_readiness_factor,
                        )
                    ),
                )
                for bar in profile.bars
            ),
        )

    @classmethod
    def create_initial_states(
        cls,
        *,
        effective: EffectiveMatchStaminaSnapshot,
        player_ids: tuple[str, str],
    ) -> tuple[PlayerStaminaState, PlayerStaminaState]:
        return (
            cls._initial_state(effective.profile_for(player_ids[0])),
            cls._initial_state(effective.profile_for(player_ids[1])),
        )

    @staticmethod
    def rally_workload(rally: RallyEvent) -> float:
        return _round(
            0.45
            + rally.elapsed_seconds * 0.05
            + rally.estimated_shot_count * 0.025
            + rally.abstract_segments * 0.03
        )

    @staticmethod
    def _delta(
        profile: PlayerStaminaProfile,
        state: PlayerStaminaState,
        *,
        cause: StaminaTransitionCause,
        elapsed_seconds: float,
        workload_units: float,
        match_stamina_limits_recovery: bool,
    ) -> PlayerStaminaDelta:
        values: dict[StaminaDimension, float] = {}
        for dimension in StaminaDimension:
            bar = profile.bar(dimension)
            if cause == StaminaTransitionCause.RALLY_WORKLOAD:
                value = -workload_units * bar.workload_cost_factor
            else:
                missing = bar.capacity - state.current(dimension)
                recovery_efficiency = 1.0
                if match_stamina_limits_recovery:
                    match_bar = profile.bar(StaminaDimension.MATCH)
                    match_fill = state.current(StaminaDimension.MATCH) / match_bar.capacity
                    recovery_efficiency = 0.45 + 0.55 * (match_fill**0.7)
                value = min(
                    missing,
                    elapsed_seconds
                    * bar.recovery_per_second
                    * recovery_efficiency,
                )
            values[dimension] = _round(value)
        return PlayerStaminaDelta(
            player_id=profile.player_id,
            explosive=values[StaminaDimension.EXPLOSIVE],
            rally=values[StaminaDimension.RALLY],
            match=values[StaminaDimension.MATCH],
        )

    @staticmethod
    def _apply_delta(
        state: PlayerStaminaState, delta: PlayerStaminaDelta
    ) -> PlayerStaminaState:
        return PlayerStaminaState(
            player_id=state.player_id,
            bars=tuple(
                StaminaBarState(
                    dimension=bar.dimension,
                    capacity=bar.capacity,
                    current=_round(
                        _clamp(
                            bar.current + delta.for_dimension(bar.dimension),
                            0,
                            bar.capacity,
                        )
                    ),
                )
                for bar in state.bars
            ),
        )

    @classmethod
    def advance_states(
        cls,
        *,
        effective: EffectiveMatchStaminaSnapshot,
        states: tuple[PlayerStaminaState, PlayerStaminaState],
        cause: StaminaTransitionCause,
        elapsed_seconds: float,
        workload_units: float,
    ) -> tuple[
        tuple[PlayerStaminaDelta, PlayerStaminaDelta],
        tuple[PlayerStaminaState, PlayerStaminaState],
    ]:
        deltas = (
            cls._delta(
                effective.profile_for(states[0].player_id),
                states[0],
                cause=cause,
                elapsed_seconds=elapsed_seconds,
                workload_units=workload_units,
                match_stamina_limits_recovery=(
                    effective.calibration_version == "pre_alpha_physical_v2"
                ),
            ),
            cls._delta(
                effective.profile_for(states[1].player_id),
                states[1],
                cause=cause,
                elapsed_seconds=elapsed_seconds,
                workload_units=workload_units,
                match_stamina_limits_recovery=(
                    effective.calibration_version == "pre_alpha_physical_v2"
                ),
            ),
        )
        return deltas, (
            cls._apply_delta(states[0], deltas[0]),
            cls._apply_delta(states[1], deltas[1]),
        )

    @model_validator(mode="after")
    def validate_chain(self) -> MatchStaminaLog:
        previous_hash = self.timeline_log_hash
        current = self.initial_states
        for expected_index, transition in enumerate(self.transitions, start=1):
            if (
                transition.match_id != self.match_id
                or transition.transition_index != expected_index
                or transition.source_timeline_index != expected_index
            ):
                raise ValueError("stamina transition identity or order mismatch")
            if transition.previous_transition_hash != previous_hash:
                raise ValueError("stamina transition hash chain is broken")
            if transition.states_before != current:
                raise ValueError("stamina state continuity is broken")
            current = transition.states_after
            previous_hash = transition.transition_hash
        if self.total_transitions != len(self.transitions):
            raise ValueError("stamina transition total mismatch")
        if self.final_states != current:
            raise ValueError("stamina final states do not match transition chain")
        if self.match_log_hash != previous_hash:
            raise ValueError("stamina log final hash mismatch")
        return self

    def validate_timeline(self, timeline: MatchTimelineLog) -> None:
        if self.match_id != timeline.match_id or self.timeline_log_hash != timeline.match_log_hash:
            raise ValueError("stamina log does not match authoritative timeline")
        if len(self.transitions) != len(timeline.events):
            raise ValueError("stamina log must cover every timeline event")
        for transition, source in zip(self.transitions, timeline.events, strict=True):
            expected_cause = {
                "RALLY": StaminaTransitionCause.RALLY_WORKLOAD,
                "BETWEEN_RALLY_INTERVAL": StaminaTransitionCause.BETWEEN_RALLY_RECOVERY,
                "GAME_BREAK": StaminaTransitionCause.GAME_BREAK_RECOVERY,
            }[source.event_type]
            if (
                transition.source_timeline_event_hash != source.event_hash
                or transition.source_timeline_index != source.timeline_index
                or transition.elapsed_seconds != source.elapsed_seconds
                or transition.cause != expected_cause
            ):
                raise ValueError("stamina transition references the wrong timeline event")

    def validate_effective_snapshot(
        self, effective: EffectiveMatchStaminaSnapshot
    ) -> None:
        if self.calibration_version != effective.calibration_version:
            raise ValueError("stamina log uses the wrong input calibration")
        expected = tuple(
            self._initial_state(profile) for profile in effective.player_profiles
        )
        if self.initial_states != expected:
            raise ValueError("stamina initial state does not match effective input")
        if self.unsupported_components != effective.unsupported_components:
            raise ValueError("stamina log support boundary does not match effective input")
        if self.outcome_effect_applied != effective.outcome_effect_applied:
            raise ValueError("stamina log outcome boundary does not match effective input")

    def validate_rally_outcomes(self, rally_events: tuple[RallyEvent, ...]) -> None:
        transitions = tuple(
            transition
            for transition in self.transitions
            if transition.cause == StaminaTransitionCause.RALLY_WORKLOAD
        )
        if len(transitions) != len(rally_events):
            raise ValueError("stamina outcome audit does not cover every rally")
        for rally, transition in zip(rally_events, transitions, strict=True):
            context = rally.stamina_outcome_context
            if context is None:
                if self.outcome_effect_applied:
                    raise ValueError("active stamina log requires rally outcome context")
                continue
            for state, impact in zip(
                transition.states_before, context.player_impacts, strict=True
            ):
                fills = {
                    bar.dimension: round(bar.current / bar.capacity, 8)
                    for bar in state.bars
                }
                if impact.player_id != state.player_id or (
                    impact.explosive_fill_ratio,
                    impact.rally_fill_ratio,
                    impact.match_fill_ratio,
                ) != (
                    fills[StaminaDimension.EXPLOSIVE],
                    fills[StaminaDimension.RALLY],
                    fills[StaminaDimension.MATCH],
                ):
                    raise ValueError("rally stamina impact does not match live state")
                nonlinear_deficit = round(
                    (1 - fills[StaminaDimension.EXPLOSIVE]) ** 2.2 * 0.45
                    + (1 - fills[StaminaDimension.RALLY]) ** 2.2 * 0.35
                    + (1 - fills[StaminaDimension.MATCH]) ** 2.2 * 0.20,
                    8,
                )
                expected_penalty = round(
                    0.18 * nonlinear_deficit
                    if self.outcome_effect_applied
                    else 0.0,
                    8,
                )
                if (
                    impact.weighted_nonlinear_deficit != nonlinear_deficit
                    or impact.strength_penalty != expected_penalty
                ):
                    raise ValueError("rally stamina outcome curve is inconsistent")
