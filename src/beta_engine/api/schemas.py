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


class RunWorldStatusResponse(BaseModel):
    run_id: str
    source_type: Literal["fresh_seed", "rollover_bootstrap"]
    stored_world_generation_fingerprint: str | None = None
    current_world_generation_fingerprint: str
    is_stale: bool
    rebuild_supported: bool
    message: str


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
    origin_source_type: Literal["planner_generated", "manual_override"] | None = None
    origin_quality_band: str | None = None
    origin_override_id: str | None = None
    origin_season: int | None = None


class GeneratedPlayerProvenanceListResponse(BaseModel):
    run_id: str
    players: list[GeneratedPlayerProvenanceResponse] = Field(default_factory=list)


class RunPlayerListItemResponse(BaseModel):
    player_id: str
    name: str
    country_code: str
    age: int
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"]
    override_id: str | None = None
    quality_band: str | None = None
    is_top_band: bool
    origin_source_type: Literal["planner_generated", "manual_override"] | None = None
    origin_quality_band: str | None = None
    origin_override_id: str | None = None
    origin_season: int | None = None
    technique: int
    movement: int
    physical: int
    mental: int
    overall: int


class RunPlayersListResponse(BaseModel):
    run_id: str
    total: int
    limit: int
    offset: int
    players: list[RunPlayerListItemResponse] = Field(default_factory=list)


class RunPlayerHiddenTraitSummaryResponse(BaseModel):
    potential_ceiling: int
    growth_curve: str
    professionalism: float
    ambition: float
    travel_tolerance: float
    schedule_aggression: float
    injury_proneness: float
    resilience: float


class RunPlayerDetailResponse(BaseModel):
    player_id: str
    name: str
    country_code: str
    age: int
    play_style: str
    archetype: str
    technique: int
    movement: int
    physical: int
    mental: int
    consistency: int
    clutch: int
    recovery: int
    overall: int
    hidden_traits: RunPlayerHiddenTraitSummaryResponse
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"]
    quality_band: str | None = None
    is_top_band: bool
    override_id: str | None = None
    origin_source_type: Literal["planner_generated", "manual_override"] | None = None
    origin_quality_band: str | None = None
    origin_override_id: str | None = None
    origin_season: int | None = None
    talent_seed_value: int | None = None
    talent_sequence: int | None = None


class PlayerCareerHistoryEntryResponse(BaseModel):
    run_id: str
    season: int
    age: int
    overall: int
    technique: int
    movement: int
    physical: int
    mental: int
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"] | None = None
    quality_band: str | None = None
    is_top_band: bool | None = None
    origin_source_type: Literal["planner_generated", "manual_override"] | None = None
    origin_quality_band: str | None = None
    origin_override_id: str | None = None
    origin_season: int | None = None


class PlayerCareerHistoryResponse(BaseModel):
    requested_run_id: str
    player_id: str
    player_name: str | None = None
    country_code: str | None = None
    entries: list[PlayerCareerHistoryEntryResponse] = Field(default_factory=list)


class PlayerCareerSeasonPerformanceEntryResponse(BaseModel):
    run_id: str
    season: int
    ranking_position: int | None = None
    race_position: int | None = None
    tournaments_played: int
    titles: int
    finals: int
    semifinals: int
    quarterfinals: int
    wins: int
    losses: int


class PlayerCareerPerformanceResponse(BaseModel):
    requested_run_id: str
    player_id: str
    player_name: str | None = None
    country_code: str | None = None
    entries: list[PlayerCareerSeasonPerformanceEntryResponse] = Field(default_factory=list)


class PlayerTournamentResultEntryResponse(BaseModel):
    run_id: str
    season: int
    week: int | None = None
    event_sequence: int
    event_id: str
    event_name: str | None = None
    event_category: str | None = None
    template_id: str | None = None
    finish: str | None = None
    is_title: bool
    wins: int
    losses: int
    ranking_points_awarded: int | None = None


class PlayerTournamentResultsTimelineResponse(BaseModel):
    requested_run_id: str
    player_id: str
    player_name: str | None = None
    country_code: str | None = None
    entries: list[PlayerTournamentResultEntryResponse] = Field(default_factory=list)


class RunNationSummaryItemResponse(BaseModel):
    country_code: str
    country_name: str | None = None
    total_players: int
    average_overall: float
    average_age: float
    top_band_count: int
    manual_override_count: int
    planner_generated_count: int
    rollover_carried_count: int
    top_player_id: str | None = None
    top_player_name: str | None = None
    top_player_overall: int | None = None


class RunNationsSummaryResponse(BaseModel):
    run_id: str
    total: int
    limit: int
    offset: int
    nations: list[RunNationSummaryItemResponse] = Field(default_factory=list)


class RunNationAverageVisibleStatsResponse(BaseModel):
    technique: float
    movement: float
    physical: float
    mental: float


class RunNationBandDistributionItemResponse(BaseModel):
    band: str
    count: int


class RunNationTopPlayerItemResponse(BaseModel):
    player_id: str
    name: str
    age: int
    overall: int
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"]
    quality_band: str | None = None
    is_top_band: bool


class RunNationDetailResponse(BaseModel):
    run_id: str
    country_code: str
    country_name: str | None = None
    total_players: int
    average_overall: float
    average_age: float
    top_band_count: int
    manual_override_count: int
    planner_generated_count: int
    rollover_carried_count: int
    average_visible_stats: RunNationAverageVisibleStatsResponse
    source_mix: dict[str, int]
    band_distribution: list[RunNationBandDistributionItemResponse] = Field(default_factory=list)
    origin_band_distribution: list[RunNationBandDistributionItemResponse] = Field(default_factory=list)
    top_players: list[RunNationTopPlayerItemResponse] = Field(default_factory=list)


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


class ManualPlayerOverridesImportRequest(BaseModel):
    csv_text: str = Field(min_length=1)
    dry_run: bool = False


class ManualPlayerOverridesImportErrorResponse(BaseModel):
    row_number: int | None = None
    field: str | None = None
    message: str


class ManualPlayerOverridesImportSummaryResponse(BaseModel):
    total_records: int
    new_records: int
    updated_records: int
    unchanged_records: int


class ManualPlayerOverridesImportResponse(BaseModel):
    ok: bool
    dry_run: bool
    summary: ManualPlayerOverridesImportSummaryResponse
    errors: list[ManualPlayerOverridesImportErrorResponse] = Field(default_factory=list)




class WorldPackageImportRequest(BaseModel):
    package_text: str = Field(min_length=1)
    dry_run: bool = False


class WorldPackageImportErrorResponse(BaseModel):
    field: str | None = None
    message: str


class WorldPackageImportSummaryResponse(BaseModel):
    total_records: int
    new_records: int
    updated_records: int
    unchanged_records: int


class WorldPackageImportResponse(BaseModel):
    ok: bool
    dry_run: bool
    countries_summary: WorldPackageImportSummaryResponse
    manual_overrides_summary: WorldPackageImportSummaryResponse
    errors: list[WorldPackageImportErrorResponse] = Field(default_factory=list)

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
    competition_density: float | None = Field(default=None, ge=1.0, le=5.0)
    federation_quality: float | None = Field(default=None, ge=1.0, le=5.0)
    court_count: int | None = Field(default=None, ge=0)
    travel_region: str | None = None
    notes: str | None = None
    style_dna: dict[str, float] = Field(default_factory=dict)

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
    competition_density: float
    federation_quality: float
    court_count: int | None = None
    travel_region: str | None = None
    notes: str | None = None
    style_dna: dict[str, float] = Field(default_factory=dict)


class CountriesListResponse(BaseModel):
    countries: list[CountryResponse] = Field(default_factory=list)


class CountriesMetadataResponse(BaseModel):
    dataset_status: str | None = None
    country_count: int
    source_path: str


class CountriesDatasetResponse(BaseModel):
    dataset_status: str | None = None
    countries: list[CountryResponse] = Field(default_factory=list)


class CountriesImportRequest(BaseModel):
    csv_text: str = Field(min_length=1)
    dry_run: bool = False


class CountriesImportErrorResponse(BaseModel):
    row_number: int | None = None
    field: str | None = None
    message: str


class CountriesImportSummaryResponse(BaseModel):
    total_records: int
    new_records: int
    updated_records: int
    unchanged_records: int


class CountriesImportResponse(BaseModel):
    ok: bool
    dry_run: bool
    summary: CountriesImportSummaryResponse
    errors: list[CountriesImportErrorResponse] = Field(default_factory=list)


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


class LuckyLoserRulesResponse(BaseModel):
    enabled: bool = True
    max_spots: int = Field(ge=0)
    replacement_window: str = "pre_main_draw_round_1"


class TournamentPointDistributionResponse(BaseModel):
    winner: int = Field(ge=0)
    finalist: int = Field(ge=0)
    semifinalist: int = Field(ge=0)
    quarterfinalist: int = Field(ge=0)
    round_of_16: int = Field(default=0, ge=0)
    round_of_32: int = Field(default=0, ge=0)


class TournamentTemplateUpsertRequest(BaseModel):
    template_id: str = Field(min_length=3)
    tour_level: Literal["WORLD_TOUR", "ELITE_TOUR"]
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
    lucky_loser_rules: LuckyLoserRulesResponse
    point_distribution_ref: str | None = None
    point_distribution: TournamentPointDistributionResponse | None = None
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

    @field_validator("template_id", "category", "event_name", "region")
    @classmethod
    def non_empty_trimmed_template_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    @field_validator("host_country")
    @classmethod
    def normalize_host_country(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3:
            raise ValueError("host_country must be exactly 3 characters")
        return normalized


class TournamentTemplateResponse(TournamentTemplateUpsertRequest):
    pass


class TournamentTemplatesListResponse(BaseModel):
    templates: list[TournamentTemplateResponse] = Field(default_factory=list)


class TournamentTemplatesMetadataResponse(BaseModel):
    template_count: int
    source_path: str
    referenced_by_calendar: bool
    referenced_template_ids: list[str] = Field(default_factory=list)


class TournamentTemplatesDatasetResponse(BaseModel):
    templates: list[TournamentTemplateResponse] = Field(default_factory=list)


class TournamentTemplatesImportRequest(BaseModel):
    dataset: dict[str, object]
    dry_run: bool = False


class TournamentTemplatesValidationIssueResponse(BaseModel):
    field: str | None = None
    message: str


class TournamentTemplatesImportResponse(BaseModel):
    ok: bool
    dry_run: bool
    template_count: int
    errors: list[TournamentTemplatesValidationIssueResponse] = Field(default_factory=list)


class InitialPoolGenerateRequest(BaseModel):
    season: str = Field(default="2000/2001", min_length=4, max_length=16)
    seed: int
    target_pool_size: int | None = Field(default=128, ge=1, le=2000)
    dry_run: bool = True


class InitialPoolRegenerateRequest(BaseModel):
    season: str = Field(default="2000/2001", min_length=4, max_length=16)
    seed: int
    target_pool_size: int | None = Field(default=None, ge=1, le=2000)
    country_code: str | None = Field(default=None, min_length=3, max_length=3)
    region: str | None = None
    dry_run: bool = True

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value
