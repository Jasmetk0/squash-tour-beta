"""Application services for FastAPI simulation command/query endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from beta_engine.application.finals_models import (
    FinalsSimulationResult,
    FinalsSummaryResponse,
    PersistedFinalsQualification,
    PersistedFinalsResult,
)
from beta_engine.application.finals_service import FinalsOrchestrationService
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
from beta_engine.domain.careers import CareerProgressionEngine
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.entries import AcceptanceStatus
from beta_engine.domain.players import Player, PlayerGenerator
from beta_engine.domain.tournaments import CalendarEvent
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.points_config import load_points_config
from beta_engine.infrastructure.tournament_config import load_season_calendar, load_tournament_templates_config
from beta_engine.infrastructure.world_config import load_countries_config, load_player_identity_config
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


ActivityKind = Literal[
    "event",
    "ranking_snapshot",
    "race_snapshot",
    "finals_qualification",
    "finals_result",
    "rollover",
    "bootstrap_child",
    "admin_wildcard_assignment",
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


@dataclass(slots=True)
class SimulationApiService:
    """High-level API-facing service that keeps orchestration out of routers."""

    repository: SimulationPersistenceRepository
    players_per_country: int = 24

    def initialize_run(
        self,
        *,
        run_id: str,
        season: int,
        seed: int,
        config_version: str | None,
        config_fingerprint: str | None,
    ) -> PersistedRunSummary:
        orchestrator = self._build_orchestrator(season=season, seed=seed, run_info=None)
        state = orchestrator.initialize_state()

        run_info = SimulationRunInfo(
            run_id=run_id,
            season=season,
            seed=seed,
            config_version=config_version,
            config_fingerprint=config_fingerprint,
            source_type="fresh_seed",
        )
        persistence = SimulationPersistenceService(repository=self.repository)
        persistence.initialize_run(run=run_info)
        self.repository.save_season_state(run_id=run_id, state=state)
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
        response = bootstrap_service.bootstrap_from_rollover(
            parent_run=parent_run,
            child_run_id=child_run_id,
            child_seed=effective_seed,
        )
        if response.already_bootstrapped:
            return response

        orchestrator = self._build_orchestrator(season=response.to_season, seed=effective_seed, run_info=None, parent_run_id=run_id)
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
        self._load_run_context(run_id=run_id)
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
        countries = load_countries_config().countries
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
        )

    def _load_run_context(self, *, run_id: str) -> tuple[SimulationRunInfo, SeasonState]:
        run_info = self.repository.get_simulation_run(run_id=run_id)
        state = self.repository.load_season_state(run_id=run_id)
        if run_info is None or state is None:
            raise KeyError(f"run_id {run_id} was not found")
        return run_info, state

    def _build_players(self, *, seed: int, countries: list[Country]) -> list[Player]:
        generator = PlayerGenerator(
            rng=DeterministicRng(seed),
            identity_config=load_player_identity_config(),
            country_talent_model=CountryTalentModel(),
        )
        players: list[Player] = []
        for country in countries:
            players.extend(generator.generate(country=country, sequence=index + 1) for index in range(self.players_per_country))
        return players

    def _build_players_by_id(self, *, seed: int) -> dict[str, Player]:
        countries = load_countries_config().countries
        return {player.player_id: player for player in self._build_players(seed=seed, countries=countries)}

    def _load_players_by_id_for_run(self, *, run_info: SimulationRunInfo) -> dict[str, Player]:
        countries = load_countries_config().countries
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
        source_rollover_run_id = run_info.source_rollover_run_id if run_info is not None else parent_run_id
        source_rollover_to_season = run_info.source_rollover_to_season if run_info is not None else season

        if source_rollover_run_id is not None and source_rollover_to_season is not None:
            records = self.repository.list_next_season_players(
                run_id=source_rollover_run_id,
                to_season=source_rollover_to_season,
            )
            if records:
                return [record.state.player for record in records]
        return self._build_players(seed=seed, countries=countries)

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
