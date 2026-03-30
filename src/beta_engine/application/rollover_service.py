"""Application-layer orchestration for explicit season rollover commands/queries."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.careers import SeasonRolloverService
from beta_engine.application.rollover_models import (
    NextSeasonPlayerRecord,
    PersistedPlayerTransition,
    PersistedSeasonRollover,
    SeasonRolloverResponse,
    SeasonRolloverSummaryResponse,
)
from beta_engine.application.season_models import SeasonState
from beta_engine.domain.players import Player
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo


@dataclass(slots=True)
class SeasonRolloverOrchestrationService:
    """Coordinates deterministic rollover execution and persistence."""

    repository: SimulationPersistenceRepository
    rollover_service: SeasonRolloverService

    def rollover_to_next_season(
        self,
        *,
        run: SimulationRunInfo,
        state: SeasonState,
        players_by_id: dict[str, Player],
    ) -> SeasonRolloverResponse:
        self._validate_season_complete(state=state)
        to_season = run.season + 1

        existing = self.repository.get_season_rollover(run_id=run.run_id, to_season=to_season)
        if existing is not None:
            transitions = self.repository.list_player_transitions(run_id=run.run_id, to_season=to_season)
            next_players = self.repository.list_next_season_players(run_id=run.run_id, to_season=to_season)
            return SeasonRolloverResponse(
                run_id=existing.run_id,
                from_season=existing.from_season,
                to_season=existing.to_season,
                transitioned_players=existing.transitioned_players,
                metadata=existing.metadata,
                transitions=[record.transition for record in transitions],
                next_season_players=[record.state for record in next_players],
                already_persisted=True,
            )

        source_players = sorted(players_by_id.values(), key=lambda player: player.player_id)
        result = self.rollover_service.rollover(
            season=run.season,
            players=source_players,
            completed_tournaments=state.completed_tournament_inputs,
        )
        metadata: dict[str, object] = {
            "placeholders": result.placeholders,
            "status": "mvp_rollover",
        }

        self.repository.upsert_season_rollover(
            run_id=run.run_id,
            from_season=result.from_season,
            to_season=result.to_season,
            transitioned_players=len(result.transitions),
            metadata=metadata,
            transitions=result.transitions,
            next_player_states=list(result.next_states_by_player_id.values()),
        )

        return SeasonRolloverResponse(
            run_id=run.run_id,
            from_season=result.from_season,
            to_season=result.to_season,
            transitioned_players=len(result.transitions),
            metadata=metadata,
            transitions=result.transitions,
            next_season_players=list(result.next_states_by_player_id.values()),
            already_persisted=False,
        )

    def get_rollover_summary(self, *, run_id: str, to_season: int) -> SeasonRolloverSummaryResponse | None:
        record = self.repository.get_season_rollover(run_id=run_id, to_season=to_season)
        if record is None:
            return None
        return SeasonRolloverSummaryResponse(
            run_id=record.run_id,
            from_season=record.from_season,
            to_season=record.to_season,
            transitioned_players=record.transitioned_players,
            metadata=record.metadata,
        )

    def get_latest_rollover_summary(self, *, run_id: str) -> SeasonRolloverSummaryResponse | None:
        record = self.repository.get_latest_season_rollover(run_id=run_id)
        if record is None:
            return None
        return SeasonRolloverSummaryResponse(
            run_id=record.run_id,
            from_season=record.from_season,
            to_season=record.to_season,
            transitioned_players=record.transitioned_players,
            metadata=record.metadata,
        )

    def list_next_season_players(self, *, run_id: str, to_season: int) -> list[NextSeasonPlayerRecord]:
        return [
            NextSeasonPlayerRecord(
                run_id=record.run_id,
                from_season=record.from_season,
                to_season=record.to_season,
                player_id=record.player_id,
                state=record.state,
            )
            for record in self.repository.list_next_season_players(run_id=run_id, to_season=to_season)
        ]

    def list_transitions(self, *, run_id: str, to_season: int) -> list[PersistedPlayerTransition]:
        return [
            PersistedPlayerTransition(
                run_id=record.run_id,
                from_season=record.from_season,
                to_season=record.to_season,
                player_id=record.player_id,
                transition=record.transition,
            )
            for record in self.repository.list_player_transitions(run_id=run_id, to_season=to_season)
        ]

    @staticmethod
    def _validate_season_complete(*, state: SeasonState) -> None:
        if state.has_remaining_events:
            raise ValueError("Season rollover requires a completed season; run simulate_full_season first")


def to_persisted_rollover(payload: SeasonRolloverSummaryResponse) -> PersistedSeasonRollover:
    return PersistedSeasonRollover(
        run_id=payload.run_id,
        from_season=payload.from_season,
        to_season=payload.to_season,
        transitioned_players=payload.transitioned_players,
        metadata=payload.metadata,
    )
