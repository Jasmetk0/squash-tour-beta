"""World Tour Finals qualification, seeding, and event result DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from beta_engine.domain.matches.models import MatchResult


class FinalsQualifiedPlayer(BaseModel):
    """One player's qualification metadata derived from race standings."""

    player_id: str
    race_rank: int = Field(ge=1)
    race_points: int = Field(ge=0)
    seed: int = Field(ge=1)


class FinalsQualificationResult(BaseModel):
    """Explainable qualification and reserve list snapshot."""

    target_season: int = Field(ge=1900)
    qualifier_count: int = Field(ge=1)
    reserve_count: int = Field(ge=0)
    qualified: list[FinalsQualifiedPlayer] = Field(default_factory=list)
    reserves: list[FinalsQualifiedPlayer] = Field(default_factory=list)
    ineligible_race_entries: list[str] = Field(default_factory=list)


class FinalsGroupSlot(BaseModel):
    group_id: str
    slot: int = Field(ge=1)
    player: FinalsQualifiedPlayer


class FinalsGroupMatch(BaseModel):
    match_id: str
    group_id: str
    match_number: int = Field(ge=1)
    player_a_id: str
    player_b_id: str
    winner_player_id: str
    loser_player_id: str
    match_result: MatchResult


class FinalsGroupStandingEntry(BaseModel):
    group_id: str
    rank: int = Field(ge=1)
    player_id: str
    seed: int = Field(ge=1)
    match_wins: int = Field(ge=0)
    match_losses: int = Field(ge=0)
    set_wins: int = Field(ge=0)
    set_losses: int = Field(ge=0)
    set_differential: int
    game_wins: int = Field(ge=0)
    game_losses: int = Field(ge=0)
    game_differential: int


class FinalsGroup(BaseModel):
    group_id: str
    slots: list[FinalsGroupSlot] = Field(default_factory=list)
    matches: list[FinalsGroupMatch] = Field(default_factory=list)
    standings: list[FinalsGroupStandingEntry] = Field(default_factory=list)


class FinalsKnockoutMatch(BaseModel):
    stage: str
    match_id: str
    player_a_id: str
    player_b_id: str
    winner_player_id: str
    loser_player_id: str
    match_result: MatchResult


class FinalsPlacement(BaseModel):
    player_id: str
    finish: str


class FinalsResult(BaseModel):
    event_id: str
    season: int = Field(ge=1900)
    qualification: FinalsQualificationResult
    groups: list[FinalsGroup] = Field(default_factory=list)
    knockout: list[FinalsKnockoutMatch] = Field(default_factory=list)
    placements: list[FinalsPlacement] = Field(default_factory=list)
