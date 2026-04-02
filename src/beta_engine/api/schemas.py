"""Request/response DTOs for simulation API endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.application.finals_models import FinalsSimulationResult
from beta_engine.application.run_bootstrap_models import (
    BootstrapNextSeasonRequest,
    BootstrapNextSeasonResponse,
    RunLineageRecord,
    RunSourceSummary,
)
from beta_engine.application.rollover_models import (
    NextSeasonPlayerRecord,
    PersistedPlayerTransition,
    SeasonRolloverResponse,
    SeasonRolloverSummaryResponse,
)
from beta_engine.application.season_models import RaceSnapshot, RankingSnapshot, SeasonState, SimulationStepResult
from beta_engine.domain.finals import FinalsQualificationResult, FinalsResult


class HealthResponse(BaseModel):
    status: Literal["ok"]


class CreateRunRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    seed: int
    season: int = Field(ge=1900)
    config_version: str | None = Field(default=None, max_length=128)
    config_fingerprint: str | None = Field(default=None, max_length=256)


class RunSummaryResponse(BaseModel):
    run_id: str
    season: int
    seed: int
    config_version: str | None = None
    config_fingerprint: str | None = None
    next_event_index: int
    total_events: int
    completed_event_ids: list[str] = Field(default_factory=list)


class RunStatusSummaryProgressResponse(BaseModel):
    next_event_index: int
    total_events: int
    completed_event_count: int


class RunStatusSummaryFinalsResponse(BaseModel):
    qualification_available: bool
    result_available: bool


class RunStatusSummaryRolloverResponse(BaseModel):
    latest_to_season: int
    transitioned_players: int


class RunStatusSummarySourceResponse(BaseModel):
    source_type: Literal["fresh_seed", "rollover_bootstrap"]
    parent_run_id: str | None = None


class RunStatusSummaryLineageResponse(BaseModel):
    child_run_count: int


class RunStatusSummaryHistoryCountsResponse(BaseModel):
    events: int
    ranking_snapshots: int
    race_snapshots: int


class RunStatusSummaryResponse(BaseModel):
    run_id: str
    season: int
    seed: int
    progress: RunStatusSummaryProgressResponse
    finals: RunStatusSummaryFinalsResponse
    rollover: RunStatusSummaryRolloverResponse | None = None
    source: RunStatusSummarySourceResponse | None = None
    lineage: RunStatusSummaryLineageResponse
    history_counts: RunStatusSummaryHistoryCountsResponse


class RunIndexSummaryProgressResponse(BaseModel):
    next_event_index: int
    total_events: int
    completed_event_count: int


class RunIndexSummaryResponse(BaseModel):
    run_id: str
    season: int
    seed: int
    progress: RunIndexSummaryProgressResponse
    source_type: Literal["fresh_seed", "rollover_bootstrap"]
    parent_run_id: str | None = None
    child_run_count: int


class RunIndexResponse(BaseModel):
    runs: list[RunIndexSummaryResponse] = Field(default_factory=list)


class SimulateResponse(BaseModel):
    mode: str
    run: RunSummaryResponse
    step: SimulationStepResult


class EventRecordResponse(BaseModel):
    event_sequence: int
    event_id: str
    season: int | None = None
    week: int | None = None
    template_id: str | None = None
    tournament_result: dict[str, object] | None = None


class EventListResponse(BaseModel):
    run_id: str
    events: list[EventRecordResponse] = Field(default_factory=list)


class RunActivityItemResponse(BaseModel):
    kind: str
    sequence: int | None = None
    label: str
    season: int | None = None
    week: int | None = None
    event_id: str | None = None
    snapshot_sequence: int | None = None
    source_event_id: str | None = None
    related_run_id: str | None = None


class RunActivityResponse(BaseModel):
    run_id: str
    items: list[RunActivityItemResponse] = Field(default_factory=list)


class RankingSnapshotRecordResponse(BaseModel):
    snapshot_sequence: int
    snapshot_kind: str
    source_event_id: str | None = None
    payload: RankingSnapshot


class RankingSnapshotListResponse(BaseModel):
    run_id: str
    snapshots: list[RankingSnapshotRecordResponse] = Field(default_factory=list)


class RaceSnapshotRecordResponse(BaseModel):
    snapshot_sequence: int
    snapshot_kind: str
    source_event_id: str | None = None
    payload: RaceSnapshot


class RaceSnapshotListResponse(BaseModel):
    run_id: str
    snapshots: list[RaceSnapshotRecordResponse] = Field(default_factory=list)


class SeasonStateResponse(BaseModel):
    run: RunSummaryResponse
    season_state: SeasonState


class FinalsQualificationResponse(BaseModel):
    run_id: str
    season: int
    source_as_of_season: int
    source_as_of_week: int
    qualification: FinalsQualificationResult


class FinalsResultResponse(BaseModel):
    run_id: str
    season: int
    event_id: str
    source_as_of_season: int
    source_as_of_week: int
    result: FinalsResult


class FinalsSimulationResponse(BaseModel):
    mode: Literal["simulate_world_tour_finals"]
    run: RunSummaryResponse
    finals: FinalsSimulationResult


class FinalsSummaryApiResponse(BaseModel):
    run_id: str
    season: int
    qualification: FinalsQualificationResponse | None = None
    result: FinalsResultResponse | None = None


class SeasonRolloverExecutionResponse(BaseModel):
    run: RunSummaryResponse
    rollover: SeasonRolloverResponse


class SeasonRolloverSummaryApiResponse(BaseModel):
    rollover: SeasonRolloverSummaryResponse


class NextSeasonPlayersResponse(BaseModel):
    run_id: str
    to_season: int
    players: list[NextSeasonPlayerRecord] = Field(default_factory=list)


class PlayerTransitionsResponse(BaseModel):
    run_id: str
    to_season: int
    transitions: list[PersistedPlayerTransition] = Field(default_factory=list)


class BootstrapNextSeasonApiResponse(BaseModel):
    run: RunSummaryResponse
    bootstrap: BootstrapNextSeasonResponse


class RunLineageApiResponse(BaseModel):
    lineage: RunLineageRecord


class RunSourceApiResponse(BaseModel):
    source: RunSourceSummary


class ConfigValidationIssueResponse(BaseModel):
    severity: Literal["warning", "error"]
    domain: str
    check_id: str
    source: str
    message: str
    location: str | None = None


class ConfigDomainValidationResponse(BaseModel):
    domain: str
    source: str
    valid: bool
    warnings: list[ConfigValidationIssueResponse] = Field(default_factory=list)
    errors: list[ConfigValidationIssueResponse] = Field(default_factory=list)


class ConfigValidationResponse(BaseModel):
    valid: bool
    warnings: list[ConfigValidationIssueResponse] = Field(default_factory=list)
    errors: list[ConfigValidationIssueResponse] = Field(default_factory=list)
    domains: list[ConfigDomainValidationResponse] = Field(default_factory=list)
