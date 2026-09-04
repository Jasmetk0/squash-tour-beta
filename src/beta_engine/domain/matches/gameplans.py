"""Versioned four-axis style and active-gameplan inputs for one match."""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.core import DeterministicRng, SeedScope

if TYPE_CHECKING:
    from beta_engine.domain.matches.models import (
        MatchContext,
        MatchParticipantContext,
    )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _round(value: float) -> float:
    return round(value, 8)


class StyleAxes(BaseModel):
    """Simultaneous style coordinates used by the first pre-alpha gameplan model.

    ``court_positioning`` runs from a deeper/reactive position at ``0`` to a
    higher/front-seeking position at ``1``. The remaining axes run from low to
    high risk, patient to fast tempo, and repetition to high variation.
    """

    model_config = ConfigDict(frozen=True)

    risk: float = Field(ge=0, le=1)
    tempo: float = Field(ge=0, le=1)
    court_positioning: float = Field(ge=0, le=1)
    variation: float = Field(ge=0, le=1)

    def blend(self, other: StyleAxes, other_weight: float) -> StyleAxes:
        weight = _clamp(other_weight, 0.0, 1.0)
        return StyleAxes(
            risk=_round(self.risk * (1.0 - weight) + other.risk * weight),
            tempo=_round(self.tempo * (1.0 - weight) + other.tempo * weight),
            court_positioning=_round(
                self.court_positioning * (1.0 - weight)
                + other.court_positioning * weight
            ),
            variation=_round(
                self.variation * (1.0 - weight) + other.variation * weight
            ),
        )

    def mean_distance(self, other: StyleAxes) -> float:
        return _round(
            (
                abs(self.risk - other.risk)
                + abs(self.tempo - other.tempo)
                + abs(self.court_positioning - other.court_positioning)
                + abs(self.variation - other.variation)
            )
            / 4.0
        )


class GameplanStrategy(str, Enum):
    OWN_STRENGTH = "OWN_STRENGTH"
    COUNTER_ESTIMATE = "COUNTER_ESTIMATE"
    DELAYED_PAYOFF = "DELAYED_PAYOFF"


class GameplanMechanism(str, Enum):
    IMPOSE_NATURAL_PATTERN = "IMPOSE_NATURAL_PATTERN"
    DISRUPT_ESTIMATED_PATTERN = "DISRUPT_ESTIMATED_PATTERN"
    EXTEND_PHYSICAL_TEST = "EXTEND_PHYSICAL_TEST"


class GameplanTimeHorizon(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    GAME_PHASE = "GAME_PHASE"
    MATCH_LONG = "MATCH_LONG"


class GameplanDecisionAction(str, Enum):
    START = "START"
    STICK = "STICK"
    ADAPT = "ADAPT"


class GameplanDecisionReason(str, Enum):
    INITIAL_SELECTION = "INITIAL_SELECTION"
    REVIEW_NOT_DUE = "REVIEW_NOT_DUE"
    OBSERVED_PLAN_WORKING = "OBSERVED_PLAN_WORKING"
    EXPECTED_LATER_PAYOFF = "EXPECTED_LATER_PAYOFF"
    HIGH_CONFIDENCE_STICK = "HIGH_CONFIDENCE_STICK"
    LOW_ADAPTABILITY_STICK = "LOW_ADAPTABILITY_STICK"
    MISREAD_PERFORMANCE_STICK = "MISREAD_PERFORMANCE_STICK"
    NEGATIVE_REASSESSMENT = "NEGATIVE_REASSESSMENT"


class PlayerNaturalStyleProfile(BaseModel):
    """Match-time materialization of a player's long-term style direction."""

    model_config = ConfigDict(frozen=True)

    player_id: str = Field(min_length=1)
    source_play_style: str = Field(min_length=1)
    axes: StyleAxes
    adaptability_proxy: float = Field(ge=0, le=1)
    familiarity_baseline: float = Field(ge=0, le=1)
    profile_seed: str = Field(pattern=r"^[0-9]+$")
    profile_source: Literal["legacy_style_materialization_v1"] = (
        "legacy_style_materialization_v1"
    )


class OpponentStyleEstimate(BaseModel):
    """What one player's decision layer believes about the opponent."""

    model_config = ConfigDict(frozen=True)

    opponent_player_id: str = Field(min_length=1)
    estimated_axes: StyleAxes
    confidence: float = Field(ge=0, le=1)
    mean_absolute_error: float = Field(ge=0, le=1)


class PlayerActiveGameplan(BaseModel):
    """One chosen plan revision, including why and when it may be reconsidered."""

    model_config = ConfigDict(frozen=True)

    player_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    selected_before_rally_index: int = Field(ge=1)
    strategy: GameplanStrategy
    intended_mechanism: GameplanMechanism
    time_horizon: GameplanTimeHorizon
    axes: StyleAxes
    style_familiarity: float = Field(ge=0, le=1)
    base_execution_factor: float = Field(ge=0.4, le=1.1)
    confidence: float = Field(ge=0, le=1)
    reassessment_after_rallies: int = Field(ge=3, le=16)
    anticipated_payoff_after_rallies: int = Field(ge=0, le=24)
    opponent_estimate: OpponentStyleEstimate
    selection_seed: str = Field(pattern=r"^[0-9]+$")
    source: Literal["PLAYER_AI_PRE_ALPHA_V1"] = "PLAYER_AI_PRE_ALPHA_V1"

    @model_validator(mode="after")
    def validate_opponent(self) -> PlayerActiveGameplan:
        if self.opponent_estimate.opponent_player_id == self.player_id:
            raise ValueError("active gameplan opponent must differ from its player")
        if (
            self.time_horizon == GameplanTimeHorizon.MATCH_LONG
            and self.anticipated_payoff_after_rallies == 0
        ):
            raise ValueError("match-long gameplan requires a later payoff horizon")
        return self


class EffectiveMatchGameplanSnapshot(BaseModel):
    """Frozen AI choices and style truth captured before the first rally.

    The four axes and decision contract are product rules. All numeric mappings
    in this class are explicitly replaceable ``pre_alpha_gameplan_v1``
    calibration, not final squash constants.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["effective_match_gameplans.v1"] = (
        "effective_match_gameplans.v1"
    )
    calibration_version: Literal["pre_alpha_gameplan_v1"] = "pre_alpha_gameplan_v1"
    natural_style_profiles: tuple[PlayerNaturalStyleProfile, PlayerNaturalStyleProfile]
    initial_gameplans: tuple[PlayerActiveGameplan, PlayerActiveGameplan]
    four_axis_execution_applied: Literal[True] = True
    imperfect_opponent_estimates_applied: Literal[True] = True
    in_match_reassessment_applied: Literal[True] = True
    unsupported_components: tuple[
        Literal[
            "persistent_authored_style_profiles",
            "match_preparation",
            "scouting_history_and_memory",
            "mental_bar_execution_coupling",
        ],
        ...,
    ] = (
        "persistent_authored_style_profiles",
        "match_preparation",
        "scouting_history_and_memory",
        "mental_bar_execution_coupling",
    )

    @classmethod
    def create(
        cls,
        *,
        context: MatchContext,
        simulation_seed: int,
    ) -> EffectiveMatchGameplanSnapshot:
        participants = (context.player_a, context.player_b)
        profiles = tuple(
            cls._natural_profile(participant) for participant in participants
        )
        decision_rng = DeterministicRng(simulation_seed).branch(
            SeedScope.MATCH,
            context.match_id,
            "active-gameplans-v1",
        )
        initial_gameplans = tuple(
            cls._build_plan(
                participant=participants[player_index],
                profile=profiles[player_index],
                opponent_profile=profiles[1 - player_index],
                revision=1,
                selected_before_rally_index=1,
                strategy=None,
                prior_estimate=None,
                rng=decision_rng.branch(
                    SeedScope.MATCH,
                    participants[player_index].player.player_id,
                    "initial",
                ),
            )
            for player_index in range(2)
        )
        return cls(
            natural_style_profiles=profiles,
            initial_gameplans=initial_gameplans,
        )

    @model_validator(mode="after")
    def validate_players(self) -> EffectiveMatchGameplanSnapshot:
        profile_ids = tuple(
            profile.player_id for profile in self.natural_style_profiles
        )
        plan_ids = tuple(plan.player_id for plan in self.initial_gameplans)
        if len(set(profile_ids)) != 2 or plan_ids != profile_ids:
            raise ValueError(
                "effective gameplans require two ordered, distinct player profiles"
            )
        if tuple(
            plan.opponent_estimate.opponent_player_id for plan in self.initial_gameplans
        ) != (profile_ids[1], profile_ids[0]):
            raise ValueError("effective gameplan opponent estimates are not reciprocal")
        return self

    def profile_for(self, player_id: str) -> PlayerNaturalStyleProfile:
        try:
            return next(
                profile
                for profile in self.natural_style_profiles
                if profile.player_id == player_id
            )
        except StopIteration as exc:
            raise ValueError(
                f"no natural style profile for player '{player_id}'"
            ) from exc

    def initial_plan_for(self, player_id: str) -> PlayerActiveGameplan:
        try:
            return next(
                plan for plan in self.initial_gameplans if plan.player_id == player_id
            )
        except StopIteration as exc:
            raise ValueError(f"no initial gameplan for player '{player_id}'") from exc

    def revise_plan(
        self,
        *,
        participant: MatchParticipantContext,
        opponent_active_axes: StyleAxes,
        previous_plan: PlayerActiveGameplan,
        selected_before_rally_index: int,
        rng: DeterministicRng,
    ) -> PlayerActiveGameplan:
        profile = self.profile_for(participant.player.player_id)
        opponent_profile = next(
            candidate
            for candidate in self.natural_style_profiles
            if candidate.player_id != profile.player_id
        )
        next_strategy = (
            GameplanStrategy.OWN_STRENGTH
            if previous_plan.strategy == GameplanStrategy.COUNTER_ESTIMATE
            else GameplanStrategy.COUNTER_ESTIMATE
        )
        observed_profile = opponent_profile.model_copy(
            update={"axes": opponent_active_axes}
        )
        return self._build_plan(
            participant=participant,
            profile=profile,
            opponent_profile=observed_profile,
            revision=previous_plan.revision + 1,
            selected_before_rally_index=selected_before_rally_index,
            strategy=next_strategy,
            prior_estimate=previous_plan.opponent_estimate,
            rng=rng,
        )

    @classmethod
    def counter_fit(cls, plan_axes: StyleAxes, opponent_axes: StyleAxes) -> float:
        ideal = cls._counter_axes(opponent_axes)
        return _round(_clamp(1.0 - plan_axes.mean_distance(ideal) * 1.45, 0.0, 1.0))

    @classmethod
    def _natural_profile(
        cls, participant: MatchParticipantContext
    ) -> PlayerNaturalStyleProfile:
        player = participant.player
        profile_seed = cls._stable_seed(
            "natural-style-v1", player.player_id, player.play_style
        )
        profile_rng = DeterministicRng(profile_seed)
        base = cls._style_base(player.play_style)
        axes = StyleAxes(
            risk=_round(_clamp(base.risk + profile_rng.uniform(-0.065, 0.065), 0, 1)),
            tempo=_round(_clamp(base.tempo + profile_rng.uniform(-0.065, 0.065), 0, 1)),
            court_positioning=_round(
                _clamp(
                    base.court_positioning + profile_rng.uniform(-0.065, 0.065),
                    0,
                    1,
                )
            ),
            variation=_round(
                _clamp(base.variation + profile_rng.uniform(-0.065, 0.065), 0, 1)
            ),
        )
        adaptability = _round(
            _clamp((player.mental * 0.58 + player.consistency * 0.42) / 99.0, 0, 1)
        )
        familiarity = _round(
            _clamp(
                0.62
                + player.technique / 99.0 * 0.12
                + player.consistency / 99.0 * 0.12
                + profile_rng.uniform(-0.055, 0.055),
                0.55,
                0.97,
            )
        )
        return PlayerNaturalStyleProfile(
            player_id=player.player_id,
            source_play_style=player.play_style,
            axes=axes,
            adaptability_proxy=adaptability,
            familiarity_baseline=familiarity,
            profile_seed=str(profile_seed),
        )

    @classmethod
    def _build_plan(
        cls,
        *,
        participant: MatchParticipantContext,
        profile: PlayerNaturalStyleProfile,
        opponent_profile: PlayerNaturalStyleProfile,
        revision: int,
        selected_before_rally_index: int,
        strategy: GameplanStrategy | None,
        prior_estimate: OpponentStyleEstimate | None,
        rng: DeterministicRng,
    ) -> PlayerActiveGameplan:
        player = participant.player
        estimate = cls._estimate_opponent(
            observer=participant,
            opponent_profile=opponent_profile,
            prior_estimate=prior_estimate,
            rng=rng.branch(SeedScope.MATCH, "opponent-estimate"),
        )
        chosen_strategy = strategy or cls._select_strategy(
            participant=participant,
            profile=profile,
            rng=rng.branch(SeedScope.MATCH, "strategy"),
        )
        if chosen_strategy == GameplanStrategy.COUNTER_ESTIMATE:
            counter_target = cls._counter_axes(estimate.estimated_axes)
            target_weight = 0.38 + profile.adaptability_proxy * 0.34
            axes = profile.axes.blend(counter_target, target_weight)
            mechanism = GameplanMechanism.DISRUPT_ESTIMATED_PATTERN
            horizon = GameplanTimeHorizon.GAME_PHASE
            anticipated_payoff = 3 + round((1.0 - axes.tempo) * 3)
        elif chosen_strategy == GameplanStrategy.DELAYED_PAYOFF:
            delayed_target = StyleAxes(
                risk=_round(_clamp(profile.axes.risk * 0.62, 0.14, 0.56)),
                tempo=_round(_clamp(profile.axes.tempo * 0.65, 0.12, 0.52)),
                court_positioning=_round(
                    _clamp(profile.axes.court_positioning * 0.70, 0.16, 0.58)
                ),
                variation=_round(_clamp(profile.axes.variation + 0.08, 0, 1)),
            )
            axes = profile.axes.blend(
                delayed_target, 0.34 + profile.adaptability_proxy * 0.22
            )
            mechanism = GameplanMechanism.EXTEND_PHYSICAL_TEST
            horizon = GameplanTimeHorizon.MATCH_LONG
            anticipated_payoff = 8 + round((1.0 - axes.tempo) * 6)
        else:
            axes = profile.axes
            mechanism = GameplanMechanism.IMPOSE_NATURAL_PATTERN
            horizon = GameplanTimeHorizon.IMMEDIATE
            anticipated_payoff = 0

        distance = axes.mean_distance(profile.axes)
        familiarity = _round(
            _clamp(
                profile.familiarity_baseline
                - distance * (0.52 - profile.adaptability_proxy * 0.22),
                0.38,
                0.98,
            )
        )
        base_execution = _round(
            _clamp(
                0.24
                + player.technique / 99.0 * 0.19
                + player.movement / 99.0 * 0.10
                + player.consistency / 99.0 * 0.17
                + player.mental / 99.0 * 0.10
                + familiarity * 0.24,
                0.48,
                1.04,
            )
        )
        confidence = _round(
            _clamp(
                0.16
                + familiarity * 0.39
                + profile.adaptability_proxy * 0.15
                + estimate.confidence * 0.18
                + rng.uniform(-0.075, 0.075),
                0.28,
                0.96,
            )
        )
        horizon_delay = {
            GameplanTimeHorizon.IMMEDIATE: 0,
            GameplanTimeHorizon.GAME_PHASE: 1,
            GameplanTimeHorizon.MATCH_LONG: 3,
        }[horizon]
        reassessment = round(
            3.0
            + confidence * 3.2
            + (1.0 - profile.adaptability_proxy) * 2.0
            + horizon_delay
        )
        return PlayerActiveGameplan(
            player_id=player.player_id,
            revision=revision,
            selected_before_rally_index=selected_before_rally_index,
            strategy=chosen_strategy,
            intended_mechanism=mechanism,
            time_horizon=horizon,
            axes=axes,
            style_familiarity=familiarity,
            base_execution_factor=base_execution,
            confidence=confidence,
            reassessment_after_rallies=max(3, min(16, reassessment)),
            anticipated_payoff_after_rallies=anticipated_payoff,
            opponent_estimate=estimate,
            selection_seed=str(rng.seed.value),
        )

    @staticmethod
    def _select_strategy(
        *,
        participant: MatchParticipantContext,
        profile: PlayerNaturalStyleProfile,
        rng: DeterministicRng,
    ) -> GameplanStrategy:
        player = participant.player
        counter_weight = (
            0.16
            + profile.adaptability_proxy * 0.23
            + player.mental / 99.0 * 0.10
            + (
                0.10
                if player.play_style in {"counter-punching", "tempo-controller"}
                else 0
            )
        )
        delayed_weight = (
            0.08
            + (1.0 - profile.axes.tempo) * 0.16
            + (0.10 if player.play_style in {"retrieving", "tempo-controller"} else 0)
        )
        roll = rng.random()
        if roll < counter_weight:
            return GameplanStrategy.COUNTER_ESTIMATE
        if roll < counter_weight + delayed_weight:
            return GameplanStrategy.DELAYED_PAYOFF
        return GameplanStrategy.OWN_STRENGTH

    @classmethod
    def _estimate_opponent(
        cls,
        *,
        observer: MatchParticipantContext,
        opponent_profile: PlayerNaturalStyleProfile,
        prior_estimate: OpponentStyleEstimate | None,
        rng: DeterministicRng,
    ) -> OpponentStyleEstimate:
        observer_player = observer.player
        base_confidence = _clamp(
            0.34
            + observer_player.mental / 99.0 * 0.27
            + observer_player.consistency / 99.0 * 0.15
            + (0.06 if prior_estimate is not None else 0.0),
            0.42,
            0.86,
        )
        error_radius = 0.24 - base_confidence * 0.16

        # Every update blends a noisy new observation with the previous belief.
        # The exact opponent axes are used only to generate that noisy signal;
        # they are never blended into the AI belief as omniscient information.
        values: dict[str, float] = {}
        for axis_name in ("risk", "tempo", "court_positioning", "variation"):
            actual = getattr(opponent_profile.axes, axis_name)
            observed = _clamp(
                actual + rng.uniform(-error_radius, error_radius),
                0,
                1,
            )
            if prior_estimate is None:
                values[axis_name] = _round(observed)
            else:
                prior_axis = getattr(prior_estimate.estimated_axes, axis_name)
                values[axis_name] = _round(observed * 0.70 + prior_axis * 0.30)
        estimated_axes = StyleAxes(**values)
        return OpponentStyleEstimate(
            opponent_player_id=opponent_profile.player_id,
            estimated_axes=estimated_axes,
            confidence=_round(base_confidence),
            mean_absolute_error=estimated_axes.mean_distance(opponent_profile.axes),
        )

    @staticmethod
    def _counter_axes(opponent: StyleAxes) -> StyleAxes:
        return StyleAxes(
            risk=_round(_clamp(0.50 - (opponent.risk - 0.5) * 0.52, 0.12, 0.88)),
            tempo=_round(_clamp(0.50 - (opponent.tempo - 0.5) * 0.68, 0.10, 0.90)),
            court_positioning=_round(
                _clamp(0.52 + (opponent.court_positioning - 0.5) * 0.38, 0.18, 0.88)
            ),
            variation=_round(
                _clamp(0.58 + abs(opponent.tempo - 0.5) * 0.34, 0.45, 0.88)
            ),
        )

    @staticmethod
    def _style_base(play_style: str) -> StyleAxes:
        return {
            "attacking": StyleAxes(
                risk=0.78, tempo=0.72, court_positioning=0.66, variation=0.56
            ),
            "counter-punching": StyleAxes(
                risk=0.46, tempo=0.47, court_positioning=0.48, variation=0.62
            ),
            "retrieving": StyleAxes(
                risk=0.25, tempo=0.34, court_positioning=0.27, variation=0.43
            ),
            "front-court": StyleAxes(
                risk=0.69, tempo=0.68, court_positioning=0.86, variation=0.64
            ),
            "tempo-controller": StyleAxes(
                risk=0.39, tempo=0.30, court_positioning=0.44, variation=0.74
            ),
        }.get(
            play_style,
            StyleAxes(risk=0.5, tempo=0.5, court_positioning=0.5, variation=0.5),
        )

    @staticmethod
    def _stable_seed(*parts: object) -> int:
        material = "|".join(["pre_alpha_gameplan_v1", *(str(part) for part in parts)])
        digest = hashlib.blake2b(material.encode("utf-8"), digest_size=16).digest()
        return int.from_bytes(digest, byteorder="big", signed=False)


class PlayerGameplanState(BaseModel):
    """Internal sequential evidence available before the next rally decision."""

    model_config = ConfigDict(frozen=True)

    player_id: str = Field(min_length=1)
    active_plan: PlayerActiveGameplan
    rallies_since_reassessment: int = Field(ge=0)
    points_won_since_reassessment: int = Field(ge=0)
    points_lost_since_reassessment: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_plan_owner(self) -> PlayerGameplanState:
        if self.active_plan.player_id != self.player_id:
            raise ValueError("runtime gameplan state and active plan owners differ")
        if self.rallies_since_reassessment != (
            self.points_won_since_reassessment + self.points_lost_since_reassessment
        ):
            raise ValueError("gameplan evidence must account for every observed rally")
        return self


class PlayerGameplanRallyEffect(BaseModel):
    player_id: str = Field(min_length=1)
    execution_factor: float = Field(ge=0.35, le=1.1)
    actual_counter_fit: float = Field(ge=0, le=1)
    control_execution_signal: float = Field(ge=-0.25, le=0.25)
    pace_preference_signal: float = Field(ge=-0.3, le=0.3)
    closure_pressure_signal: float = Field(ge=-0.1, le=0.1)
    workload_factor: float = Field(ge=0.75, le=1.35)


class PlayerRallyGameplanDecision(BaseModel):
    player_id: str = Field(min_length=1)
    active_plan: PlayerActiveGameplan
    action: GameplanDecisionAction
    reason: GameplanDecisionReason
    observed_rallies: int = Field(ge=0)
    observed_point_differential: int
    perceived_performance_signal: float = Field(ge=-1, le=1)

    @model_validator(mode="after")
    def validate_plan_owner(self) -> PlayerRallyGameplanDecision:
        if self.active_plan.player_id != self.player_id:
            raise ValueError("rally gameplan decision and active plan owners differ")
        if (
            abs(self.observed_point_differential) > self.observed_rallies
            or (self.observed_rallies - self.observed_point_differential) % 2
        ):
            raise ValueError("gameplan point evidence is internally inconsistent")
        if self.action == GameplanDecisionAction.START and (
            self.reason != GameplanDecisionReason.INITIAL_SELECTION
            or self.active_plan.revision != 1
            or self.observed_rallies != 0
        ):
            raise ValueError("gameplan start must be the unobserved initial plan")
        if self.action == GameplanDecisionAction.ADAPT and (
            self.reason != GameplanDecisionReason.NEGATIVE_REASSESSMENT
            or self.active_plan.revision < 2
        ):
            raise ValueError("gameplan adaptation requires a negative reassessment")
        if self.action == GameplanDecisionAction.STICK and self.reason in {
            GameplanDecisionReason.INITIAL_SELECTION,
            GameplanDecisionReason.NEGATIVE_REASSESSMENT,
        }:
            raise ValueError("gameplan stick action uses an incompatible reason")
        return self

    @property
    def axes(self) -> StyleAxes:
        return self.active_plan.axes

    @property
    def strategy(self) -> GameplanStrategy:
        return self.active_plan.strategy

    @property
    def confidence(self) -> float:
        return self.active_plan.confidence


class RallyGameplanContext(BaseModel):
    """Logged decisions and causal style effects used by one rally."""

    calibration_version: Literal["pre_alpha_gameplan_v1"] = "pre_alpha_gameplan_v1"
    player_decisions: tuple[PlayerRallyGameplanDecision, PlayerRallyGameplanDecision]
    player_effects: tuple[PlayerGameplanRallyEffect, PlayerGameplanRallyEffect]
    control_drive_adjustment_player_a: float = Field(ge=-0.5, le=0.5)
    shared_pace_signal: float = Field(ge=-0.3, le=0.3)
    shared_closure_probability_adjustment: float = Field(ge=-0.1, le=0.1)

    @model_validator(mode="after")
    def validate_players(self) -> RallyGameplanContext:
        decision_ids = tuple(decision.player_id for decision in self.player_decisions)
        effect_ids = tuple(effect.player_id for effect in self.player_effects)
        if len(set(decision_ids)) != 2 or effect_ids != decision_ids:
            raise ValueError(
                "rally gameplan decisions and effects must share player order"
            )
        expected_control_drive = _round(
            self.player_effects[0].control_execution_signal
            - self.player_effects[1].control_execution_signal
        )
        if self.control_drive_adjustment_player_a != expected_control_drive:
            raise ValueError(
                "rally gameplan control drive does not match player effects"
            )
        expected_pace = _round(
            sum(effect.pace_preference_signal for effect in self.player_effects) / 2.0
        )
        if self.shared_pace_signal != expected_pace:
            raise ValueError("shared gameplan pace does not match player effects")
        expected_closure = _round(
            sum(effect.closure_pressure_signal for effect in self.player_effects) / 2.0
        )
        if self.shared_closure_probability_adjustment != expected_closure:
            raise ValueError("shared gameplan closure does not match player effects")
        return self
