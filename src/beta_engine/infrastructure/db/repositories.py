"""Persistence adapters for season state, snapshots, and tournament history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, Select, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.season_models import RaceSnapshot, RankingSnapshot, SeasonState, TournamentSimulationResult
from beta_engine.domain.careers import NextSeasonPlayerState, PlayerSeasonTransition
from beta_engine.domain.finals import FinalsQualificationResult, FinalsResult
from beta_engine.domain.rankings import CompletedTournamentPointsInput

from beta_engine.infrastructure.db.models import (
    AdminActionModel,
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
    RunGeneratedPlayerProvenanceModel,
    RunTalentCountryAllocationModel,
    RunTalentPlanModel,
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


@dataclass(frozen=True)
class PersistedAdminActionRecord:
    run_id: str
    event_id: str
    action_sequence: int
    action_kind: str
    payload: dict[str, object]


@dataclass(frozen=True)
class PersistedRunTalentPlanRecord:
    run_id: str
    season: int
    seed: int
    total_talents: int
    dataset_status: str | None
    config_version: str | None
    config_fingerprint: str | None


@dataclass(frozen=True)
class PersistedRunTalentCountryAllocationRecord:
    run_id: str
    season: int
    country_code: str
    planned_count: int
    quality_weights: dict[str, float]
    actual_band_counts: dict[str, int]
    bias_profile: dict[str, float]


@dataclass(frozen=True)
class PersistedGeneratedPlayerProvenanceRecord:
    run_id: str
    season: int
    player_id: str
    country_code: str
    talent_sequence: int | None
    talent_seed_value: int | None
    quality_band: str | None
    is_top_band: bool
    source_type: str
    override_id: str | None


class SimulationPersistenceRepository:
    """SQLAlchemy repository for deterministic simulation persistence."""

    def __init__(self, *, engine: Engine, session_factory: sessionmaker[Session]) -> None:
        self._engine = engine
        self._session_factory = session_factory

    def bootstrap_schema(self) -> None:
        Base.metadata.create_all(self._engine)
        self._ensure_schema_compatibility()

    def _ensure_schema_compatibility(self) -> None:
        with self._engine.begin() as connection:
            self._ensure_text_column(
                connection=connection,
                table_name="season_state",
                column_name="active_tournament_json",
            )
            self._ensure_text_column(
                connection=connection,
                table_name="run_generated_player_provenance",
                column_name="source_type",
            )
            self._ensure_text_column(
                connection=connection,
                table_name="run_generated_player_provenance",
                column_name="override_id",
            )

    @staticmethod
    def _ensure_text_column(*, connection, table_name: str, column_name: str) -> None:
        result = connection.execute(text(f"PRAGMA table_info({table_name})"))
        existing_columns = {row[1] for row in result}
        if column_name in existing_columns:
            return
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT"))

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
            active_tournament_json = _to_json(state.active_tournament.model_dump()) if state.active_tournament else None
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
                        active_tournament_json=active_tournament_json,
                    )
                )
            else:
                model.season = state.season
                model.next_event_index = state.next_event_index
                model.ordered_events_json = ordered_events_json
                model.completed_event_ids_json = completed_event_ids_json
                model.ranking_snapshot_json = ranking_snapshot_json
                model.race_snapshot_json = race_snapshot_json
                model.active_tournament_json = active_tournament_json

            self._upsert_completed_inputs(session=session, run_id=run_id, completed_inputs=state.completed_tournament_inputs)
            self._upsert_completed_events(session=session, run_id=run_id, completed_event_ids=state.completed_event_ids)

    def save_completed_tournament_result(
        self,
        *,
        run_id: str,
        event_sequence: int,
        tournament_result: TournamentSimulationResult,
    ) -> None:
        if tournament_result.completed_tournament_input is None:
            raise ValueError("tournament_result.completed_tournament_input is required for completed-event persistence")
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
            active_tournament = _from_json(model.active_tournament_json) if model.active_tournament_json else None
            return SeasonState.model_validate(
                {
                    "season": model.season,
                    "ordered_events": _from_json(model.ordered_events_json),
                    "next_event_index": model.next_event_index,
                    "completed_event_ids": _from_json(model.completed_event_ids_json),
                    "completed_tournament_inputs": [payload.model_dump() for payload in completed_inputs],
                    "ranking_snapshot": ranking_snapshot.model_dump() if ranking_snapshot else None,
                    "race_snapshot": race_snapshot.model_dump() if race_snapshot else None,
                    "active_tournament": active_tournament,
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

    def list_simulation_runs(self) -> list[SimulationRunInfo]:
        with self._session_factory() as session:
            statement = select(SimulationRunModel).order_by(SimulationRunModel.run_id.asc())
            return [
                SimulationRunInfo(
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
                for model in session.execute(statement).scalars().all()
            ]

    def list_child_run_counts(self) -> dict[str, int]:
        with self._session_factory() as session:
            statement = (
                select(SimulationRunModel.parent_run_id, func.count(SimulationRunModel.run_id))
                .where(SimulationRunModel.parent_run_id.is_not(None))
                .group_by(SimulationRunModel.parent_run_id)
            )
            return {str(parent_run_id): int(count) for parent_run_id, count in session.execute(statement).all()}

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

    def save_run_talent_plan(self, record: PersistedRunTalentPlanRecord) -> None:
        with self._session_factory.begin() as session:
            statement: Select[tuple[RunTalentPlanModel]] = select(RunTalentPlanModel).where(
                RunTalentPlanModel.run_id == record.run_id,
                RunTalentPlanModel.season == record.season,
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                session.add(
                    RunTalentPlanModel(
                        run_id=record.run_id,
                        season=record.season,
                        seed=record.seed,
                        total_talents=record.total_talents,
                        dataset_status=record.dataset_status,
                        config_version=record.config_version,
                        config_fingerprint=record.config_fingerprint,
                    )
                )
                return
            model.seed = record.seed
            model.total_talents = record.total_talents
            model.dataset_status = record.dataset_status
            model.config_version = record.config_version
            model.config_fingerprint = record.config_fingerprint

    def get_run_talent_plan(self, *, run_id: str) -> PersistedRunTalentPlanRecord | None:
        with self._session_factory() as session:
            statement: Select[tuple[RunTalentPlanModel]] = (
                select(RunTalentPlanModel)
                .where(RunTalentPlanModel.run_id == run_id)
                .order_by(RunTalentPlanModel.season.desc())
                .limit(1)
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return PersistedRunTalentPlanRecord(
                run_id=model.run_id,
                season=model.season,
                seed=model.seed,
                total_talents=model.total_talents,
                dataset_status=model.dataset_status,
                config_version=model.config_version,
                config_fingerprint=model.config_fingerprint,
            )

    def replace_run_talent_country_allocations(
        self,
        *,
        run_id: str,
        season: int,
        records: list[PersistedRunTalentCountryAllocationRecord],
    ) -> None:
        with self._session_factory.begin() as session:
            session.query(RunTalentCountryAllocationModel).filter(
                RunTalentCountryAllocationModel.run_id == run_id,
                RunTalentCountryAllocationModel.season == season,
            ).delete()
            for record in records:
                session.add(
                    RunTalentCountryAllocationModel(
                        run_id=record.run_id,
                        season=record.season,
                        country_code=record.country_code,
                        planned_count=record.planned_count,
                        quality_weights_json=_to_json(record.quality_weights),
                        actual_band_counts_json=_to_json(record.actual_band_counts),
                        bias_profile_json=_to_json(record.bias_profile),
                    )
                )

    def list_run_talent_country_allocations(self, *, run_id: str) -> list[PersistedRunTalentCountryAllocationRecord]:
        with self._session_factory() as session:
            statement: Select[tuple[RunTalentCountryAllocationModel]] = (
                select(RunTalentCountryAllocationModel)
                .where(RunTalentCountryAllocationModel.run_id == run_id)
                .order_by(
                    RunTalentCountryAllocationModel.season.asc(),
                    RunTalentCountryAllocationModel.country_code.asc(),
                )
            )
            return [
                PersistedRunTalentCountryAllocationRecord(
                    run_id=model.run_id,
                    season=model.season,
                    country_code=model.country_code,
                    planned_count=model.planned_count,
                    quality_weights=_from_json(model.quality_weights_json),
                    actual_band_counts=_from_json(model.actual_band_counts_json),
                    bias_profile=_from_json(model.bias_profile_json),
                )
                for model in session.execute(statement).scalars().all()
            ]

    def replace_generated_player_provenance(
        self,
        *,
        run_id: str,
        season: int,
        records: list[PersistedGeneratedPlayerProvenanceRecord],
    ) -> None:
        with self._session_factory.begin() as session:
            session.query(RunGeneratedPlayerProvenanceModel).filter(
                RunGeneratedPlayerProvenanceModel.run_id == run_id,
                RunGeneratedPlayerProvenanceModel.season == season,
            ).delete()
            for record in records:
                session.add(
                    RunGeneratedPlayerProvenanceModel(
                        run_id=record.run_id,
                        season=record.season,
                        player_id=record.player_id,
                        country_code=record.country_code,
                        talent_sequence=record.talent_sequence,
                        talent_seed_value=(str(record.talent_seed_value) if record.talent_seed_value is not None else None),
                        quality_band=record.quality_band,
                        is_top_band=1 if record.is_top_band else 0,
                        source_type=record.source_type,
                        override_id=record.override_id,
                    )
                )

    def list_generated_player_provenance(
        self,
        *,
        run_id: str,
        country_code: str | None = None,
        quality_band: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[PersistedGeneratedPlayerProvenanceRecord]:
        with self._session_factory() as session:
            statement: Select[tuple[RunGeneratedPlayerProvenanceModel]] = select(RunGeneratedPlayerProvenanceModel).where(
                RunGeneratedPlayerProvenanceModel.run_id == run_id
            )
            if country_code is not None:
                statement = statement.where(RunGeneratedPlayerProvenanceModel.country_code == country_code.upper())
            if quality_band is not None:
                statement = statement.where(RunGeneratedPlayerProvenanceModel.quality_band == quality_band)
            statement = statement.order_by(
                RunGeneratedPlayerProvenanceModel.season.asc(),
                RunGeneratedPlayerProvenanceModel.country_code.asc(),
                RunGeneratedPlayerProvenanceModel.talent_sequence.asc(),
            )
            if offset > 0:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)
            return [
                PersistedGeneratedPlayerProvenanceRecord(
                    run_id=model.run_id,
                    season=model.season,
                    player_id=model.player_id,
                    country_code=model.country_code,
                    talent_sequence=model.talent_sequence,
                    talent_seed_value=(int(model.talent_seed_value) if model.talent_seed_value is not None else None),
                    quality_band=model.quality_band,
                    is_top_band=model.is_top_band > 0,
                    source_type=model.source_type or "planner_generated",
                    override_id=model.override_id,
                )
                for model in session.execute(statement).scalars().all()
            ]

    def get_generated_player_provenance(
        self,
        *,
        run_id: str,
        player_id: str,
    ) -> PersistedGeneratedPlayerProvenanceRecord | None:
        with self._session_factory() as session:
            statement: Select[tuple[RunGeneratedPlayerProvenanceModel]] = (
                select(RunGeneratedPlayerProvenanceModel)
                .where(
                    RunGeneratedPlayerProvenanceModel.run_id == run_id,
                    RunGeneratedPlayerProvenanceModel.player_id == player_id,
                )
                .order_by(RunGeneratedPlayerProvenanceModel.season.desc())
                .limit(1)
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return PersistedGeneratedPlayerProvenanceRecord(
                run_id=model.run_id,
                season=model.season,
                player_id=model.player_id,
                country_code=model.country_code,
                talent_sequence=model.talent_sequence,
                talent_seed_value=(int(model.talent_seed_value) if model.talent_seed_value is not None else None),
                quality_band=model.quality_band,
                is_top_band=model.is_top_band > 0,
                source_type=model.source_type or "planner_generated",
                override_id=model.override_id,
            )

    def list_table_names(self) -> list[str]:
        with self._session_factory() as session:
            return sorted(session.bind.dialect.get_table_names(session.connection()))

    def append_admin_action(
        self,
        *,
        run_id: str,
        event_id: str,
        action_kind: str,
        payload: dict[str, object],
    ) -> PersistedAdminActionRecord:
        with self._session_factory.begin() as session:
            max_statement = select(func.max(AdminActionModel.action_sequence)).where(
                AdminActionModel.run_id == run_id,
                AdminActionModel.event_id == event_id,
            )
            prior_max = session.execute(max_statement).scalar_one_or_none()
            next_sequence = 1 if prior_max is None else int(prior_max) + 1
            model = AdminActionModel(
                run_id=run_id,
                event_id=event_id,
                action_sequence=next_sequence,
                action_kind=action_kind,
                payload_json=_to_json(payload),
            )
            session.add(model)
            return PersistedAdminActionRecord(
                run_id=run_id,
                event_id=event_id,
                action_sequence=next_sequence,
                action_kind=action_kind,
                payload=payload,
            )

    def list_admin_actions(
        self,
        *,
        run_id: str,
        event_id: str | None = None,
        action_kind: str | None = None,
    ) -> list[PersistedAdminActionRecord]:
        with self._session_factory() as session:
            statement = select(AdminActionModel).where(AdminActionModel.run_id == run_id)
            if event_id is not None:
                statement = statement.where(AdminActionModel.event_id == event_id)
            if action_kind is not None:
                statement = statement.where(AdminActionModel.action_kind == action_kind)
            statement = statement.order_by(
                AdminActionModel.event_id.asc(),
                AdminActionModel.action_sequence.asc(),
                AdminActionModel.id.asc(),
            )
            return [
                PersistedAdminActionRecord(
                    run_id=row.run_id,
                    event_id=row.event_id,
                    action_sequence=row.action_sequence,
                    action_kind=row.action_kind,
                    payload=_from_json(row.payload_json),
                )
                for row in session.execute(statement).scalars().all()
            ]

    def get_wildcard_assignments_for_event(self, *, run_id: str, event_id: str) -> dict[int, str]:
        assignments: dict[int, str] = {}
        for action in self.list_admin_actions(
            run_id=run_id,
            event_id=event_id,
            action_kind="assign_wildcards",
        ):
            raw_assignments = action.payload.get("assignments", [])
            if not isinstance(raw_assignments, list):
                continue
            for raw_assignment in raw_assignments:
                if not isinstance(raw_assignment, dict):
                    continue
                raw_slot_index = raw_assignment.get("slot_index")
                raw_player_id = raw_assignment.get("player_id")
                if not isinstance(raw_slot_index, int) or not isinstance(raw_player_id, str):
                    continue
                assignments[raw_slot_index] = raw_player_id
        return assignments

    def get_wildcard_assignments_for_run(self, *, run_id: str) -> dict[str, dict[int, str]]:
        event_ids = {
            action.event_id
            for action in self.list_admin_actions(
                run_id=run_id,
                action_kind="assign_wildcards",
            )
        }
        return {
            event_id: self.get_wildcard_assignments_for_event(run_id=run_id, event_id=event_id)
            for event_id in sorted(event_ids)
        }

    def get_pre_draw_withdrawal_replacements_for_event(self, *, run_id: str, event_id: str) -> list[dict[str, object]]:
        return [
            dict(action.payload)
            for action in self.list_admin_actions(
                run_id=run_id,
                event_id=event_id,
                action_kind="pre_draw_withdrawal_replacement",
            )
        ]

    def get_pre_draw_withdrawal_replacements_for_run(self, *, run_id: str) -> dict[str, list[dict[str, object]]]:
        actions = self.list_admin_actions(run_id=run_id, action_kind="pre_draw_withdrawal_replacement")
        event_ids = sorted({action.event_id for action in actions})
        return {
            event_id: self.get_pre_draw_withdrawal_replacements_for_event(run_id=run_id, event_id=event_id)
            for event_id in event_ids
        }

    def get_late_replacements_for_event(self, *, run_id: str, event_id: str) -> list[dict[str, object]]:
        return [
            dict(action.payload)
            for action in self.list_admin_actions(
                run_id=run_id,
                event_id=event_id,
                action_kind="late_replacement_lucky_loser",
            )
        ]

    def get_late_replacements_for_run(self, *, run_id: str) -> dict[str, list[dict[str, object]]]:
        actions = self.list_admin_actions(run_id=run_id, action_kind="late_replacement_lucky_loser")
        event_ids = sorted({action.event_id for action in actions})
        return {
            event_id: self.get_late_replacements_for_event(run_id=run_id, event_id=event_id)
            for event_id in event_ids
        }

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

    def get_ranking_snapshot(
        self,
        *,
        run_id: str,
        snapshot_sequence: int,
    ) -> tuple[int, str, str | None, RankingSnapshot] | None:
        with self._session_factory() as session:
            statement = (
                select(RankingSnapshotModel)
                .where(
                    RankingSnapshotModel.run_id == run_id,
                    RankingSnapshotModel.snapshot_sequence == snapshot_sequence,
                )
                .order_by(RankingSnapshotModel.id.asc())
            )
            row = session.execute(statement).scalars().first()
            if row is None:
                return None
            return (
                row.snapshot_sequence,
                row.snapshot_kind,
                row.source_event_id,
                RankingSnapshot.model_validate(_from_json(row.payload_json)),
            )

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

    def get_race_snapshot(
        self,
        *,
        run_id: str,
        snapshot_sequence: int,
    ) -> tuple[int, str, str | None, RaceSnapshot] | None:
        with self._session_factory() as session:
            statement = (
                select(RaceSnapshotModel)
                .where(
                    RaceSnapshotModel.run_id == run_id,
                    RaceSnapshotModel.snapshot_sequence == snapshot_sequence,
                )
                .order_by(RaceSnapshotModel.id.asc())
            )
            row = session.execute(statement).scalars().first()
            if row is None:
                return None
            return (
                row.snapshot_sequence,
                row.snapshot_kind,
                row.source_event_id,
                RaceSnapshot.model_validate(_from_json(row.payload_json)),
            )

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

    def list_finals_qualifications(self, *, run_id: str) -> list[PersistedFinalsQualificationRecord]:
        with self._session_factory() as session:
            statement = (
                select(FinalsQualificationModel)
                .where(FinalsQualificationModel.run_id == run_id)
                .order_by(FinalsQualificationModel.season.asc(), FinalsQualificationModel.id.asc())
            )
            return [
                PersistedFinalsQualificationRecord(
                    run_id=model.run_id,
                    season=model.season,
                    source_as_of_season=model.source_as_of_season,
                    source_as_of_week=model.source_as_of_week,
                    qualification=FinalsQualificationResult.model_validate(_from_json(model.payload_json)),
                )
                for model in session.execute(statement).scalars().all()
            ]

    def list_finals_results(self, *, run_id: str) -> list[PersistedFinalsResultRecord]:
        with self._session_factory() as session:
            statement = (
                select(FinalsResultModel)
                .where(FinalsResultModel.run_id == run_id)
                .order_by(FinalsResultModel.season.asc(), FinalsResultModel.id.asc())
            )
            return [
                PersistedFinalsResultRecord(
                    run_id=model.run_id,
                    season=model.season,
                    event_id=model.event_id,
                    source_as_of_season=model.source_as_of_season,
                    source_as_of_week=model.source_as_of_week,
                    result=FinalsResult.model_validate(_from_json(model.payload_json)),
                )
                for model in session.execute(statement).scalars().all()
            ]

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

    def list_season_rollovers(self, *, run_id: str) -> list[PersistedSeasonRolloverRecord]:
        with self._session_factory() as session:
            statement = (
                select(SeasonRolloverModel)
                .where(SeasonRolloverModel.run_id == run_id)
                .order_by(SeasonRolloverModel.to_season.asc(), SeasonRolloverModel.id.asc())
            )
            return [
                PersistedSeasonRolloverRecord(
                    run_id=model.run_id,
                    from_season=model.from_season,
                    to_season=model.to_season,
                    transitioned_players=model.transitioned_players,
                    metadata=_from_json(model.metadata_json),
                )
                for model in session.execute(statement).scalars().all()
            ]

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
