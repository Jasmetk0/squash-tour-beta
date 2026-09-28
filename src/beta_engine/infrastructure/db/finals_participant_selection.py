"""Persistence for immutable canonical World Tour Finals participant selection."""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsParticipantSelectionSnapshot,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    WorldTourFinalsParticipantSelectionConfigurationModel,
    WorldTourFinalsParticipantSelectionSnapshotModel,
)


class WorldTourFinalsParticipantSelectionConflict(ValueError):
    """A season already owns different immutable Finals participant authority."""


class WorldTourFinalsParticipantSelectionStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Finals participant-selection Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Finals participant-selection scope is not writable")

    def get_configuration(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ) -> WorldTourFinalsParticipantSelectionConfiguration | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            WorldTourFinalsParticipantSelectionConfigurationModel,
            (run_id, branch_id, target_season_index),
        )
        if row is None:
            return None
        configuration = (
            WorldTourFinalsParticipantSelectionConfiguration.model_validate_json(
                row.payload_json
            )
        )
        if (
            configuration.run_id,
            configuration.branch_id,
            configuration.target_season_index,
            configuration.fingerprint,
            configuration.race_snapshot_fingerprint,
            configuration.adopted_by_command_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.target_season_index,
            row.configuration_fingerprint,
            row.race_snapshot_fingerprint,
            row.adopted_by_command_id,
        ):
            raise ValueError(
                "Stored Finals participant-selection configuration identity mismatch"
            )
        return configuration

    def put_configuration(
        self,
        configuration: WorldTourFinalsParticipantSelectionConfiguration,
    ) -> WorldTourFinalsParticipantSelectionConfiguration:
        self._scope(configuration.run_id, configuration.branch_id, writing=True)
        existing = self.get_configuration(
            run_id=configuration.run_id,
            branch_id=configuration.branch_id,
            target_season_index=configuration.target_season_index,
        )
        if existing is not None:
            if existing.fingerprint != configuration.fingerprint:
                raise WorldTourFinalsParticipantSelectionConflict(
                    "Finals participant-selection configuration already differs for this season"
                )
            return existing

        self.session.add(
            WorldTourFinalsParticipantSelectionConfigurationModel(
                run_id=configuration.run_id,
                branch_id=configuration.branch_id,
                target_season_index=configuration.target_season_index,
                configuration_fingerprint=configuration.fingerprint,
                race_snapshot_fingerprint=configuration.race_snapshot_fingerprint,
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
    ) -> WorldTourFinalsParticipantSelectionSnapshot | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            WorldTourFinalsParticipantSelectionSnapshotModel,
            (run_id, branch_id, target_season_index),
        )
        if row is None:
            return None
        snapshot = WorldTourFinalsParticipantSelectionSnapshot.model_validate_json(
            row.payload_json
        )
        if (
            snapshot.run_id,
            snapshot.branch_id,
            snapshot.target_season_index,
            snapshot.fingerprint,
            snapshot.configuration_fingerprint,
            snapshot.race_snapshot_fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.target_season_index,
            row.snapshot_fingerprint,
            row.configuration_fingerprint,
            row.race_snapshot_fingerprint,
        ):
            raise ValueError(
                "Stored Finals participant-selection snapshot identity mismatch"
            )

        configuration = self.get_configuration(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=target_season_index,
        )
        if configuration is None:
            raise ValueError(
                "Stored Finals participant-selection snapshot has no configuration"
            )
        if (
            snapshot.configuration_fingerprint != configuration.fingerprint
            or snapshot.race_snapshot_fingerprint
            != configuration.race_snapshot_fingerprint
        ):
            raise ValueError(
                "Stored Finals participant-selection snapshot binding mismatch"
            )
        return snapshot

    def put_snapshot(
        self,
        snapshot: WorldTourFinalsParticipantSelectionSnapshot,
    ) -> WorldTourFinalsParticipantSelectionSnapshot:
        self._scope(snapshot.run_id, snapshot.branch_id, writing=True)
        configuration = self.get_configuration(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            target_season_index=snapshot.target_season_index,
        )
        if configuration is None:
            raise ValueError(
                "Finals participant-selection snapshot requires stored configuration"
            )
        if (
            snapshot.configuration_fingerprint != configuration.fingerprint
            or snapshot.race_snapshot_fingerprint
            != configuration.race_snapshot_fingerprint
            or snapshot.finals_event_id != configuration.finals_event_id
            or snapshot.participant_capacity != configuration.participant_capacity
        ):
            raise ValueError(
                "Finals participant-selection snapshot does not match stored configuration"
            )

        existing = self.get_snapshot(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            target_season_index=snapshot.target_season_index,
        )
        if existing is not None:
            if existing.fingerprint != snapshot.fingerprint:
                raise WorldTourFinalsParticipantSelectionConflict(
                    "Finals participant-selection snapshot already differs for this season"
                )
            return existing

        self.session.add(
            WorldTourFinalsParticipantSelectionSnapshotModel(
                run_id=snapshot.run_id,
                branch_id=snapshot.branch_id,
                target_season_index=snapshot.target_season_index,
                snapshot_fingerprint=snapshot.fingerprint,
                configuration_fingerprint=snapshot.configuration_fingerprint,
                race_snapshot_fingerprint=snapshot.race_snapshot_fingerprint,
                payload_json=snapshot.model_dump_json(),
            )
        )
        self.session.flush()
        return snapshot
