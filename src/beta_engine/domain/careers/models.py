"""Domain DTOs for deterministic multi-season career progression."""

from __future__ import annotations

from pydantic import BaseModel, Field

from beta_engine.domain.players import Player


class SeasonHealthInput(BaseModel):
    """Lightweight season-end health and workload signals per player."""

    fatigue_load: float = Field(default=0.0, ge=0.0, le=1.0)
    wear_load: float = Field(default=0.0, ge=0.0, le=1.0)
    injury_events: int = Field(default=0, ge=0)


class PlayerDevelopmentDelta(BaseModel):
    """Attribute-level before/after values with deterministic delta."""

    attribute: str
    before: int = Field(ge=1, le=99)
    after: int = Field(ge=1, le=99)
    delta: int = Field(ge=-20, le=20)
    reasons: list[str] = Field(default_factory=list)


class NextSeasonPlayerState(BaseModel):
    """Player state carried into the next season."""

    player: Player
    readiness: float = Field(ge=0.0, le=1.0)
    carryover_fatigue: float = Field(ge=0.0, le=1.0)


class PlayerSeasonTransition(BaseModel):
    """Structured explainability record for one player's season rollover."""

    player_id: str
    from_season: int = Field(ge=1900)
    to_season: int = Field(ge=1900)
    age_before: int = Field(ge=16, le=60)
    age_after: int = Field(ge=16, le=60)
    season_health_input: SeasonHealthInput
    development_deltas: list[PlayerDevelopmentDelta] = Field(default_factory=list)
    style_changed: bool = False
    style_change_reason: str | None = None
    notes: list[str] = Field(default_factory=list)


class CareerProgressionResult(BaseModel):
    """Deterministic progression result for one player."""

    transition: PlayerSeasonTransition
    next_state: NextSeasonPlayerState


class SeasonRolloverResult(BaseModel):
    """Deterministic full-pool season rollover output."""

    from_season: int = Field(ge=1900)
    to_season: int = Field(ge=1900)
    transitions: list[PlayerSeasonTransition] = Field(default_factory=list)
    next_players: list[Player] = Field(default_factory=list)
    next_states_by_player_id: dict[str, NextSeasonPlayerState] = Field(default_factory=dict)
    placeholders: list[str] = Field(default_factory=list)
