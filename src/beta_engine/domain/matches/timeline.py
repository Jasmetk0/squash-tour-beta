"""Immutable authoritative match timeline and its verifiable hash chain."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from itertools import pairwise
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator

from beta_engine.domain.matches.timing import RestartDecisionFactor, RestartIntent


class ReadinessComponent(str, Enum):
    SERVER = "SERVER"
    RECEIVER = "RECEIVER"
    OFFICIAL = "OFFICIAL"
    COURT = "COURT"


class MatchTimelineEventBase(BaseModel):
    match_id: str = Field(min_length=1)
    timeline_index: int = Field(ge=1)
    elapsed_seconds: float = Field(ge=0)
    previous_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_hash_algorithm: Literal["sha256"] = "sha256"
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: object) -> Self:
        draft = cls.model_construct(**values, event_hash="0" * 64)
        payload = draft.model_dump(
            mode="json", exclude={"event_hash", "event_hash_algorithm"}
        )
        return cls(**values, event_hash=cls._content_hash(payload))

    @model_validator(mode="after")
    def validate_event_hash(self) -> MatchTimelineEventBase:
        payload = self.model_dump(
            mode="json", exclude={"event_hash", "event_hash_algorithm"}
        )
        if self.event_hash != self._content_hash(payload):
            raise ValueError("match timeline event hash mismatch")
        return self

    @staticmethod
    def _content_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class RallyTimelineEvent(MatchTimelineEventBase):
    schema_version: Literal["rally_timeline_event.v1"] = "rally_timeline_event.v1"
    event_type: Literal["RALLY"] = "RALLY"
    rally_index: int = Field(ge=1)
    set_number: int = Field(ge=1)
    rally_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    elapsed_seconds: float = Field(gt=0)


class BetweenRallyIntervalEvent(MatchTimelineEventBase):
    schema_version: Literal["between_rally_interval_event.v1"] = (
        "between_rally_interval_event.v1"
    )
    event_type: Literal["BETWEEN_RALLY_INTERVAL"] = "BETWEEN_RALLY_INTERVAL"
    after_rally_index: int = Field(ge=1)
    set_number: int = Field(ge=1)
    server_player_id: str = Field(min_length=1)
    receiver_player_id: str = Field(min_length=1)
    server_intent: RestartIntent
    receiver_intent: RestartIntent
    server_decision_factors: tuple[RestartDecisionFactor, ...]
    receiver_decision_factors: tuple[RestartDecisionFactor, ...]
    server_ready_seconds: float = Field(ge=0)
    receiver_ready_seconds: float = Field(ge=0)
    official_ready_seconds: float = Field(ge=0)
    court_ready_seconds: float = Field(ge=0)
    dominant_readiness: ReadinessComponent
    conduct_outcome: Literal["NONE"] = "NONE"
    interval_seed: str = Field(pattern=r"^[0-9]+$")

    @model_validator(mode="after")
    def validate_readiness(self) -> BetweenRallyIntervalEvent:
        if self.server_player_id == self.receiver_player_id:
            raise ValueError("between-rally server and receiver must be distinct")
        readiness = {
            ReadinessComponent.SERVER: self.server_ready_seconds,
            ReadinessComponent.RECEIVER: self.receiver_ready_seconds,
            ReadinessComponent.OFFICIAL: self.official_ready_seconds,
            ReadinessComponent.COURT: self.court_ready_seconds,
        }
        maximum = round(max(readiness.values()), 3)
        if self.elapsed_seconds != maximum:
            raise ValueError("between-rally elapsed time must equal maximum readiness")
        if readiness[self.dominant_readiness] != max(readiness.values()):
            raise ValueError(
                "between-rally dominant readiness is not a maximum component"
            )
        return self


class GameBreakEvent(MatchTimelineEventBase):
    schema_version: Literal["game_break_event.v1"] = "game_break_event.v1"
    event_type: Literal["GAME_BREAK"] = "GAME_BREAK"
    after_rally_index: int = Field(ge=1)
    completed_set_number: int = Field(ge=1)
    nominal_seconds: float = Field(gt=0)
    duration_source: Literal["NOMINAL_RULE"] = "NOMINAL_RULE"
    dynamic_recovery_applied: Literal[False] = False

    @model_validator(mode="after")
    def validate_nominal_duration(self) -> GameBreakEvent:
        if self.elapsed_seconds != self.nominal_seconds:
            raise ValueError(
                "pre-alpha game break must use its stored nominal duration"
            )
        return self


MatchTimelineEvent = Annotated[
    RallyTimelineEvent | BetweenRallyIntervalEvent | GameBreakEvent,
    Field(discriminator="event_type"),
]


class MatchTimelineLog(BaseModel):
    schema_version: Literal["match_timeline_log.v1"] = "match_timeline_log.v1"
    match_id: str = Field(min_length=1)
    input_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    events: tuple[MatchTimelineEvent, ...]
    total_timeline_events: int = Field(ge=0)
    rally_event_count: int = Field(ge=0)
    between_rally_interval_count: int = Field(ge=0)
    game_break_count: int = Field(ge=0)
    rally_elapsed_seconds: float = Field(ge=0)
    between_rally_elapsed_seconds: float = Field(ge=0)
    game_break_elapsed_seconds: float = Field(ge=0)
    total_elapsed_seconds: float = Field(ge=0)
    unsupported_timeline_components: tuple[
        Literal[
            "medical_breaks",
            "objective_delay_events",
            "dynamic_stamina_recovery",
            "conduct_escalation",
            "non_scoring_replay_rallies",
            "variable_game_break_duration",
            "restart_rhythm_effects",
            "full_situational_restart_ai",
        ],
        ...,
    ] = (
        "medical_breaks",
        "objective_delay_events",
        "dynamic_stamina_recovery",
        "conduct_escalation",
        "non_scoring_replay_rallies",
        "variable_game_break_duration",
        "restart_rhythm_effects",
        "full_situational_restart_ai",
    )
    match_log_hash_algorithm: Literal["sha256"] = "sha256"
    match_log_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        match_id: str,
        input_snapshot_hash: str,
        events: list[MatchTimelineEvent],
    ) -> MatchTimelineLog:
        rally_events = [event for event in events if event.event_type == "RALLY"]
        intervals = [
            event for event in events if event.event_type == "BETWEEN_RALLY_INTERVAL"
        ]
        game_breaks = [event for event in events if event.event_type == "GAME_BREAK"]
        rally_seconds = round(sum(event.elapsed_seconds for event in rally_events), 3)
        interval_seconds = round(sum(event.elapsed_seconds for event in intervals), 3)
        game_break_seconds = round(
            sum(event.elapsed_seconds for event in game_breaks), 3
        )
        return cls(
            match_id=match_id,
            input_snapshot_hash=input_snapshot_hash,
            events=tuple(events),
            total_timeline_events=len(events),
            rally_event_count=len(rally_events),
            between_rally_interval_count=len(intervals),
            game_break_count=len(game_breaks),
            rally_elapsed_seconds=rally_seconds,
            between_rally_elapsed_seconds=interval_seconds,
            game_break_elapsed_seconds=game_break_seconds,
            total_elapsed_seconds=round(
                rally_seconds + interval_seconds + game_break_seconds, 3
            ),
            match_log_hash=(events[-1].event_hash if events else input_snapshot_hash),
        )

    @model_validator(mode="after")
    def validate_chain_and_totals(self) -> MatchTimelineLog:
        previous_hash = self.input_snapshot_hash
        previous_event: MatchTimelineEvent | None = None
        rally_indices: list[int] = []
        for expected_index, event in enumerate(self.events, start=1):
            if (
                event.match_id != self.match_id
                or event.timeline_index != expected_index
            ):
                raise ValueError(
                    "match timeline has mismatched identity or event order"
                )
            if event.previous_event_hash != previous_hash:
                raise ValueError("match timeline hash chain is broken")
            if event.event_type == "RALLY":
                rally_indices.append(event.rally_index)
            elif previous_event is None or previous_event.event_type != "RALLY":
                raise ValueError("match timeline time event must follow a rally")
            if (
                previous_event is not None
                and previous_event.event_type != "RALLY"
                and event.event_type != "RALLY"
            ):
                raise ValueError("match timeline cannot contain adjacent time events")
            previous_hash = event.event_hash
            previous_event = event
        if rally_indices != list(range(1, len(rally_indices) + 1)):
            raise ValueError("match timeline rally references are not contiguous")
        if self.events and self.events[0].event_type != "RALLY":
            raise ValueError("match timeline must start with a rally")
        if self.events and self.events[-1].event_type == "BETWEEN_RALLY_INTERVAL":
            raise ValueError("between-rally interval cannot end a match timeline")
        rally_positions = [
            index
            for index, event in enumerate(self.events)
            if event.event_type == "RALLY"
        ]
        for left, right in pairwise(rally_positions):
            current = self.events[left]
            following = self.events[right]
            elapsed = self.events[left + 1 : right]
            if len(elapsed) != 1:
                raise ValueError(
                    "match timeline requires one elapsed event between rallies"
                )
            expected_type = (
                "BETWEEN_RALLY_INTERVAL"
                if current.set_number == following.set_number
                else "GAME_BREAK"
            )
            if elapsed[0].event_type != expected_type:
                raise ValueError(
                    "match timeline uses the wrong event between rally sets"
                )
            if elapsed[0].after_rally_index != current.rally_index:
                raise ValueError(
                    "match timeline elapsed event references the wrong rally"
                )
            if (
                elapsed[0].event_type == "BETWEEN_RALLY_INTERVAL"
                and elapsed[0].set_number != current.set_number
            ) or (
                elapsed[0].event_type == "GAME_BREAK"
                and elapsed[0].completed_set_number != current.set_number
            ):
                raise ValueError(
                    "match timeline elapsed event references the wrong set"
                )
            if following.set_number not in {
                current.set_number,
                current.set_number + 1,
            }:
                raise ValueError("match timeline set order is broken")

        event_groups = {
            "RALLY": [event for event in self.events if event.event_type == "RALLY"],
            "BETWEEN_RALLY_INTERVAL": [
                event
                for event in self.events
                if event.event_type == "BETWEEN_RALLY_INTERVAL"
            ],
            "GAME_BREAK": [
                event for event in self.events if event.event_type == "GAME_BREAK"
            ],
        }
        if self.total_timeline_events != len(self.events):
            raise ValueError("match timeline total event count mismatch")
        if self.rally_event_count != len(event_groups["RALLY"]):
            raise ValueError("match timeline rally event count mismatch")
        if self.between_rally_interval_count != len(
            event_groups["BETWEEN_RALLY_INTERVAL"]
        ):
            raise ValueError("match timeline between-rally count mismatch")
        if self.game_break_count != len(event_groups["GAME_BREAK"]):
            raise ValueError("match timeline game-break count mismatch")

        expected_rally_seconds = round(
            sum(event.elapsed_seconds for event in event_groups["RALLY"]), 3
        )
        expected_interval_seconds = round(
            sum(
                event.elapsed_seconds
                for event in event_groups["BETWEEN_RALLY_INTERVAL"]
            ),
            3,
        )
        expected_game_break_seconds = round(
            sum(event.elapsed_seconds for event in event_groups["GAME_BREAK"]),
            3,
        )
        if self.rally_elapsed_seconds != expected_rally_seconds:
            raise ValueError("match timeline rally elapsed time mismatch")
        if self.between_rally_elapsed_seconds != expected_interval_seconds:
            raise ValueError("match timeline between-rally elapsed time mismatch")
        if self.game_break_elapsed_seconds != expected_game_break_seconds:
            raise ValueError("match timeline game-break elapsed time mismatch")
        if self.total_elapsed_seconds != round(
            expected_rally_seconds
            + expected_interval_seconds
            + expected_game_break_seconds,
            3,
        ):
            raise ValueError("match timeline total elapsed time mismatch")
        if self.match_log_hash != previous_hash:
            raise ValueError("match timeline final hash mismatch")
        return self
