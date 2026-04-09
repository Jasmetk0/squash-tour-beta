"""Application services for FastAPI simulation command/query endpoints."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal

from beta_engine.application.finals_models import (
    FinalsSimulationResult,
    FinalsSummaryResponse,
    PersistedFinalsQualification,
    PersistedFinalsResult,
)
from beta_engine.application.finals_service import FinalsOrchestrationService
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.application.player_career_performance_query_service import (
    PlayerCareerPerformance as PlayerCareerPerformanceReadModel,
    PlayerCareerPerformanceQueryService,
)
from beta_engine.application.player_career_query_service import (
    PlayerCareerHistory as PlayerCareerHistoryReadModel,
    PlayerCareerQueryService,
)
from beta_engine.application.persistence import SimulationPersistenceService
from beta_engine.application.run_bootstrap_models import BootstrapNextSeasonResponse, RunLineageRecord, RunSourceSummary
from beta_engine.application.run_bootstrap_service import NextSeasonRunBootstrapService
from beta_engine.application.rollover_models import (
    NextSeasonPlayerRecord,
    PersistedPlayerTransition,
    SeasonRolloverResponse,
    SeasonRolloverSummaryResponse,
)
from beta_engine.application.rollover_service import SeasonRolloverOrchestrationService
from beta_engine.application.season_models import RaceSnapshot, RankingSnapshot, SeasonState, SimulationStepResult
from beta_engine.application.services import SeasonSimulationOrchestrator
from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.careers import CareerProgressionEngine, NextSeasonPlayerState
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.entries import AcceptanceList, AcceptanceStatus, TournamentEntry
from beta_engine.domain.players import (
    AnnualTalentClassPlanner,
    ManualPlayerOverride,
    ManualPlayerProfileTier,
    Player,
    PlayerGenerator,
    RecentGreatnessSignal,
    TalentQualityBand,
    WeightedRecentGreatnessDampener,
)
from beta_engine.domain.tournaments import CalendarEvent
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo
from beta_engine.infrastructure.db.repositories import (
    PersistedGeneratedPlayerProvenanceRecord,
    PersistedRunTalentCountryAllocationRecord,
    PersistedRunTalentPlanRecord,
)
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.points_config import load_points_config
from beta_engine.infrastructure.tournament_config import load_season_calendar, load_tournament_templates_config
from beta_engine.infrastructure.world_config import load_player_identity_config
from beta_engine.application.careers import SeasonRolloverService


@dataclass(frozen=True)
class PersistedEventRecord:
    event_sequence: int
    event_id: str
    season: int | None = None
    week: int | None = None
    template_id: str | None = None
    tournament_result: dict[str, object] | None = None


@dataclass(frozen=True)
class PersistedRunSummary:
    run_id: str
    season: int
    seed: int
    config_version: str | None
    config_fingerprint: str | None
    next_event_index: int
    total_events: int
    completed_event_ids: list[str]


@dataclass(frozen=True)
class RunIndexSummaryProgress:
    next_event_index: int
    total_events: int
    completed_event_count: int


@dataclass(frozen=True)
class RunIndexSummary:
    run_id: str
    season: int
    seed: int
    progress: RunIndexSummaryProgress
    source_type: str
    parent_run_id: str | None
    child_run_count: int


@dataclass(frozen=True)
class RunStatusSummaryProgress:
    next_event_index: int
    total_events: int
    completed_event_count: int


@dataclass(frozen=True)
class RunStatusSummaryFinals:
    qualification_available: bool
    result_available: bool


@dataclass(frozen=True)
class RunStatusSummaryRollover:
    latest_to_season: int
    transitioned_players: int


@dataclass(frozen=True)
class RunStatusSummarySource:
    source_type: str
    parent_run_id: str | None


@dataclass(frozen=True)
class RunStatusSummaryLineage:
    child_run_count: int


@dataclass(frozen=True)
class RunStatusSummaryHistoryCounts:
    events: int
    ranking_snapshots: int
    race_snapshots: int


@dataclass(frozen=True)
class RunStatusSummary:
    run_id: str
    season: int
    seed: int
    progress: RunStatusSummaryProgress
    finals: RunStatusSummaryFinals
    rollover: RunStatusSummaryRollover | None
    source: RunStatusSummarySource | None
    lineage: RunStatusSummaryLineage
    history_counts: RunStatusSummaryHistoryCounts


@dataclass(frozen=True)
class RunWorldStatus:
    run_id: str
    source_type: str
    stored_world_generation_fingerprint: str | None
    current_world_generation_fingerprint: str
    is_stale: bool
    rebuild_supported: bool
    message: str


ActivityKind = Literal[
    "event",
    "ranking_snapshot",
    "race_snapshot",
    "finals_qualification",
    "finals_result",
    "rollover",
    "bootstrap_child",
    "admin_wildcard_assignment",
    "admin_pre_draw_withdrawal_replacement",
    "admin_late_replacement_lucky_loser",
]

_CANONICAL_SOURCE_TYPE_MAP: dict[str, str] = {
    "fresh_seed": "fresh_seed",
    "rollover_bootstrap": "rollover_bootstrap",
    # Legacy values persisted by earlier versions before source-type contract hardening.
    "new_run": "fresh_seed",
    "bootstrap": "rollover_bootstrap",
    "bootstrapped_rollover": "rollover_bootstrap",
}


def _normalize_source_type(raw_source_type: str) -> str:
    return _CANONICAL_SOURCE_TYPE_MAP.get(raw_source_type, raw_source_type)


@dataclass(frozen=True)
class RunActivityItem:
    kind: ActivityKind
    sequence: int | None
    label: str
    season: int | None = None
    week: int | None = None
    event_id: str | None = None
    snapshot_sequence: int | None = None
    source_event_id: str | None = None
    related_run_id: str | None = None


@dataclass(frozen=True)
class RunActivityFeed:
    run_id: str
    items: list[RunActivityItem]


@dataclass(frozen=True)
class RunTalentPlanCountryAllocation:
    country_code: str
    planned_count: int
    quality_weights: dict[str, float]
    actual_band_counts: dict[str, int]
    bias_profile: dict[str, float]
    dampener: dict[str, object]


@dataclass(frozen=True)
class RunTalentPlanSummary:
    run_id: str
    season: int
    seed: int
    total_talents: int
    dataset_status: str | None
    config_version: str | None
    config_fingerprint: str | None
    countries: list[RunTalentPlanCountryAllocation]


@dataclass(frozen=True)
class GeneratedPlayerProvenance:
    run_id: str
    season: int
    player_id: str
    country_code: str
    talent_sequence: int | None
    talent_seed_value: int | None
    quality_band: str | None
    is_top_band: bool
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"]
    override_id: str | None
    origin_source_type: Literal["planner_generated", "manual_override"] | None
    origin_quality_band: str | None
    origin_override_id: str | None
    origin_season: int | None


@dataclass(frozen=True)
class RunPlayerListItem:
    player_id: str
    name: str
    country_code: str
    age: int
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"]
    override_id: str | None
    quality_band: str | None
    is_top_band: bool
    origin_source_type: Literal["planner_generated", "manual_override"] | None
    origin_quality_band: str | None
    origin_override_id: str | None
    origin_season: int | None
    technique: int
    movement: int
    physical: int
    mental: int
    overall: int


@dataclass(frozen=True)
class RunPlayerListResponse:
    run_id: str
    total: int
    limit: int
    offset: int
    players: list[RunPlayerListItem]


@dataclass(frozen=True)
class RunPlayerHiddenTraitSummary:
    potential_ceiling: int
    growth_curve: str
    professionalism: float
    ambition: float
    travel_tolerance: float
    schedule_aggression: float
    injury_proneness: float
    resilience: float


@dataclass(frozen=True)
class RunPlayerDetail:
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
    hidden_traits: RunPlayerHiddenTraitSummary
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"]
    quality_band: str | None
    is_top_band: bool
    override_id: str | None
    origin_source_type: Literal["planner_generated", "manual_override"] | None
    origin_quality_band: str | None
    origin_override_id: str | None
    origin_season: int | None
    talent_seed_value: int | None
    talent_sequence: int | None


@dataclass(frozen=True)
class PlayerCareerHistoryEntry:
    run_id: str
    season: int
    age: int
    overall: int
    technique: int
    movement: int
    physical: int
    mental: int
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"] | None
    quality_band: str | None
    is_top_band: bool | None
    origin_source_type: Literal["planner_generated", "manual_override"] | None
    origin_quality_band: str | None
    origin_override_id: str | None
    origin_season: int | None


@dataclass(frozen=True)
class PlayerCareerHistoryResponse:
    requested_run_id: str
    player_id: str
    player_name: str | None
    country_code: str | None
    entries: list[PlayerCareerHistoryEntry]




@dataclass(frozen=True)
class PlayerCareerSeasonPerformanceEntry:
    run_id: str
    season: int
    ranking_position: int | None
    race_position: int | None
    tournaments_played: int
    titles: int
    finals: int
    semifinals: int
    quarterfinals: int
    wins: int
    losses: int


@dataclass(frozen=True)
class PlayerCareerPerformanceResponse:
    requested_run_id: str
    player_id: str
    player_name: str | None
    country_code: str | None
    entries: list[PlayerCareerSeasonPerformanceEntry]

@dataclass(frozen=True)
class RunNationSummaryItem:
    country_code: str
    country_name: str | None
    total_players: int
    average_overall: float
    average_age: float
    top_band_count: int
    manual_override_count: int
    planner_generated_count: int
    rollover_carried_count: int
    top_player_id: str | None
    top_player_name: str | None
    top_player_overall: int | None


@dataclass(frozen=True)
class RunNationsSummaryResponse:
    run_id: str
    total: int
    limit: int
    offset: int
    nations: list[RunNationSummaryItem]


@dataclass(frozen=True)
class RunNationAverageVisibleStats:
    technique: float
    movement: float
    physical: float
    mental: float


@dataclass(frozen=True)
class RunNationBandDistributionItem:
    band: str
    count: int


@dataclass(frozen=True)
class RunNationTopPlayerItem:
    player_id: str
    name: str
    age: int
    overall: int
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"]
    quality_band: str | None
    is_top_band: bool


@dataclass(frozen=True)
class RunNationDetail:
    run_id: str
    country_code: str
    country_name: str | None
    total_players: int
    average_overall: float
    average_age: float
    top_band_count: int
    manual_override_count: int
    planner_generated_count: int
    rollover_carried_count: int
    average_visible_stats: RunNationAverageVisibleStats
    source_mix: dict[str, int]
    band_distribution: list[RunNationBandDistributionItem]
    origin_band_distribution: list[RunNationBandDistributionItem]
    top_players: list[RunNationTopPlayerItem]


@dataclass(frozen=True)
class WildcardAssignment:
    slot_index: int
    player_id: str


@dataclass(frozen=True)
class WildcardSlotState:
    slot_index: int
    entry_id: str
    assigned_player_id: str | None


@dataclass(frozen=True)
class WildcardStateResponse:
    run_id: str
    event_id: str
    eligible: bool
    eligibility_reason: str | None
    total_slots: int
    slots: list[WildcardSlotState]


@dataclass(frozen=True)
class WildcardCandidateRecord:
    player_id: str
    player_name: str
    country_code: str
    country_name: str | None
    source: Literal["main_draw_waitlist", "qualification_waitlist", "non_applicant_pool"]
    source_priority: int | None
    entry_score: float | None


@dataclass(frozen=True)
class WildcardCandidatesResponse:
    run_id: str
    event_id: str
    candidates: list[WildcardCandidateRecord]


@dataclass(frozen=True)
class WildcardActionAssignmentSummary:
    slot_index: int
    player_id: str


@dataclass(frozen=True)
class WildcardActionHistoryItem:
    action_sequence: int
    action_kind: str
    event_id: str
    assignment_payload_summary: list[WildcardActionAssignmentSummary]


@dataclass(frozen=True)
class WildcardActionHistoryResponse:
    run_id: str
    event_id: str
    actions: list[WildcardActionHistoryItem]


ReplacementSource = Literal["main_draw_waitlist", "qualification_waitlist"]


@dataclass(frozen=True)
class PreDrawWithdrawablePlayerRecord:
    player_id: str
    player_name: str
    country_code: str
    country_name: str | None
    entry_id: str
    acceptance_status: str


@dataclass(frozen=True)
class PreDrawWithdrawalStateResponse:
    run_id: str
    event_id: str
    eligible: bool
    eligibility_reason: str | None
    withdrawable_main_draw_players: list[PreDrawWithdrawablePlayerRecord]


@dataclass(frozen=True)
class PreDrawWithdrawalResultResponse:
    run_id: str
    event_id: str
    withdrawn_player_id: str
    replacement_player_id: str
    replacement_source: ReplacementSource
    withdrawn_entry_id: str
    replacement_entry_id: str
    eligible: bool
    eligibility_reason: str | None


@dataclass(frozen=True)
class PreDrawWithdrawalActionHistoryItem:
    action_sequence: int
    action_kind: str
    event_id: str
    withdrawn_player_id: str
    replacement_player_id: str
    replacement_source: ReplacementSource
    withdrawn_entry_id: str
    replacement_entry_id: str
    notes: str | None


@dataclass(frozen=True)
class PreDrawWithdrawalActionHistoryResponse:
    run_id: str
    event_id: str
    actions: list[PreDrawWithdrawalActionHistoryItem]


@dataclass(frozen=True)
class LateReplacementCandidateRecord:
    candidate_slot_index: int
    player_id: str
    player_name: str
    country_code: str
    country_name: str | None
    source: ReplacementSource
    source_priority: int | None
    ranking_priority: int | None
    entry_id: str


@dataclass(frozen=True)
class LateReplacementCandidatesResponse:
    run_id: str
    event_id: str
    candidates: list[LateReplacementCandidateRecord]


@dataclass(frozen=True)
class LateReplacementStateResponse:
    run_id: str
    event_id: str
    eligible: bool
    eligibility_reason: str | None
    replaceable_main_draw_players: list[PreDrawWithdrawablePlayerRecord]
    remaining_capacity: int


@dataclass(frozen=True)
class LateReplacementResultResponse:
    run_id: str
    event_id: str
    withdrawn_player_id: str
    replacement_player_id: str
    replacement_source: ReplacementSource
    withdrawn_entry_id: str
    replacement_entry_id: str
    candidate_slot_index: int | None
    eligible: bool
    eligibility_reason: str | None
    remaining_capacity: int


@dataclass(frozen=True)
class LateReplacementActionHistoryItem:
    action_sequence: int
    action_kind: str
    event_id: str
    withdrawn_player_id: str
    replacement_player_id: str
    replacement_source: ReplacementSource
    withdrawn_entry_id: str
    replacement_entry_id: str
    candidate_slot_index: int | None
    notes: str | None


@dataclass(frozen=True)
class LateReplacementActionHistoryResponse:
    run_id: str
    event_id: str
    actions: list[LateReplacementActionHistoryItem]


@dataclass(slots=True)
class SimulationApiService:
    """High-level API-facing service that keeps orchestration out of routers."""

    repository: SimulationPersistenceRepository
    manual_overrides_service: ManualPlayerOverridesService = field(default_factory=ManualPlayerOverridesService)
    countries_service: CountriesConfigService = field(default_factory=CountriesConfigService)
    def initialize_run(
        self,
        *,
        run_id: str,
        season: int,
        seed: int,
        config_version: str | None,
        config_fingerprint: str | None,
    ) -> PersistedRunSummary:
        world_generation_fingerprint = self._current_world_generation_fingerprint()
        countries_metadata = self.countries_service.get_config()
        countries = countries_metadata.countries
        _, plan_record, country_records, provenance_records = self._build_fresh_players_and_provenance(
            run_id=run_id,
            season=season,
            seed=seed,
            countries=countries,
            dataset_status=countries_metadata.dataset_status,
            config_version=config_version,
            config_fingerprint=config_fingerprint,
        )
        orchestrator = self._build_orchestrator(season=season, seed=seed, run_info=None)
        state = orchestrator.initialize_state()

        run_info = SimulationRunInfo(
            run_id=run_id,
            season=season,
            seed=seed,
            config_version=config_version,
            config_fingerprint=config_fingerprint,
            world_generation_fingerprint=world_generation_fingerprint,
            source_type="fresh_seed",
        )
        persistence = SimulationPersistenceService(repository=self.repository)
        persistence.initialize_run(run=run_info)
        self.repository.save_season_state(run_id=run_id, state=state)
        self.repository.save_run_talent_plan(plan_record)
        self.repository.replace_run_talent_country_allocations(run_id=run_id, season=season, records=country_records)
        self.repository.replace_generated_player_provenance(run_id=run_id, season=season, records=provenance_records)
        return self.get_run_summary(run_id=run_id)

    def get_run_summary(self, *, run_id: str) -> PersistedRunSummary:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        state = self.repository.load_season_state(run_id=run_id)
        if run_info is None or state is None:
            raise KeyError(f"run_id {run_id} was not found")

        return PersistedRunSummary(
            run_id=run_info.run_id,
            season=run_info.season,
            seed=run_info.seed,
            config_version=run_info.config_version,
            config_fingerprint=run_info.config_fingerprint,
            next_event_index=state.next_event_index,
            total_events=len(state.ordered_events),
            completed_event_ids=list(state.completed_event_ids),
        )

    def get_season_state(self, *, run_id: str) -> SeasonState:
        state = self.repository.load_season_state(run_id=run_id)
        if state is None:
            raise KeyError(f"run_id {run_id} was not found")
        return state

    def get_run_talent_plan_summary(self, *, run_id: str) -> RunTalentPlanSummary:
        self.get_run_summary(run_id=run_id)
        plan = self.repository.get_run_talent_plan(run_id=run_id)
        if plan is None:
            raise KeyError(f"run_id {run_id} has no persisted annual talent plan")
        countries = self.repository.list_run_talent_country_allocations(run_id=run_id)
        return RunTalentPlanSummary(
            run_id=plan.run_id,
            season=plan.season,
            seed=plan.seed,
            total_talents=plan.total_talents,
            dataset_status=plan.dataset_status,
            config_version=plan.config_version,
            config_fingerprint=plan.config_fingerprint,
            countries=[
                RunTalentPlanCountryAllocation(
                    country_code=country.country_code,
                    planned_count=country.planned_count,
                    quality_weights=country.quality_weights,
                    actual_band_counts=country.actual_band_counts,
                    bias_profile=country.bias_profile,
                    dampener=country.dampener,
                )
                for country in countries
            ],
        )

    def list_generated_player_provenance(
        self,
        *,
        run_id: str,
        country_code: str | None = None,
        quality_band: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[GeneratedPlayerProvenance]:
        self.get_run_summary(run_id=run_id)
        records = self.repository.list_generated_player_provenance(
            run_id=run_id,
            country_code=country_code,
            quality_band=quality_band,
            limit=limit,
            offset=offset,
        )
        return [self._to_generated_player_provenance(record) for record in records]

    def get_generated_player_provenance(self, *, run_id: str, player_id: str) -> GeneratedPlayerProvenance:
        self.get_run_summary(run_id=run_id)
        record = self.repository.get_generated_player_provenance(run_id=run_id, player_id=player_id)
        if record is None:
            raise KeyError(f"player_id {player_id} has no persisted generation provenance in run_id {run_id}")
        return self._to_generated_player_provenance(record)

    def list_run_players(
        self,
        *,
        run_id: str,
        country_code: str | None = None,
        source_type: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "name_asc",
    ) -> RunPlayerListResponse:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        if run_info is None:
            raise KeyError(f"run_id {run_id} was not found")

        players_by_id = self._load_players_by_id_for_run(run_info=run_info)
        provenance_by_id = {item.player_id: item for item in self.list_generated_player_provenance(run_id=run_id)}
        rows = [self._to_run_player_list_item(players_by_id[player_id], provenance_by_id.get(player_id)) for player_id in players_by_id]
        filtered = self._filter_run_players(
            players=rows,
            country_code=country_code,
            source_type=source_type,
            min_age=min_age,
            max_age=max_age,
            search=search,
        )
        ordered = self._sort_run_players(players=filtered, sort=sort)
        page = ordered[offset : offset + limit]
        return RunPlayerListResponse(
            run_id=run_id,
            total=len(filtered),
            limit=limit,
            offset=offset,
            players=page,
        )

    def get_run_player_detail(self, *, run_id: str, player_id: str) -> RunPlayerDetail:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        if run_info is None:
            raise KeyError(f"run_id {run_id} was not found")
        players_by_id = self._load_players_by_id_for_run(run_info=run_info)
        player = players_by_id.get(player_id)
        if player is None:
            raise KeyError(f"player_id {player_id} was not found in run_id {run_id}")
        provenance = self.repository.get_generated_player_provenance(run_id=run_id, player_id=player_id)
        return self._to_run_player_detail(player=player, provenance=provenance)

    def get_player_career_history(self, *, run_id: str, player_id: str) -> PlayerCareerHistoryResponse:
        query = PlayerCareerQueryService(
            repository=self.repository,
            load_players_for_run=lambda run_info: self._load_players_by_id_for_run(run_info=run_info),
        )
        result = query.get_player_career_history(run_id=run_id, player_id=player_id)
        return self._to_player_career_history_response(result)

    def get_player_career_performance(self, *, run_id: str, player_id: str) -> PlayerCareerPerformanceResponse:
        query = PlayerCareerPerformanceQueryService(
            repository=self.repository,
            load_players_for_run=lambda run_info: self._load_players_by_id_for_run(run_info=run_info),
        )
        result = query.get_player_career_performance(run_id=run_id, player_id=player_id)
        return self._to_player_career_performance_response(result)

    def list_run_nations(
        self,
        *,
        run_id: str,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
        sort: str = "total_players_desc",
    ) -> RunNationsSummaryResponse:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        if run_info is None:
            raise KeyError(f"run_id {run_id} was not found")

        players_by_id = self._load_players_by_id_for_run(run_info=run_info)
        provenance_by_id = {item.player_id: item for item in self.list_generated_player_provenance(run_id=run_id)}
        country_names = {country.code: country.name for country in self.countries_service.get_config().countries}
        rows = [self._to_run_player_list_item(players_by_id[player_id], provenance_by_id.get(player_id)) for player_id in players_by_id]
        summaries = self._aggregate_run_nation_summaries(rows=rows, country_names=country_names)
        filtered = self._filter_run_nations(summaries=summaries, search=search)
        ordered = self._sort_run_nations(summaries=filtered, sort=sort)
        page = ordered[offset : offset + limit]
        return RunNationsSummaryResponse(run_id=run_id, total=len(filtered), limit=limit, offset=offset, nations=page)

    def get_run_nation_detail(self, *, run_id: str, country_code: str, top_limit: int = 10) -> RunNationDetail:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        if run_info is None:
            raise KeyError(f"run_id {run_id} was not found")

        normalized_country_code = country_code.strip().upper()
        players_by_id = self._load_players_by_id_for_run(run_info=run_info)
        provenance_by_id = {item.player_id: item for item in self.list_generated_player_provenance(run_id=run_id)}
        country_names = {country.code: country.name for country in self.countries_service.get_config().countries}
        rows = [self._to_run_player_list_item(players_by_id[player_id], provenance_by_id.get(player_id)) for player_id in players_by_id]
        country_rows = [row for row in rows if row.country_code.upper() == normalized_country_code]
        if not country_rows:
            raise KeyError(f"country_code {normalized_country_code} was not found in run_id {run_id}")

        summaries = self._aggregate_run_nation_summaries(rows=country_rows, country_names=country_names)
        summary = summaries[0]
        top_players = sorted(country_rows, key=lambda row: (-row.overall, row.name, row.player_id))[: max(top_limit, 1)]
        band_counts: dict[str, int] = {}
        origin_band_counts: dict[str, int] = {}
        for row in country_rows:
            band = row.quality_band or "unclassified"
            band_counts[band] = band_counts.get(band, 0) + 1
            if row.origin_quality_band is not None:
                origin_band_counts[row.origin_quality_band] = origin_band_counts.get(row.origin_quality_band, 0) + 1

        total_players = len(country_rows)
        return RunNationDetail(
            run_id=run_id,
            country_code=summary.country_code,
            country_name=summary.country_name,
            total_players=summary.total_players,
            average_overall=summary.average_overall,
            average_age=summary.average_age,
            top_band_count=summary.top_band_count,
            manual_override_count=summary.manual_override_count,
            planner_generated_count=summary.planner_generated_count,
            rollover_carried_count=summary.rollover_carried_count,
            average_visible_stats=RunNationAverageVisibleStats(
                technique=round(sum(row.technique for row in country_rows) / total_players, 2),
                movement=round(sum(row.movement for row in country_rows) / total_players, 2),
                physical=round(sum(row.physical for row in country_rows) / total_players, 2),
                mental=round(sum(row.mental for row in country_rows) / total_players, 2),
            ),
            source_mix={
                "rollover_carried": summary.rollover_carried_count,
                "planner_generated": summary.planner_generated_count,
                "manual_override": summary.manual_override_count,
            },
            band_distribution=[
                RunNationBandDistributionItem(band=band, count=count)
                for band, count in sorted(band_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            origin_band_distribution=[
                RunNationBandDistributionItem(band=band, count=count)
                for band, count in sorted(origin_band_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            top_players=[
                RunNationTopPlayerItem(
                    player_id=row.player_id,
                    name=row.name,
                    age=row.age,
                    overall=row.overall,
                    source_type=row.source_type,
                    quality_band=row.quality_band,
                    is_top_band=row.is_top_band,
                )
                for row in top_players
            ],
        )

    def get_wildcard_state(self, *, run_id: str, event_id: str) -> WildcardStateResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        event, _ = self._resolve_event_and_index(state=state, event_id=event_id)
        templates_by_id = {template.template_id: template for template in load_tournament_templates_config().templates}
        template = templates_by_id[event.template_id]
        total_slots = template.wild_cards
        assignments = self.repository.get_wildcard_assignments_for_event(run_id=run_id, event_id=event_id)

        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        acceptance = orchestrator.entry_engine.build_acceptance_list(
            event=event,
            template=template,
            players=list(orchestrator.players_by_id.values()),
            countries_by_code=orchestrator.countries_by_code,
        )
        wild_card_entries = sorted(
            [entry for entry in acceptance.main_draw_entries if entry.status == AcceptanceStatus.WILD_CARD_PLACEHOLDER],
            key=lambda entry: (10_000 if entry.ranking_priority is None else entry.ranking_priority, entry.entry_id),
        )
        slots: list[WildcardSlotState] = []
        for index, entry in enumerate(wild_card_entries, start=1):
            slots.append(
                WildcardSlotState(
                    slot_index=index,
                    entry_id=entry.entry_id,
                    assigned_player_id=assignments.get(index),
                )
            )

        eligible, reason = self._wildcard_event_eligibility(run_id=run_id, state=state, event=event)
        return WildcardStateResponse(
            run_id=run_id,
            event_id=event_id,
            eligible=eligible,
            eligibility_reason=reason,
            total_slots=total_slots,
            slots=slots,
        )

    def assign_wildcards(
        self,
        *,
        run_id: str,
        event_id: str,
        assignments: list[WildcardAssignment],
    ) -> WildcardStateResponse:
        if not assignments:
            raise ValueError("assignments must be non-empty")
        run_info, state = self._load_run_context(run_id=run_id)
        event, _ = self._resolve_event_and_index(state=state, event_id=event_id)
        eligible, reason = self._wildcard_event_eligibility(run_id=run_id, state=state, event=event)
        if not eligible:
            raise ValueError(reason or "event is not eligible for wildcard assignment")

        templates_by_id = {template.template_id: template for template in load_tournament_templates_config().templates}
        template = templates_by_id[event.template_id]
        if template.wild_cards <= 0:
            raise ValueError("event does not define wildcard slots")

        seen_slots: set[int] = set()
        seen_players: set[str] = set()
        normalized_assignments: list[WildcardAssignment] = []
        for assignment in assignments:
            if assignment.slot_index < 1 or assignment.slot_index > template.wild_cards:
                raise ValueError(f"slot_index {assignment.slot_index} is outside available wildcard slots")
            if assignment.slot_index in seen_slots:
                raise ValueError(f"slot_index {assignment.slot_index} was provided more than once")
            if assignment.player_id in seen_players:
                raise ValueError(f"player_id {assignment.player_id} was provided more than once")
            seen_slots.add(assignment.slot_index)
            seen_players.add(assignment.player_id)
            normalized_assignments.append(WildcardAssignment(slot_index=assignment.slot_index, player_id=assignment.player_id))

        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        players_by_id = orchestrator.players_by_id
        for assignment in normalized_assignments:
            if assignment.player_id not in players_by_id:
                raise ValueError(f"player_id {assignment.player_id} was not found")

        acceptance = orchestrator.entry_engine.build_acceptance_list(
            event=event,
            template=template,
            players=list(players_by_id.values()),
            countries_by_code=orchestrator.countries_by_code,
        )
        accepted_player_ids = {
            entry.player_id
            for entry in [*acceptance.main_draw_entries, *acceptance.qualification_entries]
            if entry.player_id is not None
        }
        for assignment in normalized_assignments:
            if assignment.player_id in accepted_player_ids:
                raise ValueError(f"player_id {assignment.player_id} is already entered for event {event_id}")

        existing_assignments = self.repository.get_wildcard_assignments_for_event(run_id=run_id, event_id=event_id)
        inverse_existing = {player_id: slot_index for slot_index, player_id in existing_assignments.items()}
        for assignment in normalized_assignments:
            existing_slot = inverse_existing.get(assignment.player_id)
            if existing_slot is not None and existing_slot != assignment.slot_index:
                raise ValueError(f"player_id {assignment.player_id} is already assigned to wildcard slot {existing_slot}")

        payload = {
            "assignments": [
                {"slot_index": item.slot_index, "player_id": item.player_id}
                for item in sorted(normalized_assignments, key=lambda item: item.slot_index)
            ]
        }
        self.repository.append_admin_action(
            run_id=run_id,
            event_id=event_id,
            action_kind="assign_wildcards",
            payload=payload,
        )
        return self.get_wildcard_state(run_id=run_id, event_id=event_id)

    def get_wildcard_candidates(self, *, run_id: str, event_id: str) -> WildcardCandidatesResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        event, _ = self._resolve_event_and_index(state=state, event_id=event_id)
        templates_by_id = {template.template_id: template for template in load_tournament_templates_config().templates}
        template = templates_by_id[event.template_id]
        if template.wild_cards <= 0:
            return WildcardCandidatesResponse(run_id=run_id, event_id=event_id, candidates=[])

        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        acceptance = orchestrator.entry_engine.build_acceptance_list(
            event=event,
            template=template,
            players=list(orchestrator.players_by_id.values()),
            countries_by_code=orchestrator.countries_by_code,
        )
        entered_player_ids = {
            entry.player_id
            for entry in [*acceptance.main_draw_entries, *acceptance.qualification_entries]
            if entry.player_id is not None
        }
        assigned_player_ids = set(
            self.repository.get_wildcard_assignments_for_event(run_id=run_id, event_id=event_id).values()
        )

        raw_candidates: list[tuple[int, int, str, str, int | None, float | None]] = []
        for source_order, source_label, applicants in (
            (0, "main_draw_waitlist", acceptance.main_draw_applicants),
            (1, "qualification_waitlist", acceptance.qualification_applicants),
        ):
            for applicant in applicants:
                if applicant.player_id in entered_player_ids or applicant.player_id in assigned_player_ids:
                    continue
                raw_candidates.append(
                    (
                        source_order,
                        10_000 if applicant.ranking_priority is None else applicant.ranking_priority,
                        applicant.player_id,
                        source_label,
                        applicant.ranking_priority,
                        applicant.entry_score,
                    )
                )

        deduplicated_candidates: dict[str, tuple[str, int | None, float | None]] = {}
        for _, _, player_id, source_label, source_priority, entry_score in sorted(raw_candidates):
            if player_id in deduplicated_candidates:
                continue
            deduplicated_candidates[player_id] = (source_label, source_priority, entry_score)

        fallback_candidates = sorted(
            [
                player_id
                for player_id in orchestrator.players_by_id
                if player_id not in entered_player_ids and player_id not in assigned_player_ids and player_id not in deduplicated_candidates
            ]
        )
        for player_id in fallback_candidates:
            deduplicated_candidates[player_id] = ("non_applicant_pool", None, None)

        countries_by_code = orchestrator.countries_by_code
        candidates = [
            WildcardCandidateRecord(
                player_id=player.player_id,
                player_name=player.name,
                country_code=player.nationality,
                country_name=(countries_by_code[player.nationality].name if player.nationality in countries_by_code else None),
                source=source_label,
                source_priority=source_priority,
                entry_score=entry_score,
            )
            for player_id, (source_label, source_priority, entry_score) in deduplicated_candidates.items()
            for player in [orchestrator.players_by_id[player_id]]
        ]
        return WildcardCandidatesResponse(
            run_id=run_id,
            event_id=event_id,
            candidates=candidates,
        )

    def get_wildcard_action_history(self, *, run_id: str, event_id: str) -> WildcardActionHistoryResponse:
        _, state = self._load_run_context(run_id=run_id)
        self._resolve_event_and_index(state=state, event_id=event_id)

        actions: list[WildcardActionHistoryItem] = []
        for action in self.repository.list_admin_actions(
            run_id=run_id,
            event_id=event_id,
            action_kind="assign_wildcards",
        ):
            raw_assignments = action.payload.get("assignments", [])
            assignments: list[WildcardActionAssignmentSummary] = []
            if isinstance(raw_assignments, list):
                for item in raw_assignments:
                    if not isinstance(item, dict):
                        continue
                    raw_slot_index = item.get("slot_index")
                    raw_player_id = item.get("player_id")
                    if not isinstance(raw_slot_index, int) or not isinstance(raw_player_id, str):
                        continue
                    assignments.append(
                        WildcardActionAssignmentSummary(
                            slot_index=raw_slot_index,
                            player_id=raw_player_id,
                        )
                    )
            actions.append(
                WildcardActionHistoryItem(
                    action_sequence=action.action_sequence,
                    action_kind=action.action_kind,
                    event_id=action.event_id,
                    assignment_payload_summary=sorted(assignments, key=lambda item: item.slot_index),
                )
            )

        return WildcardActionHistoryResponse(
            run_id=run_id,
            event_id=event_id,
            actions=actions,
        )

    def get_pre_draw_withdrawal_state(self, *, run_id: str, event_id: str) -> PreDrawWithdrawalStateResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        event, _ = self._resolve_event_and_index(state=state, event_id=event_id)
        eligible, reason = self._pre_draw_withdrawal_event_eligibility(run_id=run_id, state=state, event=event)

        acceptance = self._build_effective_acceptance_for_event(run_id=run_id, run_info=run_info, event=event)
        withdrawable_entries = sorted(
            [
                entry
                for entry in acceptance.main_draw_entries
                if entry.player_id is not None
                and entry.status
                in {
                    AcceptanceStatus.DIRECT_ACCEPTANCE,
                    AcceptanceStatus.WILD_CARD_PLACEHOLDER,
                    AcceptanceStatus.WITHDRAWAL_PLACEHOLDER,
                    AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER,
                }
            ],
            key=lambda entry: (10_000 if entry.ranking_priority is None else entry.ranking_priority, entry.entry_id),
        )

        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        countries_by_code = orchestrator.countries_by_code
        withdrawable_players = [
            PreDrawWithdrawablePlayerRecord(
                player_id=entry.player_id or "",
                player_name=orchestrator.players_by_id[entry.player_id].name,
                country_code=orchestrator.players_by_id[entry.player_id].nationality,
                country_name=(
                    countries_by_code[orchestrator.players_by_id[entry.player_id].nationality].name
                    if orchestrator.players_by_id[entry.player_id].nationality in countries_by_code
                    else None
                ),
                entry_id=entry.entry_id,
                acceptance_status=entry.status.value,
            )
            for entry in withdrawable_entries
            if entry.player_id is not None and entry.player_id in orchestrator.players_by_id
        ]

        return PreDrawWithdrawalStateResponse(
            run_id=run_id,
            event_id=event_id,
            eligible=eligible,
            eligibility_reason=reason,
            withdrawable_main_draw_players=withdrawable_players,
        )

    def apply_pre_draw_withdrawal_replacement(
        self,
        *,
        run_id: str,
        event_id: str,
        withdrawn_player_id: str,
        notes: str | None = None,
    ) -> PreDrawWithdrawalResultResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        event, _ = self._resolve_event_and_index(state=state, event_id=event_id)
        eligible, reason = self._pre_draw_withdrawal_event_eligibility(run_id=run_id, state=state, event=event)
        if not eligible:
            raise ValueError(reason or "event is not eligible for pre-draw withdrawal replacement")

        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        if withdrawn_player_id not in orchestrator.players_by_id:
            raise ValueError(f"player_id {withdrawn_player_id} was not found")

        acceptance = self._build_effective_acceptance_for_event(run_id=run_id, run_info=run_info, event=event)
        withdrawn_entry = next(
            (
                entry
                for entry in acceptance.main_draw_entries
                if entry.player_id == withdrawn_player_id
                and entry.status
                in {
                    AcceptanceStatus.DIRECT_ACCEPTANCE,
                    AcceptanceStatus.WILD_CARD_PLACEHOLDER,
                    AcceptanceStatus.WITHDRAWAL_PLACEHOLDER,
                    AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER,
                }
            ),
            None,
        )
        if withdrawn_entry is None:
            raise ValueError(f"player_id {withdrawn_player_id} is not currently entered in the main draw for event {event_id}")

        entered_player_ids = {
            entry.player_id
            for entry in [*acceptance.main_draw_entries, *acceptance.qualification_entries]
            if entry.player_id is not None and entry.player_id != withdrawn_player_id
        }
        replacement_player_id: str | None = None
        replacement_source: ReplacementSource | None = None
        for source_label, applicants in (
            ("main_draw_waitlist", acceptance.main_draw_applicants),
            ("qualification_waitlist", acceptance.qualification_applicants),
        ):
            for applicant in applicants:
                if applicant.player_id in entered_player_ids:
                    continue
                replacement_player_id = applicant.player_id
                replacement_source = source_label
                break
            if replacement_player_id is not None:
                break
        if replacement_player_id is None or replacement_source is None:
            raise ValueError("no eligible replacement exists in main-draw or qualification waitlist")

        replacement_entry = next(
            (
                entry
                for entry in sorted(
                    acceptance.main_draw_entries,
                    key=lambda item: (10_000 if item.ranking_priority is None else item.ranking_priority, item.entry_id),
                )
                if entry.status == AcceptanceStatus.WITHDRAWAL_PLACEHOLDER and entry.player_id is None
            ),
            withdrawn_entry,
        )

        payload = {
            "withdrawn_player_id": withdrawn_player_id,
            "replacement_player_id": replacement_player_id,
            "replacement_source": replacement_source,
            "withdrawn_entry_id": withdrawn_entry.entry_id,
            "replacement_entry_id": replacement_entry.entry_id,
            "notes": notes,
        }
        self.repository.append_admin_action(
            run_id=run_id,
            event_id=event_id,
            action_kind="pre_draw_withdrawal_replacement",
            payload=payload,
        )
        post_state = self.get_pre_draw_withdrawal_state(run_id=run_id, event_id=event_id)
        return PreDrawWithdrawalResultResponse(
            run_id=run_id,
            event_id=event_id,
            withdrawn_player_id=withdrawn_player_id,
            replacement_player_id=replacement_player_id,
            replacement_source=replacement_source,
            withdrawn_entry_id=withdrawn_entry.entry_id,
            replacement_entry_id=replacement_entry.entry_id,
            eligible=post_state.eligible,
            eligibility_reason=post_state.eligibility_reason,
        )

    def get_pre_draw_withdrawal_action_history(self, *, run_id: str, event_id: str) -> PreDrawWithdrawalActionHistoryResponse:
        _, state = self._load_run_context(run_id=run_id)
        self._resolve_event_and_index(state=state, event_id=event_id)

        items: list[PreDrawWithdrawalActionHistoryItem] = []
        for action in self.repository.list_admin_actions(
            run_id=run_id,
            event_id=event_id,
            action_kind="pre_draw_withdrawal_replacement",
        ):
            withdrawn_player_id = action.payload.get("withdrawn_player_id")
            replacement_player_id = action.payload.get("replacement_player_id")
            replacement_source = action.payload.get("replacement_source")
            withdrawn_entry_id = action.payload.get("withdrawn_entry_id")
            replacement_entry_id = action.payload.get("replacement_entry_id")
            notes = action.payload.get("notes")
            if (
                not isinstance(withdrawn_player_id, str)
                or not isinstance(replacement_player_id, str)
                or replacement_source not in {"main_draw_waitlist", "qualification_waitlist"}
                or not isinstance(withdrawn_entry_id, str)
                or not isinstance(replacement_entry_id, str)
                or (notes is not None and not isinstance(notes, str))
            ):
                continue
            items.append(
                PreDrawWithdrawalActionHistoryItem(
                    action_sequence=action.action_sequence,
                    action_kind=action.action_kind,
                    event_id=action.event_id,
                    withdrawn_player_id=withdrawn_player_id,
                    replacement_player_id=replacement_player_id,
                    replacement_source=replacement_source,
                    withdrawn_entry_id=withdrawn_entry_id,
                    replacement_entry_id=replacement_entry_id,
                    notes=notes,
                )
            )

        return PreDrawWithdrawalActionHistoryResponse(
            run_id=run_id,
            event_id=event_id,
            actions=items,
        )

    def get_late_replacement_candidates(self, *, run_id: str, event_id: str) -> LateReplacementCandidatesResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        event, _ = self._resolve_event_and_index(state=state, event_id=event_id)
        acceptance = self._build_effective_acceptance_for_event(run_id=run_id, run_info=run_info, event=event)
        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        countries_by_code = orchestrator.countries_by_code
        candidates = self._ordered_late_replacement_candidates(
            acceptance=acceptance,
            players_by_id=orchestrator.players_by_id,
            countries_by_code=countries_by_code,
        )
        return LateReplacementCandidatesResponse(run_id=run_id, event_id=event_id, candidates=candidates)

    def get_late_replacement_state(self, *, run_id: str, event_id: str) -> LateReplacementStateResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        event, _ = self._resolve_event_and_index(state=state, event_id=event_id)
        templates_by_id = {template.template_id: template for template in load_tournament_templates_config().templates}
        template = templates_by_id[event.template_id]

        acceptance = self._build_effective_acceptance_for_event(run_id=run_id, run_info=run_info, event=event)
        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        countries_by_code = orchestrator.countries_by_code
        withdrawable_players = self._withdrawable_main_draw_players(
            acceptance=acceptance,
            players_by_id=orchestrator.players_by_id,
            countries_by_code=countries_by_code,
        )
        candidates = self._ordered_late_replacement_candidates(
            acceptance=acceptance,
            players_by_id=orchestrator.players_by_id,
            countries_by_code=countries_by_code,
        )
        used_spots = len(self.repository.get_late_replacements_for_event(run_id=run_id, event_id=event_id))
        remaining_capacity = max(0, template.lucky_loser_rules.max_spots - used_spots)
        eligible, reason = self._late_replacement_event_eligibility(
            run_id=run_id,
            state=state,
            event=event,
            has_replaceable_players=bool(withdrawable_players),
            has_candidates=bool(candidates),
            remaining_capacity=remaining_capacity,
        )
        return LateReplacementStateResponse(
            run_id=run_id,
            event_id=event_id,
            eligible=eligible,
            eligibility_reason=reason,
            replaceable_main_draw_players=withdrawable_players,
            remaining_capacity=remaining_capacity,
        )

    def apply_late_replacement(
        self,
        *,
        run_id: str,
        event_id: str,
        withdrawn_player_id: str,
        notes: str | None = None,
    ) -> LateReplacementResultResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        event, _ = self._resolve_event_and_index(state=state, event_id=event_id)
        templates_by_id = {template.template_id: template for template in load_tournament_templates_config().templates}
        template = templates_by_id[event.template_id]
        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        if withdrawn_player_id not in orchestrator.players_by_id:
            raise ValueError(f"player_id {withdrawn_player_id} was not found")

        acceptance = self._build_effective_acceptance_for_event(run_id=run_id, run_info=run_info, event=event)
        candidates = self._ordered_late_replacement_candidates(
            acceptance=acceptance,
            players_by_id=orchestrator.players_by_id,
            countries_by_code=orchestrator.countries_by_code,
        )
        used_spots = len(self.repository.get_late_replacements_for_event(run_id=run_id, event_id=event_id))
        remaining_capacity = max(0, template.lucky_loser_rules.max_spots - used_spots)
        has_withdrawable = any(
            item.player_id == withdrawn_player_id
            for item in self._withdrawable_main_draw_players(
                acceptance=acceptance,
                players_by_id=orchestrator.players_by_id,
                countries_by_code=orchestrator.countries_by_code,
            )
        )
        eligible, reason = self._late_replacement_event_eligibility(
            run_id=run_id,
            state=state,
            event=event,
            has_replaceable_players=has_withdrawable,
            has_candidates=bool(candidates),
            remaining_capacity=remaining_capacity,
        )
        if not eligible:
            raise ValueError(reason or "event is not eligible for late replacement lucky loser workflow")

        withdrawn_entry = next(
            (
                entry
                for entry in acceptance.main_draw_entries
                if entry.player_id == withdrawn_player_id
                and entry.status
                in {
                    AcceptanceStatus.DIRECT_ACCEPTANCE,
                    AcceptanceStatus.WILD_CARD_PLACEHOLDER,
                    AcceptanceStatus.WITHDRAWAL_PLACEHOLDER,
                    AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER,
                }
            ),
            None,
        )
        if withdrawn_entry is None:
            raise ValueError(f"player_id {withdrawn_player_id} is not currently entered in the main draw for event {event_id}")

        replacement = candidates[0]
        replacement_entry = self._resolve_late_replacement_destination(acceptance=acceptance, withdrawn_entry=withdrawn_entry)
        payload = {
            "withdrawn_player_id": withdrawn_player_id,
            "replacement_player_id": replacement.player_id,
            "replacement_source": replacement.source,
            "withdrawn_entry_id": withdrawn_entry.entry_id,
            "replacement_entry_id": replacement_entry.entry_id,
            "candidate_slot_index": replacement.candidate_slot_index,
            "notes": notes,
        }
        self.repository.append_admin_action(
            run_id=run_id,
            event_id=event_id,
            action_kind="late_replacement_lucky_loser",
            payload=payload,
        )
        post_state = self.get_late_replacement_state(run_id=run_id, event_id=event_id)
        return LateReplacementResultResponse(
            run_id=run_id,
            event_id=event_id,
            withdrawn_player_id=withdrawn_player_id,
            replacement_player_id=replacement.player_id,
            replacement_source=replacement.source,
            withdrawn_entry_id=withdrawn_entry.entry_id,
            replacement_entry_id=replacement_entry.entry_id,
            candidate_slot_index=replacement.candidate_slot_index,
            eligible=post_state.eligible,
            eligibility_reason=post_state.eligibility_reason,
            remaining_capacity=post_state.remaining_capacity,
        )

    def get_late_replacement_action_history(self, *, run_id: str, event_id: str) -> LateReplacementActionHistoryResponse:
        _, state = self._load_run_context(run_id=run_id)
        self._resolve_event_and_index(state=state, event_id=event_id)
        items: list[LateReplacementActionHistoryItem] = []
        for action in self.repository.list_admin_actions(
            run_id=run_id,
            event_id=event_id,
            action_kind="late_replacement_lucky_loser",
        ):
            withdrawn_player_id = action.payload.get("withdrawn_player_id")
            replacement_player_id = action.payload.get("replacement_player_id")
            replacement_source = action.payload.get("replacement_source")
            withdrawn_entry_id = action.payload.get("withdrawn_entry_id")
            replacement_entry_id = action.payload.get("replacement_entry_id")
            candidate_slot_index = action.payload.get("candidate_slot_index")
            notes = action.payload.get("notes")
            if (
                not isinstance(withdrawn_player_id, str)
                or not isinstance(replacement_player_id, str)
                or replacement_source not in {"main_draw_waitlist", "qualification_waitlist"}
                or not isinstance(withdrawn_entry_id, str)
                or not isinstance(replacement_entry_id, str)
                or (candidate_slot_index is not None and not isinstance(candidate_slot_index, int))
                or (notes is not None and not isinstance(notes, str))
            ):
                continue
            items.append(
                LateReplacementActionHistoryItem(
                    action_sequence=action.action_sequence,
                    action_kind=action.action_kind,
                    event_id=action.event_id,
                    withdrawn_player_id=withdrawn_player_id,
                    replacement_player_id=replacement_player_id,
                    replacement_source=replacement_source,
                    withdrawn_entry_id=withdrawn_entry_id,
                    replacement_entry_id=replacement_entry_id,
                    candidate_slot_index=candidate_slot_index,
                    notes=notes,
                )
            )
        return LateReplacementActionHistoryResponse(run_id=run_id, event_id=event_id, actions=items)

    def simulate_next_tournament(self, *, run_id: str) -> SimulationStepResult:
        return self._simulate_step(run_id=run_id, mode="simulate_next_tournament")

    def simulate_next_match(self, *, run_id: str) -> SimulationStepResult:
        return self._simulate_step(run_id=run_id, mode="simulate_next_match")

    def simulate_next_round(self, *, run_id: str) -> SimulationStepResult:
        return self._simulate_step(run_id=run_id, mode="simulate_next_round")

    def simulate_next_week(self, *, run_id: str) -> SimulationStepResult:
        return self._simulate_step(run_id=run_id, mode="simulate_next_week")

    def simulate_full_season(self, *, run_id: str) -> SimulationStepResult:
        return self._simulate_step(run_id=run_id, mode="simulate_full_season")

    def simulate_world_tour_finals(self, *, run_id: str) -> FinalsSimulationResult:
        run_info, state = self._load_run_context(run_id=run_id)
        orchestrator = FinalsOrchestrationService(repository=self.repository)
        return orchestrator.simulate_world_tour_finals(
            run=run_info,
            state=state,
            players_by_id=self._load_players_by_id_for_run(run_info=run_info),
        )

    def get_finals_qualification(self, *, run_id: str) -> PersistedFinalsQualification:
        run_info, state = self._load_run_context(run_id=run_id)
        orchestrator = FinalsOrchestrationService(repository=self.repository)
        existing = self.repository.get_finals_qualification(run_id=run_id, season=run_info.season)
        if existing is not None:
            return PersistedFinalsQualification(
                run_id=existing.run_id,
                season=existing.season,
                source_as_of_season=existing.source_as_of_season,
                source_as_of_week=existing.source_as_of_week,
                qualification=existing.qualification,
            )
        return orchestrator.derive_and_persist_qualification(
            run=run_info,
            state=state,
            players_by_id=self._load_players_by_id_for_run(run_info=run_info),
        )

    def get_finals_result(self, *, run_id: str) -> PersistedFinalsResult | None:
        run_info, _ = self._load_run_context(run_id=run_id)
        existing = self.repository.get_finals_result(run_id=run_id, season=run_info.season)
        if existing is None:
            return None
        return PersistedFinalsResult(
            run_id=existing.run_id,
            season=existing.season,
            event_id=existing.event_id,
            source_as_of_season=existing.source_as_of_season,
            source_as_of_week=existing.source_as_of_week,
            result=existing.result,
        )

    def get_finals_summary(self, *, run_id: str) -> FinalsSummaryResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        summary = FinalsOrchestrationService(repository=self.repository).get_summary(run_id=run_id, season=run_info.season)
        if summary.qualification is not None:
            return summary
        if state.has_remaining_events or state.race_snapshot is None:
            return summary
        derived = self.get_finals_qualification(run_id=run_id)
        return summary.model_copy(update={"qualification": derived})

    def rollover_to_next_season(self, *, run_id: str) -> SeasonRolloverResponse:
        run_info, state = self._load_run_context(run_id=run_id)
        orchestration = self._build_rollover_orchestration(seed=run_info.seed, season=run_info.season)
        return orchestration.rollover_to_next_season(
            run=run_info,
            state=state,
            players_by_id=self._load_players_by_id_for_run(run_info=run_info),
        )

    def get_latest_rollover(self, *, run_id: str) -> SeasonRolloverSummaryResponse | None:
        run_info, _ = self._load_run_context(run_id=run_id)
        orchestration = self._build_rollover_orchestration(seed=run_info.seed, season=run_info.season)
        return orchestration.get_latest_rollover_summary(run_id=run_id)

    def get_rollover(self, *, run_id: str, to_season: int) -> SeasonRolloverSummaryResponse | None:
        run_info, _ = self._load_run_context(run_id=run_id)
        orchestration = self._build_rollover_orchestration(seed=run_info.seed, season=run_info.season)
        return orchestration.get_rollover_summary(run_id=run_id, to_season=to_season)

    def list_next_season_players(self, *, run_id: str, to_season: int) -> list[NextSeasonPlayerRecord]:
        run_info, _ = self._load_run_context(run_id=run_id)
        orchestration = self._build_rollover_orchestration(seed=run_info.seed, season=run_info.season)
        return orchestration.list_next_season_players(run_id=run_id, to_season=to_season)

    def list_player_transitions(self, *, run_id: str, to_season: int) -> list[PersistedPlayerTransition]:
        run_info, _ = self._load_run_context(run_id=run_id)
        orchestration = self._build_rollover_orchestration(seed=run_info.seed, season=run_info.season)
        return orchestration.list_transitions(run_id=run_id, to_season=to_season)

    def bootstrap_next_season_run(
        self,
        *,
        run_id: str,
        child_run_id: str,
        child_seed: int | None = None,
    ) -> BootstrapNextSeasonResponse:
        parent_run, _ = self._load_run_context(run_id=run_id)
        effective_seed = parent_run.seed if child_seed is None else child_seed
        bootstrap_service = NextSeasonRunBootstrapService(repository=self.repository)
        world_generation_fingerprint = self._current_world_generation_fingerprint()
        response = bootstrap_service.bootstrap_from_rollover(
            parent_run=parent_run,
            child_run_id=child_run_id,
            child_seed=effective_seed,
            world_generation_fingerprint=world_generation_fingerprint,
        )
        if response.already_bootstrapped:
            return response

        countries_metadata = self.countries_service.get_config()
        countries = countries_metadata.countries
        parent_next_season_players = self.repository.list_next_season_players(
            run_id=run_id,
            to_season=response.to_season,
        )
        carried_player_states = [record.state for record in parent_next_season_players]
        (
            child_player_states,
            child_plan_record,
            child_country_records,
            child_provenance_records,
        ) = self._build_bootstrapped_players_and_provenance(
            run_id=child_run_id,
            parent_run_id=run_id,
            season=response.to_season,
            seed=effective_seed,
            countries=countries,
            carried_player_states=carried_player_states,
            dataset_status=countries_metadata.dataset_status,
            config_version=parent_run.config_version,
            config_fingerprint=parent_run.config_fingerprint,
        )
        self.repository.save_run_talent_plan(child_plan_record)
        self.repository.replace_run_talent_country_allocations(
            run_id=child_run_id,
            season=response.to_season,
            records=child_country_records,
        )
        self.repository.replace_generated_player_provenance(
            run_id=child_run_id,
            season=response.to_season,
            records=child_provenance_records,
        )
        self.repository.replace_next_season_players(
            run_id=child_run_id,
            from_season=response.from_season,
            to_season=response.to_season,
            next_player_states=child_player_states,
        )

        child_run_info = self.repository.get_simulation_run(run_id=child_run_id)
        if child_run_info is None:
            raise KeyError(f"run_id {child_run_id} was not found")
        orchestrator = self._build_orchestrator(season=response.to_season, seed=effective_seed, run_info=child_run_info)
        state = orchestrator.initialize_state()
        self.repository.save_season_state(run_id=child_run_id, state=state)
        return response

    def get_run_lineage(self, *, run_id: str) -> RunLineageRecord:
        lineage = self.repository.get_run_lineage(run_id=run_id)
        if lineage is None:
            raise KeyError(f"run_id {run_id} was not found")
        children = self.repository.list_child_runs(parent_run_id=run_id)
        return RunLineageRecord(
            run_id=lineage.run_id,
            source=RunSourceSummary(
                source_type=_normalize_source_type(lineage.source_type),
                parent_run_id=lineage.parent_run_id,
                source_rollover_run_id=lineage.source_rollover_run_id,
                source_rollover_from_season=lineage.source_rollover_from_season,
                source_rollover_to_season=lineage.source_rollover_to_season,
            ),
            children=[child.run_id for child in children],
        )

    def get_run_source(self, *, run_id: str) -> RunSourceSummary:
        lineage = self.repository.get_run_lineage(run_id=run_id)
        if lineage is None:
            raise KeyError(f"run_id {run_id} was not found")
        return RunSourceSummary(
            source_type=_normalize_source_type(lineage.source_type),
            parent_run_id=lineage.parent_run_id,
            source_rollover_run_id=lineage.source_rollover_run_id,
            source_rollover_from_season=lineage.source_rollover_from_season,
            source_rollover_to_season=lineage.source_rollover_to_season,
        )

    def get_run_status_summary(self, *, run_id: str) -> RunStatusSummary:
        run_info, state = self._load_run_context(run_id=run_id)
        finals_summary = self.get_finals_summary(run_id=run_id)
        latest_rollover = self.repository.get_latest_season_rollover(run_id=run_id)
        source_summary = self.get_run_source(run_id=run_id)
        child_count = len(self.repository.list_child_runs(parent_run_id=run_id))

        source: RunStatusSummarySource | None = None
        if (
            _normalize_source_type(source_summary.source_type) != "fresh_seed"
            or source_summary.parent_run_id is not None
            or source_summary.source_rollover_run_id is not None
        ):
            source = RunStatusSummarySource(
                source_type=_normalize_source_type(source_summary.source_type),
                parent_run_id=source_summary.parent_run_id,
            )

        return RunStatusSummary(
            run_id=run_info.run_id,
            season=run_info.season,
            seed=run_info.seed,
            progress=RunStatusSummaryProgress(
                next_event_index=state.next_event_index,
                total_events=len(state.ordered_events),
                completed_event_count=len(state.completed_event_ids),
            ),
            finals=RunStatusSummaryFinals(
                qualification_available=finals_summary.qualification is not None,
                result_available=finals_summary.result is not None,
            ),
            rollover=(
                RunStatusSummaryRollover(
                    latest_to_season=latest_rollover.to_season,
                    transitioned_players=latest_rollover.transitioned_players,
                )
                if latest_rollover is not None
                else None
            ),
            source=source,
            lineage=RunStatusSummaryLineage(child_run_count=child_count),
            history_counts=RunStatusSummaryHistoryCounts(
                events=len(self.repository.list_completed_event_ids(run_id=run_id)),
                ranking_snapshots=self.repository.count_ranking_snapshots(run_id=run_id),
                race_snapshots=self.repository.count_race_snapshots(run_id=run_id),
            ),
        )

    def get_run_world_status(self, *, run_id: str) -> RunWorldStatus:
        run_info, state = self._load_run_context(run_id=run_id)
        current_fingerprint = self._current_world_generation_fingerprint()
        stored_fingerprint = run_info.world_generation_fingerprint
        is_stale = stored_fingerprint != current_fingerprint
        rebuild_supported, reason = self._evaluate_rebuild_support(run_info=run_info, state=state)
        if rebuild_supported and is_stale:
            message = "Run world inputs are stale; rebuild is available for this pristine fresh-seed run."
        elif rebuild_supported:
            message = "Run world inputs are fresh; rebuild is available for this pristine fresh-seed run."
        else:
            message = reason
        return RunWorldStatus(
            run_id=run_id,
            source_type=_normalize_source_type(run_info.source_type),
            stored_world_generation_fingerprint=stored_fingerprint,
            current_world_generation_fingerprint=current_fingerprint,
            is_stale=is_stale,
            rebuild_supported=rebuild_supported,
            message=message,
        )

    def rebuild_run_world(self, *, run_id: str) -> RunWorldStatus:
        run_info, state = self._load_run_context(run_id=run_id)
        rebuild_supported, reason = self._evaluate_rebuild_support(run_info=run_info, state=state)
        if not rebuild_supported:
            raise ValueError(reason)

        world_generation_fingerprint = self._current_world_generation_fingerprint()
        countries_metadata = self.countries_service.get_config()
        countries = countries_metadata.countries
        _, plan_record, country_records, provenance_records = self._build_fresh_players_and_provenance(
            run_id=run_id,
            season=run_info.season,
            seed=run_info.seed,
            countries=countries,
            dataset_status=countries_metadata.dataset_status,
            config_version=run_info.config_version,
            config_fingerprint=run_info.config_fingerprint,
        )
        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        rebuilt_state = orchestrator.initialize_state()
        self.repository.save_season_state(run_id=run_id, state=rebuilt_state)
        self.repository.save_run_talent_plan(plan_record)
        self.repository.replace_run_talent_country_allocations(run_id=run_id, season=run_info.season, records=country_records)
        self.repository.replace_generated_player_provenance(run_id=run_id, season=run_info.season, records=provenance_records)
        self.repository.upsert_simulation_run(
            SimulationRunInfo(
                run_id=run_info.run_id,
                season=run_info.season,
                seed=run_info.seed,
                config_version=run_info.config_version,
                config_fingerprint=run_info.config_fingerprint,
                world_generation_fingerprint=world_generation_fingerprint,
                parent_run_id=run_info.parent_run_id,
                source_type=run_info.source_type,
                source_rollover_run_id=run_info.source_rollover_run_id,
                source_rollover_from_season=run_info.source_rollover_from_season,
                source_rollover_to_season=run_info.source_rollover_to_season,
            )
        )
        return self.get_run_world_status(run_id=run_id)

    def _evaluate_rebuild_support(
        self,
        *,
        run_info: SimulationRunInfo,
        state: SeasonState,
    ) -> tuple[bool, str]:
        source_type = _normalize_source_type(run_info.source_type)
        if source_type != "fresh_seed":
            return False, "Rebuild is not supported for bootstrap/child runs in this MVP."
        if state.next_event_index != 0 or state.completed_event_ids or state.active_tournament is not None:
            return False, "Rebuild is not allowed after simulation progress."
        return True, "Rebuild supported."

    def list_runs_index(self) -> list[RunIndexSummary]:
        runs = self.repository.list_simulation_runs()
        child_counts = self.repository.list_child_run_counts()
        summaries: list[RunIndexSummary] = []
        for run in runs:
            state = self.repository.load_season_state(run_id=run.run_id)
            if state is None:
                continue
            source_type = _normalize_source_type(run.source_type)
            summaries.append(
                RunIndexSummary(
                    run_id=run.run_id,
                    season=run.season,
                    seed=run.seed,
                    progress=RunIndexSummaryProgress(
                        next_event_index=state.next_event_index,
                        total_events=len(state.ordered_events),
                        completed_event_count=len(state.completed_event_ids),
                    ),
                    source_type=source_type,
                    parent_run_id=run.parent_run_id,
                    child_run_count=child_counts.get(run.run_id, 0),
                )
            )
        return summaries

    def list_events(self, *, run_id: str) -> list[PersistedEventRecord]:
        return self.repository.list_completed_events(run_id=run_id)

    def get_event(self, *, run_id: str, event_id: str) -> PersistedEventRecord | None:
        return self.repository.get_completed_event(run_id=run_id, event_id=event_id)

    def list_ranking_snapshots(self, *, run_id: str) -> list[tuple[int, str, str | None, RankingSnapshot]]:
        return self.repository.list_ranking_snapshots(run_id=run_id)

    def get_ranking_snapshot(
        self, *, run_id: str, snapshot_sequence: int
    ) -> tuple[int, str, str | None, RankingSnapshot] | None:
        return self.repository.get_ranking_snapshot(run_id=run_id, snapshot_sequence=snapshot_sequence)

    def list_race_snapshots(self, *, run_id: str) -> list[tuple[int, str, str | None, RaceSnapshot]]:
        return self.repository.list_race_snapshots(run_id=run_id)

    def get_race_snapshot(
        self, *, run_id: str, snapshot_sequence: int
    ) -> tuple[int, str, str | None, RaceSnapshot] | None:
        return self.repository.get_race_snapshot(run_id=run_id, snapshot_sequence=snapshot_sequence)

    def get_run_activity_feed(self, *, run_id: str) -> RunActivityFeed:
        _, state = self._load_run_context(run_id=run_id)
        items: list[RunActivityItem] = []

        for event in self.repository.list_completed_events(run_id=run_id):
            items.append(
                RunActivityItem(
                    kind="event",
                    sequence=event.event_sequence,
                    label=f"Event {event.event_id}",
                    season=event.season,
                    week=event.week,
                    event_id=event.event_id,
                )
            )

        for snapshot in self.repository.list_ranking_snapshot_records(run_id=run_id):
            items.append(
                RunActivityItem(
                    kind="ranking_snapshot",
                    sequence=snapshot.snapshot_sequence,
                    label=f"Ranking snapshot {snapshot.snapshot_sequence}",
                    season=snapshot.as_of_season,
                    week=snapshot.as_of_week,
                    snapshot_sequence=snapshot.snapshot_sequence,
                    source_event_id=snapshot.source_event_id,
                )
            )

        for snapshot in self.repository.list_race_snapshot_records(run_id=run_id):
            items.append(
                RunActivityItem(
                    kind="race_snapshot",
                    sequence=snapshot.snapshot_sequence,
                    label=f"Race snapshot {snapshot.snapshot_sequence}",
                    season=snapshot.as_of_season,
                    week=snapshot.as_of_week,
                    snapshot_sequence=snapshot.snapshot_sequence,
                    source_event_id=snapshot.source_event_id,
                )
            )

        for qualification in self.repository.list_finals_qualifications(run_id=run_id):
            items.append(
                RunActivityItem(
                    kind="finals_qualification",
                    sequence=qualification.season,
                    label=f"Finals qualification S{qualification.season}",
                    season=qualification.source_as_of_season,
                    week=qualification.source_as_of_week,
                )
            )

        for result in self.repository.list_finals_results(run_id=run_id):
            items.append(
                RunActivityItem(
                    kind="finals_result",
                    sequence=result.season,
                    label=f"Finals result S{result.season}",
                    season=result.source_as_of_season,
                    week=result.source_as_of_week,
                    event_id=result.event_id,
                )
            )

        for rollover in self.repository.list_season_rollovers(run_id=run_id):
            items.append(
                RunActivityItem(
                    kind="rollover",
                    sequence=rollover.to_season,
                    label=f"Season rollover S{rollover.from_season}→S{rollover.to_season}",
                    season=rollover.to_season,
                )
            )

        for child in self.repository.list_child_runs(parent_run_id=run_id):
            items.append(
                RunActivityItem(
                    kind="bootstrap_child",
                    sequence=child.source_rollover_to_season,
                    label=f"Bootstrapped child run {child.run_id}",
                    season=child.source_rollover_to_season,
                    related_run_id=child.run_id,
                )
            )

        kind_order: dict[ActivityKind, int] = {
            "event": 1,
            "ranking_snapshot": 2,
            "race_snapshot": 3,
            "finals_qualification": 4,
            "finals_result": 5,
            "rollover": 6,
            "bootstrap_child": 7,
            "admin_wildcard_assignment": 8,
            "admin_pre_draw_withdrawal_replacement": 9,
            "admin_late_replacement_lucky_loser": 10,
        }
        for admin_action in self.repository.list_admin_actions(run_id=run_id, action_kind="assign_wildcards"):
            items.append(
                RunActivityItem(
                    kind="admin_wildcard_assignment",
                    sequence=admin_action.action_sequence,
                    label=f"Commissioner wildcard assignment ({admin_action.event_id})",
                    event_id=admin_action.event_id,
                )
            )
        for admin_action in self.repository.list_admin_actions(run_id=run_id, action_kind="pre_draw_withdrawal_replacement"):
            event, _ = self._resolve_event_and_index(state=state, event_id=admin_action.event_id)
            items.append(
                RunActivityItem(
                    kind="admin_pre_draw_withdrawal_replacement",
                    sequence=admin_action.action_sequence,
                    label=f"Commissioner pre-draw withdrawal replacement ({admin_action.event_id})",
                    season=event.season,
                    week=event.week,
                    event_id=admin_action.event_id,
                )
            )
        for admin_action in self.repository.list_admin_actions(run_id=run_id, action_kind="late_replacement_lucky_loser"):
            event, _ = self._resolve_event_and_index(state=state, event_id=admin_action.event_id)
            items.append(
                RunActivityItem(
                    kind="admin_late_replacement_lucky_loser",
                    sequence=admin_action.action_sequence,
                    label=f"Commissioner late replacement lucky loser ({admin_action.event_id})",
                    season=event.season,
                    week=event.week,
                    event_id=admin_action.event_id,
                )
            )
        ordered = sorted(
            items,
            key=lambda item: (
                item.season if item.season is not None else 9999,
                item.week if item.week is not None else 99,
                kind_order[item.kind],
                item.sequence if item.sequence is not None else 999999,
                item.event_id or item.source_event_id or item.related_run_id or item.label,
            ),
        )
        return RunActivityFeed(run_id=run_id, items=ordered)

    def _simulate_step(self, *, run_id: str, mode: str) -> SimulationStepResult:
        run_info, state = self._load_run_context(run_id=run_id)
        if mode in {"simulate_next_match", "simulate_next_round"}:
            self._validate_finals_phase_not_started(run_id=run_id, season=run_info.season)

        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        if mode == "simulate_next_match":
            step = orchestrator.simulate_next_match(state=state)
        elif mode == "simulate_next_round":
            step = orchestrator.simulate_next_round(state=state)
        elif mode == "simulate_next_tournament":
            step = orchestrator.simulate_next_tournament(state=state)
        elif mode == "simulate_next_week":
            step = orchestrator.simulate_next_week(state=state)
        elif mode == "simulate_full_season":
            step = orchestrator.simulate_full_season(state=state)
        else:
            raise ValueError(f"unsupported mode: {mode}")

        persistence = SimulationPersistenceService(repository=self.repository)
        persistence.persist_step(run_id=run_id, step=step)
        return step

    def _validate_finals_phase_not_started(self, *, run_id: str, season: int) -> None:
        if self.repository.get_finals_result(run_id=run_id, season=season) is not None:
            raise ValueError("cannot simulate next match/round after finals completion")
        if self.repository.get_finals_qualification(run_id=run_id, season=season) is not None:
            raise ValueError("cannot simulate next match/round after finals phase has begun")

    def _build_orchestrator(
        self,
        *,
        season: int,
        seed: int,
        run_info: SimulationRunInfo | None,
        parent_run_id: str | None = None,
    ) -> SeasonSimulationOrchestrator:
        calendar = load_season_calendar(season=season)

        templates = load_tournament_templates_config().templates
        countries = self.countries_service.get_config().countries
        countries_by_code = {country.code: country for country in countries}
        players = self._build_players_for_run(
            run_info=run_info,
            season=season,
            seed=seed,
            countries=countries,
            parent_run_id=parent_run_id,
        )

        return SeasonSimulationOrchestrator.build(
            calendar=calendar,
            templates=templates,
            players=players,
            countries_by_code=countries_by_code,
            points_by_ref=load_points_config(),
            entry_tuning=load_entry_tuning_config(),
            seed=seed,
            wildcard_assignments_by_event=(
                {}
                if run_info is None
                else self.repository.get_wildcard_assignments_for_run(run_id=run_info.run_id)
            ),
            pre_draw_withdrawal_replacements_by_event=(
                {}
                if run_info is None
                else self.repository.get_pre_draw_withdrawal_replacements_for_run(run_id=run_info.run_id)
            ),
            late_replacements_by_event=(
                {}
                if run_info is None
                else self.repository.get_late_replacements_for_run(run_id=run_info.run_id)
            ),
        )

    def _load_run_context(self, *, run_id: str) -> tuple[SimulationRunInfo, SeasonState]:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        state = self.repository.load_season_state(run_id=run_id)
        if run_info is None or state is None:
            raise KeyError(f"run_id {run_id} was not found")
        return run_info, state

    def _build_players(self, *, seed: int, season: int, countries: list[Country]) -> list[Player]:
        players, _, _, _ = self._build_fresh_players_and_provenance(
            run_id="ephemeral-preview",
            season=season,
            seed=seed,
            countries=countries,
            dataset_status=None,
            config_version=None,
            config_fingerprint=None,
        )
        return players

    def _build_fresh_players_and_provenance(
        self,
        *,
        run_id: str,
        season: int,
        seed: int,
        countries: list[Country],
        dataset_status: str | None,
        config_version: str | None,
        config_fingerprint: str | None,
    ) -> tuple[
        list[Player],
        PersistedRunTalentPlanRecord,
        list[PersistedRunTalentCountryAllocationRecord],
        list[PersistedGeneratedPlayerProvenanceRecord],
    ]:
        return self._build_intake_players_and_provenance(
            run_id=run_id,
            season=season,
            seed=seed,
            countries=countries,
            dataset_status=dataset_status,
            config_version=config_version,
            config_fingerprint=config_fingerprint,
            existing_player_ids=None,
            sequence_floor_by_country=None,
        )

    def _build_intake_players_and_provenance(
        self,
        *,
        run_id: str,
        season: int,
        seed: int,
        countries: list[Country],
        dataset_status: str | None,
        config_version: str | None,
        config_fingerprint: str | None,
        existing_player_ids: set[str] | None,
        sequence_floor_by_country: dict[str, int] | None,
    ) -> tuple[
        list[Player],
        PersistedRunTalentPlanRecord,
        list[PersistedRunTalentCountryAllocationRecord],
        list[PersistedGeneratedPlayerProvenanceRecord],
    ]:
        planner = AnnualTalentClassPlanner(dampener=self._build_recent_greatness_dampener(season=season, include_history=run_id != "ephemeral-preview"))
        plan = planner.plan(year=season, seed=seed, countries=countries)
        generator = PlayerGenerator(
            rng=DeterministicRng(seed),
            identity_config=load_player_identity_config(),
            country_talent_model=CountryTalentModel(),
        )
        countries_by_code = {country.code: country for country in countries}
        reserved_player_ids = set() if existing_player_ids is None else set(existing_player_ids)
        floor_by_country = {} if sequence_floor_by_country is None else dict(sequence_floor_by_country)
        bias_profiles_by_country = {allocation.country_code: allocation.bias_profile for allocation in plan.allocations}
        planner_sequence_by_country = {
            allocation.country_code: max(
                max((talent.sequence for talent in allocation.talents), default=0),
                floor_by_country.get(allocation.country_code, 0),
            )
            for allocation in plan.allocations
        }
        players: list[Player] = []
        country_records: list[PersistedRunTalentCountryAllocationRecord] = []
        provenance_records: list[PersistedGeneratedPlayerProvenanceRecord] = []
        for allocation in plan.allocations:
            country = countries_by_code[allocation.country_code]
            next_sequence = floor_by_country.get(allocation.country_code, 0)
            band_counts: dict[str, int] = {}
            for talent in allocation.talents:
                next_sequence += 1
                player = generator.generate_from_talent_seed(
                    country=country,
                    sequence=next_sequence,
                    talent_seed_value=talent.seed_value,
                    quality_band=talent.quality_band,
                    bias_profile=allocation.bias_profile,
                )
                if player.player_id in reserved_player_ids:
                    raise ValueError(
                        f"intake player_id collision for run_id {run_id} season {season}: {player.player_id}"
                    )
                reserved_player_ids.add(player.player_id)
                players.append(player)
                band_key = talent.quality_band.value
                band_counts[band_key] = band_counts.get(band_key, 0) + 1
                provenance_records.append(
                    PersistedGeneratedPlayerProvenanceRecord(
                        run_id=run_id,
                        season=season,
                        player_id=player.player_id,
                        country_code=allocation.country_code,
                        talent_sequence=next_sequence,
                        talent_seed_value=talent.seed_value,
                        quality_band=band_key,
                        is_top_band=band_key in {"elite_prospect", "special_prospect", "generational_talent"},
                        source_type="planner_generated",
                        override_id=None,
                        origin_source_type="planner_generated",
                        origin_quality_band=band_key,
                        origin_override_id=None,
                        origin_season=season,
                    )
                )
            country_records.append(
                PersistedRunTalentCountryAllocationRecord(
                    run_id=run_id,
                    season=season,
                    country_code=allocation.country_code,
                    planned_count=allocation.planned_count,
                    quality_weights={band.value: float(weight) for band, weight in allocation.quality_weights.items()},
                    actual_band_counts=band_counts,
                    bias_profile=allocation.bias_profile.model_dump(),
                    dampener=allocation.dampener.model_dump(mode="json"),
                )
            )

        active_manual_overrides = self.manual_overrides_service.list_overrides(season=season, enabled=True)
        for index, override in enumerate(active_manual_overrides, start=1):
            country = countries_by_code.get(override.country_code)
            if country is None:
                raise ValueError(
                    "manual override "
                    f"'{override.override_id}' references unknown country_code '{override.country_code}'"
                )
            planner_sequence_by_country[override.country_code] = planner_sequence_by_country.get(override.country_code, 0) + 1
            manual_sequence = planner_sequence_by_country[override.country_code]
            quality_band = self._manual_quality_band(override)
            seed_value = DeterministicRng(seed).derive(
                SeedScope.SEASON,
                "manual_override_player",
                season,
                override.override_id,
                index,
            ).value
            base_player = generator.generate_from_talent_seed(
                country=country,
                sequence=manual_sequence,
                talent_seed_value=seed_value,
                quality_band=quality_band,
                bias_profile=bias_profiles_by_country.get(override.country_code),
            )
            player = self._apply_manual_override_to_player(
                base_player=base_player,
                override=override,
                season=season,
            )
            if player.player_id in reserved_player_ids:
                raise ValueError(
                    f"manual override player_id collision for run_id {run_id} season {season}: {player.player_id}"
                )
            reserved_player_ids.add(player.player_id)
            players.append(player)
            provenance_records.append(
                PersistedGeneratedPlayerProvenanceRecord(
                    run_id=run_id,
                    season=season,
                    player_id=player.player_id,
                    country_code=override.country_code,
                    talent_sequence=None,
                    talent_seed_value=seed_value,
                    quality_band=quality_band.value,
                    is_top_band=quality_band in {
                        TalentQualityBand.ELITE,
                        TalentQualityBand.SPECIAL,
                        TalentQualityBand.GENERATIONAL,
                    },
                    source_type="manual_override",
                    override_id=override.override_id,
                    origin_source_type="manual_override",
                    origin_quality_band=quality_band.value,
                    origin_override_id=override.override_id,
                    origin_season=season,
                )
            )
        plan_record = PersistedRunTalentPlanRecord(
            run_id=run_id,
            season=season,
            seed=seed,
            total_talents=plan.total_talents,
            dataset_status=dataset_status,
            config_version=config_version,
            config_fingerprint=config_fingerprint,
        )
        return players, plan_record, country_records, provenance_records

    def _build_bootstrapped_players_and_provenance(
        self,
        *,
        run_id: str,
        parent_run_id: str,
        season: int,
        seed: int,
        countries: list[Country],
        carried_player_states: list[NextSeasonPlayerState],
        dataset_status: str | None,
        config_version: str | None,
        config_fingerprint: str | None,
    ) -> tuple[
        list[NextSeasonPlayerState],
        PersistedRunTalentPlanRecord,
        list[PersistedRunTalentCountryAllocationRecord],
        list[PersistedGeneratedPlayerProvenanceRecord],
    ]:
        carried_players_by_id = {state.player.player_id: state for state in carried_player_states}
        sequence_floor_by_country: dict[str, int] = {}
        for state in carried_player_states:
            country_code, sequence = self._parse_player_sequence(state.player.player_id)
            if country_code is None or sequence is None:
                continue
            sequence_floor_by_country[country_code] = max(sequence_floor_by_country.get(country_code, 0), sequence)

        intake_players, plan_record, country_records, intake_provenance = self._build_intake_players_and_provenance(
            run_id=run_id,
            season=season,
            seed=seed,
            countries=countries,
            dataset_status=dataset_status,
            config_version=config_version,
            config_fingerprint=config_fingerprint,
            existing_player_ids=set(carried_players_by_id),
            sequence_floor_by_country=sequence_floor_by_country,
        )

        merged_player_states = list(carried_player_states)
        for player in intake_players:
            if player.player_id in carried_players_by_id:
                raise ValueError(f"bootstrapped intake collision for run_id {run_id}: {player.player_id}")
            merged_player_states.append(
                NextSeasonPlayerState(
                    player=player,
                    readiness=1.0,
                    carryover_fatigue=0.0,
                )
            )

        parent_provenance_by_player_id = {
            record.player_id: record for record in self.repository.list_generated_player_provenance(run_id=parent_run_id)
        }
        carried_provenance: list[PersistedGeneratedPlayerProvenanceRecord] = [
            self._build_carried_provenance_record(
                run_id=run_id,
                season=season,
                player_state=state,
                prior_provenance=parent_provenance_by_player_id.get(state.player.player_id),
            )
            for state in carried_player_states
        ]
        provenance_records = sorted(
            [*carried_provenance, *intake_provenance],
            key=lambda record: (record.country_code, record.source_type, record.player_id),
        )

        if len({state.player.player_id for state in merged_player_states}) != len(merged_player_states):
            raise ValueError(f"bootstrapped player pool contains duplicate player_id values for run_id {run_id}")
        return merged_player_states, plan_record, country_records, provenance_records

    def _build_recent_greatness_dampener(self, *, season: int, include_history: bool) -> WeightedRecentGreatnessDampener:
        if not include_history:
            return WeightedRecentGreatnessDampener(signals=tuple())

        signals: list[RecentGreatnessSignal] = []

        for override in self.manual_overrides_service.list_overrides(enabled=True):
            if override.season >= season:
                continue
            signals.append(
                RecentGreatnessSignal(
                    country_code=override.country_code,
                    season=override.season,
                    source="manual_override",
                    quality_band=self._manual_quality_band(override),
                    raw_weight=self._manual_override_signal_weight(override),
                    reference_id=override.override_id,
                )
            )

        historical = self.repository.list_generated_player_provenance_history(
            season_lt=season,
            season_gte=season - 8,
            source_type="planner_generated",
        )
        seen: set[tuple[int, str, str, str]] = set()
        for record in historical:
            if record.quality_band not in {
                TalentQualityBand.GENERATIONAL.value,
                TalentQualityBand.SPECIAL.value,
                TalentQualityBand.ELITE.value,
            }:
                continue
            dedupe_key = (record.season, record.country_code, record.quality_band or "", record.player_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            signals.append(
                RecentGreatnessSignal(
                    country_code=record.country_code,
                    season=record.season,
                    source="planner_generated",
                    quality_band=TalentQualityBand(record.quality_band),
                    raw_weight=self._planner_history_signal_weight(TalentQualityBand(record.quality_band)),
                    reference_id=record.player_id,
                )
            )

        return WeightedRecentGreatnessDampener(signals=tuple(sorted(signals, key=lambda item: (item.country_code, item.season, item.source, item.reference_id or ""))))

    def _current_world_generation_fingerprint(self) -> str:
        payload = self._world_generation_fingerprint_payload()
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _world_generation_fingerprint_payload(self) -> dict[str, object]:
        countries = sorted(
            (country.model_dump(mode="json") for country in self.countries_service.get_config().countries),
            key=lambda item: str(item["code"]),
        )
        overrides = sorted(
            (override.model_dump(mode="json") for override in self.manual_overrides_service.list_overrides()),
            key=lambda item: (int(item["season"]), str(item["country_code"]), str(item["override_id"])),
        )
        return {
            "countries": countries,
            "manual_player_overrides": overrides,
        }

    @staticmethod
    def _manual_override_signal_weight(override: ManualPlayerOverride) -> float:
        quality = SimulationApiService._manual_quality_band(override)
        if override.is_exceptional and quality == TalentQualityBand.GENERATIONAL:
            return 2.6
        if override.is_exceptional and quality == TalentQualityBand.SPECIAL:
            return 1.9
        if override.is_exceptional:
            return 1.4
        if quality == TalentQualityBand.GENERATIONAL:
            return 1.1
        if quality == TalentQualityBand.SPECIAL:
            return 0.8
        if quality == TalentQualityBand.ELITE:
            return 0.35
        return 0.0

    @staticmethod
    def _planner_history_signal_weight(quality_band: TalentQualityBand) -> float:
        if quality_band == TalentQualityBand.GENERATIONAL:
            return 1.05
        if quality_band == TalentQualityBand.SPECIAL:
            return 0.55
        if quality_band == TalentQualityBand.ELITE:
            return 0.16
        return 0.0

    @staticmethod
    def _to_generated_player_provenance(record: PersistedGeneratedPlayerProvenanceRecord) -> GeneratedPlayerProvenance:
        return GeneratedPlayerProvenance(
            run_id=record.run_id,
            season=record.season,
            player_id=record.player_id,
            country_code=record.country_code,
            talent_sequence=record.talent_sequence,
            talent_seed_value=record.talent_seed_value,
            quality_band=record.quality_band,
            is_top_band=record.is_top_band,
            source_type=record.source_type,
            override_id=record.override_id,
            origin_source_type=SimulationApiService._normalize_origin_source_type(record.origin_source_type),
            origin_quality_band=record.origin_quality_band,
            origin_override_id=record.origin_override_id,
            origin_season=record.origin_season,
        )

    def _build_carried_provenance_record(
        self,
        *,
        run_id: str,
        season: int,
        player_state: NextSeasonPlayerState,
        prior_provenance: PersistedGeneratedPlayerProvenanceRecord | None,
    ) -> PersistedGeneratedPlayerProvenanceRecord:
        return PersistedGeneratedPlayerProvenanceRecord(
            run_id=run_id,
            season=season,
            player_id=player_state.player.player_id,
            country_code=player_state.player.nationality,
            talent_sequence=None,
            talent_seed_value=None,
            quality_band=None,
            is_top_band=False,
            source_type="rollover_carried",
            override_id=None,
            origin_source_type=(
                self._normalize_origin_source_type(prior_provenance.origin_source_type)
                if prior_provenance is not None and prior_provenance.origin_source_type is not None
                else self._normalize_origin_source_type(prior_provenance.source_type) if prior_provenance is not None else None
            ),
            origin_quality_band=(
                prior_provenance.origin_quality_band
                if prior_provenance is not None and prior_provenance.origin_quality_band is not None
                else prior_provenance.quality_band if prior_provenance is not None else None
            ),
            origin_override_id=(
                prior_provenance.origin_override_id
                if prior_provenance is not None and prior_provenance.origin_override_id is not None
                else prior_provenance.override_id if prior_provenance is not None else None
            ),
            origin_season=(
                prior_provenance.origin_season
                if prior_provenance is not None and prior_provenance.origin_season is not None
                else prior_provenance.season if prior_provenance is not None else None
            ),
        )

    @staticmethod
    def _manual_quality_band(override: ManualPlayerOverride) -> TalentQualityBand:
        if override.quality_band_override is not None:
            return override.quality_band_override
        mapping = {
            ManualPlayerProfileTier.STRONG: TalentQualityBand.STRONG,
            ManualPlayerProfileTier.ELITE: TalentQualityBand.ELITE,
            ManualPlayerProfileTier.SPECIAL: TalentQualityBand.SPECIAL,
            ManualPlayerProfileTier.GENERATIONAL: TalentQualityBand.GENERATIONAL,
        }
        return mapping[override.profile_tier]

    @staticmethod
    def _apply_manual_override_to_player(*, base_player: Player, override: ManualPlayerOverride, season: int) -> Player:
        player_id = override.player_id or f"MAN-{season}-{override.country_code}-{override.override_id}".upper()
        player = base_player.model_copy(
            update={
                "player_id": player_id,
                "name": override.player_name,
                "age": override.age,
            }
        )
        if override.attribute_overrides is not None:
            data = {k: v for k, v in override.attribute_overrides.model_dump().items() if v is not None}
            if data:
                player = player.model_copy(update=data)

        if override.hidden_trait_overrides is not None:
            hidden_updates = {k: v for k, v in override.hidden_trait_overrides.model_dump().items() if v is not None}
            if hidden_updates:
                player = player.model_copy(
                    update={
                        "hidden_career_traits": player.hidden_career_traits.model_copy(update=hidden_updates),
                    }
                )
        return player

    def _build_players_by_id(self, *, seed: int, season: int) -> dict[str, Player]:
        countries = self.countries_service.get_config().countries
        return {player.player_id: player for player in self._build_players(seed=seed, season=season, countries=countries)}

    def _load_players_by_id_for_run(self, *, run_info: SimulationRunInfo) -> dict[str, Player]:
        countries = self.countries_service.get_config().countries
        players = self._build_players_for_run(
            run_info=run_info,
            season=run_info.season,
            seed=run_info.seed,
            countries=countries,
        )
        return {player.player_id: player for player in players}

    def _build_players_for_run(
        self,
        *,
        run_info: SimulationRunInfo | None,
        season: int,
        seed: int,
        countries: list[Country],
        parent_run_id: str | None = None,
    ) -> list[Player]:
        if run_info is not None:
            own_records = self.repository.list_next_season_players(
                run_id=run_info.run_id,
                to_season=season,
            )
            if own_records:
                return [record.state.player for record in own_records]

        source_rollover_run_id = run_info.source_rollover_run_id if run_info is not None else parent_run_id
        source_rollover_to_season = run_info.source_rollover_to_season if run_info is not None else season

        if source_rollover_run_id is not None and source_rollover_to_season is not None:
            records = self.repository.list_next_season_players(
                run_id=source_rollover_run_id,
                to_season=source_rollover_to_season,
            )
            if records:
                return [record.state.player for record in records]
        return self._build_players(seed=seed, season=season, countries=countries)

    @staticmethod
    def _parse_player_sequence(player_id: str) -> tuple[str | None, int | None]:
        parts = player_id.split("-")
        if len(parts) < 2:
            return None, None
        country_code = parts[0].upper()
        sequence_part = parts[1]
        if not sequence_part.isdigit():
            return country_code, None
        return country_code, int(sequence_part)

    def _to_run_player_list_item(
        self,
        player: Player,
        provenance: PersistedGeneratedPlayerProvenanceRecord | None,
    ) -> RunPlayerListItem:
        return RunPlayerListItem(
            player_id=player.player_id,
            name=player.name,
            country_code=player.nationality,
            age=player.age,
            source_type=self._provenance_source_type(provenance),
            override_id=provenance.override_id if provenance else None,
            quality_band=provenance.quality_band if provenance else None,
            is_top_band=provenance.is_top_band if provenance else False,
            origin_source_type=self._normalize_origin_source_type(provenance.origin_source_type) if provenance else None,
            origin_quality_band=provenance.origin_quality_band if provenance else None,
            origin_override_id=provenance.origin_override_id if provenance else None,
            origin_season=provenance.origin_season if provenance else None,
            technique=player.technique,
            movement=player.movement,
            physical=player.physical,
            mental=player.mental,
            overall=self._player_overall(player),
        )

    @staticmethod
    def _provenance_source_type(
        provenance: PersistedGeneratedPlayerProvenanceRecord | None,
    ) -> Literal["rollover_carried", "planner_generated", "manual_override"]:
        if provenance is None:
            return "rollover_carried"
        source_type = _normalize_source_type(provenance.source_type)
        if source_type not in {"rollover_carried", "planner_generated", "manual_override"}:
            return "rollover_carried"
        return source_type

    @staticmethod
    def _normalize_origin_source_type(
        raw_source_type: str | None,
    ) -> Literal["planner_generated", "manual_override"] | None:
        if raw_source_type is None:
            return None
        source_type = _normalize_source_type(raw_source_type)
        if source_type not in {"planner_generated", "manual_override"}:
            return None
        return source_type

    @staticmethod
    def _player_overall(player: Player) -> int:
        return round((player.technique + player.movement + player.physical + player.mental) / 4)

    @staticmethod
    def _filter_run_players(
        *,
        players: list[RunPlayerListItem],
        country_code: str | None,
        source_type: str | None,
        min_age: int | None,
        max_age: int | None,
        search: str | None,
    ) -> list[RunPlayerListItem]:
        filtered = players
        if country_code:
            normalized_country = country_code.strip().upper()
            filtered = [row for row in filtered if row.country_code.upper() == normalized_country]
        if source_type:
            normalized_source = source_type.strip().lower()
            filtered = [row for row in filtered if row.source_type == normalized_source]
        if min_age is not None:
            filtered = [row for row in filtered if row.age >= min_age]
        if max_age is not None:
            filtered = [row for row in filtered if row.age <= max_age]
        if search:
            needle = search.strip().lower()
            filtered = [
                row
                for row in filtered
                if needle in row.player_id.lower() or needle in row.name.lower()
            ]
        return filtered

    @staticmethod
    def _sort_run_players(*, players: list[RunPlayerListItem], sort: str) -> list[RunPlayerListItem]:
        if sort == "age_desc":
            return sorted(players, key=lambda row: (-row.age, row.name, row.player_id))
        if sort == "age_asc":
            return sorted(players, key=lambda row: (row.age, row.name, row.player_id))
        if sort == "overall_desc":
            return sorted(players, key=lambda row: (-row.overall, row.name, row.player_id))
        if sort == "overall_asc":
            return sorted(players, key=lambda row: (row.overall, row.name, row.player_id))
        return sorted(players, key=lambda row: (row.name.lower(), row.player_id))

    @staticmethod
    def _aggregate_run_nation_summaries(
        *,
        rows: list[RunPlayerListItem],
        country_names: dict[str, str],
    ) -> list[RunNationSummaryItem]:
        grouped: dict[str, list[RunPlayerListItem]] = {}
        for row in rows:
            grouped.setdefault(row.country_code.upper(), []).append(row)

        summaries: list[RunNationSummaryItem] = []
        for country_code, country_rows in grouped.items():
            total_players = len(country_rows)
            top_player = sorted(country_rows, key=lambda row: (-row.overall, row.name, row.player_id))[0]
            summaries.append(
                RunNationSummaryItem(
                    country_code=country_code,
                    country_name=country_names.get(country_code),
                    total_players=total_players,
                    average_overall=round(sum(row.overall for row in country_rows) / total_players, 2),
                    average_age=round(sum(row.age for row in country_rows) / total_players, 2),
                    top_band_count=sum(1 for row in country_rows if row.is_top_band),
                    manual_override_count=sum(1 for row in country_rows if row.source_type == "manual_override"),
                    planner_generated_count=sum(1 for row in country_rows if row.source_type == "planner_generated"),
                    rollover_carried_count=sum(1 for row in country_rows if row.source_type == "rollover_carried"),
                    top_player_id=top_player.player_id,
                    top_player_name=top_player.name,
                    top_player_overall=top_player.overall,
                )
            )
        return summaries

    @staticmethod
    def _filter_run_nations(*, summaries: list[RunNationSummaryItem], search: str | None) -> list[RunNationSummaryItem]:
        if not search:
            return summaries
        needle = search.strip().lower()
        return [
            summary
            for summary in summaries
            if needle in summary.country_code.lower() or needle in (summary.country_name or "").lower()
        ]

    @staticmethod
    def _sort_run_nations(*, summaries: list[RunNationSummaryItem], sort: str) -> list[RunNationSummaryItem]:
        if sort == "total_players_asc":
            return sorted(summaries, key=lambda row: (row.total_players, row.country_code))
        if sort == "avg_overall_desc":
            return sorted(summaries, key=lambda row: (-row.average_overall, row.country_code))
        if sort == "avg_overall_asc":
            return sorted(summaries, key=lambda row: (row.average_overall, row.country_code))
        if sort == "top_band_desc":
            return sorted(summaries, key=lambda row: (-row.top_band_count, row.country_code))
        if sort == "top_band_asc":
            return sorted(summaries, key=lambda row: (row.top_band_count, row.country_code))
        return sorted(summaries, key=lambda row: (-row.total_players, row.country_code))

    def _to_run_player_detail(
        self,
        *,
        player: Player,
        provenance: PersistedGeneratedPlayerProvenanceRecord | None,
    ) -> RunPlayerDetail:
        return RunPlayerDetail(
            player_id=player.player_id,
            name=player.name,
            country_code=player.nationality,
            age=player.age,
            play_style=player.play_style,
            archetype=player.archetype,
            technique=player.technique,
            movement=player.movement,
            physical=player.physical,
            mental=player.mental,
            consistency=player.consistency,
            clutch=player.clutch,
            recovery=player.recovery,
            overall=self._player_overall(player),
            hidden_traits=RunPlayerHiddenTraitSummary(
                potential_ceiling=player.hidden_career_traits.potential_ceiling,
                growth_curve=player.hidden_career_traits.growth_curve,
                professionalism=player.hidden_career_traits.professionalism,
                ambition=player.hidden_career_traits.ambition,
                travel_tolerance=player.hidden_career_traits.travel_tolerance,
                schedule_aggression=player.hidden_career_traits.schedule_aggression,
                injury_proneness=player.hidden_career_traits.injury_proneness,
                resilience=player.hidden_career_traits.resilience,
            ),
            source_type=self._provenance_source_type(provenance),
            quality_band=provenance.quality_band if provenance else None,
            is_top_band=provenance.is_top_band if provenance else False,
            override_id=provenance.override_id if provenance else None,
            origin_source_type=self._normalize_origin_source_type(provenance.origin_source_type) if provenance else None,
            origin_quality_band=provenance.origin_quality_band if provenance else None,
            origin_override_id=provenance.origin_override_id if provenance else None,
            origin_season=provenance.origin_season if provenance else None,
            talent_seed_value=provenance.talent_seed_value if provenance else None,
            talent_sequence=provenance.talent_sequence if provenance else None,
        )

    @staticmethod
    def _to_player_career_history_response(result: PlayerCareerHistoryReadModel) -> PlayerCareerHistoryResponse:
        return PlayerCareerHistoryResponse(
            requested_run_id=result.requested_run_id,
            player_id=result.player_id,
            player_name=result.player_name,
            country_code=result.country_code,
            entries=[
                PlayerCareerHistoryEntry(
                    run_id=entry.run_id,
                    season=entry.season,
                    age=entry.age,
                    overall=entry.overall,
                    technique=entry.technique,
                    movement=entry.movement,
                    physical=entry.physical,
                    mental=entry.mental,
                    source_type=entry.source_type,
                    quality_band=entry.quality_band,
                    is_top_band=entry.is_top_band,
                    origin_source_type=entry.origin_source_type,
                    origin_quality_band=entry.origin_quality_band,
                    origin_override_id=entry.origin_override_id,
                    origin_season=entry.origin_season,
                )
                for entry in result.entries
            ],
        )


    @staticmethod
    def _to_player_career_performance_response(result: PlayerCareerPerformanceReadModel) -> PlayerCareerPerformanceResponse:
        return PlayerCareerPerformanceResponse(
            requested_run_id=result.requested_run_id,
            player_id=result.player_id,
            player_name=result.player_name,
            country_code=result.country_code,
            entries=[
                PlayerCareerSeasonPerformanceEntry(
                    run_id=entry.run_id,
                    season=entry.season,
                    ranking_position=entry.ranking_position,
                    race_position=entry.race_position,
                    tournaments_played=entry.tournaments_played,
                    titles=entry.titles,
                    finals=entry.finals,
                    semifinals=entry.semifinals,
                    quarterfinals=entry.quarterfinals,
                    wins=entry.wins,
                    losses=entry.losses,
                )
                for entry in result.entries
            ],
        )

    def _build_rollover_orchestration(self, *, seed: int, season: int) -> SeasonRolloverOrchestrationService:
        progression_engine = CareerProgressionEngine(
            rng=DeterministicRng(seed).branch(SeedScope.SEASON, season, "season_rollover")
        )
        return SeasonRolloverOrchestrationService(
            repository=self.repository,
            rollover_service=SeasonRolloverService(progression_engine=progression_engine),
        )

    @staticmethod
    def _resolve_event_and_index(*, state: SeasonState, event_id: str) -> tuple[CalendarEvent, int]:
        for index, event in enumerate(state.ordered_events):
            if event.event_id == event_id:
                return event, index
        raise ValueError(f"event_id {event_id} is not present in this run")

    def _wildcard_event_eligibility(self, *, run_id: str, state: SeasonState, event: CalendarEvent) -> tuple[bool, str | None]:
        if event.event_id in state.completed_event_ids:
            return False, "cannot assign wildcards for completed events"
        if self.repository.get_completed_event(run_id=run_id, event_id=event.event_id) is not None:
            return False, "cannot assign wildcards for completed events"
        _, event_index = self._resolve_event_and_index(state=state, event_id=event.event_id)
        if event_index < state.next_event_index:
            return False, "cannot assign wildcards for completed events"
        if state.active_tournament is not None and state.active_tournament.event.event_id == event.event_id:
            return False, "cannot assign wildcards after draw/first-match simulation has started"
        return True, None

    def _pre_draw_withdrawal_event_eligibility(
        self, *, run_id: str, state: SeasonState, event: CalendarEvent
    ) -> tuple[bool, str | None]:
        if event.event_id in state.completed_event_ids:
            return False, "event is already completed"
        if self.repository.get_completed_event(run_id=run_id, event_id=event.event_id) is not None:
            return False, "event is already persisted"
        _, event_index = self._resolve_event_and_index(state=state, event_id=event.event_id)
        if event_index < state.next_event_index:
            return False, "event index is behind next_event_index and is no longer eligible"
        if state.active_tournament is not None and state.active_tournament.event.event_id == event.event_id:
            return False, "event already started and is currently active"
        return True, None

    def _late_replacement_event_eligibility(
        self,
        *,
        run_id: str,
        state: SeasonState,
        event: CalendarEvent,
        has_replaceable_players: bool,
        has_candidates: bool,
        remaining_capacity: int,
    ) -> tuple[bool, str | None]:
        base_eligible, base_reason = self._pre_draw_withdrawal_event_eligibility(run_id=run_id, state=state, event=event)
        if not base_eligible:
            return False, base_reason
        templates_by_id = {template.template_id: template for template in load_tournament_templates_config().templates}
        template = templates_by_id[event.template_id]
        if not template.lucky_loser_rules.enabled:
            return False, "lucky loser rules are disabled for this event template"
        if remaining_capacity <= 0:
            return False, "lucky loser replacement capacity is exhausted for this event"
        if not has_replaceable_players:
            return False, "no replaceable main-draw players are currently entered"
        if not has_candidates:
            return False, "no eligible late-replacement candidates are currently available"
        return True, None

    @staticmethod
    def _withdrawable_main_draw_players(
        *,
        acceptance: AcceptanceList,
        players_by_id: dict[str, Player],
        countries_by_code: dict[str, Country],
    ) -> list[PreDrawWithdrawablePlayerRecord]:
        withdrawable_entries = sorted(
            [
                entry
                for entry in acceptance.main_draw_entries
                if entry.player_id is not None
                and entry.status
                in {
                    AcceptanceStatus.DIRECT_ACCEPTANCE,
                    AcceptanceStatus.WILD_CARD_PLACEHOLDER,
                    AcceptanceStatus.WITHDRAWAL_PLACEHOLDER,
                    AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER,
                }
            ],
            key=lambda entry: (10_000 if entry.ranking_priority is None else entry.ranking_priority, entry.entry_id),
        )
        return [
            PreDrawWithdrawablePlayerRecord(
                player_id=entry.player_id or "",
                player_name=players_by_id[entry.player_id].name,
                country_code=players_by_id[entry.player_id].nationality,
                country_name=(
                    countries_by_code[players_by_id[entry.player_id].nationality].name
                    if players_by_id[entry.player_id].nationality in countries_by_code
                    else None
                ),
                entry_id=entry.entry_id,
                acceptance_status=entry.status.value,
            )
            for entry in withdrawable_entries
            if entry.player_id is not None and entry.player_id in players_by_id
        ]

    @staticmethod
    def _ordered_late_replacement_candidates(
        *,
        acceptance: AcceptanceList,
        players_by_id: dict[str, Player],
        countries_by_code: dict[str, Country],
    ) -> list[LateReplacementCandidateRecord]:
        entered_main_player_ids = {entry.player_id for entry in acceptance.main_draw_entries if entry.player_id is not None}
        blocked_player_ids = set(entered_main_player_ids)
        candidate_pool: list[tuple[int, int, str, str, ReplacementSource, int | None]] = []
        for source_order, source_label, applicants in (
            (0, "qualification_waitlist", acceptance.qualification_applicants),
            (1, "main_draw_waitlist", acceptance.main_draw_applicants),
        ):
            for applicant in applicants:
                if applicant.player_id in blocked_player_ids:
                    continue
                candidate_pool.append(
                    (
                        source_order,
                        10_000 if applicant.ranking_priority is None else applicant.ranking_priority,
                        applicant.player_id,
                        applicant.entry_id,
                        source_label,
                        applicant.ranking_priority,
                    )
                )

        ordered_candidates: list[LateReplacementCandidateRecord] = []
        for index, (_, _, player_id, entry_id, source_label, ranking_priority) in enumerate(sorted(candidate_pool), start=1):
            player = players_by_id.get(player_id)
            if player is None:
                continue
            ordered_candidates.append(
                LateReplacementCandidateRecord(
                    candidate_slot_index=index,
                    player_id=player.player_id,
                    player_name=player.name,
                    country_code=player.nationality,
                    country_name=(countries_by_code[player.nationality].name if player.nationality in countries_by_code else None),
                    source=source_label,
                    source_priority=0 if source_label == "qualification_waitlist" else 1,
                    ranking_priority=ranking_priority,
                    entry_id=entry_id,
                )
            )
        return ordered_candidates

    @staticmethod
    def _resolve_late_replacement_destination(
        *,
        acceptance: AcceptanceList,
        withdrawn_entry: TournamentEntry,
    ) -> TournamentEntry:
        ordered_entries = sorted(
            acceptance.main_draw_entries,
            key=lambda item: (10_000 if item.ranking_priority is None else item.ranking_priority, item.entry_id),
        )
        for entry in ordered_entries:
            if entry.status == AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER and entry.player_id is None:
                return entry
        for entry in ordered_entries:
            if entry.status == AcceptanceStatus.WITHDRAWAL_PLACEHOLDER and entry.player_id is None:
                return entry
        return withdrawn_entry

    def _build_effective_acceptance_for_event(
        self,
        *,
        run_id: str,
        run_info: SimulationRunInfo,
        event: CalendarEvent,
    ) -> AcceptanceList:
        templates_by_id = {template.template_id: template for template in load_tournament_templates_config().templates}
        template = templates_by_id[event.template_id]
        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed, run_info=run_info)
        acceptance = orchestrator.entry_engine.build_acceptance_list(
            event=event,
            template=template,
            players=list(orchestrator.players_by_id.values()),
            countries_by_code=orchestrator.countries_by_code,
        )
        acceptance = orchestrator._apply_wildcard_assignments(
            acceptance=acceptance,
            assignments=self.repository.get_wildcard_assignments_for_event(run_id=run_id, event_id=event.event_id),
        )
        acceptance = orchestrator._apply_pre_draw_withdrawal_replacements(
            acceptance=acceptance,
            replacements=self.repository.get_pre_draw_withdrawal_replacements_for_event(run_id=run_id, event_id=event.event_id),
        )
        return orchestrator._apply_late_replacements(
            acceptance=acceptance,
            replacements=self.repository.get_late_replacements_for_event(run_id=run_id, event_id=event.event_id),
        )
