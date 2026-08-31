"""Standalone deterministic set-by-set squash match models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from beta_engine.domain.matches.rallies import MatchRallyLog
from beta_engine.domain.players.models import Player


class MatchTerminationReason(str, Enum):
    COMPLETED = "COMPLETED"
    RETIREMENT = "RETIREMENT"


class RetirementTrigger(str, Enum):
    EXPLICIT_SET_START = "EXPLICIT_SET_START"
    PROBABILISTIC_SET_START = "PROBABILISTIC_SET_START"


class MatchParticipantContext(BaseModel):
    """Context modifiers for one participant without mutating player state."""

    player: Player
    form_modifier: float = Field(default=0.0, ge=-0.35, le=0.35)
    fatigue_modifier: float = Field(default=0.0, ge=-0.35, le=0.35)
    health_modifier: float = Field(default=0.0, ge=-0.35, le=0.35)
    travel_modifier: float = Field(default=0.0, ge=-0.35, le=0.35)


class RetirementRule(BaseModel):
    """Optional retirement support for deterministic standalone matches."""

    enabled: bool = False
    retired_player_id: str | None = None
    trigger: RetirementTrigger = RetirementTrigger.EXPLICIT_SET_START
    set_number: int | None = Field(default=None, ge=1)
    probability: float = Field(default=0.0, ge=0.0, le=1.0)


class MatchContext(BaseModel):
    """Input object for standalone player-vs-player match simulation."""

    match_id: str
    player_a: MatchParticipantContext
    player_b: MatchParticipantContext
    best_of: int = Field(default=5)
    games_to: int = Field(default=11)
    win_by: int = Field(default=2)
    upset_variance: float = Field(default=0.12, ge=0.0, le=0.35)
    retirement_rule: RetirementRule = Field(default_factory=RetirementRule)

    @model_validator(mode="after")
    def validate_match_settings(self) -> MatchContext:
        if self.player_a.player.player_id == self.player_b.player.player_id:
            raise ValueError("player_a and player_b must be distinct players")
        if self.best_of < 1 or self.best_of % 2 == 0:
            raise ValueError("best_of must be a positive odd number")
        if self.games_to < 1:
            raise ValueError("games_to must be positive")
        if self.win_by < 1:
            raise ValueError("win_by must be positive")
        retirement = self.retirement_rule
        if retirement.enabled and retirement.retired_player_id not in {
            self.player_a.player.player_id,
            self.player_b.player.player_id,
        }:
            raise ValueError("retired_player_id must reference one of the two match players")
        if retirement.enabled and retirement.trigger == RetirementTrigger.EXPLICIT_SET_START and retirement.set_number is None:
            raise ValueError("explicit set-start retirement requires set_number")
        return self


class SetResult(BaseModel):
    set_number: int = Field(ge=1)
    winner_player_id: str
    loser_player_id: str
    winner_games: int = Field(ge=0)
    loser_games: int = Field(ge=0)
    was_close_endgame: bool = False
    ended_by_retirement: bool = False


class MatchResult(BaseModel):
    match_id: str
    winner_player_id: str
    loser_player_id: str
    player_a_id: str
    player_b_id: str
    best_of: int
    games_to: int
    win_by: int
    sets: list[SetResult]
    sets_won: dict[str, int]
    termination_reason: MatchTerminationReason
    retired_player_id: str | None = None
    retired_at_set_start: int | None = None
    rally_log: MatchRallyLog | None = None

    @model_validator(mode="after")
    def validate_rally_log_result(self) -> MatchResult:
        if self.rally_log is None:
            return self
        if self.rally_log.match_id != self.match_id:
            raise ValueError("match result and rally log identities do not agree")
        if self.rally_log.total_rallies != sum(
            set_result.winner_games + set_result.loser_games
            for set_result in self.sets
        ):
            raise ValueError("match result score and rally count do not agree")
        if {event.set_number for event in self.rally_log.events} != {
            set_result.set_number for set_result in self.sets
        }:
            raise ValueError("match result and rally log contain different played sets")
        events_by_set = {
            set_number: [
                event
                for event in self.rally_log.events
                if event.set_number == set_number
            ]
            for set_number in range(1, len(self.sets) + 1)
        }
        for set_result in self.sets:
            events = events_by_set[set_result.set_number]
            if not events:
                raise ValueError("played set has no authoritative rally events")
            final_score = events[-1].score_after
            winner_points = (
                final_score.points_a
                if set_result.winner_player_id == self.player_a_id
                else final_score.points_b
            )
            loser_points = (
                final_score.points_b
                if set_result.winner_player_id == self.player_a_id
                else final_score.points_a
            )
            if (
                winner_points != set_result.winner_games
                or loser_points != set_result.loser_games
            ):
                raise ValueError("set result does not match its authoritative rally events")
        if self.rally_log.events:
            final_score = self.rally_log.events[-1].score_after
            if self.sets_won != {
                self.player_a_id: final_score.sets_a,
                self.player_b_id: final_score.sets_b,
            }:
                raise ValueError("match sets_won does not match authoritative rally log")
        return self
