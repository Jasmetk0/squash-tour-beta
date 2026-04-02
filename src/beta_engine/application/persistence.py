"""Application-layer persistence coordinator for simulation snapshots/history."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.season_models import SimulationStepResult
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo


@dataclass(slots=True)
class SimulationPersistenceService:
    """Coordinates persistence writes using explicit application DTOs."""

    repository: SimulationPersistenceRepository

    def initialize_run(self, *, run: SimulationRunInfo) -> None:
        self.repository.bootstrap_schema()
        self.repository.upsert_simulation_run(run)

    def persist_step(self, *, run_id: str, step: SimulationStepResult) -> None:
        self.repository.save_season_state(run_id=run_id, state=step.season_state)

        if step.tournament_result is not None and step.season_state.active_tournament is None:
            if (
                step.tournament_result.ranking_snapshot is None
                or step.tournament_result.race_snapshot is None
                or step.tournament_result.completed_tournament_input is None
            ):
                raise ValueError("completed tournament persistence requires ranking/race snapshots and completed input")
            event_sequence = step.season_state.next_event_index - 1
            self.repository.save_completed_tournament_result(
                run_id=run_id,
                event_sequence=event_sequence,
                tournament_result=step.tournament_result,
            )
            self.repository.append_snapshot(
                run_id=run_id,
                snapshot_sequence=self._tournament_snapshot_sequence(event_sequence),
                snapshot_kind="tournament",
                source_event_id=step.tournament_result.event.event_id,
                ranking_snapshot=step.tournament_result.ranking_snapshot,
                race_snapshot=step.tournament_result.race_snapshot,
            )

        if step.weekly_result is not None:
            end_event_sequence = step.season_state.next_event_index - 1
            start_event_sequence = end_event_sequence - len(step.weekly_result.tournaments) + 1

            for offset, tournament in enumerate(step.weekly_result.tournaments):
                event_sequence = start_event_sequence + offset
                self.repository.save_completed_tournament_result(
                    run_id=run_id,
                    event_sequence=event_sequence,
                    tournament_result=tournament,
                )
                self.repository.append_snapshot(
                    run_id=run_id,
                    snapshot_sequence=self._tournament_snapshot_sequence(event_sequence),
                    snapshot_kind="tournament",
                    source_event_id=tournament.event.event_id,
                    ranking_snapshot=tournament.ranking_snapshot,
                    race_snapshot=tournament.race_snapshot,
                )

            self.repository.append_snapshot(
                run_id=run_id,
                snapshot_sequence=self._weekly_snapshot_sequence(end_event_sequence),
                snapshot_kind="week",
                source_event_id=step.weekly_result.tournaments[-1].event.event_id,
                ranking_snapshot=step.weekly_result.ranking_snapshot,
                race_snapshot=step.weekly_result.race_snapshot,
            )

    @staticmethod
    def _tournament_snapshot_sequence(event_sequence: int) -> int:
        return event_sequence * 10 + 1

    @staticmethod
    def _weekly_snapshot_sequence(event_sequence: int) -> int:
        return event_sequence * 10 + 9
