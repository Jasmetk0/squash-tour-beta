"""Tournament templates and calendar domain models (config-driven)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


TourLevel = Literal["WORLD_TOUR", "ELITE_TOUR"]


class LuckyLoserRules(BaseModel):
    """Rules metadata for lucky-loser substitution behavior."""

    enabled: bool = True
    max_spots: int = Field(ge=0)
    replacement_window: str = "pre_main_draw_round_1"


class TournamentPointDistribution(BaseModel):
    """Optional inline point distribution for template categories."""

    winner: int = Field(ge=0)
    finalist: int = Field(ge=0)
    semifinalist: int = Field(ge=0)
    quarterfinalist: int = Field(ge=0)
    round_of_16: int = Field(default=0, ge=0)
    round_of_32: int = Field(default=0, ge=0)


class TournamentTemplate(BaseModel):
    """Reusable tournament template shared by season calendar entries."""

    template_id: str = Field(min_length=3)
    tour_level: TourLevel
    category: str = Field(min_length=1)
    event_name: str = Field(min_length=1)
    region: str = Field(min_length=1)
    host_country: str = Field(min_length=3, max_length=3)
    main_draw_size: int = Field(gt=0)
    qualification_draw_size: int = Field(ge=0)
    seeds_count: int = Field(ge=0)
    qualifier_spots: int = Field(ge=0)
    wild_cards: int = Field(ge=0)
    byes: int = Field(ge=0)
    lucky_loser_rules: LuckyLoserRules
    point_distribution_ref: str | None = None
    point_distribution: TournamentPointDistribution | None = None
    event_duration_days: int = Field(gt=0)
    qualification_duration_days: int = Field(ge=0)
    preferred_week_type: str | None = None
    seasonal_grouping: str | None = None

    @model_validator(mode="after")
    def validate_point_distribution_source(self) -> "TournamentTemplate":
        if self.point_distribution_ref is None and self.point_distribution is None:
            raise ValueError(
                "TournamentTemplate requires point_distribution_ref or point_distribution"
            )
        if self.seeds_count > self.main_draw_size:
            raise ValueError("seeds_count cannot exceed main_draw_size")
        if self.qualifier_spots > self.main_draw_size:
            raise ValueError("qualifier_spots cannot exceed main_draw_size")
        if self.wild_cards > self.main_draw_size:
            raise ValueError("wild_cards cannot exceed main_draw_size")
        if self.byes > self.main_draw_size:
            raise ValueError("byes cannot exceed main_draw_size")
        return self


class TournamentTemplatesConfig(BaseModel):
    """Top-level template config payload."""

    templates: list[TournamentTemplate] = Field(min_length=1)


class CalendarEvent(BaseModel):
    """Scheduled tournament event for a specific season week."""

    event_id: str = Field(min_length=3)
    season: int = Field(ge=1900)
    week: int = Field(ge=1, le=61)
    template_id: str = Field(min_length=3)
    start_day: str = Field(min_length=1)
    region: str = Field(min_length=1)
    host_country: str = Field(min_length=3, max_length=3)
    is_world_tour: bool = False
    is_elite_tour: bool = False
    cluster_id: str = Field(min_length=1)
    travel_group: str = Field(min_length=1)
    status: str = "scheduled"

    @model_validator(mode="after")
    def validate_tour_flags(self) -> "CalendarEvent":
        if self.is_world_tour == self.is_elite_tour:
            raise ValueError("Exactly one of is_world_tour or is_elite_tour must be true")
        return self


class SeasonCalendar(BaseModel):
    """Season calendar that supports parallel events across tours."""

    season: int = Field(ge=1900)
    events: list[CalendarEvent] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_season_consistency(self) -> "SeasonCalendar":
        seen_event_ids: set[str] = set()
        for event in self.events:
            if event.season != self.season:
                raise ValueError("All calendar events must match SeasonCalendar.season")
            if event.event_id in seen_event_ids:
                raise ValueError(f"Duplicate event_id in calendar: {event.event_id}")
            seen_event_ids.add(event.event_id)
        return self
