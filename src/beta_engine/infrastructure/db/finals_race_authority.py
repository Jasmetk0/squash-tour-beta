"""Persistence for immutable World Tour Finals Race configuration and snapshots."""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.domain.finals import FinalsRaceConfiguration, FinalsRaceSnapshot
from beta_engine.infrastructure.db.models import (
    FinalsRaceConfigurationModel,
    FinalsRaceSnapshotModel,
)


class FinalsRaceAuthorityConflict(ValueError):
    """A season already owns different Finals Race authority."""


class FinalsRaceAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def get_configuration(
        self, *, run_id: str, branch_id: str, season_index: int
    ) -> FinalsRaceConfiguration | None:
        row = self.session.get(
            FinalsRaceConfigurationModel,
            (run_id, branch_id, season_index),
        )
        if row is None:
            return None
        configuration = FinalsRaceConfiguration.model_validate_json(row.payload_json)
        if (
            configuration.run_id,
            configuration.branch_id,
            configuration.season_index,
            configuration.fingerprint,
            configuration.adopted_by_command_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.season_index,
            row.configuration_fingerprint,
            row.adopted_by_command_id,
        ):
            raise ValueError("Stored Finals Race configuration identity mismatch")
        return configuration

    def put_configuration(
        self, configuration: FinalsRaceConfiguration
    ) -> FinalsRaceConfiguration:
        existing = self.get_configuration(
            run_id=configuration.run_id,
            branch_id=configuration.branch_id,
            season_index=configuration.season_index,
        )
        if existing is not None:
            if existing.fingerprint != configuration.fingerprint:
                raise FinalsRaceAuthorityConflict(
                    "Finals Race configuration already differs for this season"
                )
            return existing
        self.session.add(
            FinalsRaceConfigurationModel(
                run_id=configuration.run_id,
                branch_id=configuration.branch_id,
                season_index=configuration.season_index,
                configuration_fingerprint=configuration.fingerprint,
                adopted_by_command_id=configuration.adopted_by_command_id,
                payload_json=configuration.model_dump_json(),
            )
        )
        self.session.flush()
        return configuration

    def get_snapshot(
        self, *, run_id: str, branch_id: str, season_index: int
    ) -> FinalsRaceSnapshot | None:
        row = self.session.get(
            FinalsRaceSnapshotModel,
            (run_id, branch_id, season_index),
        )
        if row is None:
            return None
        snapshot = FinalsRaceSnapshot.model_validate_json(row.payload_json)
        if (
            snapshot.run_id,
            snapshot.branch_id,
            snapshot.season_index,
            snapshot.fingerprint,
            snapshot.configuration_fingerprint,
            snapshot.cutoff_ranking_week.ordinal,
        ) != (
            row.run_id,
            row.branch_id,
            row.season_index,
            row.snapshot_fingerprint,
            row.configuration_fingerprint,
            row.cutoff_week_ordinal,
        ):
            raise ValueError("Stored Finals Race snapshot identity mismatch")
        return snapshot

    def put_snapshot(self, snapshot: FinalsRaceSnapshot) -> FinalsRaceSnapshot:
        configuration = self.get_configuration(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            season_index=snapshot.season_index,
        )
        if configuration is None:
            raise ValueError(
                "Finals Race snapshot requires persisted season configuration"
            )
        if configuration.fingerprint != snapshot.configuration_fingerprint:
            raise ValueError(
                "Finals Race snapshot configuration fingerprint mismatch"
            )
        existing = self.get_snapshot(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            season_index=snapshot.season_index,
        )
        if existing is not None:
            if existing.fingerprint != snapshot.fingerprint:
                raise FinalsRaceAuthorityConflict(
                    "Finals Race snapshot already differs for this season"
                )
            return existing
        self.session.add(
            FinalsRaceSnapshotModel(
                run_id=snapshot.run_id,
                branch_id=snapshot.branch_id,
                season_index=snapshot.season_index,
                snapshot_fingerprint=snapshot.fingerprint,
                configuration_fingerprint=snapshot.configuration_fingerprint,
                cutoff_week_ordinal=snapshot.cutoff_ranking_week.ordinal,
                payload_json=snapshot.model_dump_json(),
            )
        )
        self.session.flush()
        return snapshot
