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


class RallyEvent(BaseModel):
    schema_version: Literal["rally_event.v1"] = "rally_event.v1"
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
        return {
            key: _json_value(value)
            for key, value in values.items()
            if key not in {"event_hash", "event_hash_algorithm"}
        }

    @staticmethod
    def _content_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class MatchRallyLog(BaseModel):
    schema_version: Literal["match_rally_log.v1"] = "match_rally_log.v1"
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
        "between_rally_intervals",
        "game_breaks",
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
        cls, *, match_id: str, input_snapshot_hash: str, events: list[RallyEvent]
    ) -> MatchRallyLog:
        return cls(
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
