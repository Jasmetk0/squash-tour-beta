"""Persistence adapters for season state, snapshots, and tournament history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, Select, select
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.season_models import RaceSnapshot, RankingSnapshot, SeasonState, TournamentSimulationResult
from beta_engine.domain.rankings import CompletedTournamentPointsInput

from beta_engine.infrastructure.db.models import (
    Base,
    CompletedEventMetadataModel,
    CompletedEventModel,
    CompletedTournamentInputModel,
    RaceSnapshotModel,
    RankingSnapshotModel,
    SeasonStateModel,
    SimulationRunModel,
)

SnapshotKind = Literal["tournament", "week"]


def _to_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _from_json(payload: str) -> object:
    return json.loads(payload)


@dataclass(frozen=True)
class SimulationRunInfo:
    run_id: str
    season: int
    seed: int
    config_version: str | None = None
    config_fingerprint: str | None = None


@dataclass(frozen=True)
class PersistedSnapshotRecord:
    snapshot_sequence: int
    snapshot_kind: str
    source_event_id: str | None
    as_of_season: int
    as_of_week: int


@dataclass(frozen=True)
class PersistedCompletedEventRecord:
    event_sequence: int
    event_id: str
    season: int | None = None
    week: int | None = None
    template_id: str | None = None
    tournament_result: dict[str, object] | None = None


class SimulationPersistenceRepository:
    """SQLAlchemy repository for deterministic simulation persistence."""

    def __init__(self, *, engine: Engine, session_factory: sessionmaker[Session]) -> None:
        self._engine = engine
        self._session_factory = session_factory

    def bootstrap_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def upsert_simulation_run(self, run: SimulationRunInfo) -> None:
        with self._session_factory.begin() as session:
            model = session.get(SimulationRunModel, run.run_id)
            if model is None:
                model = SimulationRunModel(
                    run_id=run.run_id,
                    season=run.season,
                    seed=run.seed,
                    config_version=run.config_version,
                    config_fingerprint=run.config_fingerprint,
                )
                session.add(model)
                return
            model.season = run.season
            model.seed = run.seed
            model.config_version = run.config_version
            model.config_fingerprint = run.config_fingerprint

    def save_season_state(self, *, run_id: str, state: SeasonState) -> None:
        with self._session_factory.begin() as session:
            model = session.get(SeasonStateModel, run_id)
            ordered_events_json = _to_json([event.model_dump() for event in state.ordered_events])
            completed_event_ids_json = _to_json(state.completed_event_ids)
            ranking_snapshot_json = _to_json(state.ranking_snapshot.model_dump()) if state.ranking_snapshot else None
            race_snapshot_json = _to_json(state.race_snapshot.model_dump()) if state.race_snapshot else None
            if model is None:
                session.add(
                    SeasonStateModel(
                        run_id=run_id,
                        season=state.season,
                        next_event_index=state.next_event_index,
                        ordered_events_json=ordered_events_json,
                        completed_event_ids_json=completed_event_ids_json,
                        ranking_snapshot_json=ranking_snapshot_json,
                        race_snapshot_json=race_snapshot_json,
                    )
                )
            else:
                model.season = state.season
                model.next_event_index = state.next_event_index
                model.ordered_events_json = ordered_events_json
                model.completed_event_ids_json = completed_event_ids_json
                model.ranking_snapshot_json = ranking_snapshot_json
                model.race_snapshot_json = race_snapshot_json

            self._upsert_completed_inputs(session=session, run_id=run_id, completed_inputs=state.completed_tournament_inputs)
            self._upsert_completed_events(session=session, run_id=run_id, completed_event_ids=state.completed_event_ids)

    def save_completed_tournament_result(
        self,
        *,
        run_id: str,
        event_sequence: int,
        tournament_result: TournamentSimulationResult,
    ) -> None:
        with self._session_factory.begin() as session:
            statement: Select[tuple[CompletedEventMetadataModel]] = select(CompletedEventMetadataModel).where(
                CompletedEventMetadataModel.run_id == run_id,
                CompletedEventMetadataModel.event_id == tournament_result.event.event_id,
            )
            model = session.execute(statement).scalar_one_or_none()
            payload = _to_json(tournament_result.tournament_result.model_dump())
            if model is None:
                session.add(
                    CompletedEventMetadataModel(
                        run_id=run_id,
                        event_id=tournament_result.event.event_id,
                        season=tournament_result.event.season,
                        week=tournament_result.event.week,
                        template_id=tournament_result.event.template_id,
                        tournament_result_json=payload,
                    )
                )
            else:
                model.season = tournament_result.event.season
                model.week = tournament_result.event.week
                model.template_id = tournament_result.event.template_id
                model.tournament_result_json = payload

            self._upsert_completed_events(
                session=session,
                run_id=run_id,
                completed_event_ids=[tournament_result.event.event_id],
                start_sequence=event_sequence,
            )
            self._upsert_completed_inputs(
                session=session,
                run_id=run_id,
                completed_inputs=[tournament_result.completed_tournament_input],
                start_sequence=event_sequence,
            )

    def append_snapshot(
        self,
        *,
        run_id: str,
        snapshot_sequence: int,
        snapshot_kind: SnapshotKind,
        source_event_id: str | None,
        ranking_snapshot: RankingSnapshot,
        race_snapshot: RaceSnapshot,
    ) -> None:
        with self._session_factory.begin() as session:
            self._upsert_ranking_snapshot(
                session=session,
                run_id=run_id,
                snapshot_sequence=snapshot_sequence,
                snapshot_kind=snapshot_kind,
                source_event_id=source_event_id,
                snapshot=ranking_snapshot,
            )
            self._upsert_race_snapshot(
                session=session,
                run_id=run_id,
                snapshot_sequence=snapshot_sequence,
                snapshot_kind=snapshot_kind,
                source_event_id=source_event_id,
                snapshot=race_snapshot,
            )

    def load_season_state(self, *, run_id: str) -> SeasonState | None:
        with self._session_factory() as session:
            model = session.get(SeasonStateModel, run_id)
            if model is None:
                return None

            completed_inputs = self._load_completed_inputs(session=session, run_id=run_id)
            ranking_snapshot = RankingSnapshot.model_validate(_from_json(model.ranking_snapshot_json)) if model.ranking_snapshot_json else None
            race_snapshot = RaceSnapshot.model_validate(_from_json(model.race_snapshot_json)) if model.race_snapshot_json else None
            return SeasonState.model_validate(
                {
                    "season": model.season,
                    "ordered_events": _from_json(model.ordered_events_json),
                    "next_event_index": model.next_event_index,
                    "completed_event_ids": _from_json(model.completed_event_ids_json),
                    "completed_tournament_inputs": [payload.model_dump() for payload in completed_inputs],
                    "ranking_snapshot": ranking_snapshot.model_dump() if ranking_snapshot else None,
                    "race_snapshot": race_snapshot.model_dump() if race_snapshot else None,
                }
            )

    def get_simulation_run(self, *, run_id: str) -> SimulationRunInfo | None:
        with self._session_factory() as session:
            model = session.get(SimulationRunModel, run_id)
            if model is None:
                return None
            return SimulationRunInfo(
                run_id=model.run_id,
                season=model.season,
                seed=model.seed,
                config_version=model.config_version,
                config_fingerprint=model.config_fingerprint,
            )

    def list_table_names(self) -> list[str]:
        with self._session_factory() as session:
            return sorted(session.bind.dialect.get_table_names(session.connection()))

    def list_completed_event_ids(self, *, run_id: str) -> list[str]:
        with self._session_factory() as session:
            statement = (
                select(CompletedEventModel)
                .where(CompletedEventModel.run_id == run_id)
                .order_by(CompletedEventModel.event_sequence.asc(), CompletedEventModel.id.asc())
            )
            return [row.event_id for row in session.execute(statement).scalars().all()]

    def list_completed_events(self, *, run_id: str) -> list[PersistedCompletedEventRecord]:
        with self._session_factory() as session:
            statement = (
                select(CompletedEventModel)
                .where(CompletedEventModel.run_id == run_id)
                .order_by(CompletedEventModel.event_sequence.asc(), CompletedEventModel.id.asc())
            )
            events = session.execute(statement).scalars().all()
            records: list[PersistedCompletedEventRecord] = []
            for event in events:
                metadata_statement = select(CompletedEventMetadataModel).where(
                    CompletedEventMetadataModel.run_id == run_id,
                    CompletedEventMetadataModel.event_id == event.event_id,
                )
                metadata = session.execute(metadata_statement).scalar_one_or_none()
                records.append(
                    PersistedCompletedEventRecord(
                        event_sequence=event.event_sequence,
                        event_id=event.event_id,
                        season=metadata.season if metadata else None,
                        week=metadata.week if metadata else None,
                        template_id=metadata.template_id if metadata else None,
                        tournament_result=(
                            _from_json(metadata.tournament_result_json) if metadata and metadata.tournament_result_json else None
                        ),
                    )
                )
            return records

    def get_completed_event(self, *, run_id: str, event_id: str) -> PersistedCompletedEventRecord | None:
        with self._session_factory() as session:
            event_statement = select(CompletedEventModel).where(
                CompletedEventModel.run_id == run_id,
                CompletedEventModel.event_id == event_id,
            )
            event = session.execute(event_statement).scalar_one_or_none()
            if event is None:
                return None

            metadata_statement = select(CompletedEventMetadataModel).where(
                CompletedEventMetadataModel.run_id == run_id,
                CompletedEventMetadataModel.event_id == event_id,
            )
            metadata = session.execute(metadata_statement).scalar_one_or_none()
            return PersistedCompletedEventRecord(
                event_sequence=event.event_sequence,
                event_id=event.event_id,
                season=metadata.season if metadata else None,
                week=metadata.week if metadata else None,
                template_id=metadata.template_id if metadata else None,
                tournament_result=(
                    _from_json(metadata.tournament_result_json) if metadata and metadata.tournament_result_json else None
                ),
            )

    def list_ranking_snapshot_records(self, *, run_id: str) -> list[PersistedSnapshotRecord]:
        with self._session_factory() as session:
            statement = (
                select(RankingSnapshotModel)
                .where(RankingSnapshotModel.run_id == run_id)
                .order_by(RankingSnapshotModel.snapshot_sequence.asc(), RankingSnapshotModel.id.asc())
            )
            return [
                PersistedSnapshotRecord(
                    snapshot_sequence=row.snapshot_sequence,
                    snapshot_kind=row.snapshot_kind,
                    source_event_id=row.source_event_id,
                    as_of_season=row.as_of_season,
                    as_of_week=row.as_of_week,
                )
                for row in session.execute(statement).scalars().all()
            ]

    def list_ranking_snapshots(self, *, run_id: str) -> list[tuple[int, str, str | None, RankingSnapshot]]:
        with self._session_factory() as session:
            statement = (
                select(RankingSnapshotModel)
                .where(RankingSnapshotModel.run_id == run_id)
                .order_by(RankingSnapshotModel.snapshot_sequence.asc(), RankingSnapshotModel.id.asc())
            )
            rows = session.execute(statement).scalars().all()
            return [
                (
                    row.snapshot_sequence,
                    row.snapshot_kind,
                    row.source_event_id,
                    RankingSnapshot.model_validate(_from_json(row.payload_json)),
                )
                for row in rows
            ]

    def list_race_snapshot_records(self, *, run_id: str) -> list[PersistedSnapshotRecord]:
        with self._session_factory() as session:
            statement = (
                select(RaceSnapshotModel)
                .where(RaceSnapshotModel.run_id == run_id)
                .order_by(RaceSnapshotModel.snapshot_sequence.asc(), RaceSnapshotModel.id.asc())
            )
            return [
                PersistedSnapshotRecord(
                    snapshot_sequence=row.snapshot_sequence,
                    snapshot_kind=row.snapshot_kind,
                    source_event_id=row.source_event_id,
                    as_of_season=row.as_of_season,
                    as_of_week=row.as_of_week,
                )
                for row in session.execute(statement).scalars().all()
            ]

    def list_race_snapshots(self, *, run_id: str) -> list[tuple[int, str, str | None, RaceSnapshot]]:
        with self._session_factory() as session:
            statement = (
                select(RaceSnapshotModel)
                .where(RaceSnapshotModel.run_id == run_id)
                .order_by(RaceSnapshotModel.snapshot_sequence.asc(), RaceSnapshotModel.id.asc())
            )
            rows = session.execute(statement).scalars().all()
            return [
                (
                    row.snapshot_sequence,
                    row.snapshot_kind,
                    row.source_event_id,
                    RaceSnapshot.model_validate(_from_json(row.payload_json)),
                )
                for row in rows
            ]

    def count_ranking_snapshots(self, *, run_id: str) -> int:
        return len(self.list_ranking_snapshot_records(run_id=run_id))

    def count_race_snapshots(self, *, run_id: str) -> int:
        return len(self.list_race_snapshot_records(run_id=run_id))

    @staticmethod
    def _upsert_completed_events(
        *,
        session: Session,
        run_id: str,
        completed_event_ids: list[str],
        start_sequence: int = 0,
    ) -> None:
        for offset, event_id in enumerate(completed_event_ids):
            event_sequence = start_sequence + offset
            statement = select(CompletedEventModel).where(
                CompletedEventModel.run_id == run_id,
                CompletedEventModel.event_sequence == event_sequence,
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                session.add(
                    CompletedEventModel(
                        run_id=run_id,
                        event_sequence=event_sequence,
                        event_id=event_id,
                    )
                )
            else:
                model.event_id = event_id

    @staticmethod
    def _upsert_completed_inputs(
        *,
        session: Session,
        run_id: str,
        completed_inputs: list[CompletedTournamentPointsInput],
        start_sequence: int = 0,
    ) -> None:
        for offset, completed_input in enumerate(completed_inputs):
            event_sequence = start_sequence + offset
            statement = select(CompletedTournamentInputModel).where(
                CompletedTournamentInputModel.run_id == run_id,
                CompletedTournamentInputModel.event_id == completed_input.event_id,
            )
            model = session.execute(statement).scalar_one_or_none()
            payload = _to_json(completed_input.model_dump())
            if model is None:
                session.add(
                    CompletedTournamentInputModel(
                        run_id=run_id,
                        event_sequence=event_sequence,
                        event_id=completed_input.event_id,
                        payload_json=payload,
                    )
                )
            else:
                model.event_sequence = event_sequence
                model.payload_json = payload

    @staticmethod
    def _upsert_ranking_snapshot(
        *,
        session: Session,
        run_id: str,
        snapshot_sequence: int,
        snapshot_kind: SnapshotKind,
        source_event_id: str | None,
        snapshot: RankingSnapshot,
    ) -> None:
        statement = select(RankingSnapshotModel).where(
            RankingSnapshotModel.run_id == run_id,
            RankingSnapshotModel.snapshot_sequence == snapshot_sequence,
        )
        model = session.execute(statement).scalar_one_or_none()
        payload = _to_json(snapshot.model_dump())
        if model is None:
            session.add(
                RankingSnapshotModel(
                    run_id=run_id,
                    snapshot_sequence=snapshot_sequence,
                    snapshot_kind=snapshot_kind,
                    source_event_id=source_event_id,
                    as_of_season=snapshot.as_of_season,
                    as_of_week=snapshot.as_of_week,
                    payload_json=payload,
                )
            )
            return
        model.snapshot_kind = snapshot_kind
        model.source_event_id = source_event_id
        model.as_of_season = snapshot.as_of_season
        model.as_of_week = snapshot.as_of_week
        model.payload_json = payload

    @staticmethod
    def _upsert_race_snapshot(
        *,
        session: Session,
        run_id: str,
        snapshot_sequence: int,
        snapshot_kind: SnapshotKind,
        source_event_id: str | None,
        snapshot: RaceSnapshot,
    ) -> None:
        statement = select(RaceSnapshotModel).where(
            RaceSnapshotModel.run_id == run_id,
            RaceSnapshotModel.snapshot_sequence == snapshot_sequence,
        )
        model = session.execute(statement).scalar_one_or_none()
        payload = _to_json(snapshot.model_dump())
        if model is None:
            session.add(
                RaceSnapshotModel(
                    run_id=run_id,
                    snapshot_sequence=snapshot_sequence,
                    snapshot_kind=snapshot_kind,
                    source_event_id=source_event_id,
                    as_of_season=snapshot.as_of_season,
                    as_of_week=snapshot.as_of_week,
                    payload_json=payload,
                )
            )
            return
        model.snapshot_kind = snapshot_kind
        model.source_event_id = source_event_id
        model.as_of_season = snapshot.as_of_season
        model.as_of_week = snapshot.as_of_week
        model.payload_json = payload

    @staticmethod
    def _load_completed_inputs(*, session: Session, run_id: str) -> list[CompletedTournamentPointsInput]:
        statement = (
            select(CompletedTournamentInputModel)
            .where(CompletedTournamentInputModel.run_id == run_id)
            .order_by(CompletedTournamentInputModel.event_sequence.asc(), CompletedTournamentInputModel.id.asc())
        )
        rows = session.execute(statement).scalars().all()
        return [CompletedTournamentPointsInput.model_validate(_from_json(row.payload_json)) for row in rows]
