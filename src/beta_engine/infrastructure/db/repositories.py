"""Persistence adapters for season state, snapshots, and tournament history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, Select, select
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.season_models import RaceSnapshot, RankingSnapshot, SeasonState, TournamentSimulationResult
from beta_engine.domain.careers import NextSeasonPlayerState, PlayerSeasonTransition
from beta_engine.domain.finals import FinalsQualificationResult, FinalsResult
from beta_engine.domain.rankings import CompletedTournamentPointsInput

from beta_engine.infrastructure.db.models import (
    Base,
    CompletedEventMetadataModel,
    FinalsQualificationModel,
    FinalsResultModel,
    NextSeasonPlayerModel,
    PlayerSeasonTransitionModel,
    SeasonRolloverModel,
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
    parent_run_id: str | None = None
    source_type: str = "fresh_seed"
    source_rollover_run_id: str | None = None
    source_rollover_from_season: int | None = None
    source_rollover_to_season: int | None = None


@dataclass(frozen=True)
class RunLineageRecord:
    run_id: str
    parent_run_id: str | None
    source_type: str
    source_rollover_run_id: str | None
    source_rollover_from_season: int | None
    source_rollover_to_season: int | None


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


@dataclass(frozen=True)
class PersistedFinalsQualificationRecord:
    run_id: str
    season: int
    source_as_of_season: int
    source_as_of_week: int
    qualification: FinalsQualificationResult


@dataclass(frozen=True)
class PersistedFinalsResultRecord:
    run_id: str
    season: int
    event_id: str
    source_as_of_season: int
    source_as_of_week: int
    result: FinalsResult


@dataclass(frozen=True)
class PersistedSeasonRolloverRecord:
    run_id: str
    from_season: int
    to_season: int
    transitioned_players: int
    metadata: dict[str, object]


@dataclass(frozen=True)
class PersistedPlayerTransitionRecord:
    run_id: str
    from_season: int
    to_season: int
    player_id: str
    transition: PlayerSeasonTransition


@dataclass(frozen=True)
class NextSeasonPlayerRecord:
    run_id: str
    from_season: int
    to_season: int
    player_id: str
    state: NextSeasonPlayerState


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
                    parent_run_id=run.parent_run_id,
                    source_type=run.source_type,
                    source_rollover_run_id=run.source_rollover_run_id,
                    source_rollover_from_season=run.source_rollover_from_season,
                    source_rollover_to_season=run.source_rollover_to_season,
                )
                session.add(model)
                return
            model.season = run.season
            model.seed = run.seed
            model.config_version = run.config_version
            model.config_fingerprint = run.config_fingerprint
            model.parent_run_id = run.parent_run_id
            model.source_type = run.source_type
            model.source_rollover_run_id = run.source_rollover_run_id
            model.source_rollover_from_season = run.source_rollover_from_season
            model.source_rollover_to_season = run.source_rollover_to_season

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
                parent_run_id=model.parent_run_id,
                source_type=model.source_type,
                source_rollover_run_id=model.source_rollover_run_id,
                source_rollover_from_season=model.source_rollover_from_season,
                source_rollover_to_season=model.source_rollover_to_season,
            )

    def get_run_lineage(self, *, run_id: str) -> RunLineageRecord | None:
        with self._session_factory() as session:
            model = session.get(SimulationRunModel, run_id)
            if model is None:
                return None
            return RunLineageRecord(
                run_id=model.run_id,
                parent_run_id=model.parent_run_id,
                source_type=model.source_type,
                source_rollover_run_id=model.source_rollover_run_id,
                source_rollover_from_season=model.source_rollover_from_season,
                source_rollover_to_season=model.source_rollover_to_season,
            )

    def list_child_runs(self, *, parent_run_id: str) -> list[RunLineageRecord]:
        with self._session_factory() as session:
            statement = (
                select(SimulationRunModel)
                .where(SimulationRunModel.parent_run_id == parent_run_id)
                .order_by(SimulationRunModel.run_id.asc())
            )
            return [
                RunLineageRecord(
                    run_id=model.run_id,
                    parent_run_id=model.parent_run_id,
                    source_type=model.source_type,
                    source_rollover_run_id=model.source_rollover_run_id,
                    source_rollover_from_season=model.source_rollover_from_season,
                    source_rollover_to_season=model.source_rollover_to_season,
                )
                for model in session.execute(statement).scalars().all()
            ]

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

    def upsert_finals_qualification(
        self,
        *,
        run_id: str,
        season: int,
        source_as_of_season: int,
        source_as_of_week: int,
        qualification: FinalsQualificationResult,
    ) -> None:
        with self._session_factory.begin() as session:
            statement = select(FinalsQualificationModel).where(
                FinalsQualificationModel.run_id == run_id,
                FinalsQualificationModel.season == season,
            )
            model = session.execute(statement).scalar_one_or_none()
            payload = _to_json(qualification.model_dump())
            if model is None:
                session.add(
                    FinalsQualificationModel(
                        run_id=run_id,
                        season=season,
                        source_as_of_season=source_as_of_season,
                        source_as_of_week=source_as_of_week,
                        payload_json=payload,
                    )
                )
                return
            model.source_as_of_season = source_as_of_season
            model.source_as_of_week = source_as_of_week
            model.payload_json = payload

    def get_finals_qualification(self, *, run_id: str, season: int) -> PersistedFinalsQualificationRecord | None:
        with self._session_factory() as session:
            statement = select(FinalsQualificationModel).where(
                FinalsQualificationModel.run_id == run_id,
                FinalsQualificationModel.season == season,
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return PersistedFinalsQualificationRecord(
                run_id=model.run_id,
                season=model.season,
                source_as_of_season=model.source_as_of_season,
                source_as_of_week=model.source_as_of_week,
                qualification=FinalsQualificationResult.model_validate(_from_json(model.payload_json)),
            )

    def upsert_finals_result(
        self,
        *,
        run_id: str,
        season: int,
        event_id: str,
        source_as_of_season: int,
        source_as_of_week: int,
        result: FinalsResult,
    ) -> None:
        with self._session_factory.begin() as session:
            statement = select(FinalsResultModel).where(
                FinalsResultModel.run_id == run_id,
                FinalsResultModel.season == season,
            )
            model = session.execute(statement).scalar_one_or_none()
            payload = _to_json(result.model_dump())
            if model is None:
                session.add(
                    FinalsResultModel(
                        run_id=run_id,
                        season=season,
                        event_id=event_id,
                        source_as_of_season=source_as_of_season,
                        source_as_of_week=source_as_of_week,
                        payload_json=payload,
                    )
                )
                return
            model.event_id = event_id
            model.source_as_of_season = source_as_of_season
            model.source_as_of_week = source_as_of_week
            model.payload_json = payload

    def get_finals_result(self, *, run_id: str, season: int) -> PersistedFinalsResultRecord | None:
        with self._session_factory() as session:
            statement = select(FinalsResultModel).where(
                FinalsResultModel.run_id == run_id,
                FinalsResultModel.season == season,
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return PersistedFinalsResultRecord(
                run_id=model.run_id,
                season=model.season,
                event_id=model.event_id,
                source_as_of_season=model.source_as_of_season,
                source_as_of_week=model.source_as_of_week,
                result=FinalsResult.model_validate(_from_json(model.payload_json)),
            )

    def upsert_season_rollover(
        self,
        *,
        run_id: str,
        from_season: int,
        to_season: int,
        transitioned_players: int,
        metadata: dict[str, object],
        transitions: list[PlayerSeasonTransition],
        next_player_states: list[NextSeasonPlayerState],
    ) -> None:
        with self._session_factory.begin() as session:
            statement = select(SeasonRolloverModel).where(
                SeasonRolloverModel.run_id == run_id,
                SeasonRolloverModel.to_season == to_season,
            )
            model = session.execute(statement).scalar_one_or_none()
            metadata_json = _to_json(metadata)
            if model is None:
                session.add(
                    SeasonRolloverModel(
                        run_id=run_id,
                        from_season=from_season,
                        to_season=to_season,
                        transitioned_players=transitioned_players,
                        metadata_json=metadata_json,
                    )
                )
            else:
                model.from_season = from_season
                model.transitioned_players = transitioned_players
                model.metadata_json = metadata_json

            for transition in transitions:
                transition_statement = select(PlayerSeasonTransitionModel).where(
                    PlayerSeasonTransitionModel.run_id == run_id,
                    PlayerSeasonTransitionModel.to_season == to_season,
                    PlayerSeasonTransitionModel.player_id == transition.player_id,
                )
                transition_model = session.execute(transition_statement).scalar_one_or_none()
                transition_payload = _to_json(transition.model_dump())
                if transition_model is None:
                    session.add(
                        PlayerSeasonTransitionModel(
                            run_id=run_id,
                            from_season=from_season,
                            to_season=to_season,
                            player_id=transition.player_id,
                            payload_json=transition_payload,
                        )
                    )
                else:
                    transition_model.from_season = from_season
                    transition_model.payload_json = transition_payload

            for next_state in next_player_states:
                next_player_id = next_state.player.player_id
                next_state_statement = select(NextSeasonPlayerModel).where(
                    NextSeasonPlayerModel.run_id == run_id,
                    NextSeasonPlayerModel.to_season == to_season,
                    NextSeasonPlayerModel.player_id == next_player_id,
                )
                next_state_model = session.execute(next_state_statement).scalar_one_or_none()
                next_state_payload = _to_json(next_state.model_dump())
                if next_state_model is None:
                    session.add(
                        NextSeasonPlayerModel(
                            run_id=run_id,
                            from_season=from_season,
                            to_season=to_season,
                            player_id=next_player_id,
                            payload_json=next_state_payload,
                        )
                    )
                else:
                    next_state_model.from_season = from_season
                    next_state_model.payload_json = next_state_payload

    def get_season_rollover(self, *, run_id: str, to_season: int) -> PersistedSeasonRolloverRecord | None:
        with self._session_factory() as session:
            statement = select(SeasonRolloverModel).where(
                SeasonRolloverModel.run_id == run_id,
                SeasonRolloverModel.to_season == to_season,
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return PersistedSeasonRolloverRecord(
                run_id=model.run_id,
                from_season=model.from_season,
                to_season=model.to_season,
                transitioned_players=model.transitioned_players,
                metadata=_from_json(model.metadata_json),
            )

    def get_latest_season_rollover(self, *, run_id: str) -> PersistedSeasonRolloverRecord | None:
        with self._session_factory() as session:
            statement = (
                select(SeasonRolloverModel)
                .where(SeasonRolloverModel.run_id == run_id)
                .order_by(SeasonRolloverModel.to_season.desc(), SeasonRolloverModel.id.desc())
                .limit(1)
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return PersistedSeasonRolloverRecord(
                run_id=model.run_id,
                from_season=model.from_season,
                to_season=model.to_season,
                transitioned_players=model.transitioned_players,
                metadata=_from_json(model.metadata_json),
            )

    def list_player_transitions(self, *, run_id: str, to_season: int) -> list[PersistedPlayerTransitionRecord]:
        with self._session_factory() as session:
            statement = (
                select(PlayerSeasonTransitionModel)
                .where(
                    PlayerSeasonTransitionModel.run_id == run_id,
                    PlayerSeasonTransitionModel.to_season == to_season,
                )
                .order_by(PlayerSeasonTransitionModel.player_id.asc(), PlayerSeasonTransitionModel.id.asc())
            )
            return [
                PersistedPlayerTransitionRecord(
                    run_id=row.run_id,
                    from_season=row.from_season,
                    to_season=row.to_season,
                    player_id=row.player_id,
                    transition=PlayerSeasonTransition.model_validate(_from_json(row.payload_json)),
                )
                for row in session.execute(statement).scalars().all()
            ]

    def list_next_season_players(self, *, run_id: str, to_season: int) -> list[NextSeasonPlayerRecord]:
        with self._session_factory() as session:
            statement = (
                select(NextSeasonPlayerModel)
                .where(
                    NextSeasonPlayerModel.run_id == run_id,
                    NextSeasonPlayerModel.to_season == to_season,
                )
                .order_by(NextSeasonPlayerModel.player_id.asc(), NextSeasonPlayerModel.id.asc())
            )
            return [
                NextSeasonPlayerRecord(
                    run_id=row.run_id,
                    from_season=row.from_season,
                    to_season=row.to_season,
                    player_id=row.player_id,
                    state=NextSeasonPlayerState.model_validate(_from_json(row.payload_json)),
                )
                for row in session.execute(statement).scalars().all()
            ]

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
