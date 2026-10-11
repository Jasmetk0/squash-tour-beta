"""Deterministic tournament progression DTOs for module 6 event orchestration."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from beta_engine.domain.draws.models import DrawEntrantType, DrawType


class MatchDisposition(str, Enum):
    PLAYED = "PLAYED"
    BYE_ADVANCE = "BYE_ADVANCE"
    WALKOVER_ADVANCE = "WALKOVER_ADVANCE"
    UNRESOLVED = "UNRESOLVED"


class PlaceholderResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class PlaceholderResolution(BaseModel):
    draw_type: DrawType
    slot_index: int = Field(gt=0)
    placeholder_type: DrawEntrantType
    placeholder_entry_id: str | None = None
    resolved_player_id: str | None = None
    source_label: str
    status: PlaceholderResolutionStatus


class TournamentMatchRecord(BaseModel):
    draw_type: DrawType
    node_id: str
    round_number: int = Field(ge=1)
    round_sequence: int = Field(ge=1)
    top_source: str
    bottom_source: str
    top_player_id: str | None = None
    bottom_player_id: str | None = None
    winner_player_id: str | None = None
    loser_player_id: str | None = None
    disposition: MatchDisposition
    match_id: str | None = None
    match_result: dict | None = None


class TournamentRoundResult(BaseModel):
    draw_type: DrawType
    round_number: int = Field(ge=1)
    matches: list[TournamentMatchRecord]


class QualificationOutcome(BaseModel):
    rounds: list[TournamentRoundResult]
    qualifiers_in_order: list[str] = Field(default_factory=list)
    unresolved_qualifier_count: int = Field(ge=0, default=0)
    qualifier_rounds_played: int = Field(ge=0, default=0)


class Placement(BaseModel):
    player_id: str
    finish: str


class MainDrawOutcome(BaseModel):
    rounds: list[TournamentRoundResult]
    champion_player_id: str | None = None
    finalist_player_id: str | None = None
    placements: list[Placement] = Field(default_factory=list)


class TournamentResult(BaseModel):
    event_id: str
    season: int = Field(ge=1900)
    week: int = Field(ge=1, le=61)
    qualification: QualificationOutcome
    qualifier_slot_resolutions: list[PlaceholderResolution] = Field(default_factory=list)
    main_draw: MainDrawOutcome
