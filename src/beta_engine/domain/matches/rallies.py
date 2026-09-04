"""Immutable authoritative rally events and their verifiable hash chain."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


class RallyTerminalTrigger(str, Enum):
    GOOD_RETURN_UNANSWERED = "GOOD_RETURN_UNANSWERED"
    SERVE_FAULT = "SERVE_FAULT"
    RETURN_DOWN = "RETURN_DOWN"
    RETURN_OUT = "RETURN_OUT"
    RETURN_NOT_UP = "RETURN_NOT_UP"
    INTERFERENCE_STOP = "INTERFERENCE_STOP"
    BALL_HIT_PLAYER = "BALL_HIT_PLAYER"
    PROCEDURAL_OR_OFFICIAL_STOP = "PROCEDURAL_OR_OFFICIAL_STOP"
    BALL_COURT_OR_EXTERNAL_STOP = "BALL_COURT_OR_EXTERNAL_STOP"
    HEALTH_STOP = "HEALTH_STOP"
    CONDUCT_STOP = "CONDUCT_STOP"


class RallyAnalyticalAttribution(str, Enum):
    CLEAN_WINNER = "CLEAN_WINNER"
    FORCED_ERROR = "FORCED_ERROR"
    UNFORCED_ERROR = "UNFORCED_ERROR"
    OFFICIAL_AWARD = "OFFICIAL_AWARD"
    NEUTRAL_REPLAY = "NEUTRAL_REPLAY"


class RallyScoreSnapshot(BaseModel):
    player_a_id: str = Field(min_length=1)
    player_b_id: str = Field(min_length=1)
    sets_a: int = Field(ge=0)
    sets_b: int = Field(ge=0)
    points_a: int = Field(ge=0)
    points_b: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_participants(self) -> RallyScoreSnapshot:
        if self.player_a_id == self.player_b_id:
            raise ValueError("rally score participants must be distinct")
        return self


class RallyScoreMutation(BaseModel):
    mutation_type: Literal["POINT_AWARDED"] = "POINT_AWARDED"
    player_id: str = Field(min_length=1)
    reason: Literal["RALLY_RESULT", "CONDUCT_STROKE", "OFFICIAL_ADJUSTMENT"] = (
        "RALLY_RESULT"
    )


class PostRallyStateSnapshot(BaseModel):
    score: RallyScoreSnapshot
    next_server_player_id: str = Field(min_length=1)
    set_complete: bool = False
    match_complete: bool = False
    unsupported_dynamic_state: tuple[
        Literal["physical_stamina", "explosive_stamina", "mental_stamina"], ...
    ] = ("physical_stamina", "explosive_stamina", "mental_stamina")


class PlayerRallyStaminaImpact(BaseModel):
    player_id: str = Field(min_length=1)
    explosive_fill_ratio: float = Field(ge=0, le=1)
    rally_fill_ratio: float = Field(ge=0, le=1)
    match_fill_ratio: float = Field(ge=0, le=1)
    weighted_nonlinear_deficit: float = Field(ge=0, le=1)
    strength_penalty: float = Field(ge=0, le=0.25)


class RallyEffortLevel(str, Enum):
    CONSERVE = "CONSERVE"
    NORMAL = "NORMAL"
    INCREASED = "INCREASED"
    MAXIMUM = "MAXIMUM"


class RallyEffortDecisionFactor(str, Enum):
    NATURAL_STYLE = "NATURAL_STYLE"
    PERCEIVED_LOW_RESERVE = "PERCEIVED_LOW_RESERVE"
    CLOSE_ENDGAME = "CLOSE_ENDGAME"
    TRAILING_SCORE = "TRAILING_SCORE"
    LEADING_SCORE = "LEADING_SCORE"
    TACTICAL_VARIATION = "TACTICAL_VARIATION"


class RallyControlState(str, Enum):
    STRONG_CONTROL_A = "STRONG_CONTROL_A"
    SLIGHT_CONTROL_A = "SLIGHT_CONTROL_A"
    NEUTRAL = "NEUTRAL"
    SLIGHT_CONTROL_B = "SLIGHT_CONTROL_B"
    STRONG_CONTROL_B = "STRONG_CONTROL_B"


class RallyControlTransitionKind(str, Enum):
    STAY = "STAY"
    LOCAL_SHIFT = "LOCAL_SHIFT"
    SIGNIFICANT_BREAK = "SIGNIFICANT_BREAK"
    DIRECT_REVERSAL = "DIRECT_REVERSAL"


class RallyPhasePace(str, Enum):
    PATIENT = "PATIENT"
    BALANCED = "BALANCED"
    FAST = "FAST"


class RallyClosureReason(str, Enum):
    OPENING_TERMINAL = "OPENING_TERMINAL"
    NATURAL_TERMINAL = "NATURAL_TERMINAL"
    HARD_SEGMENT_CAP = "HARD_SEGMENT_CAP"


class RallyEffortChangeReason(str, Enum):
    CONSERVE_LOW_RESERVE = "CONSERVE_LOW_RESERVE"
    RESPOND_TO_PRESSURE = "RESPOND_TO_PRESSURE"
    PRESS_CONTROL_ADVANTAGE = "PRESS_CONTROL_ADVANTAGE"
    TACTICAL_VARIATION = "TACTICAL_VARIATION"


class RallyEffortChange(BaseModel):
    player_id: str = Field(min_length=1)
    from_level: RallyEffortLevel
    to_level: RallyEffortLevel
    reason: RallyEffortChangeReason

    @model_validator(mode="after")
    def validate_change(self) -> RallyEffortChange:
        order = list(RallyEffortLevel)
        if abs(order.index(self.to_level) - order.index(self.from_level)) != 1:
            raise ValueError("within-rally effort changes must move exactly one level")
        return self


class PlayerControlSegmentWorkload(BaseModel):
    player_id: str = Field(min_length=1)
    effort_level: RallyEffortLevel
    intensity_multiplier: float = Field(ge=0.5, le=1.5)
    control_pressure_factor: float = Field(ge=0.5, le=1.5)
    workload_units: float = Field(ge=0)


class RallyControlSegment(BaseModel):
    segment_index: int = Field(ge=1, le=24)
    state_before: RallyControlState
    state_after: RallyControlState
    transition_kind: RallyControlTransitionKind
    phase_pace: RallyPhasePace
    estimated_shot_count: int = Field(ge=1, le=5)
    elapsed_seconds: float = Field(gt=0)
    closure_probability: float = Field(ge=0, le=1)
    closure_roll: float = Field(ge=0, lt=1)
    closed_rally: bool
    effort_changes: tuple[RallyEffortChange, ...] = ()
    player_workloads: tuple[PlayerControlSegmentWorkload, PlayerControlSegmentWorkload]

    @model_validator(mode="after")
    def validate_transition(self) -> RallyControlSegment:
        values = {
            RallyControlState.STRONG_CONTROL_A: 2,
            RallyControlState.SLIGHT_CONTROL_A: 1,
            RallyControlState.NEUTRAL: 0,
            RallyControlState.SLIGHT_CONTROL_B: -1,
            RallyControlState.STRONG_CONTROL_B: -2,
        }
        distance = abs(values[self.state_after] - values[self.state_before])
        expected = (
            RallyControlTransitionKind.STAY
            if distance == 0
            else RallyControlTransitionKind.LOCAL_SHIFT
            if distance == 1
            else RallyControlTransitionKind.DIRECT_REVERSAL
            if distance == 4
            else RallyControlTransitionKind.SIGNIFICANT_BREAK
        )
        if self.transition_kind != expected:
            raise ValueError("control transition kind does not match its distance")
        player_ids = tuple(workload.player_id for workload in self.player_workloads)
        if len(set(player_ids)) != 2:
            raise ValueError("control segment requires two distinct player workloads")
        if any(change.player_id not in player_ids for change in self.effort_changes):
            raise ValueError("effort change references a non-participant")
        if len({change.player_id for change in self.effort_changes}) != len(
            self.effort_changes
        ):
            raise ValueError("a player may change effort only once per segment")
        if self.closed_rally != (self.closure_roll < self.closure_probability):
            raise ValueError("segment closure does not match its probability roll")
        return self


class PlayerRallyControlWorkload(BaseModel):
    player_id: str = Field(min_length=1)
    opening_workload_units: float = Field(ge=0)
    segment_workload_units: float = Field(ge=0)
    terminal_workload_units: float = Field(ge=0)
    mean_control_pressure_factor: float = Field(ge=0.5, le=1.5)
    total_workload_units: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> PlayerRallyControlWorkload:
        expected = round(
            self.opening_workload_units
            + self.segment_workload_units
            + self.terminal_workload_units,
            4,
        )
        if self.total_workload_units != expected:
            raise ValueError("control workload phases do not match total")
        return self


class RallyControlTrace(BaseModel):
    calibration_version: Literal["pre_alpha_control_v1"] = "pre_alpha_control_v1"
    trace_seed: str = Field(pattern=r"^[0-9]+$")
    opening_state: RallyControlState
    opening_terminal_probability: float = Field(ge=0, le=1)
    opening_terminal_roll: float = Field(ge=0, lt=1)
    segments: tuple[RallyControlSegment, ...]
    final_state: RallyControlState
    closure_reason: RallyClosureReason
    control_segment_count: int = Field(ge=0, le=24)
    opening_shot_count: int = Field(ge=1, le=2)
    terminal_shot_count: int = Field(ge=0, le=1)
    estimated_shot_count: int = Field(ge=1)
    opening_elapsed_seconds: float = Field(gt=0)
    terminal_elapsed_seconds: float = Field(ge=0)
    active_rally_duration: float = Field(gt=0)
    probability_before_control_player_a: float = Field(ge=0, le=1)
    terminal_probability_player_a: float = Field(ge=0, le=1)
    terminal_roll: float = Field(ge=0, lt=1)
    player_workloads: tuple[PlayerRallyControlWorkload, PlayerRallyControlWorkload]

    @model_validator(mode="after")
    def validate_trace(self) -> RallyControlTrace:
        if self.control_segment_count != len(self.segments):
            raise ValueError("control segment count does not match trace")
        if self.closure_reason == RallyClosureReason.OPENING_TERMINAL:
            if self.segments:
                raise ValueError("opening terminal cannot contain control segments")
            if self.opening_terminal_roll >= self.opening_terminal_probability:
                raise ValueError("opening terminal does not match its probability roll")
            if self.terminal_shot_count != 0:
                raise ValueError("opening terminal cannot add a later terminal shot")
        elif not self.segments:
            raise ValueError("non-opening terminal requires control segments")
        elif self.opening_terminal_roll < self.opening_terminal_probability:
            raise ValueError("continued rally contradicts its opening-terminal roll")
        elif self.terminal_shot_count != 1:
            raise ValueError("continued rally requires one abstract terminal shot")
        previous = self.opening_state
        for expected_index, segment in enumerate(self.segments, start=1):
            if (
                segment.segment_index != expected_index
                or segment.state_before != previous
            ):
                raise ValueError("control trace continuity is broken")
            if segment.closed_rally != (expected_index == len(self.segments)):
                raise ValueError("only the final control segment may close the rally")
            previous = segment.state_after
        if self.final_state != previous:
            raise ValueError("control trace final state does not match segments")
        if (
            self.closure_reason == RallyClosureReason.HARD_SEGMENT_CAP
            and self.control_segment_count != 24
        ):
            raise ValueError("hard-cap closure requires segment 24")
        if (
            self.control_segment_count == 24
            and self.closure_reason != RallyClosureReason.HARD_SEGMENT_CAP
        ):
            raise ValueError("segment 24 must be recorded as the hard-cap closure")
        expected_shots = (
            self.opening_shot_count
            + sum(segment.estimated_shot_count for segment in self.segments)
            + self.terminal_shot_count
        )
        if self.estimated_shot_count != expected_shots:
            raise ValueError("control trace shot total is inconsistent")
        expected_duration = round(
            self.opening_elapsed_seconds
            + sum(segment.elapsed_seconds for segment in self.segments)
            + self.terminal_elapsed_seconds,
            3,
        )
        if self.active_rally_duration != expected_duration:
            raise ValueError("control trace duration total is inconsistent")
        if len({workload.player_id for workload in self.player_workloads}) != 2:
            raise ValueError("control trace requires two distinct player workloads")
        workload_player_ids = tuple(
            workload.player_id for workload in self.player_workloads
        )
        if any(
            tuple(workload.player_id for workload in segment.player_workloads)
            != workload_player_ids
            for segment in self.segments
        ):
            raise ValueError("control segment workload order is inconsistent")
        return self


class PlayerRallyEffort(BaseModel):
    player_id: str = Field(min_length=1)
    intended_level: RallyEffortLevel
    decision_factors: tuple[RallyEffortDecisionFactor, ...]
    perceived_reserve: float = Field(ge=0, le=1)
    requested_intensity_multiplier: float = Field(ge=0.5, le=1.5)
    executed_intensity_multiplier: float = Field(ge=0.5, le=1.5)
    outcome_strength_adjustment: float = Field(ge=-0.1, le=0.1)
    movement_efficiency_factor: float = Field(ge=0.5, le=1.5)
    style_workload_factor: float = Field(ge=0.5, le=1.5)
    pressure_workload_factor: float = Field(ge=0.5, le=1.5)
    workload_units: float = Field(ge=0)


class RallyEffortContext(BaseModel):
    """Logged pre-rally intent and resulting per-player physical cost."""

    calibration_version: Literal["pre_alpha_effort_v1"] = "pre_alpha_effort_v1"
    base_workload_units: float = Field(ge=0)
    probability_before_effort_player_a: float = Field(ge=0, le=1)
    probability_after_effort_player_a: float = Field(ge=0, le=1)
    player_efforts: tuple[PlayerRallyEffort, PlayerRallyEffort]

    @model_validator(mode="after")
    def validate_players(self) -> RallyEffortContext:
        if len({effort.player_id for effort in self.player_efforts}) != 2:
            raise ValueError("rally effort context requires two distinct players")
        return self


class RallyStaminaOutcomeContext(BaseModel):
    calibration_version: Literal["pre_alpha_outcome_v1"] = "pre_alpha_outcome_v1"
    base_probability_player_a: float = Field(ge=0, le=1)
    adjusted_probability_player_a: float = Field(ge=0, le=1)
    player_impacts: tuple[PlayerRallyStaminaImpact, PlayerRallyStaminaImpact]

    @model_validator(mode="after")
    def validate_players(self) -> RallyStaminaOutcomeContext:
        if len({impact.player_id for impact in self.player_impacts}) != 2:
            raise ValueError("rally stamina impact requires two distinct players")
        return self


class RallyEvent(BaseModel):
    schema_version: Literal[
        "rally_event.v1", "rally_event.v2", "rally_event.v3", "rally_event.v4"
    ] = "rally_event.v1"
    match_id: str = Field(min_length=1)
    rally_index: int = Field(ge=1)
    set_number: int = Field(ge=1)
    rally_in_set: int = Field(ge=1)
    serving_player_id: str = Field(min_length=1)
    winner_player_id: str = Field(min_length=1)
    primary_terminal_trigger: RallyTerminalTrigger
    terminal_subtype: str | None = None
    official_resolution: Literal["POINT_AWARDED"] = "POINT_AWARDED"
    analytical_attribution: RallyAnalyticalAttribution
    score_before: RallyScoreSnapshot
    score_mutations: tuple[RallyScoreMutation, ...]
    score_after: RallyScoreSnapshot
    abstract_segments: int = Field(ge=0, le=24)
    estimated_shot_count: int = Field(ge=1)
    elapsed_seconds: float = Field(gt=0)
    rally_seed: str = Field(pattern=r"^[0-9]+$")
    post_rally_state: PostRallyStateSnapshot
    stamina_outcome_context: RallyStaminaOutcomeContext | None = None
    effort_context: RallyEffortContext | None = None
    control_trace: RallyControlTrace | None = None
    side_incidents: tuple[dict[str, object], ...] = ()
    previous_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_hash_algorithm: Literal["sha256"] = "sha256"
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: object) -> RallyEvent:
        draft = cls.model_construct(**values, event_hash="0" * 64)
        payload = cls._hash_payload(
            draft.model_dump(
                mode="json", exclude={"event_hash", "event_hash_algorithm"}
            )
        )
        return cls(**values, event_hash=cls._content_hash(payload))

    @model_validator(mode="after")
    def validate_event(self) -> RallyEvent:
        participants = {self.score_before.player_a_id, self.score_before.player_b_id}
        if (
            self.score_before.player_a_id != self.score_after.player_a_id
            or self.score_before.player_b_id != self.score_after.player_b_id
        ):
            raise ValueError("rally score snapshots have mismatched participants")
        if (
            self.serving_player_id not in participants
            or self.winner_player_id not in participants
        ):
            raise ValueError("rally server and winner must be match participants")
        if not self.score_mutations or (
            self.score_mutations[0].player_id != self.winner_player_id
            or self.score_mutations[0].reason != "RALLY_RESULT"
        ):
            raise ValueError(
                "completed scoring rally must start with its winner point mutation"
            )
        expected_points = [self.score_before.points_a, self.score_before.points_b]
        for mutation in self.score_mutations:
            if mutation.player_id not in participants:
                raise ValueError("rally score mutation must reference a participant")
            point_index = (
                0 if mutation.player_id == self.score_before.player_a_id else 1
            )
            expected_points[point_index] += 1
        if (self.score_after.points_a, self.score_after.points_b) != tuple(
            expected_points
        ):
            raise ValueError("rally score_after does not apply its point mutation")
        set_delta = (
            self.score_after.sets_a - self.score_before.sets_a,
            self.score_after.sets_b - self.score_before.sets_b,
        )
        allowed_set_deltas = (
            {(1, 0), (0, 1)} if self.post_rally_state.set_complete else {(0, 0)}
        )
        if set_delta not in allowed_set_deltas:
            raise ValueError("rally score_after has an invalid set-score transition")
        if (
            self.post_rally_state.match_complete
            and not self.post_rally_state.set_complete
        ):
            raise ValueError("match-complete rally must also complete its set")
        if self.post_rally_state.score != self.score_after:
            raise ValueError(
                "post-rally state does not contain authoritative score_after"
            )
        if self.post_rally_state.next_server_player_id != self.winner_player_id:
            raise ValueError("rally winner must serve next in current individual rules")
        if self.schema_version in {
            "rally_event.v2",
            "rally_event.v3",
            "rally_event.v4",
        }:
            if self.stamina_outcome_context is None:
                raise ValueError("v2 rally event requires stamina outcome context")
            if tuple(
                impact.player_id
                for impact in self.stamina_outcome_context.player_impacts
            ) != (
                self.score_before.player_a_id,
                self.score_before.player_b_id,
            ):
                raise ValueError("rally stamina impacts do not match participant order")
        elif self.stamina_outcome_context is not None:
            raise ValueError("v1 rally event cannot contain stamina outcome context")
        if self.schema_version in {"rally_event.v3", "rally_event.v4"}:
            if self.effort_context is None:
                raise ValueError("v3 rally event requires effort context")
            if tuple(
                effort.player_id for effort in self.effort_context.player_efforts
            ) != (
                self.score_before.player_a_id,
                self.score_before.player_b_id,
            ):
                raise ValueError("rally effort does not match participant order")
        elif self.effort_context is not None:
            raise ValueError("legacy rally event cannot contain effort context")
        if self.schema_version == "rally_event.v4":
            if self.control_trace is None or self.effort_context is None:
                raise ValueError("v4 rally event requires effort and control contexts")
            if (
                self.control_trace.control_segment_count != self.abstract_segments
                or self.control_trace.estimated_shot_count != self.estimated_shot_count
                or self.control_trace.active_rally_duration != self.elapsed_seconds
            ):
                raise ValueError("rally summary does not match control trace")
            if (
                self.effort_context.probability_after_effort_player_a
                != self.control_trace.probability_before_control_player_a
            ):
                raise ValueError("effort and control probabilities do not connect")
            expected_winner = (
                self.score_before.player_a_id
                if self.control_trace.terminal_roll
                < self.control_trace.terminal_probability_player_a
                else self.score_before.player_b_id
            )
            if self.winner_player_id != expected_winner:
                raise ValueError("rally winner does not match control terminal roll")
            if tuple(
                workload.player_id
                for workload in self.control_trace.player_workloads
            ) != (
                self.score_before.player_a_id,
                self.score_before.player_b_id,
            ):
                raise ValueError(
                    "control workloads do not match match participant order"
                )
            workload_by_player = {
                workload.player_id: workload.total_workload_units
                for workload in self.control_trace.player_workloads
            }
            if any(
                effort.workload_units != workload_by_player.get(effort.player_id)
                for effort in self.effort_context.player_efforts
            ):
                raise ValueError("effort workload does not match control trace")
            effort_levels = {
                effort.player_id: effort.intended_level
                for effort in self.effort_context.player_efforts
            }
            for segment in self.control_trace.segments:
                for change in segment.effort_changes:
                    if effort_levels[change.player_id] != change.from_level:
                        raise ValueError("control effort change sequence is broken")
                    effort_levels[change.player_id] = change.to_level
                if any(
                    workload.effort_level != effort_levels[workload.player_id]
                    for workload in segment.player_workloads
                ):
                    raise ValueError("segment workload uses the wrong effort level")
        elif self.control_trace is not None:
            raise ValueError("legacy rally event cannot contain control trace")
        if self.event_hash != self._content_hash(
            self._hash_payload(
                self.model_dump(
                    mode="json", exclude={"event_hash", "event_hash_algorithm"}
                )
            )
        ):
            raise ValueError("rally event hash mismatch")
        return self

    @staticmethod
    def _hash_payload(values: dict[str, object]) -> dict[str, object]:
        payload = {
            key: _json_value(value)
            for key, value in values.items()
            if key not in {"event_hash", "event_hash_algorithm"}
        }
        if values.get("schema_version") == "rally_event.v1":
            payload.pop("stamina_outcome_context", None)
        if values.get("schema_version") in {"rally_event.v1", "rally_event.v2"}:
            payload.pop("effort_context", None)
        if values.get("schema_version") in {
            "rally_event.v1",
            "rally_event.v2",
            "rally_event.v3",
        }:
            payload.pop("control_trace", None)
        return payload

    @staticmethod
    def _content_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class MatchRallyLog(BaseModel):
    schema_version: Literal[
        "match_rally_log.v1",
        "match_rally_log.v2",
        "match_rally_log.v3",
        "match_rally_log.v4",
    ] = "match_rally_log.v4"
    match_id: str = Field(min_length=1)
    input_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    events: tuple[RallyEvent, ...]
    total_rallies: int = Field(ge=0)
    rally_elapsed_seconds: float = Field(ge=0)
    estimated_shot_count: int = Field(ge=0)
    unsupported_timeline_components: tuple[
        Literal[
            "between_rally_intervals",
            "game_breaks",
            "medical_breaks",
            "dynamic_stamina",
            "non_scoring_replay_rallies",
            "interference_and_official_calls",
            "health_and_conduct_incidents",
        ],
        ...,
    ] = (
        "medical_breaks",
        "dynamic_stamina",
        "non_scoring_replay_rallies",
        "interference_and_official_calls",
        "health_and_conduct_incidents",
    )
    match_log_hash_algorithm: Literal["sha256"] = "sha256"
    match_log_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        match_id: str,
        input_snapshot_hash: str,
        events: list[RallyEvent],
        schema_version: Literal[
            "match_rally_log.v1",
            "match_rally_log.v2",
            "match_rally_log.v3",
            "match_rally_log.v4",
        ]
        | None = None,
    ) -> MatchRallyLog:
        event_versions = {event.schema_version for event in events}
        inferred_schema_version = (
            "match_rally_log.v4"
            if "rally_event.v4" in event_versions
            else "match_rally_log.v3"
            if "rally_event.v3" in event_versions
            else "match_rally_log.v2"
            if "rally_event.v2" in event_versions
            else "match_rally_log.v1"
        )
        return cls(
            schema_version=schema_version or inferred_schema_version,
            match_id=match_id,
            input_snapshot_hash=input_snapshot_hash,
            events=tuple(events),
            total_rallies=len(events),
            rally_elapsed_seconds=round(
                sum(event.elapsed_seconds for event in events), 3
            ),
            estimated_shot_count=sum(event.estimated_shot_count for event in events),
            match_log_hash=events[-1].event_hash if events else input_snapshot_hash,
        )

    @model_validator(mode="after")
    def validate_chain(self) -> MatchRallyLog:
        if self.schema_version == "match_rally_log.v4" and any(
            event.schema_version != "rally_event.v4" for event in self.events
        ):
            raise ValueError("rally log and event schema versions do not agree")
        previous_hash = self.input_snapshot_hash
        previous_event: RallyEvent | None = None
        for expected_index, event in enumerate(self.events, start=1):
            if event.match_id != self.match_id or event.rally_index != expected_index:
                raise ValueError(
                    "rally log has mismatched match identity or event order"
                )
            if event.previous_event_hash != previous_hash:
                raise ValueError("rally log hash chain is broken")
            if previous_event is not None:
                previous_score = previous_event.score_after
                current_score = event.score_before
                if event.set_number == previous_event.set_number:
                    if current_score != previous_score:
                        raise ValueError("rally log score continuity is broken")
                elif event.set_number == previous_event.set_number + 1:
                    if (
                        current_score.sets_a != previous_score.sets_a
                        or current_score.sets_b != previous_score.sets_b
                        or current_score.points_a != 0
                        or current_score.points_b != 0
                    ):
                        raise ValueError(
                            "new set does not continue the previous rally state"
                        )
                else:
                    raise ValueError("rally log set order is broken")
            previous_hash = event.event_hash
            previous_event = event
        if self.total_rallies != len(self.events):
            raise ValueError("rally log total_rallies mismatch")
        if self.rally_elapsed_seconds != round(
            sum(event.elapsed_seconds for event in self.events), 3
        ):
            raise ValueError("rally log elapsed time mismatch")
        if self.estimated_shot_count != sum(
            event.estimated_shot_count for event in self.events
        ):
            raise ValueError("rally log shot-count mismatch")
        if self.match_log_hash != previous_hash:
            raise ValueError("rally log final hash mismatch")
        return self
