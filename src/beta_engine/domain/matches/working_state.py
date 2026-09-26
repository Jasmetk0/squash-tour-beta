"""Serializable authoritative state for resumable rally-by-rally match simulation."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.domain.matches.control import RallyCalibrationProfile
from beta_engine.domain.matches.gameplans import (
    EffectiveMatchGameplanSnapshot,
    PlayerGameplanState,
)
from beta_engine.domain.matches.models import MatchContext, MatchResult, SetResult
from beta_engine.domain.matches.rallies import RallyEvent
from beta_engine.domain.matches.rally_rules import EffectiveRallyRulesSnapshot
from beta_engine.domain.matches.stamina import (
    EffectiveMatchStaminaSnapshot,
    PlayerStaminaState,
)
from beta_engine.domain.matches.timing import EffectiveMatchTimingSnapshot


class MatchWorkingInput(BaseModel):
    """Immutable effective input frozen before the first rally is simulated."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["match_working_input.v1"] = "match_working_input.v1"
    context: MatchContext
    simulation_seed: int
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    timing: EffectiveMatchTimingSnapshot
    stamina: EffectiveMatchStaminaSnapshot
    rally_calibration: RallyCalibrationProfile
    gameplans: EffectiveMatchGameplanSnapshot
    rules: EffectiveRallyRulesSnapshot

    @model_validator(mode="after")
    def validate_participants(self) -> "MatchWorkingInput":
        ids = (
            self.context.player_a.player.player_id,
            self.context.player_b.player.player_id,
        )
        if tuple(profile.player_id for profile in self.stamina.player_profiles) != ids:
            raise ValueError("working-match stamina profiles must match participant order")
        if tuple(profile.player_id for profile in self.gameplans.natural_style_profiles) != ids:
            raise ValueError("working-match gameplans must match participant order")
        if {profile.player_id for profile in self.timing.player_restart_profiles} != set(ids):
            raise ValueError("working-match timing profiles must match participants")
        return self

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class MatchRallyWorkingState(BaseModel):
    """Dynamic match state required to resume at exactly the next rally."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["match_rally_working_state.v1"] = (
        "match_rally_working_state.v1"
    )
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    set_number: int = Field(ge=1)
    games_a: int = Field(ge=0)
    games_b: int = Field(ge=0)
    sets: tuple[SetResult, ...] = ()
    sets_won: dict[str, int]
    momentum_owner: str | None = None
    rally_events: tuple[RallyEvent, ...] = ()
    rally_index: int = Field(ge=1)
    rally_in_set: int = Field(ge=1)
    consecutive_replays: int = Field(ge=0)
    server_player_id: str = Field(min_length=1)
    service_box: Literal["LEFT", "RIGHT"]
    previous_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    stamina_states: tuple[PlayerStaminaState, PlayerStaminaState]
    gameplan_states: tuple[PlayerGameplanState, PlayerGameplanState]
    was_close_endgame: bool = False

    @model_validator(mode="after")
    def validate_state(self) -> "MatchRallyWorkingState":
        ids = tuple(self.sets_won)
        if len(ids) != 2:
            raise ValueError("working match requires exactly two set-score participants")
        if self.server_player_id not in self.sets_won:
            raise ValueError("working-match server must be a participant")
        if tuple(state.player_id for state in self.stamina_states) != ids:
            raise ValueError("working-match stamina state order must match set-score order")
        if tuple(state.player_id for state in self.gameplan_states) != ids:
            raise ValueError("working-match gameplan state order must match set-score order")
        if self.rally_events:
            if self.rally_events[-1].event_hash != self.previous_event_hash:
                raise ValueError("working-match previous hash must match the last rally")
            if self.rally_events[-1].rally_index != self.rally_index - 1:
                raise ValueError("working-match rally cursor is not contiguous")
        return self

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class MatchRallyStepOutcome(BaseModel):
    """Result of advancing a working match by at most one rally."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["match_rally_step_outcome.v1"] = (
        "match_rally_step_outcome.v1"
    )
    state: MatchRallyWorkingState | None = None
    rally: RallyEvent | None = None
    final_result: MatchResult | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "MatchRallyStepOutcome":
        if self.final_result is None and self.state is None:
            raise ValueError("incomplete rally step must return resumable state")
        if self.final_result is not None and self.state is not None:
            raise ValueError("completed rally step must not return resumable state")
        return self
