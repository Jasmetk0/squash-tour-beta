"""Request/response DTOs for simulation API endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic import field_validator

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


class RunTalentPlanCountryAllocationResponse(BaseModel):
    country_code: str
    planned_count: int
    quality_weights: dict[str, float]
    actual_band_counts: dict[str, int]
    bias_profile: dict[str, float]
    dampener: dict[str, object] = Field(default_factory=dict)


class RunTalentPlanSummaryResponse(BaseModel):
    run_id: str
    season: int
    seed: int
    total_talents: int
    dataset_status: str | None = None
    config_version: str | None = None
    config_fingerprint: str | None = None
    countries: list[RunTalentPlanCountryAllocationResponse] = Field(default_factory=list)


class GeneratedPlayerProvenanceResponse(BaseModel):
    run_id: str
    season: int
    player_id: str
    country_code: str
    talent_sequence: int | None = None
    talent_seed_value: int | None = None
    quality_band: str | None = None
    is_top_band: bool
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"]
    override_id: str | None = None


class GeneratedPlayerProvenanceListResponse(BaseModel):
    run_id: str
    players: list[GeneratedPlayerProvenanceResponse] = Field(default_factory=list)


class ManualPlayerAttributeOverridesRequest(BaseModel):
    technique: int | None = Field(default=None, ge=20, le=99)
    movement: int | None = Field(default=None, ge=20, le=99)
    physical: int | None = Field(default=None, ge=20, le=99)
    mental: int | None = Field(default=None, ge=20, le=99)
    consistency: int | None = Field(default=None, ge=20, le=99)
    clutch: int | None = Field(default=None, ge=20, le=99)
    recovery: int | None = Field(default=None, ge=20, le=99)


class ManualPlayerHiddenTraitOverridesRequest(BaseModel):
    potential_ceiling: int | None = Field(default=None, ge=55, le=99)
    growth_curve: str | None = None
    professionalism: float | None = Field(default=None, ge=0.0, le=1.0)
    ambition: float | None = Field(default=None, ge=0.0, le=1.0)
    travel_tolerance: float | None = Field(default=None, ge=0.0, le=1.0)
    schedule_aggression: float | None = Field(default=None, ge=0.0, le=1.0)
    injury_proneness: float | None = Field(default=None, ge=0.0, le=1.0)
    resilience: float | None = Field(default=None, ge=0.0, le=1.0)


class ManualPlayerOverrideRequest(BaseModel):
    override_id: str = Field(min_length=1, max_length=128)
    season: int = Field(ge=1900)
    country_code: str = Field(min_length=3, max_length=3)
    player_name: str = Field(min_length=1, max_length=128)
    player_slug: str | None = Field(default=None, min_length=1, max_length=64)
    player_id: str | None = Field(default=None, min_length=1, max_length=128)
    age: int = Field(ge=15, le=45)
    profile_tier: Literal["strong", "elite", "special", "generational"]
    quality_band_override: str | None = None
    attribute_overrides: ManualPlayerAttributeOverridesRequest | None = None
    hidden_trait_overrides: ManualPlayerHiddenTraitOverridesRequest | None = None
    is_exceptional: bool = False
    enabled: bool = True
    notes: str | None = Field(default=None, max_length=512)


class ManualPlayerOverrideResponse(ManualPlayerOverrideRequest):
    pass


class ManualPlayerOverridesListResponse(BaseModel):
    overrides: list[ManualPlayerOverrideResponse] = Field(default_factory=list)


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


class WildcardAssignmentRequest(BaseModel):
    slot_index: int = Field(ge=1)
    player_id: str = Field(min_length=1)


class WildcardAssignRequest(BaseModel):
    assignments: list[WildcardAssignmentRequest] = Field(min_length=1)


class WildcardSlotResponse(BaseModel):
    slot_index: int
    entry_id: str
    assigned_player_id: str | None = None


class WildcardStateApiResponse(BaseModel):
    run_id: str
    event_id: str
    eligible: bool
    eligibility_reason: str | None = None
    total_slots: int
    slots: list[WildcardSlotResponse] = Field(default_factory=list)


class WildcardCandidateResponse(BaseModel):
    player_id: str
    player_name: str
    country_code: str
    country_name: str | None = None
    source: Literal["main_draw_waitlist", "qualification_waitlist", "non_applicant_pool"]
    source_priority: int | None = None
    entry_score: float | None = None


class WildcardCandidatesApiResponse(BaseModel):
    run_id: str
    event_id: str
    candidates: list[WildcardCandidateResponse] = Field(default_factory=list)


class WildcardActionAssignmentSummaryResponse(BaseModel):
    slot_index: int
    player_id: str


class WildcardActionHistoryItemResponse(BaseModel):
    action_sequence: int
    action_kind: str
    event_id: str
    assignment_payload_summary: list[WildcardActionAssignmentSummaryResponse] = Field(default_factory=list)


class WildcardActionHistoryApiResponse(BaseModel):
    run_id: str
    event_id: str
    actions: list[WildcardActionHistoryItemResponse] = Field(default_factory=list)


class PreDrawWithdrawalRequest(BaseModel):
    withdrawn_player_id: str = Field(min_length=1)


class PreDrawWithdrawablePlayerResponse(BaseModel):
    player_id: str
    player_name: str
    country_code: str
    country_name: str | None = None
    entry_id: str
    acceptance_status: str


class PreDrawWithdrawalStateApiResponse(BaseModel):
    run_id: str
    event_id: str
    eligible: bool
    eligibility_reason: str | None = None
    withdrawable_main_draw_players: list[PreDrawWithdrawablePlayerResponse] = Field(default_factory=list)


class PreDrawWithdrawalResultApiResponse(BaseModel):
    run_id: str
    event_id: str
    withdrawn_player_id: str
    replacement_player_id: str
    replacement_source: Literal["main_draw_waitlist", "qualification_waitlist"]
    withdrawn_entry_id: str
    replacement_entry_id: str
    eligible: bool
    eligibility_reason: str | None = None


class PreDrawWithdrawalActionHistoryItemResponse(BaseModel):
    action_sequence: int
    action_kind: str
    event_id: str
    withdrawn_player_id: str
    replacement_player_id: str
    replacement_source: Literal["main_draw_waitlist", "qualification_waitlist"]
    withdrawn_entry_id: str
    replacement_entry_id: str
    notes: str | None = None


class PreDrawWithdrawalActionHistoryApiResponse(BaseModel):
    run_id: str
    event_id: str
    actions: list[PreDrawWithdrawalActionHistoryItemResponse] = Field(default_factory=list)


class LateReplacementRequest(BaseModel):
    withdrawn_player_id: str = Field(min_length=1)


class LateReplacementCandidateResponse(BaseModel):
    candidate_slot_index: int
    player_id: str
    player_name: str
    country_code: str
    country_name: str | None = None
    source: Literal["main_draw_waitlist", "qualification_waitlist"]
    source_priority: int | None = None
    ranking_priority: int | None = None
    entry_id: str


class LateReplacementCandidatesApiResponse(BaseModel):
    run_id: str
    event_id: str
    candidates: list[LateReplacementCandidateResponse] = Field(default_factory=list)


class LateReplacementStateApiResponse(BaseModel):
    run_id: str
    event_id: str
    eligible: bool
    eligibility_reason: str | None = None
    replaceable_main_draw_players: list[PreDrawWithdrawablePlayerResponse] = Field(default_factory=list)
    remaining_capacity: int


class LateReplacementResultApiResponse(BaseModel):
    run_id: str
    event_id: str
    withdrawn_player_id: str
    replacement_player_id: str
    replacement_source: Literal["main_draw_waitlist", "qualification_waitlist"]
    withdrawn_entry_id: str
    replacement_entry_id: str
    candidate_slot_index: int | None = None
    eligible: bool
    eligibility_reason: str | None = None
    remaining_capacity: int


class LateReplacementActionHistoryItemResponse(BaseModel):
    action_sequence: int
    action_kind: str
    event_id: str
    withdrawn_player_id: str
    replacement_player_id: str
    replacement_source: Literal["main_draw_waitlist", "qualification_waitlist"]
    withdrawn_entry_id: str
    replacement_entry_id: str
    candidate_slot_index: int | None = None
    notes: str | None = None


class LateReplacementActionHistoryApiResponse(BaseModel):
    run_id: str
    event_id: str
    actions: list[LateReplacementActionHistoryItemResponse] = Field(default_factory=list)


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


class CountryUpsertRequest(BaseModel):
    code: str = Field(min_length=3, max_length=3)
    name: str = Field(min_length=1)
    flag_asset: str | None = None
    region: str = Field(min_length=1)
    population: int = Field(gt=0)
    wealth_support: int = Field(ge=1, le=5)
    squash_popularity: int = Field(ge=1, le=5)
    squash_tradition: int = Field(ge=1, le=5)
    system_quality: int = Field(ge=1, le=5)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3:
            raise ValueError("code must be exactly 3 characters")
        return normalized

    @field_validator("name", "region")
    @classmethod
    def non_empty_trimmed(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    @field_validator("flag_asset")
    @classmethod
    def normalize_flag_asset(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CountryResponse(BaseModel):
    code: str
    name: str
    flag_asset: str | None = None
    region: str
    population: int
    wealth_support: int
    squash_popularity: int
    squash_tradition: int
    system_quality: int


class CountriesListResponse(BaseModel):
    countries: list[CountryResponse] = Field(default_factory=list)


class CountriesMetadataResponse(BaseModel):
    dataset_status: str | None = None
    country_count: int
    source_path: str


class CountriesDatasetResponse(BaseModel):
    dataset_status: str | None = None
    countries: list[CountryResponse] = Field(default_factory=list)


class CountryTalentYearPreviewResponse(BaseModel):
    country_code: str
    country_name: str
    planned_count: int
    quality_weights: dict[str, float]
    actual_band_counts: dict[str, int]
    bias_profile: dict[str, float]
    dampener: dict[str, object] = Field(default_factory=dict)


class TalentClassYearPreviewResponse(BaseModel):
    year: int
    seed: int
    dataset_status: str | None = None
    country_count: int
    source_path: str
    total_talents: int
    countries: list[CountryTalentYearPreviewResponse] = Field(default_factory=list)


class CountryTalentSummaryResponse(BaseModel):
    country_code: str
    country_name: str
    total_planned_talents: int
    average_talents_per_year: float
    total_elite_count: int
    total_special_count: int
    total_generational_count: int
    average_top_band_rate: float


class TalentClassSummaryResponse(BaseModel):
    year_start: int
    years: int
    seed: int
    dataset_status: str | None = None
    country_count: int
    source_path: str
    total_talents_across_span: int
    average_total_talents_per_year: float
    global_band_totals: dict[str, int]
    countries: list[CountryTalentSummaryResponse] = Field(default_factory=list)
