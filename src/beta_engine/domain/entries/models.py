"""Deterministic entry and acceptance list domain models for MVP module 3."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from beta_engine.domain.tournaments.models import TourLevel


class EntryTarget(str, Enum):
    NONE = "NONE"
    MAIN = "MAIN"
    QUALIFICATION = "QUALIFICATION"


class AcceptanceStatus(str, Enum):
    APPLICANT_MAIN = "APPLICANT_MAIN"
    APPLICANT_QUALIFICATION = "APPLICANT_QUALIFICATION"
    DIRECT_ACCEPTANCE = "DIRECT_ACCEPTANCE"
    QUALIFICATION_ACCEPTANCE = "QUALIFICATION_ACCEPTANCE"
    WILD_CARD_PLACEHOLDER = "WILD_CARD_PLACEHOLDER"
    QUALIFIER_PLACEHOLDER = "QUALIFIER_PLACEHOLDER"
    WITHDRAWAL_PLACEHOLDER = "WITHDRAWAL_PLACEHOLDER"
    LATE_REPLACEMENT_PLACEHOLDER = "LATE_REPLACEMENT_PLACEHOLDER"
    NOT_ACCEPTED = "NOT_ACCEPTED"


class EntryDecision(BaseModel):
    """Deterministic decision payload for one player and one tournament."""

    player_id: str
    event_id: str
    week: int = Field(ge=1, le=61)
    target: EntryTarget
    entry_score: float
    entry_probability: float = Field(ge=0.0, le=1.0)
    travel_score: float = Field(ge=0.0, le=1.0)
    quality_score: float = Field(ge=0.0, le=1.0)
    prestige_score: float = Field(ge=0.0, le=1.0)


class TournamentEntry(BaseModel):
    """Represents an applicant, accepted entry, or placeholder slot."""

    entry_id: str
    event_id: str
    season: int = Field(ge=1900)
    week: int = Field(ge=1, le=61)
    player_id: str | None = None
    slot: EntryTarget
    status: AcceptanceStatus
    tour_level: TourLevel
    category: str
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    entry_score: float | None = None
    ranking_priority: int | None = None
    placeholder_reason: str | None = None


class AcceptanceList(BaseModel):
    """Main-draw and qualification intake result for a single event."""

    event_id: str
    template_id: str
    season: int = Field(ge=1900)
    week: int = Field(ge=1, le=61)
    main_draw_size: int = Field(gt=0)
    qualification_draw_size: int = Field(ge=0)
    qualifier_spots: int = Field(ge=0)
    wild_card_slots: int = Field(ge=0)
    main_draw_applicants: list[TournamentEntry]
    qualification_applicants: list[TournamentEntry]
    main_draw_entries: list[TournamentEntry]
    qualification_entries: list[TournamentEntry]
    pending_week_conflict_resolution: bool = True


class EntryTuningConfig(BaseModel):
    """Config-driven entry behavior constants."""

    player_quality_weight: float = 0.36
    tournament_strength_weight: float = 0.18
    prestige_weight: float = 0.14
    travel_weight: float = 0.12
    ambition_weight: float = 0.08
    professionalism_weight: float = 0.04
    schedule_aggression_weight: float = 0.05
    travel_tolerance_weight: float = 0.04
    age_weight: float = 0.03
    baseline_bias: float = -0.2
    main_quality_target: float = 0.62
    qualification_quality_target: float = 0.46
    main_margin: float = 0.03
    qualification_margin: float = 0.12
    direct_acceptance_slots_buffer: int = 0
    withdrawal_placeholder_slots: int = 1
    late_replacement_placeholder_slots: int = 1
    category_strength: dict[str, float] = Field(default_factory=dict)
    category_prestige: dict[str, float] = Field(default_factory=dict)
    tour_level_strength: dict[TourLevel, float] = Field(default_factory=dict)
    tour_level_prestige: dict[TourLevel, float] = Field(default_factory=dict)
