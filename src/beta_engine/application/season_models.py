"""Application-layer DTOs for deterministic season simulation orchestration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.domain.draws import GeneratedDraw
from beta_engine.domain.entries import AcceptanceList
from beta_engine.domain.rankings import CompletedTournamentPointsInput, RankingRaceReport
from beta_engine.domain.tournaments import CalendarEvent
from beta_engine.domain.tournaments.progression import TournamentResult


class RankingSnapshot(BaseModel):
    """Snapshot-ready ranking state after a simulation step."""

    as_of_season: int = Field(ge=1900)
    as_of_week: int = Field(ge=1, le=61)
    report: RankingRaceReport


class RaceSnapshot(BaseModel):
    """Snapshot-ready race state after a simulation step."""

    target_season: int = Field(ge=1900)
    as_of_season: int = Field(ge=1900)
    as_of_week: int = Field(ge=1, le=61)
    report: RankingRaceReport


class TournamentSimulationResult(BaseModel):
    """End-to-end deterministic output for one completed event."""

    event: CalendarEvent
    acceptance_list: AcceptanceList
    qualification_draw: GeneratedDraw
    main_draw: GeneratedDraw
    tournament_result: TournamentResult
    ranking_snapshot: RankingSnapshot | None = None
    race_snapshot: RaceSnapshot | None = None
    completed_tournament_input: CompletedTournamentPointsInput | None = None


class ActiveTournamentState(BaseModel):
    """Persisted in-progress tournament context for fine-grained simulation commands."""

    event: CalendarEvent
    full_result: TournamentSimulationResult
    revealed_match_count: int = Field(default=0, ge=0)


class WeeklySimulationResult(BaseModel):
    """Deterministic output for all events completed in one week."""

    season: int = Field(ge=1900)
    week: int = Field(ge=1, le=61)
    tournaments: list[TournamentSimulationResult] = Field(default_factory=list)
    ranking_snapshot: RankingSnapshot
    race_snapshot: RaceSnapshot


class SeasonState(BaseModel):
    """Explicit mutable-by-copy simulation state owned by application layer."""

    season: int = Field(ge=1900)
    ordered_events: list[CalendarEvent] = Field(default_factory=list)
    next_event_index: int = Field(default=0, ge=0)
    completed_event_ids: list[str] = Field(default_factory=list)
    completed_tournament_inputs: list[CompletedTournamentPointsInput] = Field(default_factory=list)
    ranking_snapshot: RankingSnapshot | None = None
    race_snapshot: RaceSnapshot | None = None
    active_tournament: ActiveTournamentState | None = None

    @property
    def has_remaining_events(self) -> bool:
        return self.next_event_index < len(self.ordered_events)


class SeasonSimulationResult(BaseModel):
    """Final deterministic output for simulate_full_season."""

    season: int = Field(ge=1900)
    weekly_results: list[WeeklySimulationResult] = Field(default_factory=list)
    ranking_snapshot: RankingSnapshot | None = None
    race_snapshot: RaceSnapshot | None = None


class SimulationStepResult(BaseModel):
    """Generic command result wrapper with updated state."""

    mode: Literal[
        "simulate_next_match",
        "simulate_next_round",
        "simulate_next_tournament",
        "simulate_next_week",
        "simulate_full_season",
    ]
    season_state: SeasonState
    tournament_result: TournamentSimulationResult | None = None
    weekly_result: WeeklySimulationResult | None = None
    season_result: SeasonSimulationResult | None = None
