"""Persistence for immutable canonical World Tour Finals Race authority."""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.domain.finals import (
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceSnapshot,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    WorldTourFinalsRaceConfigurationModel,
    WorldTourFinalsRaceSnapshotModel,
)


class WorldTourFinalsRaceAuthorityConflict(ValueError):
    """A season already owns different immutable Finals Race authority."""


class WorldTourFinalsRaceAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Finals Race Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Finals Race scope is not writable")

    @staticmethod
    def _validate_snapshot_configuration(
        configuration: WorldTourFinalsRaceConfiguration,
        snapshot: WorldTourFinalsRaceSnapshot,
    ) -> None:
        if (
            snapshot.run_id,
            snapshot.branch_id,
            snapshot.target_season_index,
            snapshot.cutoff_week,
            snapshot.cutoff_official_ranking_fingerprint,
            snapshot.eligibility_fingerprint,
            snapshot.policy_id,
            snapshot.best_n,
        ) != (
            configuration.run_id,
            configuration.branch_id,
            configuration.target_season_index,
            configuration.cutoff_week,
            configuration.cutoff_official_ranking_fingerprint,
            configuration.eligibility_fingerprint,
            configuration.policy_id,
            configuration.best_n,
        ):
            raise ValueError("Finals Race snapshot does not match stored configuration")

    def get_configuration(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ) -> WorldTourFinalsRaceConfiguration | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            WorldTourFinalsRaceConfigurationModel,
            (run_id, branch_id, target_season_index),
        )
        if row is None:
            return None
        configuration = WorldTourFinalsRaceConfiguration.model_validate_json(
            row.payload_json
        )
        if (
            configuration.run_id,
            configuration.branch_id,
            configuration.target_season_index,
            configuration.fingerprint,
            configuration.adopted_by_command_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.target_season_index,
            row.configuration_fingerprint,
            row.adopted_by_command_id,
        ):
            raise ValueError("Stored Finals Race configuration identity mismatch")
        return configuration

    def put_configuration(
        self,
        configuration: WorldTourFinalsRaceConfiguration,
    ) -> WorldTourFinalsRaceConfiguration:
        self._scope(configuration.run_id, configuration.branch_id, writing=True)
        existing = self.get_configuration(
            run_id=configuration.run_id,
            branch_id=configuration.branch_id,
            target_season_index=configuration.target_season_index,
        )
        if existing is not None:
            if existing.fingerprint != configuration.fingerprint:
                raise WorldTourFinalsRaceAuthorityConflict(
                    "Finals Race configuration already differs for this season"
                )
            return existing

        self.session.add(
            WorldTourFinalsRaceConfigurationModel(
                run_id=configuration.run_id,
                branch_id=configuration.branch_id,
                target_season_index=configuration.target_season_index,
                configuration_fingerprint=configuration.fingerprint,
                adopted_by_command_id=configuration.adopted_by_command_id,
                payload_json=configuration.model_dump_json(),
            )
        )
        self.session.flush()
        return configuration

    def get_snapshot(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ) -> WorldTourFinalsRaceSnapshot | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            WorldTourFinalsRaceSnapshotModel,
            (run_id, branch_id, target_season_index),
        )
        if row is None:
            return None

        snapshot = WorldTourFinalsRaceSnapshot.model_validate_json(row.payload_json)
        if (
            snapshot.run_id,
            snapshot.branch_id,
            snapshot.target_season_index,
            snapshot.fingerprint,
            snapshot.input_fingerprint,
            snapshot.cutoff_week.ordinal,
        ) != (
            row.run_id,
            row.branch_id,
            row.target_season_index,
            row.snapshot_fingerprint,
            row.input_fingerprint,
            row.cutoff_week_ordinal,
        ):
            raise ValueError("Stored Finals Race snapshot identity mismatch")

        configuration = self.get_configuration(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
        )
        if configuration is None:
            raise ValueError("Stored Finals Race snapshot has no configuration authority")
        if row.configuration_fingerprint != configuration.fingerprint:
            raise ValueError("Stored Finals Race configuration fingerprint mismatch")
        self._validate_snapshot_configuration(configuration, snapshot)
        return snapshot

    def put_snapshot(
        self,
        snapshot: WorldTourFinalsRaceSnapshot,
    ) -> WorldTourFinalsRaceSnapshot:
        self._scope(snapshot.run_id, snapshot.branch_id, writing=True)
        configuration = self.get_configuration(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            target_season_index=snapshot.target_season_index,
        )
        if configuration is None:
            raise ValueError(
                "Finals Race snapshot requires persisted season configuration"
            )
        self._validate_snapshot_configuration(configuration, snapshot)

        existing = self.get_snapshot(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            target_season_index=snapshot.target_season_index,
        )
        if existing is not None:
            if existing.fingerprint != snapshot.fingerprint:
                raise WorldTourFinalsRaceAuthorityConflict(
                    "Finals Race snapshot already differs for this season"
                )
            return existing

        self.session.add(
            WorldTourFinalsRaceSnapshotModel(
                run_id=snapshot.run_id,
                branch_id=snapshot.branch_id,
                target_season_index=snapshot.target_season_index,
                snapshot_fingerprint=snapshot.fingerprint,
                configuration_fingerprint=configuration.fingerprint,
                input_fingerprint=snapshot.input_fingerprint,
                cutoff_week_ordinal=snapshot.cutoff_week.ordinal,
                payload_json=snapshot.model_dump_json(),
            )
        )
        self.session.flush()
        return snapshot
