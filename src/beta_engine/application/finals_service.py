"""Application-layer World Tour Finals orchestration integrated with persisted season state."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.finals_models import (
    FinalsSimulationResult,
    FinalsSummaryResponse,
    PersistedFinalsQualification,
    PersistedFinalsResult,
)
from beta_engine.application.season_models import SeasonState
from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.finals import FinalsEngine
from beta_engine.domain.players import Player
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo


@dataclass(slots=True)
class FinalsOrchestrationService:
    """Explicit application command/query orchestration for World Tour Finals."""

    repository: SimulationPersistenceRepository
    finals_event_id: str = "WORLD_TOUR_FINALS"

    def derive_qualification(
        self,
        *,
        run: SimulationRunInfo,
        state: SeasonState,
        players_by_id: dict[str, Player],
    ) -> PersistedFinalsQualification:
        self._validate_season_complete(state=state)
        race_snapshot = state.race_snapshot
        if race_snapshot is None:
            raise ValueError("Cannot derive finals qualification before race snapshot exists")

        engine = self._build_engine(seed=run.seed, season=run.season)
        qualification = engine.build_qualification(race_table=race_snapshot.report.race, players_by_id=players_by_id)
        return PersistedFinalsQualification(
            run_id=run.run_id,
            season=run.season,
            source_as_of_season=race_snapshot.as_of_season,
            source_as_of_week=race_snapshot.as_of_week,
            qualification=qualification,
        )

    def derive_and_persist_qualification(
        self,
        *,
        run: SimulationRunInfo,
        state: SeasonState,
        players_by_id: dict[str, Player],
    ) -> PersistedFinalsQualification:
        qualification = self.derive_qualification(run=run, state=state, players_by_id=players_by_id)
        self.repository.upsert_finals_qualification(
            run_id=run.run_id,
            season=run.season,
            source_as_of_season=qualification.source_as_of_season,
            source_as_of_week=qualification.source_as_of_week,
            qualification=qualification.qualification,
        )
        return qualification

    def simulate_world_tour_finals(
        self,
        *,
        run: SimulationRunInfo,
        state: SeasonState,
        players_by_id: dict[str, Player],
    ) -> FinalsSimulationResult:
        self._validate_season_complete(state=state)
        race_snapshot = state.race_snapshot
        if race_snapshot is None:
            raise ValueError("Cannot simulate finals before race snapshot exists")

        existing_result = self.repository.get_finals_result(run_id=run.run_id, season=run.season)
        if existing_result is not None:
            existing_qualification = self.repository.get_finals_qualification(run_id=run.run_id, season=run.season)
            if existing_qualification is None:
                existing_qualification = self.derive_and_persist_qualification(
                    run=run,
                    state=state,
                    players_by_id=players_by_id,
                )
            else:
                existing_qualification = PersistedFinalsQualification(
                    run_id=existing_qualification.run_id,
                    season=existing_qualification.season,
                    source_as_of_season=existing_qualification.source_as_of_season,
                    source_as_of_week=existing_qualification.source_as_of_week,
                    qualification=existing_qualification.qualification,
                )

            return FinalsSimulationResult(
                run_id=run.run_id,
                season=run.season,
                event_id=existing_result.event_id,
                qualification=existing_qualification,
                result=PersistedFinalsResult(
                    run_id=existing_result.run_id,
                    season=existing_result.season,
                    event_id=existing_result.event_id,
                    source_as_of_season=existing_result.source_as_of_season,
                    source_as_of_week=existing_result.source_as_of_week,
                    result=existing_result.result,
                ),
                already_simulated=True,
            )

        derived = self.derive_world_tour_finals(run=run, state=state, players_by_id=players_by_id)
        qualification = derived.qualification
        self.repository.upsert_finals_qualification(
            run_id=run.run_id, season=run.season,
            source_as_of_season=qualification.source_as_of_season,
            source_as_of_week=qualification.source_as_of_week,
            qualification=qualification.qualification,
        )
        persisted_result = derived.result
        self.repository.upsert_finals_result(
            run_id=run.run_id, season=run.season, event_id=derived.event_id,
            source_as_of_season=persisted_result.source_as_of_season,
            source_as_of_week=persisted_result.source_as_of_week,
            result=persisted_result.result,
        )
        return derived

    def derive_world_tour_finals(
        self, *, run: SimulationRunInfo, state: SeasonState,
        players_by_id: dict[str, Player],
    ) -> FinalsSimulationResult:
        """Purely derive the deterministic Finals payload; perform no persistence."""
        self._validate_season_complete(state=state)
        race_snapshot = state.race_snapshot
        if race_snapshot is None:
            raise ValueError("Cannot simulate finals before race snapshot exists")
        qualification = self.derive_qualification(run=run, state=state, players_by_id=players_by_id)
        engine = self._build_engine(seed=run.seed, season=run.season)
        finals_result = engine.simulate_event(
            event_id=self.finals_event_id,
            season=run.season,
            race_table=race_snapshot.report.race,
            players_by_id=players_by_id,
        )
        persisted_result = PersistedFinalsResult(
            run_id=run.run_id,
            season=run.season,
            event_id=self.finals_event_id,
            source_as_of_season=race_snapshot.as_of_season,
            source_as_of_week=race_snapshot.as_of_week,
            result=finals_result,
        )
        return FinalsSimulationResult(
            run_id=run.run_id,
            season=run.season,
            event_id=self.finals_event_id,
            qualification=qualification,
            result=persisted_result,
            already_simulated=False,
        )

    def get_summary(self, *, run_id: str, season: int) -> FinalsSummaryResponse:
        qualification = self.repository.get_finals_qualification(run_id=run_id, season=season)
        result = self.repository.get_finals_result(run_id=run_id, season=season)
        return FinalsSummaryResponse(
            run_id=run_id,
            season=season,
            qualification=(
                PersistedFinalsQualification(
                    run_id=qualification.run_id,
                    season=qualification.season,
                    source_as_of_season=qualification.source_as_of_season,
                    source_as_of_week=qualification.source_as_of_week,
                    qualification=qualification.qualification,
                )
                if qualification is not None
                else None
            ),
            result=(
                PersistedFinalsResult(
                    run_id=result.run_id,
                    season=result.season,
                    event_id=result.event_id,
                    source_as_of_season=result.source_as_of_season,
                    source_as_of_week=result.source_as_of_week,
                    result=result.result,
                )
                if result is not None
                else None
            ),
        )

    @staticmethod
    def _build_engine(*, seed: int, season: int) -> FinalsEngine:
        return FinalsEngine(rng=DeterministicRng(seed).branch(SeedScope.SEASON, season, "world_tour_finals"))

    @staticmethod
    def _validate_season_complete(*, state: SeasonState) -> None:
        if state.has_remaining_events:
            raise ValueError("World Tour Finals requires a completed regular season; run simulate_full_season first")
