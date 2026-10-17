"""Deterministic DTOs for ranking/race points resolution and standings."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar


class CompletedTournamentPointsInput(BaseModel):
    """Structured tournament input; calendar-specific W is checked by the engine.

    The DTO alone cannot authorize a Run week. Legacy callers without an
    explicit clock are still capped at W61 inside RankingRaceEngine.
    """

    event_id: str = Field(min_length=1)
    season: int = Field(ge=1900)
    week: int = Field(ge=1)
    template_id: str = Field(min_length=1)
    point_distribution_ref: str | None = None
    point_distribution: dict[str, int] | None = None
    placements: list[dict[str, str]] = Field(default_factory=list)
    rounds: list[dict] = Field(default_factory=list)


class TournamentPointAward(BaseModel):
    """Resolved point award for one player from one completed tournament."""

    event_id: str
    season: int = Field(ge=1900)
    week: int = Field(ge=1)
    template_id: str
    player_id: str
    finish: str
    points_awarded: int = Field(ge=0)


class RankedResultContribution(BaseModel):
    """Explainable contribution metadata for ranking/race standings."""

    event_id: str
    season: int = Field(ge=1900)
    week: int = Field(ge=1)
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
    as_of_week: int = Field(ge=1)
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


class RunCalendarRankingRaceReport(RankingRaceReport):
    """Read-only report with explicit clock provenance; legacy reports unchanged."""

    schema_version: Literal["run_calendar_ranking_race_report.v1"] = (
        "run_calendar_ranking_race_report.v1"
    )
    run_calendar: dict[str, int | str]

    @model_validator(mode="after")
    def valid_calendar_and_window(self):
        calendar = RunCalendar.from_metadata(self.run_calendar)
        if self.ranking.window_weeks > calendar.season_count * calendar.weeks_per_year:
            # A configured window can exceed the Run horizon safely: it still
            # means all available results. Never clamp the user's setting.
            pass
        calendar.season_to_calendar(
            self.ranking.as_of_season - calendar.start_year,
            self.ranking.as_of_week,
        )
        calendar._validate_season_index(self.race.target_season - calendar.start_year)
        if any(
            calendar.season_to_calendar(
                award.season - calendar.start_year, award.week
            ) is None for award in self.point_awards
        ):
            raise ValueError("Point award is outside the Run calendar")
        return self
