"""Application-layer persistence coordinator for simulation snapshots/history."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.season_models import SeasonState, SimulationStepResult
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo


@dataclass(slots=True)
class SimulationPersistenceService:
    """Coordinates persistence writes using explicit application DTOs."""

    repository: SimulationPersistenceRepository

    def initialize_run(self, *, run: SimulationRunInfo) -> None:
        self.repository.bootstrap_schema()
        self.repository.upsert_simulation_run(run)

    def persist_step(
        self, *, run_id: str, step: SimulationStepResult,
        reviewed_pre_state: SeasonState | None = None,
    ) -> None:
        self.repository.save_season_state(run_id=run_id, state=step.season_state)

        if (
            step.mode == "simulate_next_week"
            and reviewed_pre_state is not None
            and reviewed_pre_state.active_tournament is not None
        ):
            finalized = reviewed_pre_state.active_tournament.full_result
            event_sequence = reviewed_pre_state.next_event_index
            self.repository.save_completed_tournament_result(
                run_id=run_id, event_sequence=event_sequence,
                tournament_result=finalized,
            )
            self.repository.append_snapshot(
                run_id=run_id,
                snapshot_sequence=self._tournament_snapshot_sequence(event_sequence),
                snapshot_kind="tournament",
                source_event_id=finalized.event.event_id,
                ranking_snapshot=finalized.ranking_snapshot,
                race_snapshot=finalized.race_snapshot,
            )

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

        if step.season_result is not None:
            season_events_count = sum(len(weekly.tournaments) for weekly in step.season_result.weekly_results)
            start_sequence = len(step.season_state.completed_event_ids) - season_events_count
            event_sequence = start_sequence - 1
            for weekly in step.season_result.weekly_results:
                for tournament in weekly.tournaments:
                    event_sequence += 1
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
                    snapshot_sequence=self._weekly_snapshot_sequence(event_sequence),
                    snapshot_kind="week",
                    source_event_id=weekly.tournaments[-1].event.event_id,
                    ranking_snapshot=weekly.ranking_snapshot,
                    race_snapshot=weekly.race_snapshot,
                )

    @staticmethod
    def _tournament_snapshot_sequence(event_sequence: int) -> int:
        return event_sequence * 10 + 1

    @staticmethod
    def _weekly_snapshot_sequence(event_sequence: int) -> int:
        return event_sequence * 10 + 9
