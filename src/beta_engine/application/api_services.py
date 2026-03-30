"""Application services for FastAPI simulation command/query endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.finals_models import (
    FinalsSimulationResult,
    FinalsSummaryResponse,
    PersistedFinalsQualification,
    PersistedFinalsResult,
)
from beta_engine.application.finals_service import FinalsOrchestrationService
from beta_engine.application.persistence import SimulationPersistenceService
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
from beta_engine.domain.players import Player, PlayerGenerator
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
        orchestrator = self._build_orchestrator(season=season, seed=seed)
        state = orchestrator.initialize_state()

        run_info = SimulationRunInfo(
            run_id=run_id,
            season=season,
            seed=seed,
            config_version=config_version,
            config_fingerprint=config_fingerprint,
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

    def simulate_next_tournament(self, *, run_id: str) -> SimulationStepResult:
        return self._simulate_step(run_id=run_id, mode="simulate_next_tournament")

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
            players_by_id=self._build_players_by_id(seed=run_info.seed),
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
        return orchestrator.derive_qualification(
            run=run_info,
            state=state,
            players_by_id=self._build_players_by_id(seed=run_info.seed),
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
            players_by_id=self._build_players_by_id(seed=run_info.seed),
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

    def list_events(self, *, run_id: str) -> list[PersistedEventRecord]:
        return self.repository.list_completed_events(run_id=run_id)

    def get_event(self, *, run_id: str, event_id: str) -> PersistedEventRecord | None:
        return self.repository.get_completed_event(run_id=run_id, event_id=event_id)

    def list_ranking_snapshots(self, *, run_id: str) -> list[tuple[int, str, str | None, RankingSnapshot]]:
        return self.repository.list_ranking_snapshots(run_id=run_id)

    def list_race_snapshots(self, *, run_id: str) -> list[tuple[int, str, str | None, RaceSnapshot]]:
        return self.repository.list_race_snapshots(run_id=run_id)

    def _simulate_step(self, *, run_id: str, mode: str) -> SimulationStepResult:
        run_info, state = self._load_run_context(run_id=run_id)

        orchestrator = self._build_orchestrator(season=run_info.season, seed=run_info.seed)
        if mode == "simulate_next_tournament":
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

    def _build_orchestrator(self, *, season: int, seed: int) -> SeasonSimulationOrchestrator:
        calendar = load_season_calendar()
        if calendar.season != season:
            raise ValueError(
                f"Configured calendar season {calendar.season} does not match requested run season {season}"
            )

        templates = load_tournament_templates_config().templates
        countries = load_countries_config().countries
        countries_by_code = {country.code: country for country in countries}
        players = self._build_players(seed=seed, countries=countries)

        return SeasonSimulationOrchestrator.build(
            calendar=calendar,
            templates=templates,
            players=players,
            countries_by_code=countries_by_code,
            points_by_ref=load_points_config(),
            entry_tuning=load_entry_tuning_config(),
            seed=seed,
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

    def _build_rollover_orchestration(self, *, seed: int, season: int) -> SeasonRolloverOrchestrationService:
        progression_engine = CareerProgressionEngine(
            rng=DeterministicRng(seed).branch(SeedScope.SEASON, season, "season_rollover")
        )
        return SeasonRolloverOrchestrationService(
            repository=self.repository,
            rollover_service=SeasonRolloverService(progression_engine=progression_engine),
        )
