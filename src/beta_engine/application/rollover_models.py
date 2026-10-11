"""Application DTOs for season rollover integration across orchestration, persistence, and API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from beta_engine.domain.careers import NextSeasonPlayerState, PlayerSeasonTransition


class PersistedSeasonRollover(BaseModel):
    run_id: str
    from_season: int
    to_season: int
    transitioned_players: int = Field(ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class PersistedPlayerTransition(BaseModel):
    run_id: str
    from_season: int
    to_season: int
    player_id: str
    transition: PlayerSeasonTransition


class NextSeasonPlayerRecord(BaseModel):
    run_id: str
    from_season: int
    to_season: int
    player_id: str
    state: NextSeasonPlayerState


class SeasonRolloverResponse(BaseModel):
    run_id: str
    from_season: int
    to_season: int
    transitioned_players: int = Field(ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)
    transitions: list[PlayerSeasonTransition] = Field(default_factory=list)
    next_season_players: list[NextSeasonPlayerState] = Field(default_factory=list)
    already_persisted: bool = False


class SeasonRolloverSummaryResponse(BaseModel):
    run_id: str
    from_season: int
    to_season: int
    transitioned_players: int = Field(ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)
