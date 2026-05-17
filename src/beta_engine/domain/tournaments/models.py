"""Tournament templates and calendar domain models (config-driven)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, computed_field, model_validator


TourLevel = Literal["WORLD_TOUR", "ELITE_TOUR"]
SeasonCalendarEventStatus = Literal["planned", "active", "completed", "cancelled", "scheduled"]


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
    prize_money: int = Field(default=0, ge=0)
    prestige: float = Field(default=0.0, ge=0)
    duration_in_season_weeks: int = Field(default=1, ge=1)
    host_requirements: dict[str, object] = Field(default_factory=dict)
    category_specific_rules: dict[str, object] = Field(default_factory=dict)
    notes: str | None = None
    active: bool = True

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


class SeasonCalendarValidationIssue(BaseModel):
    """Validation issue emitted by conservative calendar validation."""

    severity: Literal["warning", "error"]
    code: str
    message: str
    event_id: str | None = None
    field: str | None = None


class SeasonCalendarMetadata(BaseModel):
    """Metadata describing a season calendar build and its source inputs."""

    season: str
    season_start_calendar_year: int = Field(ge=1900, le=2100)
    season_start_year_week: int = Field(ge=1, le=53)
    total_season_weeks: int = 61
    event_count: int = Field(default=0, ge=0)
    build_seed: int | None = None
    build_fingerprint: str | None = None
    source_template_count: int = Field(default=0, ge=0)
    persistence_path: str | None = None
    dry_run: bool = True
    overwrite_existing: bool = False


class CalendarEvent(BaseModel):
    """Scheduled tournament event for a specific season week.

    This model is intentionally backward-compatible with the earlier MVP event shape
    (`week`, integer season, scheduled status) while carrying the canonical Season
    Week + Year Week fields for new season calendars.
    """

    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(min_length=3)
    season: str | int
    season_week: int = Field(ge=1, le=61, validation_alias=AliasChoices("season_week", "week"))
    calendar_year: int | None = Field(default=None, ge=1900, le=2100)
    year_week: int | None = Field(default=None, ge=1, le=53)
    template_id: str = Field(min_length=3)
    event_name: str = ""
    category: str = ""
    tour_level: TourLevel | None = None
    host_country: str = Field(min_length=3, max_length=3)
    host_city: str | None = None
    region: str = Field(min_length=1)
    duration_in_season_weeks: int = Field(default=1, ge=1)
    start_season_week: int | None = Field(default=None, ge=1, le=61)
    end_season_week: int | None = Field(default=None, ge=1, le=61)
    status: SeasonCalendarEventStatus = "planned"
    main_draw_size: int = Field(default=1, ge=0)
    qualification_draw_size: int = Field(default=0, ge=0)
    seeds_count: int = Field(default=0, ge=0)
    qualifier_spots: int = Field(default=0, ge=0)
    wild_cards: int = Field(default=0, ge=0)
    byes: int = Field(default=0, ge=0)
    point_distribution_ref: str | None = None
    point_distribution: TournamentPointDistribution | None = None
    prize_money: int = Field(default=0, ge=0)
    prestige: float = Field(default=0.0, ge=0)
    event_level_overrides: dict[str, Any] = Field(default_factory=dict)
    source_template_fingerprint: str | None = None
    template_snapshot_fingerprint: str | None = None
    calendar_fingerprint: str | None = None
    template_snapshot: dict[str, Any] = Field(default_factory=dict)

    # Legacy fields used by existing simulation services.
    start_day: str = "week_start"
    is_world_tour: bool = False
    is_elite_tour: bool = False
    cluster_id: str = "default"
    travel_group: str = "default"

    @computed_field
    @property
    def week(self) -> int:
        return self.season_week

    @model_validator(mode="after")
    def normalize_event(self) -> "CalendarEvent":
        if self.start_season_week is None:
            self.start_season_week = self.season_week
        if self.end_season_week is None:
            self.end_season_week = self.start_season_week + self.duration_in_season_weeks - 1
        if self.tour_level == "WORLD_TOUR":
            self.is_world_tour = True
            self.is_elite_tour = False
        elif self.tour_level == "ELITE_TOUR":
            self.is_elite_tour = True
            self.is_world_tour = False
        elif self.is_world_tour and not self.is_elite_tour:
            self.tour_level = "WORLD_TOUR"
        elif self.is_elite_tour and not self.is_world_tour:
            self.tour_level = "ELITE_TOUR"
        return self


SeasonCalendarEvent = CalendarEvent


class SeasonCalendar(BaseModel):
    """Season calendar that supports parallel events across tours."""

    season: str | int
    events: list[SeasonCalendarEvent] = Field(default_factory=list)
    metadata: SeasonCalendarMetadata | None = None
    validation_warnings: list[SeasonCalendarValidationIssue] = Field(default_factory=list)
    validation_errors: list[SeasonCalendarValidationIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_season_consistency(self) -> "SeasonCalendar":
        seen_event_ids: set[str] = set()
        for event in self.events:
            if str(event.season) != str(self.season):
                raise ValueError("All calendar events must match SeasonCalendar.season")
            if event.event_id in seen_event_ids:
                raise ValueError(f"Duplicate event_id in calendar: {event.event_id}")
            seen_event_ids.add(event.event_id)
        return self


class SeasonCalendarBuildRequest(BaseModel):
    """Request payload for deterministic first-season calendar builds."""

    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False
    season_start_calendar_year: int = Field(default=2000, ge=1900, le=2100)
    season_start_year_week: int = Field(default=37, ge=1, le=52)
    include_inactive_templates: bool = False
    max_events: int | None = Field(default=None, ge=1, le=1000)


class SeasonCalendarBuildSummary(BaseModel):
    """Small response summary for UI cards and tests."""

    event_count: int = 0
    season_weeks_used: int = 0
    first_event_week: int | None = None
    last_event_week: int | None = None
    world_tour_events: int = 0
    elite_tour_events: int = 0
    validation_warning_count: int = 0
    validation_error_count: int = 0
    persisted: bool = False
    calendar_exists: bool = False


class SeasonCalendarBuildResult(BaseModel):
    """Calendar build/read response returned by Admin Seasons endpoints."""

    calendar: SeasonCalendar | None = None
    summary: SeasonCalendarBuildSummary
    metadata: SeasonCalendarMetadata | None = None
    validation_warnings: list[SeasonCalendarValidationIssue] = Field(default_factory=list)
    validation_errors: list[SeasonCalendarValidationIssue] = Field(default_factory=list)
