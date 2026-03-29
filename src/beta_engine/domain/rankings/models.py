"""Deterministic DTOs for ranking/race points resolution and standings."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CompletedTournamentPointsInput(BaseModel):
    """Structured tournament payload used by ranking/race point resolution."""

    event_id: str = Field(min_length=1)
    season: int = Field(ge=1900)
    week: int = Field(ge=1, le=61)
    template_id: str = Field(min_length=1)
    point_distribution_ref: str | None = None
    point_distribution: dict[str, int] | None = None
    placements: list[dict[str, str]] = Field(default_factory=list)
    rounds: list[dict] = Field(default_factory=list)


class TournamentPointAward(BaseModel):
    """Resolved point award for one player from one completed tournament."""

    event_id: str
    season: int = Field(ge=1900)
    week: int = Field(ge=1, le=61)
    template_id: str
    player_id: str
    finish: str
    points_awarded: int = Field(ge=0)


class RankedResultContribution(BaseModel):
    """Explainable contribution metadata for ranking/race standings."""

    event_id: str
    season: int = Field(ge=1900)
    week: int = Field(ge=1, le=61)
    finish: str
    points_awarded: int = Field(ge=0)
    active_in_rolling_window: bool
    counted_in_best_12: bool
    counted_in_race: bool


class PlayerRankingEntry(BaseModel):
    rank: int = Field(ge=1)
    player_id: str
    ranking_points: int = Field(ge=0)
    counted_results: int = Field(ge=0)
    contributions: list[RankedResultContribution] = Field(default_factory=list)


class PlayerRaceEntry(BaseModel):
    rank: int = Field(ge=1)
    player_id: str
    race_points: int = Field(ge=0)
    counted_results: int = Field(ge=0)
    contributions: list[RankedResultContribution] = Field(default_factory=list)


class RankingTable(BaseModel):
    as_of_season: int = Field(ge=1900)
    as_of_week: int = Field(ge=1, le=61)
    window_weeks: int = Field(ge=1)
    best_of_results: int = Field(ge=1)
    standings: list[PlayerRankingEntry] = Field(default_factory=list)


class RaceTable(BaseModel):
    target_season: int = Field(ge=1900)
    standings: list[PlayerRaceEntry] = Field(default_factory=list)


class RankingRaceReport(BaseModel):
    point_awards: list[TournamentPointAward] = Field(default_factory=list)
    ranking: RankingTable
    race: RaceTable
