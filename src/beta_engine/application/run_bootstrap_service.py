"""Application service for deterministic multi-season run bootstrapping."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.run_bootstrap_models import BootstrapNextSeasonResponse
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo


@dataclass(slots=True)
class NextSeasonRunBootstrapService:
    repository: SimulationPersistenceRepository

    def bootstrap_from_rollover(
        self,
        *,
        parent_run: SimulationRunInfo,
        child_run_id: str,
        child_seed: int,
    ) -> BootstrapNextSeasonResponse:
        rollover = self.repository.get_season_rollover(run_id=parent_run.run_id, to_season=parent_run.season + 1)
        if rollover is None:
            raise ValueError(
                f"No persisted rollover exists for run_id {parent_run.run_id} and season {parent_run.season + 1}"
            )

        next_players = self.repository.list_next_season_players(run_id=parent_run.run_id, to_season=rollover.to_season)
        if not next_players:
            raise ValueError(
                f"Persisted rollover for run_id {parent_run.run_id} season {rollover.to_season} has no next-season players"
            )

        existing_child = self.repository.get_simulation_run(run_id=child_run_id)
        expected_run = SimulationRunInfo(
            run_id=child_run_id,
            season=rollover.to_season,
            seed=child_seed,
            config_version=parent_run.config_version,
            config_fingerprint=parent_run.config_fingerprint,
            parent_run_id=parent_run.run_id,
            source_type="rollover_bootstrap",
            source_rollover_run_id=parent_run.run_id,
            source_rollover_from_season=rollover.from_season,
            source_rollover_to_season=rollover.to_season,
        )

        if existing_child is not None:
            if existing_child != expected_run:
                raise ValueError(
                    f"run_id {child_run_id} already exists with conflicting bootstrap metadata"
                )
            state = self.repository.load_season_state(run_id=child_run_id)
            if state is None:
                raise ValueError(f"run_id {child_run_id} exists but has no season state")
            return BootstrapNextSeasonResponse(
                parent_run_id=parent_run.run_id,
                child_run_id=child_run_id,
                from_season=rollover.from_season,
                to_season=rollover.to_season,
                child_seed=child_seed,
                transitioned_players=rollover.transitioned_players,
                source_rollover_run_id=rollover.run_id,
                source_rollover_to_season=rollover.to_season,
                already_bootstrapped=True,
            )

        self.repository.upsert_simulation_run(expected_run)
        return BootstrapNextSeasonResponse(
            parent_run_id=parent_run.run_id,
            child_run_id=child_run_id,
            from_season=rollover.from_season,
            to_season=rollover.to_season,
            child_seed=child_seed,
            transitioned_players=rollover.transitioned_players,
            source_rollover_run_id=rollover.run_id,
            source_rollover_to_season=rollover.to_season,
            already_bootstrapped=False,
        )
