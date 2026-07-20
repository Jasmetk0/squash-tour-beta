"""Persistence adapters for season state, snapshots, and tournament history."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, Select, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.season_models import RaceSnapshot, RankingSnapshot, SeasonState, TournamentSimulationResult
from beta_engine.domain.careers import NextSeasonPlayerState, PlayerSeasonTransition
from beta_engine.domain.finals import FinalsQualificationResult, FinalsResult
from beta_engine.domain.rankings import CompletedTournamentPointsInput

from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID
from beta_engine.infrastructure.db.models import (
    AdminActionModel,
    BranchCheckpointModel,
    BranchStateModel,
    Base,
    CompletedEventMetadataModel,
    FinalsQualificationModel,
    FinalsResultModel,
    NextSeasonPlayerModel,
    PlayerSeasonTransitionModel,
    SeasonRolloverModel,
    CompletedEventModel,
    CompletedTournamentInputModel,
    LegacySimulationRunMappingModel,
    RaceSnapshotModel,
    RankingSnapshotModel,
    RunGeneratedPlayerProvenanceModel,
    RunContainerModel,
    RunBranchModel,
    RunProspectModel,
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
    world_id: str = OFFICIAL_FAX_WORLD_ID
    world_generation_fingerprint: str | None = None
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
    world_id: str = OFFICIAL_FAX_WORLD_ID


@dataclass(frozen=True)
class RunContainerRecord:
    run_id: str
    display_name: str | None
    storage_kind: str
    read_only: bool
    world_id: str
    world_package_fingerprint: str | None
    config_version: str | None
    config_fingerprint: str | None
    global_seed: int | None
    timeline_start_season: int
    timeline_end_season: int
    official_branch_id: str | None
    status: str
    metadata: dict[str, object]
    mapped_simulation_run_count: int = 0


@dataclass(frozen=True)
class RunBranchRecord:
    branch_id: str
    run_id: str
    display_name: str
    status: str
    read_only: bool
    branch_seed: int | None
    forked_from_branch_id: str | None
    forked_from_checkpoint_id: str | None
    head_checkpoint_id: str | None
    legacy_simulation_run_id: str | None
    metadata: dict[str, object]
    is_official: bool = False


@dataclass(frozen=True)
class BranchCheckpointRecord:
    checkpoint_id: str; run_id: str; branch_id: str; parent_checkpoint_id: str | None; sequence: int; kind: str
    season: int; week: int | None; event_id: str | None; event_sequence: int | None
    command_id: str; command_kind: str; command_boundary: str
    config_version: str | None; config_fingerprint: str | None; world_id: str; world_fingerprint: str | None
    global_seed: int | None; branch_seed: int | None; seed_namespace: dict[str, object]
    payload_schema_version: str; content_hash_algorithm: str; content_hash: str; payload: dict[str, object]


@dataclass(frozen=True)
class RunBranchStateRecord:
    branch_id: str
    run_id: str
    head_checkpoint_id: str | None
    current_season: int | None
    current_week: int | None
    current_event_id: str | None
    current_event_sequence: int | None
    state_schema_version: str
    status: str
    metadata: dict[str, object]


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
    dampener: dict[str, object]


@dataclass(frozen=True)
class RunProspectRecord:
    prospect_id: str
    run_id: str
    world_id: str
    season_start_year: int
    season_label: str
    season_week: int
    calendar_year: int
    year_week: int
    birth_year: int
    birth_year_week: int
    age: int
    country_code: str
    country_name: str | None
    status: str
    source_type: str
    cohort_policy_version: str
    profile_version: str
    first_name: str | None
    last_name: str | None
    display_name: str
    short_name: str | None
    identity_seed: str
    profile_seed: str
    development_seed: str
    potential_seed: str
    trait_seed: str
    profile_json: dict[str, object]
    development_json: dict[str, object]
    potential_json: dict[str, object]
    trait_json: dict[str, object]


def deterministic_prospect_id(
    *,
    run_id: str,
    world_id: str,
    season_start_year: int,
    season_week: int,
    country_code: str,
    local_sequence: int,
    profile_version: str,
    cohort_policy_version: str,
) -> str:
    payload = "|".join(
        [
            run_id,
            world_id,
            str(season_start_year),
            str(season_week),
            country_code.upper(),
            str(local_sequence),
            profile_version,
            cohort_policy_version,
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20].upper()
    return f"PR-{season_start_year}-W{season_week:02d}-{country_code.upper()}-{local_sequence:04d}-{digest}"

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
    origin_source_type: str | None
    origin_quality_band: str | None
    origin_override_id: str | None
    origin_season: int | None


class SimulationPersistenceRepository:
    """SQLAlchemy repository for deterministic simulation persistence."""

    def __init__(self, *, engine: Engine, session_factory: sessionmaker[Session]) -> None:
        self._engine = engine
        self._session_factory = session_factory

    def bootstrap_schema(self) -> None:
        try:
            Base.metadata.create_all(self._engine)
        except OperationalError as exc:
            if "already exists" not in str(exc).lower():
                raise
        self._ensure_schema_compatibility()
        self.backfill_default_branches_for_existing_run_containers()
        self.backfill_branch_states_for_existing_branches()

    def _ensure_schema_compatibility(self) -> None:
        with self._engine.begin() as connection:
            self._ensure_column(
                connection=connection,
                table_name="season_state",
                column_name="active_tournament_json",
                column_type="TEXT",
            )
            self._ensure_column(
                connection=connection,
                table_name="run_generated_player_provenance",
                column_name="source_type",
                column_type="TEXT",
            )
            self._ensure_column(
                connection=connection,
                table_name="run_generated_player_provenance",
                column_name="override_id",
                column_type="TEXT",
            )
            self._ensure_column(
                connection=connection,
                table_name="run_generated_player_provenance",
                column_name="origin_source_type",
                column_type="TEXT",
            )
            self._ensure_column(
                connection=connection,
                table_name="run_generated_player_provenance",
                column_name="origin_quality_band",
                column_type="TEXT",
            )
            self._ensure_column(
                connection=connection,
                table_name="run_generated_player_provenance",
                column_name="origin_override_id",
                column_type="TEXT",
            )
            self._ensure_column(
                connection=connection,
                table_name="run_generated_player_provenance",
                column_name="origin_season",
                column_type="INTEGER",
            )
            self._ensure_column(
                connection=connection,
                table_name="run_talent_country_allocations",
                column_name="dampener_json",
                column_type="TEXT",
            )
            self._ensure_column(
                connection=connection,
                table_name="simulation_runs",
                column_name="world_id",
                column_type="TEXT",
            )
            self._ensure_column(
                connection=connection,
                table_name="simulation_runs",
                column_name="world_generation_fingerprint",
                column_type="TEXT",
            )

    @staticmethod
    def _ensure_column(*, connection, table_name: str, column_name: str, column_type: str) -> None:
        result = connection.execute(text(f"PRAGMA table_info({table_name})"))
        existing_columns = {row[1] for row in result}
        if column_name in existing_columns:
            return
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))

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
                    world_id=run.world_id,
                    world_generation_fingerprint=run.world_generation_fingerprint,
                    parent_run_id=run.parent_run_id,
                    source_type=run.source_type,
                    source_rollover_run_id=run.source_rollover_run_id,
                    source_rollover_from_season=run.source_rollover_from_season,
                    source_rollover_to_season=run.source_rollover_to_season,
                )
                session.add(model)
            else:
                model.season = run.season
                model.seed = run.seed
                model.config_version = run.config_version
                model.config_fingerprint = run.config_fingerprint
                # world_id is an immutable run creation lock; preserve existing values on metadata updates.
                if model.world_id is None:
                    model.world_id = run.world_id
                model.world_generation_fingerprint = run.world_generation_fingerprint
                model.parent_run_id = run.parent_run_id
                model.source_type = run.source_type
                model.source_rollover_run_id = run.source_rollover_run_id
                model.source_rollover_from_season = run.source_rollover_from_season
                model.source_rollover_to_season = run.source_rollover_to_season
        self.ensure_run_container_for_simulation_run(simulation_run_id=run.run_id)

    @staticmethod
    def _to_run_container(model: RunContainerModel, mapped_simulation_run_count: int = 0) -> RunContainerRecord:
        return RunContainerRecord(
            run_id=model.run_id, display_name=model.display_name, storage_kind=model.storage_kind,
            read_only=bool(model.read_only), world_id=model.world_id,
            world_package_fingerprint=model.world_package_fingerprint, config_version=model.config_version,
            config_fingerprint=model.config_fingerprint, global_seed=model.global_seed,
            timeline_start_season=model.timeline_start_season, timeline_end_season=model.timeline_end_season,
            official_branch_id=model.official_branch_id, status=model.status,
            metadata=_from_json(model.metadata_json), mapped_simulation_run_count=mapped_simulation_run_count,
        )

    def create_run_container(self, record: RunContainerRecord) -> RunContainerRecord:
        if record.storage_kind not in {"built_in", "custom_local"}:
            raise ValueError("storage_kind must be 'built_in' or 'custom_local'")
        with self._session_factory.begin() as session:
            model = session.get(RunContainerModel, record.run_id)
            if model is None:
                session.add(RunContainerModel(
                    run_id=record.run_id, display_name=record.display_name, storage_kind=record.storage_kind,
                    read_only=int(record.read_only), world_id=record.world_id,
                    world_package_fingerprint=record.world_package_fingerprint, config_version=record.config_version,
                    config_fingerprint=record.config_fingerprint, global_seed=record.global_seed,
                    timeline_start_season=record.timeline_start_season, timeline_end_season=record.timeline_end_season,
                    official_branch_id=record.official_branch_id, status=record.status,
                    metadata_json=_to_json(record.metadata),
                ))
            # Containers are immutable in R1; return the persisted creation lock unchanged.
        return self.get_run_container(run_id=record.run_id)  # type: ignore[return-value]

    def get_run_container(self, *, run_id: str) -> RunContainerRecord | None:
        with self._session_factory() as session:
            model = session.get(RunContainerModel, run_id)
            if model is None:
                return None
            count = session.scalar(select(func.count(LegacySimulationRunMappingModel.simulation_run_id)).where(LegacySimulationRunMappingModel.run_id == run_id)) or 0
            return self._to_run_container(model, int(count))

    def list_run_containers(self) -> list[RunContainerRecord]:
        with self._session_factory() as session:
            counts = dict(session.execute(select(LegacySimulationRunMappingModel.run_id, func.count()).group_by(LegacySimulationRunMappingModel.run_id)).all())
            return [self._to_run_container(model, int(counts.get(model.run_id, 0))) for model in session.execute(select(RunContainerModel).order_by(RunContainerModel.run_id)).scalars()]

    def get_run_container_for_simulation_run(self, *, simulation_run_id: str) -> RunContainerRecord | None:
        with self._session_factory() as session:
            mapping = session.get(LegacySimulationRunMappingModel, simulation_run_id)
            if mapping is None:
                return None
        return self.get_run_container(run_id=mapping.run_id)

    def ensure_run_container_for_simulation_run(self, *, simulation_run_id: str) -> RunContainerRecord | None:
        legacy = self.get_simulation_run(run_id=simulation_run_id)
        if legacy is None:
            return None
        container = self.create_run_container(RunContainerRecord(
            run_id=legacy.run_id, display_name=None, storage_kind="custom_local", read_only=False,
            world_id=legacy.world_id, world_package_fingerprint=legacy.world_generation_fingerprint,
            config_version=legacy.config_version, config_fingerprint=legacy.config_fingerprint, global_seed=legacy.seed,
            timeline_start_season=legacy.season, timeline_end_season=legacy.season, official_branch_id=None,
            status="active", metadata={},
        ))
        with self._session_factory.begin() as session:
            if session.get(LegacySimulationRunMappingModel, simulation_run_id) is None:
                session.add(LegacySimulationRunMappingModel(simulation_run_id=simulation_run_id, run_id=container.run_id))
        self.ensure_default_branch_for_simulation_run(simulation_run_id=simulation_run_id)
        return self.get_run_container(run_id=container.run_id)

    def backfill_run_containers_for_existing_simulation_runs(self) -> None:
        for legacy in self.list_simulation_runs():
            self.ensure_run_container_for_simulation_run(simulation_run_id=legacy.run_id)

    @staticmethod
    def deterministic_default_branch_id(*, run_id: str, legacy_simulation_run_id: str) -> str:
        digest = hashlib.sha256(f"{run_id}\x00{legacy_simulation_run_id}".encode("utf-8")).hexdigest()[:24]
        return f"branch-{digest}"

    @staticmethod
    def _to_run_branch(model: RunBranchModel, *, official_branch_id: str | None) -> RunBranchRecord:
        return RunBranchRecord(
            branch_id=model.branch_id, run_id=model.run_id, display_name=model.display_name,
            status=model.status, read_only=bool(model.read_only), branch_seed=model.branch_seed,
            forked_from_branch_id=model.forked_from_branch_id,
            forked_from_checkpoint_id=model.forked_from_checkpoint_id,
            head_checkpoint_id=model.head_checkpoint_id,
            legacy_simulation_run_id=model.legacy_simulation_run_id,
            metadata=_from_json(model.metadata_json), is_official=model.branch_id == official_branch_id,
        )

    def create_run_branch(self, record: RunBranchRecord) -> RunBranchRecord:
        with self._session_factory.begin() as session:
            if session.get(RunBranchModel, record.branch_id) is None:
                session.add(RunBranchModel(
                    branch_id=record.branch_id, run_id=record.run_id, display_name=record.display_name,
                    status=record.status, read_only=int(record.read_only), branch_seed=record.branch_seed,
                    forked_from_branch_id=record.forked_from_branch_id,
                    forked_from_checkpoint_id=record.forked_from_checkpoint_id,
                    head_checkpoint_id=record.head_checkpoint_id,
                    legacy_simulation_run_id=record.legacy_simulation_run_id,
                    metadata_json=_to_json(record.metadata),
                ))
        created = self.get_run_branch(branch_id=record.branch_id)
        self.ensure_branch_state_for_branch(branch_id=record.branch_id)
        return created  # type: ignore[return-value]

    def get_run_branch(self, *, branch_id: str) -> RunBranchRecord | None:
        with self._session_factory() as session:
            model = session.get(RunBranchModel, branch_id)
            if model is None:
                return None
            container = session.get(RunContainerModel, model.run_id)
            return self._to_run_branch(model, official_branch_id=container.official_branch_id if container else None)

    def list_run_branches(self, *, run_id: str | None = None) -> list[RunBranchRecord]:
        with self._session_factory() as session:
            statement = select(RunBranchModel).order_by(RunBranchModel.branch_id)
            if run_id is not None:
                statement = statement.where(RunBranchModel.run_id == run_id)
            models = session.execute(statement).scalars().all()
            official_by_run = {
                container.run_id: container.official_branch_id
                for container in session.execute(select(RunContainerModel)).scalars()
            }
            return [self._to_run_branch(model, official_branch_id=official_by_run.get(model.run_id)) for model in models]

    def ensure_default_branch_for_simulation_run(self, *, simulation_run_id: str) -> RunBranchRecord | None:
        container = self.get_run_container_for_simulation_run(simulation_run_id=simulation_run_id)
        if container is None:
            return None
        branch_id = self.deterministic_default_branch_id(run_id=container.run_id, legacy_simulation_run_id=simulation_run_id)
        record = self.create_run_branch(RunBranchRecord(
            branch_id=branch_id, run_id=container.run_id, display_name="Main", status="active",
            read_only=container.read_only, branch_seed=container.global_seed,
            forked_from_branch_id=None, forked_from_checkpoint_id=None, head_checkpoint_id=None,
            legacy_simulation_run_id=simulation_run_id, metadata={},
        ))
        with self._session_factory.begin() as session:
            model = session.get(RunContainerModel, container.run_id)
            if model is not None and model.official_branch_id is None:
                model.official_branch_id = branch_id
        return self.get_run_branch(branch_id=record.branch_id)

    def backfill_default_branches_for_existing_run_containers(self) -> None:
        self.backfill_run_containers_for_existing_simulation_runs()
        for legacy in self.list_simulation_runs():
            self.ensure_default_branch_for_simulation_run(simulation_run_id=legacy.run_id)

    @staticmethod
    def _to_branch_state(model: BranchStateModel) -> RunBranchStateRecord:
        return RunBranchStateRecord(
            branch_id=model.branch_id, run_id=model.run_id, head_checkpoint_id=model.head_checkpoint_id,
            current_season=model.current_season, current_week=model.current_week,
            current_event_id=model.current_event_id, current_event_sequence=model.current_event_sequence,
            state_schema_version=model.state_schema_version, status=model.status,
            metadata=_from_json(model.metadata_json),
        )

    def create_or_update_branch_state(self, record: RunBranchStateRecord) -> RunBranchStateRecord:
        with self._session_factory.begin() as session:
            model = session.get(BranchStateModel, record.branch_id)
            values = {
                "run_id": record.run_id, "head_checkpoint_id": record.head_checkpoint_id,
                "current_season": record.current_season, "current_week": record.current_week,
                "current_event_id": record.current_event_id, "current_event_sequence": record.current_event_sequence,
                "state_schema_version": record.state_schema_version, "status": record.status,
                "metadata_json": _to_json(record.metadata),
            }
            if model is None:
                session.add(BranchStateModel(branch_id=record.branch_id, **values))
            else:
                for field, value in values.items():
                    setattr(model, field, value)
        return self.get_branch_state(branch_id=record.branch_id)  # type: ignore[return-value]

    def get_branch_state(self, *, branch_id: str) -> RunBranchStateRecord | None:
        with self._session_factory() as session:
            model = session.get(BranchStateModel, branch_id)
            return self._to_branch_state(model) if model is not None else None

    def list_branch_states(self, *, run_id: str | None = None) -> list[RunBranchStateRecord]:
        with self._session_factory() as session:
            statement = select(BranchStateModel).order_by(BranchStateModel.branch_id)
            if run_id is not None:
                statement = statement.where(BranchStateModel.run_id == run_id)
            return [self._to_branch_state(model) for model in session.execute(statement).scalars()]

    def ensure_branch_state_for_branch(self, *, branch_id: str) -> RunBranchStateRecord | None:
        branch = self.get_run_branch(branch_id=branch_id)
        if branch is None:
            return None
        return self.ensure_branch_state_for_checkpoint(checkpoint_id=branch.head_checkpoint_id, branch=branch)

    def ensure_branch_state_for_checkpoint(
        self, *, checkpoint_id: str | None, branch: RunBranchRecord | None = None
    ) -> RunBranchStateRecord | None:
        if branch is None:
            if checkpoint_id is None:
                return None
            checkpoint = self.get_branch_checkpoint(checkpoint_id=checkpoint_id)
            if checkpoint is None:
                return None
            branch = self.get_run_branch(branch_id=checkpoint.branch_id)
        if branch is None:
            return None
        checkpoint = self.get_branch_checkpoint(checkpoint_id=checkpoint_id) if checkpoint_id is not None else None
        return self.create_or_update_branch_state(RunBranchStateRecord(
            branch_id=branch.branch_id, run_id=branch.run_id, head_checkpoint_id=checkpoint_id,
            current_season=checkpoint.season if checkpoint else None,
            current_week=checkpoint.week if checkpoint else None,
            current_event_id=checkpoint.event_id if checkpoint else None,
            current_event_sequence=checkpoint.event_sequence if checkpoint else None,
            state_schema_version="branch_state_v1", status=branch.status, metadata={},
        ))

    def backfill_branch_states_for_existing_branches(self) -> None:
        for branch in self.list_run_branches():
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)

    @staticmethod
    def canonical_json(payload: object) -> str:
        """Serialize deterministic JSON for payload hashes and checkpoint envelopes."""
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def checkpoint_content_hash(cls, payload: dict[str, object]) -> str:
        """Return a payload-only hash (for example, ``admin_actions_hash``)."""
        return hashlib.sha256(cls.canonical_json(payload).encode("utf-8")).hexdigest()

    @staticmethod
    def checkpoint_hash_envelope(record: BranchCheckpointRecord) -> dict[str, object]:
        """Return the deterministic, immutable fields protected by a checkpoint hash."""
        return {
            "checkpoint_id": record.checkpoint_id,
            "run_id": record.run_id,
            "branch_id": record.branch_id,
            "parent_checkpoint_id": record.parent_checkpoint_id,
            "sequence": record.sequence,
            "kind": record.kind,
            "season": record.season,
            "week": record.week,
            "event_id": record.event_id,
            "event_sequence": record.event_sequence,
            "command_id": record.command_id,
            "command_kind": record.command_kind,
            "command_boundary": record.command_boundary,
            "config_version": record.config_version,
            "config_fingerprint": record.config_fingerprint,
            "world_id": record.world_id,
            "world_fingerprint": record.world_fingerprint,
            "global_seed": record.global_seed,
            "branch_seed": record.branch_seed,
            "seed_namespace": record.seed_namespace,
            "payload_schema_version": record.payload_schema_version,
            "payload": record.payload,
        }

    @classmethod
    def checkpoint_envelope_content_hash(cls, record: BranchCheckpointRecord) -> str:
        """Return the SHA-256 hash of the full deterministic checkpoint envelope."""
        return hashlib.sha256(cls.canonical_json(cls.checkpoint_hash_envelope(record)).encode("utf-8")).hexdigest()

    @staticmethod
    def _to_branch_checkpoint(model: BranchCheckpointModel) -> BranchCheckpointRecord:
        return BranchCheckpointRecord(
            checkpoint_id=model.checkpoint_id, run_id=model.run_id, branch_id=model.branch_id,
            parent_checkpoint_id=model.parent_checkpoint_id, sequence=model.sequence, kind=model.kind,
            season=model.season, week=model.week, event_id=model.event_id, event_sequence=model.event_sequence,
            command_id=model.command_id, command_kind=model.command_kind, command_boundary=model.command_boundary,
            config_version=model.config_version, config_fingerprint=model.config_fingerprint, world_id=model.world_id,
            world_fingerprint=model.world_fingerprint, global_seed=model.global_seed, branch_seed=model.branch_seed,
            seed_namespace=_from_json(model.seed_namespace_json), payload_schema_version=model.payload_schema_version,
            content_hash_algorithm=model.content_hash_algorithm, content_hash=model.content_hash,
            payload=_from_json(model.payload_json),
        )

    def next_checkpoint_sequence(self, *, branch_id: str) -> int:
        with self._session_factory() as session:
            value = session.execute(select(func.max(BranchCheckpointModel.sequence)).where(BranchCheckpointModel.branch_id == branch_id)).scalar_one()
            return 1 if value is None else int(value) + 1

    def get_branch_checkpoint(self, *, checkpoint_id: str) -> BranchCheckpointRecord | None:
        with self._session_factory() as session:
            model = session.get(BranchCheckpointModel, checkpoint_id)
            return self._to_branch_checkpoint(model) if model is not None else None

    def get_branch_checkpoint_by_command_id(self, *, branch_id: str, command_id: str) -> BranchCheckpointRecord | None:
        with self._session_factory() as session:
            model = session.execute(select(BranchCheckpointModel).where(BranchCheckpointModel.branch_id == branch_id, BranchCheckpointModel.command_id == command_id)).scalar_one_or_none()
            return self._to_branch_checkpoint(model) if model is not None else None

    def get_initial_branch_checkpoint(self, *, branch_id: str) -> BranchCheckpointRecord | None:
        with self._session_factory() as session:
            model = session.execute(
                select(BranchCheckpointModel).where(
                    BranchCheckpointModel.branch_id == branch_id,
                    BranchCheckpointModel.kind == "initial",
                )
            ).scalar_one_or_none()
            return self._to_branch_checkpoint(model) if model is not None else None

    def list_branch_checkpoints(self, *, branch_id: str | None = None, run_id: str | None = None) -> list[BranchCheckpointRecord]:
        with self._session_factory() as session:
            statement = select(BranchCheckpointModel)
            if branch_id is not None: statement = statement.where(BranchCheckpointModel.branch_id == branch_id)
            if run_id is not None: statement = statement.where(BranchCheckpointModel.run_id == run_id)
            return [self._to_branch_checkpoint(model) for model in session.execute(statement.order_by(BranchCheckpointModel.branch_id, BranchCheckpointModel.sequence)).scalars()]

    def verify_branch_checkpoint_hash(self, *, checkpoint_id: str) -> bool:
        record = self.get_branch_checkpoint(checkpoint_id=checkpoint_id)
        return (
            record is not None
            and record.content_hash_algorithm == "sha256"
            and self.checkpoint_envelope_content_hash(record) == record.content_hash
        )

    def create_branch_checkpoint(self, record: BranchCheckpointRecord) -> BranchCheckpointRecord:
        if record.content_hash_algorithm != "sha256" or self.checkpoint_envelope_content_hash(record) != record.content_hash:
            raise ValueError("branch checkpoint content hash is invalid")
        with self._session_factory.begin() as session:
            existing = session.get(BranchCheckpointModel, record.checkpoint_id)
            if existing is not None:
                persisted = self._to_branch_checkpoint(existing)
                if persisted == record: return persisted
                raise ValueError(f"checkpoint_id {record.checkpoint_id} already exists with different content")
            by_command = session.execute(select(BranchCheckpointModel).where(BranchCheckpointModel.branch_id == record.branch_id, BranchCheckpointModel.command_id == record.command_id)).scalar_one_or_none()
            if by_command is not None: return self._to_branch_checkpoint(by_command)
            if record.kind == "initial":
                existing_initial = session.execute(
                    select(BranchCheckpointModel).where(
                        BranchCheckpointModel.branch_id == record.branch_id,
                        BranchCheckpointModel.kind == "initial",
                    )
                ).scalar_one_or_none()
                if existing_initial is not None:
                    raise ValueError(f"branch_id {record.branch_id} already has an initial checkpoint")
            expected = session.execute(select(func.max(BranchCheckpointModel.sequence)).where(BranchCheckpointModel.branch_id == record.branch_id)).scalar_one()
            if record.sequence != (1 if expected is None else int(expected) + 1): raise ValueError("branch checkpoint sequence must increase by one")
            if record.kind == "initial" and record.parent_checkpoint_id is not None: raise ValueError("initial checkpoint parent must be null")
            session.add(BranchCheckpointModel(
                checkpoint_id=record.checkpoint_id, run_id=record.run_id, branch_id=record.branch_id, parent_checkpoint_id=record.parent_checkpoint_id,
                sequence=record.sequence, kind=record.kind, season=record.season, week=record.week, event_id=record.event_id,
                event_sequence=record.event_sequence, command_id=record.command_id, command_kind=record.command_kind,
                command_boundary=record.command_boundary, config_version=record.config_version, config_fingerprint=record.config_fingerprint,
                world_id=record.world_id, world_fingerprint=record.world_fingerprint, global_seed=record.global_seed, branch_seed=record.branch_seed,
                seed_namespace_json=self.canonical_json(record.seed_namespace), payload_schema_version=record.payload_schema_version,
                content_hash_algorithm=record.content_hash_algorithm, content_hash=record.content_hash, payload_json=self.canonical_json(record.payload),
            ))
        return record

    def capture_initial_checkpoint_for_legacy_simulation_run(self, *, simulation_run_id: str, command_id: str | None = None) -> BranchCheckpointRecord:
        legacy = self.get_simulation_run(run_id=simulation_run_id)
        if legacy is None: raise KeyError(f"run_id {simulation_run_id} was not found")
        branch = self.ensure_default_branch_for_simulation_run(simulation_run_id=simulation_run_id)
        if branch is None: raise KeyError(f"default branch for run_id {simulation_run_id} was not found")
        state = self.load_season_state(run_id=simulation_run_id)
        if state is None: raise ValueError(f"run_id {simulation_run_id} has no season state")
        command_id = command_id or f"legacy-initial-capture:{simulation_run_id}"
        existing = self.get_branch_checkpoint_by_command_id(branch_id=branch.branch_id, command_id=command_id)
        if existing is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing
        existing_initial = self.get_initial_branch_checkpoint(branch_id=branch.branch_id)
        if existing_initial is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing_initial
        actions = [action.__dict__ for action in self.list_admin_actions(run_id=simulation_run_id)]
        seed_namespace = {"hierarchy": ["global", "season", "entries", "draws", "tournament_progression"], "global_seed": legacy.seed, "branch_seed": branch.branch_seed}
        payload: dict[str, object] = {"fork_capability": "not_forkable_player_state_not_migrated", "capture_mode": "legacy_initial_capture_only", "payload_schema_version": "branch_checkpoint_payload_v1", "run_id": branch.run_id, "branch_id": branch.branch_id, "legacy_simulation_run_id": simulation_run_id, "simulation_run": legacy.__dict__, "season_state": state.model_dump(mode="json"), "admin": {"actions": actions, "admin_actions_hash": self.checkpoint_content_hash({"actions": actions})}, "provenance": {"world_id": legacy.world_id, "world_fingerprint": legacy.world_generation_fingerprint, "config_version": legacy.config_version, "config_fingerprint": legacy.config_fingerprint, "global_seed": legacy.seed, "branch_seed": branch.branch_seed, "seed_namespace": seed_namespace}, "limitations": {"player_state": "hash_only_or_not_migrated", "prospects": "legacy_run_scoped_not_captured_as_durable_identity", "forkable": False}}
        separator = "\x00"
        checkpoint_identity = separator.join([branch.branch_id, command_id])
        checkpoint_suffix = hashlib.sha256(checkpoint_identity.encode("utf-8")).hexdigest()[:24]
        checkpoint_id = f"checkpoint-{checkpoint_suffix}"
        checkpoint_without_hash = BranchCheckpointRecord(
            checkpoint_id=checkpoint_id,
            run_id=branch.run_id,
            branch_id=branch.branch_id,
            parent_checkpoint_id=None,
            sequence=self.next_checkpoint_sequence(branch_id=branch.branch_id),
            kind="initial",
            season=legacy.season,
            week=None,
            event_id=None,
            event_sequence=None,
            command_id=command_id,
            command_kind="capture_initial",
            command_boundary="after_legacy_state_load",
            config_version=legacy.config_version,
            config_fingerprint=legacy.config_fingerprint,
            world_id=legacy.world_id,
            world_fingerprint=legacy.world_generation_fingerprint,
            global_seed=legacy.seed,
            branch_seed=branch.branch_seed,
            seed_namespace=seed_namespace,
            payload_schema_version="branch_checkpoint_payload_v1",
            content_hash_algorithm="sha256",
            content_hash="",
            payload=payload,
        )
        checkpoint = BranchCheckpointRecord(
            **{
                **checkpoint_without_hash.__dict__,
                "content_hash": self.checkpoint_envelope_content_hash(checkpoint_without_hash),
            }
        )
        created = self.create_branch_checkpoint(checkpoint)
        with self._session_factory.begin() as session:
            model = session.get(RunBranchModel, branch.branch_id)
            if model is not None and model.head_checkpoint_id is None: model.head_checkpoint_id = created.checkpoint_id
        self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        return created

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
                world_id=model.world_id or OFFICIAL_FAX_WORLD_ID,
                world_generation_fingerprint=model.world_generation_fingerprint,
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
                world_id=model.world_id or OFFICIAL_FAX_WORLD_ID,
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
                    world_id=model.world_id or OFFICIAL_FAX_WORLD_ID,
                    world_generation_fingerprint=model.world_generation_fingerprint,
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
                        dampener_json=_to_json(record.dampener),
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
                    dampener=_from_json(model.dampener_json or "{}"),
                )
                for model in session.execute(statement).scalars().all()
            ]


    def upsert_run_prospects(self, records: list[RunProspectRecord]) -> None:
        with self._session_factory.begin() as session:
            for record in records:
                statement: Select[tuple[RunProspectModel]] = select(RunProspectModel).where(
                    RunProspectModel.run_id == record.run_id,
                    RunProspectModel.prospect_id == record.prospect_id,
                )
                model = session.execute(statement).scalar_one_or_none()
                payload = dict(
                    world_id=record.world_id,
                    season_start_year=record.season_start_year,
                    season_label=record.season_label,
                    season_week=record.season_week,
                    calendar_year=record.calendar_year,
                    year_week=record.year_week,
                    birth_year=record.birth_year,
                    birth_year_week=record.birth_year_week,
                    age=record.age,
                    country_code=record.country_code.upper(),
                    country_name=record.country_name,
                    status=record.status,
                    source_type=record.source_type,
                    cohort_policy_version=record.cohort_policy_version,
                    profile_version=record.profile_version,
                    first_name=record.first_name,
                    last_name=record.last_name,
                    display_name=record.display_name,
                    short_name=record.short_name,
                    identity_seed=record.identity_seed,
                    profile_seed=record.profile_seed,
                    development_seed=record.development_seed,
                    potential_seed=record.potential_seed,
                    trait_seed=record.trait_seed,
                    profile_json=_to_json(record.profile_json),
                    development_json=_to_json(record.development_json),
                    potential_json=_to_json(record.potential_json),
                    trait_json=_to_json(record.trait_json),
                )
                if model is None:
                    session.add(RunProspectModel(prospect_id=record.prospect_id, run_id=record.run_id, **payload))
                else:
                    for key, value in payload.items():
                        setattr(model, key, value)

    def delete_run_prospects_by_ids(self, *, run_id: str, prospect_ids: list[str]) -> None:
        """Delete only the explicitly identified prospects for a run."""
        if not prospect_ids:
            return
        with self._session_factory.begin() as session:
            session.query(RunProspectModel).filter(
                RunProspectModel.run_id == run_id,
                RunProspectModel.prospect_id.in_(prospect_ids),
            ).delete(synchronize_session=False)

    def list_run_prospects(
        self,
        *,
        run_id: str,
        country_code: str | None = None,
        status: str | None = None,
        season_start_year: int | None = None,
        season_week: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RunProspectRecord]:
        with self._session_factory() as session:
            statement: Select[tuple[RunProspectModel]] = select(RunProspectModel).where(RunProspectModel.run_id == run_id)
            if country_code is not None:
                statement = statement.where(RunProspectModel.country_code == country_code.upper())
            if status is not None:
                statement = statement.where(RunProspectModel.status == status)
            if season_start_year is not None:
                statement = statement.where(RunProspectModel.season_start_year == season_start_year)
            if season_week is not None:
                statement = statement.where(RunProspectModel.season_week == season_week)
            statement = statement.order_by(RunProspectModel.season_start_year.asc(), RunProspectModel.season_week.asc(), RunProspectModel.country_code.asc(), RunProspectModel.prospect_id.asc())
            if offset > 0:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)
            return [self._to_run_prospect_record(model) for model in session.execute(statement).scalars().all()]

    def count_run_prospects(self, *, run_id: str, country_code: str | None = None, status: str | None = None, season_start_year: int | None = None, season_week: int | None = None) -> int:
        with self._session_factory() as session:
            statement = select(func.count()).select_from(RunProspectModel).where(RunProspectModel.run_id == run_id)
            if country_code is not None:
                statement = statement.where(RunProspectModel.country_code == country_code.upper())
            if status is not None:
                statement = statement.where(RunProspectModel.status == status)
            if season_start_year is not None:
                statement = statement.where(RunProspectModel.season_start_year == season_start_year)
            if season_week is not None:
                statement = statement.where(RunProspectModel.season_week == season_week)
            return int(session.execute(statement).scalar_one())

    def get_run_prospect(self, *, run_id: str, prospect_id: str) -> RunProspectRecord | None:
        with self._session_factory() as session:
            statement = select(RunProspectModel).where(RunProspectModel.run_id == run_id, RunProspectModel.prospect_id == prospect_id)
            model = session.execute(statement).scalar_one_or_none()
            return None if model is None else self._to_run_prospect_record(model)

    @staticmethod
    def _to_run_prospect_record(model: RunProspectModel) -> RunProspectRecord:
        return RunProspectRecord(
            prospect_id=model.prospect_id, run_id=model.run_id, world_id=model.world_id, season_start_year=model.season_start_year,
            season_label=model.season_label, season_week=model.season_week, calendar_year=model.calendar_year, year_week=model.year_week,
            birth_year=model.birth_year, birth_year_week=model.birth_year_week, age=model.age, country_code=model.country_code,
            country_name=model.country_name, status=model.status, source_type=model.source_type, cohort_policy_version=model.cohort_policy_version,
            profile_version=model.profile_version, first_name=model.first_name, last_name=model.last_name, display_name=model.display_name,
            short_name=model.short_name, identity_seed=model.identity_seed, profile_seed=model.profile_seed, development_seed=model.development_seed,
            potential_seed=model.potential_seed, trait_seed=model.trait_seed, profile_json=_from_json(model.profile_json or "{}"),
            development_json=_from_json(model.development_json or "{}"), potential_json=_from_json(model.potential_json or "{}"), trait_json=_from_json(model.trait_json or "{}"),
        )

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
                        origin_source_type=record.origin_source_type,
                        origin_quality_band=record.origin_quality_band,
                        origin_override_id=record.origin_override_id,
                        origin_season=record.origin_season,
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
            try:
                models = session.execute(statement).scalars().all()
            except OperationalError:
                return []
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
                    origin_source_type=model.origin_source_type,
                    origin_quality_band=model.origin_quality_band,
                    origin_override_id=model.origin_override_id,
                    origin_season=model.origin_season,
                )
                for model in models
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
                origin_source_type=model.origin_source_type,
                origin_quality_band=model.origin_quality_band,
                origin_override_id=model.origin_override_id,
                origin_season=model.origin_season,
            )

    def list_generated_player_provenance_history(
        self,
        *,
        season_lt: int,
        season_gte: int | None = None,
        country_code: str | None = None,
        source_type: str | None = None,
    ) -> list[PersistedGeneratedPlayerProvenanceRecord]:
        with self._session_factory() as session:
            statement: Select[tuple[RunGeneratedPlayerProvenanceModel]] = select(RunGeneratedPlayerProvenanceModel).where(
                RunGeneratedPlayerProvenanceModel.season < season_lt
            )
            if season_gte is not None:
                statement = statement.where(RunGeneratedPlayerProvenanceModel.season >= season_gte)
            if country_code is not None:
                statement = statement.where(RunGeneratedPlayerProvenanceModel.country_code == country_code.upper())
            if source_type is not None:
                statement = statement.where(RunGeneratedPlayerProvenanceModel.source_type == source_type)
            statement = statement.order_by(
                RunGeneratedPlayerProvenanceModel.season.desc(),
                RunGeneratedPlayerProvenanceModel.country_code.asc(),
                RunGeneratedPlayerProvenanceModel.player_id.asc(),
            )
            try:
                models = session.execute(statement).scalars().all()
            except OperationalError:
                return []
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
                    origin_source_type=model.origin_source_type,
                    origin_quality_band=model.origin_quality_band,
                    origin_override_id=model.origin_override_id,
                    origin_season=model.origin_season,
                )
                for model in models
            ]

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

    def replace_next_season_players(
        self,
        *,
        run_id: str,
        from_season: int,
        to_season: int,
        next_player_states: list[NextSeasonPlayerState],
    ) -> None:
        with self._session_factory.begin() as session:
            session.query(NextSeasonPlayerModel).filter(
                NextSeasonPlayerModel.run_id == run_id,
                NextSeasonPlayerModel.to_season == to_season,
            ).delete()
            for next_state in next_player_states:
                session.add(
                    NextSeasonPlayerModel(
                        run_id=run_id,
                        from_season=from_season,
                        to_season=to_season,
                        player_id=next_state.player.player_id,
                        payload_json=_to_json(next_state.model_dump()),
                    )
                )

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
