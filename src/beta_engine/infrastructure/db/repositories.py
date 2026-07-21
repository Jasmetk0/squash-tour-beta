"""Persistence adapters for season state, snapshots, and tournament history."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, Select, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.season_models import RaceSnapshot, RankingSnapshot, SeasonState, TournamentSimulationResult
from beta_engine.domain.careers import NextSeasonPlayerState, PlayerSeasonTransition
from beta_engine.domain.finals import FinalsQualificationResult, FinalsResult
from beta_engine.domain.rankings import CompletedTournamentPointsInput

from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID
from beta_engine.infrastructure.db.models import (
    AdminActionModel,
    BranchForkCommandModel,
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
from beta_engine.infrastructure.db.checkpoint_boundaries import (
    BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_COMPLETED_EVENT_LEGACY_STATE,
    BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_COMPLETED_WEEK_LEGACY_STATE,
    BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_CURRENT_LEGACY_STATE,
    BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_ADMIN_ACTION_LEGACY_STATE,
    BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_INITIAL,
    BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_SEASON_ROLLOVER_LEGACY_STATE,
    BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_BOOTSTRAP_START_LEGACY_STATE,
    BRANCH_CHECKPOINT_COMMAND_KIND_FORK_BRANCH,
    BRANCH_CHECKPOINT_COMMAND_BOUNDARY_AFTER_ATOMIC_FORK_MATERIALIZATION,
    BRANCH_CHECKPOINT_KIND_BRANCH_FORK_START,
    BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE,
    BRANCH_CHECKPOINT_KIND_ADMIN_ACTION_APPLIED,
    BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED,
    BRANCH_CHECKPOINT_KIND_INITIAL,
    BRANCH_CHECKPOINT_KIND_SEASON_ROLLOVER,
    BRANCH_CHECKPOINT_KIND_BOOTSTRAP_START,
    BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED,
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
class BranchExecutionTarget:
    """Read-only legacy execution namespace bound to an executable Branch.

    This compatibility target deliberately contains no mutable simulation state.
    Future branch commands can resolve a Branch first, then pass only
    ``legacy_simulation_run_id`` to the unchanged legacy simulation services.
    """

    branch_id: str
    product_run_id: str
    legacy_simulation_run_id: str
    branch_status: str
    branch_read_only: bool
    is_official: bool
    display_name: str
    branch_seed: int | None
    head_checkpoint_id: str | None


class BranchExecutionTargetResolutionError(ValueError):
    """Raised when a Branch cannot safely target legacy simulation execution."""


@dataclass(frozen=True)
class LegacyRunCloneInventorySection:
    """Deterministic, bounded inventory of one legacy-run persistence section."""

    name: str
    count: int
    content_hash: str
    copy_policy: str = "copy"


@dataclass(frozen=True)
class LegacyRunCloneInventory:
    """Read-only persistence inventory required by a future legacy-run clone."""

    source_legacy_simulation_run_id: str
    source_product_run_id: str | None
    source_branch_id: str | None
    source_checkpoint_id: str | None
    source_checkpoint_kind: str | None
    season: int | None
    week: int | None
    next_event_index: int | None
    sections: tuple[LegacyRunCloneInventorySection, ...]
    inventory_hash: str


@dataclass(frozen=True)
class LegacyRunClonePreflightResult:
    """Fail-closed readiness result; this does not create, fork, or restore anything."""

    inventory: LegacyRunCloneInventory
    clone_safe: bool
    unsupported_reasons: tuple[str, ...]


class LegacyRunClonePreflightError(ValueError):
    """Raised when the source legacy simulation run cannot be inspected."""


class UnsupportedCloneSourceError(LegacyRunClonePreflightError):
    """Raised when an explicit clone source does not exist."""


class LegacyRunCloneError(ValueError):
    """Raised when a legacy namespace clone cannot be completed safely."""


class UnsafeLegacyRunCloneSourceError(LegacyRunCloneError):
    """Raised when clone preflight or checkpoint validation fails closed."""


class LegacyRunCloneTargetExistsError(LegacyRunCloneError):
    """Raised when a target legacy simulation-run namespace already exists."""


class BranchForkError(ValueError):
    """Raised when an internal atomic Branch fork cannot complete."""


class BranchForkValidationError(BranchForkError):
    """Raised when a fork command violates a fail-closed invariant."""


class BranchForkTargetExistsError(BranchForkError):
    """Raised when a requested Branch or legacy namespace target already exists."""


class BranchForkIdempotencyConflictError(BranchForkError):
    """Raised when a command id is reused with different content."""


class BranchForkSourceStateMismatchError(BranchForkValidationError):
    """Raised when persisted source state cannot prove the requested fork boundary."""


@dataclass(frozen=True)
class LegacyRunCloneSectionResult:
    name: str
    count: int


@dataclass(frozen=True)
class LegacyRunCloneResult:
    source_legacy_simulation_run_id: str
    target_legacy_simulation_run_id: str
    source_branch_id: str | None
    source_checkpoint_id: str | None
    source_checkpoint_kind: str | None
    source_inventory_hash: str
    target_inventory_hash: str
    cloned_section_counts: tuple[LegacyRunCloneSectionResult, ...]
    normalized_clone_equivalence_hash: str
    source_product_run_id: str | None
    target_product_run_id: str | None
    created_mapping: bool = False
    created_branch: bool = False


@dataclass(frozen=True)
class ForkRunBranchCommand:
    product_run_id: str; source_branch_id: str; source_checkpoint_id: str
    target_branch_id: str; target_branch_display_name: str
    target_legacy_simulation_run_id: str; target_branch_seed: int; command_id: str


@dataclass(frozen=True)
class ForkRunBranchResult:
    product_run_id: str; source_branch_id: str; source_checkpoint_id: str
    target_branch_id: str; target_legacy_simulation_run_id: str; target_checkpoint_id: str
    target_branch_seed: int; source_inventory_hash: str; normalized_clone_equivalence_hash: str
    request_fingerprint: str; idempotent_replay: bool
    created_mapping: bool = False
    official_branch_changed: bool = False


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
            self._ensure_branch_checkpoint_boundary_indexes(connection=connection)
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
            self._ensure_column(connection=connection, table_name="run_generated_player_provenance", column_name="override_id", column_type="TEXT")
            self._ensure_column(connection=connection, table_name="run_generated_player_provenance", column_name="origin_source_type", column_type="TEXT")
            self._ensure_column(connection=connection, table_name="run_generated_player_provenance", column_name="origin_quality_band", column_type="TEXT")
            self._ensure_column(connection=connection, table_name="run_generated_player_provenance", column_name="origin_override_id", column_type="TEXT")
            self._ensure_column(connection=connection, table_name="run_generated_player_provenance", column_name="origin_season", column_type="INTEGER")
            self._ensure_column(connection=connection, table_name="run_talent_country_allocations", column_name="dampener_json", column_type="TEXT")
            self._ensure_column(connection=connection, table_name="simulation_runs", column_name="world_id", column_type="TEXT")
            self._ensure_column(connection=connection, table_name="simulation_runs", column_name="world_generation_fingerprint", column_type="TEXT")

    @staticmethod
    def _ensure_branch_checkpoint_boundary_indexes(*, connection) -> None:
        """Add partial checkpoint-boundary indexes to pre-R3G SQLite databases.

        ``CREATE INDEX IF NOT EXISTS`` keeps normal bootstrap idempotent. A
        pre-existing duplicate boundary prevents SQLite from adding its unique
        index; preserve that data rather than rewriting historical records.
        """
        indexes = (
            ("uq_branch_checkpoints_one_initial_per_branch", "branch_id", BRANCH_CHECKPOINT_KIND_INITIAL),
            ("uq_branch_checkpoints_one_event_completed_per_branch_event_sequence", "branch_id, event_sequence", BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED),
            ("uq_branch_checkpoints_one_week_completed_per_branch_season_week", "branch_id, season, week", BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED),
        )
        for name, columns, kind in indexes:
            try:
                connection.execute(text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON branch_checkpoints ({columns}) WHERE kind = '{kind}'"
                ))
            except IntegrityError:
                # Repository validation reports a clear conflict on later use.
                continue

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

    def get_branch_execution_target(self, *, branch_id: str) -> BranchExecutionTarget:
        """Resolve a Branch to its existing legacy simulation execution namespace.

        The resolver is intentionally read-only.  It neither treats BranchState as
        simulation state nor changes any branch, checkpoint, or legacy-run record.
        ``active`` is the sole executable branch status currently produced by the
        branch foundation, so unknown/future status values fail closed.
        """
        with self._session_factory() as session:
            branch = session.get(RunBranchModel, branch_id)
            if branch is None:
                raise KeyError(f"run branch {branch_id} was not found")

            container = session.get(RunContainerModel, branch.run_id)
            if container is None:
                raise BranchExecutionTargetResolutionError(
                    f"run branch {branch_id} references missing product run {branch.run_id}"
                )

            legacy_simulation_run_id = (branch.legacy_simulation_run_id or "").strip()
            if not legacy_simulation_run_id:
                raise BranchExecutionTargetResolutionError(
                    f"run branch {branch_id} has no legacy simulation run binding"
                )
            if session.get(SimulationRunModel, legacy_simulation_run_id) is None:
                raise BranchExecutionTargetResolutionError(
                    f"run branch {branch_id} references missing legacy simulation run {legacy_simulation_run_id}"
                )
            if branch.read_only:
                raise BranchExecutionTargetResolutionError(
                    f"run branch {branch_id} is read-only and cannot execute simulation commands"
                )
            if branch.status != "active":
                raise BranchExecutionTargetResolutionError(
                    f"run branch {branch_id} has non-executable status {branch.status!r}"
                )

            return BranchExecutionTarget(
                branch_id=branch.branch_id,
                product_run_id=container.run_id,
                legacy_simulation_run_id=legacy_simulation_run_id,
                branch_status=branch.status,
                branch_read_only=bool(branch.read_only),
                is_official=branch.branch_id == container.official_branch_id,
                display_name=branch.display_name,
                branch_seed=branch.branch_seed,
                head_checkpoint_id=branch.head_checkpoint_id,
            )

    @staticmethod
    def _clone_inventory_value(value: object) -> object:
        """Normalize durable values without relying on database row identity."""
        if isinstance(value, str) and (value.startswith("{") or value.startswith("[")):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value

    @classmethod
    def _clone_inventory_section(
        cls, *, name: str, models: list[object], copy_policy: str = "copy"
    ) -> LegacyRunCloneInventorySection:
        rows = [
            {
                column.name: cls._clone_inventory_value(getattr(model, column.name))
                for column in model.__table__.columns
                if column.name != "id"
            }
            for model in models
        ]
        # Sorting canonicalized rows makes the inventory independent of SQL row order.
        rows.sort(key=lambda row: _to_json(row))
        content_hash = hashlib.sha256(_to_json({"name": name, "rows": rows}).encode("utf-8")).hexdigest()
        return LegacyRunCloneInventorySection(name=name, count=len(rows), content_hash=content_hash, copy_policy=copy_policy)

    def inspect_legacy_run_clone_inventory(
        self,
        *,
        simulation_run_id: str,
        branch_id: str | None = None,
        checkpoint_id: str | None = None,
    ) -> LegacyRunClonePreflightResult:
        """Inspect, but never copy or mutate, a future legacy-run clone source.

        R4C0 deliberately treats checkpoints as readiness context only. Their
        existing payload limitations remain authoritative: no checkpoint is
        restored or claimed to be forkable by this inspection.
        """
        with self._session_factory() as session:
            simulation_run = session.get(SimulationRunModel, simulation_run_id)
            if simulation_run is None:
                raise UnsupportedCloneSourceError(f"legacy simulation run {simulation_run_id} was not found")

            mapping = session.get(LegacySimulationRunMappingModel, simulation_run_id)
            product_run_id = mapping.run_id if mapping is not None else None
            selected_branch = session.get(RunBranchModel, branch_id) if branch_id else None
            if selected_branch is None and branch_id is None:
                selected_branch = session.execute(
                    select(RunBranchModel).where(RunBranchModel.legacy_simulation_run_id == simulation_run_id).order_by(RunBranchModel.branch_id)
                ).scalars().first()
            resolved_branch_id = selected_branch.branch_id if selected_branch is not None else branch_id
            checkpoint = session.get(BranchCheckpointModel, checkpoint_id) if checkpoint_id else None

            scoped = lambda model: session.execute(select(model).where(model.run_id == simulation_run_id)).scalars().all()
            sections = [
                self._clone_inventory_section(name="simulation_run", models=[simulation_run]),
                self._clone_inventory_section(name="season_state", models=scoped(SeasonStateModel)),
                self._clone_inventory_section(name="completed_events", models=scoped(CompletedEventModel)),
                self._clone_inventory_section(name="completed_event_metadata", models=scoped(CompletedEventMetadataModel)),
                self._clone_inventory_section(name="completed_tournament_inputs", models=scoped(CompletedTournamentInputModel)),
                self._clone_inventory_section(name="ranking_snapshots", models=scoped(RankingSnapshotModel)),
                self._clone_inventory_section(name="race_snapshots", models=scoped(RaceSnapshotModel)),
                self._clone_inventory_section(name="finals_qualification", models=scoped(FinalsQualificationModel)),
                self._clone_inventory_section(name="finals_results", models=scoped(FinalsResultModel)),
                self._clone_inventory_section(name="admin_actions", models=scoped(AdminActionModel)),
                self._clone_inventory_section(name="season_rollovers", models=scoped(SeasonRolloverModel)),
                self._clone_inventory_section(name="player_season_transitions", models=scoped(PlayerSeasonTransitionModel)),
                self._clone_inventory_section(name="next_season_players", models=scoped(NextSeasonPlayerModel)),
                self._clone_inventory_section(name="run_talent_plans", models=scoped(RunTalentPlanModel)),
                self._clone_inventory_section(name="run_talent_country_allocations", models=scoped(RunTalentCountryAllocationModel)),
                self._clone_inventory_section(name="run_generated_player_provenance", models=scoped(RunGeneratedPlayerProvenanceModel)),
                self._clone_inventory_section(name="run_prospects", models=scoped(RunProspectModel), copy_policy="unsupported"),
            ]
            if product_run_id is not None:
                product_scoped = lambda model: session.execute(select(model).where(model.run_id == product_run_id)).scalars().all()
                sections.extend([
                    self._clone_inventory_section(name="run_branches", models=product_scoped(RunBranchModel), copy_policy="excluded_metadata"),
                    self._clone_inventory_section(name="branch_states", models=product_scoped(BranchStateModel), copy_policy="excluded_metadata"),
                    self._clone_inventory_section(name="branch_checkpoints", models=product_scoped(BranchCheckpointModel), copy_policy="excluded_metadata"),
                ])
            else:
                for name in ("run_branches", "branch_states", "branch_checkpoints"):
                    sections.append(self._clone_inventory_section(name=name, models=[], copy_policy="excluded_metadata"))

            state = session.get(SeasonStateModel, simulation_run_id)
            reasons: list[str] = []
            if state is None:
                reasons.append("season_state_missing")
            elif state.active_tournament_json not in (None, "", "null", "{}", "[]"):
                reasons.append("active_tournament_present")
            if branch_id is not None:
                if selected_branch is None:
                    reasons.append("source_branch_not_found")
                elif selected_branch.legacy_simulation_run_id != simulation_run_id:
                    reasons.append("source_branch_legacy_simulation_run_mismatch")
                elif product_run_id is not None and selected_branch.run_id != product_run_id:
                    reasons.append("source_branch_product_run_mismatch")
            if checkpoint_id is not None:
                if checkpoint is None:
                    reasons.append("source_checkpoint_not_found")
                else:
                    if checkpoint.kind not in {BRANCH_CHECKPOINT_KIND_INITIAL, BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE}:
                        reasons.append(f"checkpoint_kind_{checkpoint.kind}_is_not_clone_safe_yet")
                    if product_run_id is None or checkpoint.run_id != product_run_id:
                        reasons.append("source_checkpoint_product_run_mismatch")
                    if branch_id is not None and (selected_branch is None or checkpoint.branch_id != selected_branch.branch_id):
                        reasons.append("source_checkpoint_branch_mismatch")
            prospects = next(section for section in sections if section.name == "run_prospects")
            if prospects.count:
                reasons.append("run_prospects_are_legacy_run_scoped_and_not_clone_safe_yet")

            checkpoint_kind = checkpoint.kind if checkpoint is not None else None
            inventory_fields = {
                "source_legacy_simulation_run_id": simulation_run_id,
                "source_product_run_id": product_run_id,
                "source_branch_id": resolved_branch_id,
                "source_checkpoint_id": checkpoint_id,
                "source_checkpoint_kind": checkpoint_kind,
                "season": state.season if state else simulation_run.season,
                "week": checkpoint.week if checkpoint else None,
                "next_event_index": state.next_event_index if state else None,
                "sections": tuple(sections),
            }
            inventory_hash_payload = {**inventory_fields, "sections": [section.__dict__ for section in sections]}
            inventory = LegacyRunCloneInventory(
                **inventory_fields,
                inventory_hash=hashlib.sha256(_to_json(inventory_hash_payload).encode("utf-8")).hexdigest(),
            )
            return LegacyRunClonePreflightResult(inventory=inventory, clone_safe=not reasons, unsupported_reasons=tuple(reasons))

    @classmethod
    def _normalized_clone_content_hash(
        cls, *, session: Session, run_id: str, expected_clone_seed: int | None = None
    ) -> str:
        """Hash all cloned durable data after normalizing namespace/provenance."""
        models = (
            SimulationRunModel, SeasonStateModel, CompletedEventModel, CompletedEventMetadataModel,
            CompletedTournamentInputModel, RankingSnapshotModel, RaceSnapshotModel,
            FinalsQualificationModel, FinalsResultModel, AdminActionModel, SeasonRolloverModel,
            PlayerSeasonTransitionModel, NextSeasonPlayerModel, RunTalentPlanModel,
            RunTalentCountryAllocationModel, RunGeneratedPlayerProvenanceModel,
        )
        sections: dict[str, list[dict[str, object]]] = {}
        for model in models:
            rows = session.execute(select(model).where(model.run_id == run_id)).scalars().all()
            canonical_rows = []
            for row in rows:
                item = {
                    column.name: cls._clone_inventory_value(getattr(row, column.name))
                    for column in model.__table__.columns if column.name != "id"
                }
                item["run_id"] = "<legacy-run>"
                if model is SimulationRunModel:
                    # These are intentional target-clone provenance differences.
                    item["source_type"] = "branch_clone"
                    item["parent_run_id"] = "<legacy-run>"
                    if expected_clone_seed is not None:
                        item["seed"] = expected_clone_seed
                canonical_rows.append(item)
            sections[model.__tablename__] = sorted(canonical_rows, key=_to_json)
        return hashlib.sha256(_to_json(sections).encode("utf-8")).hexdigest()

    def _clone_legacy_simulation_run_namespace_in_session(
        self, *, session: Session, source_simulation_run_id: str, target_simulation_run_id: str,
        target_seed: int | None = None, preserve_source_seed: bool = False,
    ) -> tuple[SimulationRunModel, SeasonStateModel, str]:
        """Copy a legacy namespace without opening or committing a transaction."""
        if session.get(SimulationRunModel, target_simulation_run_id) is not None:
            raise BranchForkTargetExistsError(f"target legacy simulation run {target_simulation_run_id} already exists")
        source_run = session.get(SimulationRunModel, source_simulation_run_id)
        source_state = session.get(SeasonStateModel, source_simulation_run_id)
        if source_run is None or source_state is None:
            raise BranchForkSourceStateMismatchError("source simulation run or season state is missing")
        copy_models = (CompletedEventModel, CompletedEventMetadataModel, CompletedTournamentInputModel,
            RankingSnapshotModel, RaceSnapshotModel, FinalsQualificationModel, FinalsResultModel,
            AdminActionModel, SeasonRolloverModel, PlayerSeasonTransitionModel, NextSeasonPlayerModel,
            RunTalentPlanModel, RunTalentCountryAllocationModel, RunGeneratedPlayerProvenanceModel)
        run_values = {column.name: getattr(source_run, column.name) for column in SimulationRunModel.__table__.columns}
        run_values.update({"run_id": target_simulation_run_id, "seed": source_run.seed if preserve_source_seed else (target_seed if target_seed is not None else source_run.seed), "parent_run_id": source_simulation_run_id, "source_type": "branch_clone"})
        target_run = SimulationRunModel(**run_values); session.add(target_run)
        state_values = {column.name: getattr(source_state, column.name) for column in SeasonStateModel.__table__.columns}; state_values["run_id"] = target_simulation_run_id
        target_state = SeasonStateModel(**state_values); session.add(target_state)
        for model in copy_models:
            for row in session.execute(select(model).where(model.run_id == source_simulation_run_id).order_by(*model.__table__.primary_key.columns)).scalars():
                values = {column.name: getattr(row, column.name) for column in model.__table__.columns if column.name != "id"}; values["run_id"] = target_simulation_run_id
                session.add(model(**values))
        session.flush()
        expected = self._normalized_clone_content_hash(session=session, run_id=source_simulation_run_id, expected_clone_seed=source_run.seed if preserve_source_seed else (target_seed if target_seed is not None else source_run.seed))
        actual = self._normalized_clone_content_hash(session=session, run_id=target_simulation_run_id)
        if actual != expected:
            raise LegacyRunCloneError("cloned namespace failed normalized durable-content equivalence verification")
        return target_run, target_state, actual

    def _season_state_payload_in_session(self, *, session: Session, model: SeasonStateModel) -> dict[str, object]:
        """Return the canonical SeasonState payload without opening a second Session."""
        completed_inputs = self._load_completed_inputs(session=session, run_id=model.run_id)
        return SeasonState.model_validate({"season": model.season, "ordered_events": _from_json(model.ordered_events_json), "next_event_index": model.next_event_index, "completed_event_ids": _from_json(model.completed_event_ids_json), "completed_tournament_inputs": [payload.model_dump() for payload in completed_inputs], "ranking_snapshot": _from_json(model.ranking_snapshot_json) if model.ranking_snapshot_json else None, "race_snapshot": _from_json(model.race_snapshot_json) if model.race_snapshot_json else None, "active_tournament": _from_json(model.active_tournament_json) if model.active_tournament_json else None}).model_dump(mode="json")

    def clone_legacy_simulation_run_namespace(
        self,
        *,
        source_simulation_run_id: str,
        target_simulation_run_id: str,
        source_branch_id: str | None = None,
        source_checkpoint_id: str | None = None,
        target_seed: int | None = None,
    ) -> LegacyRunCloneResult:
        """Transactionally copy a safe legacy-run namespace without product metadata.

        This is deliberately clone infrastructure, not a branch fork or checkpoint
        restore operation.  The target is an unmapped legacy simulation run.
        """
        if not target_simulation_run_id or not target_simulation_run_id.strip():
            raise LegacyRunCloneError("target legacy simulation run id must not be empty")
        if target_simulation_run_id == source_simulation_run_id:
            raise LegacyRunCloneError("target legacy simulation run id must differ from source")
        preflight = self.inspect_legacy_run_clone_inventory(
            simulation_run_id=source_simulation_run_id,
            branch_id=source_branch_id,
            checkpoint_id=source_checkpoint_id,
        )
        if not preflight.clone_safe:
            raise UnsafeLegacyRunCloneSourceError(
                "legacy simulation run is not clone safe: " + ", ".join(preflight.unsupported_reasons)
            )

        with self._session_factory.begin() as session:
            if session.get(SimulationRunModel, target_simulation_run_id) is not None:
                raise LegacyRunCloneTargetExistsError(
                    f"target legacy simulation run {target_simulation_run_id} already exists"
                )
            source_run = session.get(SimulationRunModel, source_simulation_run_id)
            source_state = session.get(SeasonStateModel, source_simulation_run_id)
            if source_run is None or source_state is None:
                # The source may have changed since the separate read-only preflight.
                raise UnsafeLegacyRunCloneSourceError("source changed after clone preflight")
            if source_checkpoint_id is not None:
                checkpoint = session.get(BranchCheckpointModel, source_checkpoint_id)
                branch = session.get(RunBranchModel, source_branch_id) if source_branch_id else None
                if checkpoint is None:
                    raise UnsafeLegacyRunCloneSourceError("source checkpoint no longer exists")
                if source_branch_id is not None:
                    effective_head = (session.get(BranchStateModel, source_branch_id).head_checkpoint_id
                                      if session.get(BranchStateModel, source_branch_id) is not None
                                      else branch.head_checkpoint_id if branch is not None else None)
                    if effective_head != checkpoint.checkpoint_id:
                        raise UnsafeLegacyRunCloneSourceError("source checkpoint is not the current effective branch head")
                if checkpoint.kind == BRANCH_CHECKPOINT_KIND_INITIAL:
                    if source_state.next_event_index != 0 or source_state.active_tournament_json not in (None, "", "null", "{}", "[]") or session.execute(select(CompletedEventModel).where(CompletedEventModel.run_id == source_simulation_run_id)).scalars().first() is not None:
                        raise UnsafeLegacyRunCloneSourceError("initial checkpoint source is no longer at season start")
                elif checkpoint.kind == BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE:
                    payload = _from_json(checkpoint.payload_json)
                    captured = payload.get("season_state") if isinstance(payload, dict) else None
                    current = self._season_state_payload_in_session(session=session, model=source_state)
                    if not isinstance(captured, dict) or _to_json(captured) != _to_json(current):
                        raise UnsafeLegacyRunCloneSourceError("current_state_capture cannot be proven to match current persisted source state")

            _, _, target_normalized_clone_hash = self._clone_legacy_simulation_run_namespace_in_session(
                session=session, source_simulation_run_id=source_simulation_run_id,
                target_simulation_run_id=target_simulation_run_id, target_seed=target_seed,
            )

        target = self.inspect_legacy_run_clone_inventory(simulation_run_id=target_simulation_run_id)
        counts = tuple(LegacyRunCloneSectionResult(section.name, section.count) for section in preflight.inventory.sections if section.copy_policy == "copy")
        return LegacyRunCloneResult(
            source_legacy_simulation_run_id=source_simulation_run_id, target_legacy_simulation_run_id=target_simulation_run_id,
            source_branch_id=preflight.inventory.source_branch_id, source_checkpoint_id=source_checkpoint_id,
            source_checkpoint_kind=preflight.inventory.source_checkpoint_kind, source_inventory_hash=preflight.inventory.inventory_hash,
            target_inventory_hash=target.inventory.inventory_hash, cloned_section_counts=counts,
            normalized_clone_equivalence_hash=target_normalized_clone_hash,
            source_product_run_id=preflight.inventory.source_product_run_id, target_product_run_id=None,
        )

    def fork_run_branch_atomically(self, command: ForkRunBranchCommand) -> ForkRunBranchResult:
        """Atomically materialize a Branch fork and its legacy execution namespace."""
        fields = command.__dict__
        if any(not isinstance(value, str) or not value.strip() for key, value in fields.items() if key != "target_branch_seed") or not isinstance(command.target_branch_seed, int):
            raise BranchForkValidationError("fork command fields must be non-empty and target_branch_seed must be an integer")
        canonical = {key: (value.strip() if isinstance(value, str) else value) for key, value in fields.items()}
        command = ForkRunBranchCommand(**canonical)
        with self._session_factory.begin() as session:
            container = session.get(RunContainerModel, command.product_run_id)
            branch = session.get(RunBranchModel, command.source_branch_id)
            checkpoint = session.get(BranchCheckpointModel, command.source_checkpoint_id)
            source_run = session.get(SimulationRunModel, branch.legacy_simulation_run_id) if branch and branch.legacy_simulation_run_id else None
            provenance = {"run_world_id": container.world_id if container else None, "run_config_version": container.config_version if container else None, "run_config_fingerprint": container.config_fingerprint if container else None, "run_global_seed": container.global_seed if container else None, "source_checkpoint_hash": checkpoint.content_hash if checkpoint else None, "source_legacy_seed": source_run.seed if source_run else None}
            fingerprint = hashlib.sha256(self.canonical_json({"command": canonical, "source_provenance": provenance}).encode("utf-8")).hexdigest()
            existing = session.get(BranchForkCommandModel, command.command_id)
            if existing is not None:
                if existing.request_fingerprint != fingerprint:
                    raise BranchForkIdempotencyConflictError("command_id already exists with different fork request")
                result_branch = session.get(RunBranchModel, existing.result_branch_id)
                result_checkpoint = session.get(BranchCheckpointModel, existing.result_checkpoint_id)
                result_run = session.get(SimulationRunModel, existing.result_legacy_simulation_run_id)
                if result_branch is None or result_checkpoint is None or result_run is None or result_branch.run_id != command.product_run_id or result_branch.head_checkpoint_id != result_checkpoint.checkpoint_id:
                    raise BranchForkSourceStateMismatchError("idempotent fork result is missing or inconsistent")
                metadata = _from_json(existing.metadata_json)
                return ForkRunBranchResult(command.product_run_id, command.source_branch_id, command.source_checkpoint_id, command.target_branch_id, command.target_legacy_simulation_run_id, existing.result_checkpoint_id, command.target_branch_seed, metadata["source_inventory_hash"], metadata["normalized_clone_equivalence_hash"], fingerprint, True)
            if container is None: raise BranchForkValidationError("product run was not found")
            if container.storage_kind != "custom_local" or container.read_only or container.status != "active": raise BranchForkValidationError("product run is not editable and active")
            if branch is None or branch.run_id != command.product_run_id: raise BranchForkValidationError("source branch was not found in product run")
            if branch.read_only or branch.status != "active" or not (branch.legacy_simulation_run_id or "").strip(): raise BranchForkValidationError("source branch is not writable and active with a legacy binding")
            branch_state = session.get(BranchStateModel, command.source_branch_id)
            if branch_state is None: raise BranchForkValidationError("source branch state was not found")
            if branch.head_checkpoint_id != branch_state.head_checkpoint_id: raise BranchForkSourceStateMismatchError("source branch and branch state heads disagree")
            if checkpoint is None or checkpoint.run_id != command.product_run_id or checkpoint.branch_id != command.source_branch_id or checkpoint.checkpoint_id != branch_state.head_checkpoint_id: raise BranchForkSourceStateMismatchError("source checkpoint is not the effective branch head")
            record = self._to_branch_checkpoint(checkpoint)
            if record.content_hash_algorithm != "sha256" or self.checkpoint_envelope_content_hash(record) != record.content_hash: raise BranchForkSourceStateMismatchError("source checkpoint content hash is invalid")
            if checkpoint.kind not in {BRANCH_CHECKPOINT_KIND_INITIAL, BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE}: raise BranchForkValidationError("source checkpoint kind is not fork-safe")
            source_run = session.get(SimulationRunModel, branch.legacy_simulation_run_id)
            source_state = session.get(SeasonStateModel, branch.legacy_simulation_run_id)
            if source_run is None or source_state is None: raise BranchForkSourceStateMismatchError("source legacy state is missing")
            if source_state.active_tournament_json not in (None, "", "null", "{}", "[]"): raise BranchForkValidationError("source has an active tournament")
            if session.execute(select(RunProspectModel).where(RunProspectModel.run_id == source_run.run_id)).scalars().first() is not None: raise BranchForkValidationError("source has unsupported run prospects")
            if checkpoint.kind == BRANCH_CHECKPOINT_KIND_INITIAL and (source_state.next_event_index != 0 or session.execute(select(CompletedEventModel).where(CompletedEventModel.run_id == source_run.run_id)).scalars().first() is not None): raise BranchForkSourceStateMismatchError("initial source is no longer season start")
            if checkpoint.kind == BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE:
                payload = _from_json(checkpoint.payload_json); captured = payload.get("season_state") if isinstance(payload, dict) else None
                if not isinstance(captured, dict) or _to_json(captured) != _to_json(self._season_state_payload_in_session(session=session, model=source_state)): raise BranchForkSourceStateMismatchError("current state capture is stale")
            if container.world_id != source_run.world_id or container.world_id != checkpoint.world_id: raise BranchForkSourceStateMismatchError("locked world_id provenance mismatch")
            if (container.config_version and checkpoint.config_version and container.config_version != checkpoint.config_version) or (container.config_fingerprint and checkpoint.config_fingerprint and container.config_fingerprint != checkpoint.config_fingerprint) or (container.global_seed is not None and checkpoint.global_seed is not None and container.global_seed != checkpoint.global_seed): raise BranchForkSourceStateMismatchError("run provenance mismatch")
            if command.target_branch_id == command.source_branch_id or session.get(RunBranchModel, command.target_branch_id) is not None: raise BranchForkTargetExistsError("target branch already exists or equals source")
            if command.target_legacy_simulation_run_id == source_run.run_id or session.get(SimulationRunModel, command.target_legacy_simulation_run_id) is not None or session.execute(select(RunBranchModel).where(RunBranchModel.legacy_simulation_run_id == command.target_legacy_simulation_run_id)).scalar_one_or_none() is not None: raise BranchForkTargetExistsError("target legacy simulation run already exists or is bound")
            source_inventory_hash = self._normalized_clone_content_hash(session=session, run_id=source_run.run_id, expected_clone_seed=source_run.seed)
            target_run, target_state, equivalence_hash = self._clone_legacy_simulation_run_namespace_in_session(session=session, source_simulation_run_id=source_run.run_id, target_simulation_run_id=command.target_legacy_simulation_run_id, preserve_source_seed=True)
            if target_run.world_id != container.world_id: raise BranchForkSourceStateMismatchError("cloned target world_id mismatch")
            checkpoint_id = f"checkpoint-{hashlib.sha256(('branch-fork-v1\\x00' + command.target_branch_id + '\\x00' + command.command_id).encode('utf-8')).hexdigest()[:24]}"
            seed_namespace = {"hierarchy": ["global", "branch"], "global_seed": container.global_seed, "source_branch_seed": branch.branch_seed, "source_legacy_simulation_run_seed": source_run.seed, "target_branch_seed": command.target_branch_seed}
            payload = {"product_run_id": command.product_run_id, "source_branch_id": command.source_branch_id, "source_checkpoint_id": command.source_checkpoint_id, "source_checkpoint_kind": checkpoint.kind, "source_checkpoint_content_hash": checkpoint.content_hash, "source_legacy_simulation_run_id": source_run.run_id, "target_branch_id": command.target_branch_id, "target_legacy_simulation_run_id": command.target_legacy_simulation_run_id, "source_inventory_hash": source_inventory_hash, "normalized_clone_equivalence_hash": equivalence_hash, "request_fingerprint": fingerprint, "provenance": {"world_id": container.world_id, "world_fingerprint": container.world_package_fingerprint, "config_version": container.config_version, "config_fingerprint": container.config_fingerprint, "global_seed": container.global_seed, "source_branch_seed": branch.branch_seed, "source_legacy_simulation_run_seed": source_run.seed, "target_branch_seed": command.target_branch_seed}, "fork_semantics": "cloned_current_state_not_checkpoint_replay"}
            branch_metadata = {"fork_command_id": command.command_id, "request_fingerprint": fingerprint, "source_checkpoint_id": checkpoint.checkpoint_id}
            session.add(RunBranchModel(branch_id=command.target_branch_id, run_id=command.product_run_id, display_name=command.target_branch_display_name, status="active", read_only=0, branch_seed=command.target_branch_seed, forked_from_branch_id=command.source_branch_id, forked_from_checkpoint_id=command.source_checkpoint_id, head_checkpoint_id=checkpoint_id, legacy_simulation_run_id=command.target_legacy_simulation_run_id, metadata_json=_to_json(branch_metadata)))
            state_metadata = {"fork_command_id": command.command_id, "source_checkpoint_id": checkpoint.checkpoint_id}
            session.add(BranchStateModel(branch_id=command.target_branch_id, run_id=command.product_run_id, head_checkpoint_id=checkpoint_id, current_season=target_state.season, current_week=checkpoint.week, current_event_id=checkpoint.event_id, current_event_sequence=checkpoint.event_sequence, state_schema_version="branch_state_v1", status="active", metadata_json=_to_json(state_metadata)))
            incomplete = BranchCheckpointRecord(checkpoint_id, command.product_run_id, command.target_branch_id, None, 1, BRANCH_CHECKPOINT_KIND_BRANCH_FORK_START, target_state.season, checkpoint.week, checkpoint.event_id, checkpoint.event_sequence, command.command_id, BRANCH_CHECKPOINT_COMMAND_KIND_FORK_BRANCH, BRANCH_CHECKPOINT_COMMAND_BOUNDARY_AFTER_ATOMIC_FORK_MATERIALIZATION, container.config_version, container.config_fingerprint, container.world_id, container.world_package_fingerprint, container.global_seed, command.target_branch_seed, seed_namespace, "branch_checkpoint_payload_v1", "sha256", "", payload)
            fork_checkpoint = BranchCheckpointRecord(**{**incomplete.__dict__, "content_hash": self.checkpoint_envelope_content_hash(incomplete)})
            session.add(BranchCheckpointModel(checkpoint_id=fork_checkpoint.checkpoint_id, run_id=fork_checkpoint.run_id, branch_id=fork_checkpoint.branch_id, parent_checkpoint_id=None, sequence=1, kind=fork_checkpoint.kind, season=fork_checkpoint.season, week=fork_checkpoint.week, event_id=fork_checkpoint.event_id, event_sequence=fork_checkpoint.event_sequence, command_id=fork_checkpoint.command_id, command_kind=fork_checkpoint.command_kind, command_boundary=fork_checkpoint.command_boundary, config_version=fork_checkpoint.config_version, config_fingerprint=fork_checkpoint.config_fingerprint, world_id=fork_checkpoint.world_id, world_fingerprint=fork_checkpoint.world_fingerprint, global_seed=fork_checkpoint.global_seed, branch_seed=fork_checkpoint.branch_seed, seed_namespace_json=self.canonical_json(fork_checkpoint.seed_namespace), payload_schema_version=fork_checkpoint.payload_schema_version, content_hash_algorithm="sha256", content_hash=fork_checkpoint.content_hash, payload_json=self.canonical_json(fork_checkpoint.payload)))
            metadata = {"source_inventory_hash": source_inventory_hash, "normalized_clone_equivalence_hash": equivalence_hash}
            session.add(BranchForkCommandModel(command_id=command.command_id, product_run_id=command.product_run_id, request_fingerprint=fingerprint, source_branch_id=command.source_branch_id, source_checkpoint_id=command.source_checkpoint_id, target_branch_id=command.target_branch_id, target_legacy_simulation_run_id=command.target_legacy_simulation_run_id, result_branch_id=command.target_branch_id, result_checkpoint_id=checkpoint_id, result_legacy_simulation_run_id=command.target_legacy_simulation_run_id, metadata_json=_to_json(metadata)))
            try: session.flush()
            except IntegrityError as exc: raise BranchForkTargetExistsError("fork target conflicts with existing durable state") from exc
            return ForkRunBranchResult(command.product_run_id, command.source_branch_id, command.source_checkpoint_id, command.target_branch_id, command.target_legacy_simulation_run_id, checkpoint_id, command.target_branch_seed, source_inventory_hash, equivalence_hash, fingerprint, False)

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
                    BranchCheckpointModel.kind == BRANCH_CHECKPOINT_KIND_INITIAL,
                )
            ).scalars().first()
            return self._to_branch_checkpoint(model) if model is not None else None

    def get_event_completed_branch_checkpoint(self, *, branch_id: str, event_sequence: int) -> BranchCheckpointRecord | None:
        """Return the sole capture-only event boundary for a branch/event sequence."""
        with self._session_factory() as session:
            model = session.execute(select(BranchCheckpointModel).where(
                BranchCheckpointModel.branch_id == branch_id,
                BranchCheckpointModel.kind == BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED,
                BranchCheckpointModel.event_sequence == event_sequence,
            )).scalars().first()
            return self._to_branch_checkpoint(model) if model is not None else None

    def get_week_completed_branch_checkpoint(self, *, branch_id: str, season: int, week: int) -> BranchCheckpointRecord | None:
        """Return the sole capture-only completed-week boundary for a branch/week."""
        with self._session_factory() as session:
            model = session.execute(select(BranchCheckpointModel).where(
                BranchCheckpointModel.branch_id == branch_id,
                BranchCheckpointModel.kind == BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED,
                BranchCheckpointModel.season == season,
                BranchCheckpointModel.week == week,
            )).scalars().first()
            return self._to_branch_checkpoint(model) if model is not None else None

    def get_admin_action_applied_branch_checkpoint(self, *, branch_id: str, action_sequence: int) -> BranchCheckpointRecord | None:
        """Return the sole R3H capture for a legacy ordered admin-action sequence."""
        for checkpoint in self.list_branch_checkpoints(branch_id=branch_id):
            if checkpoint.kind != BRANCH_CHECKPOINT_KIND_ADMIN_ACTION_APPLIED:
                continue
            action = checkpoint.payload.get("admin_action", {})
            if isinstance(action, dict) and action.get("action_sequence") == action_sequence:
                return checkpoint
        return None

    def get_season_rollover_branch_checkpoint(self, *, branch_id: str, from_season: int, to_season: int) -> BranchCheckpointRecord | None:
        """Find the sole capture-only checkpoint for a persisted rollover locator."""
        for checkpoint in self.list_branch_checkpoints(branch_id=branch_id):
            rollover = checkpoint.payload.get("rollover", {})
            if checkpoint.kind == BRANCH_CHECKPOINT_KIND_SEASON_ROLLOVER and isinstance(rollover, dict) and rollover.get("from_season") == from_season and rollover.get("to_season") == to_season:
                return checkpoint
        return None

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
            if record.kind == BRANCH_CHECKPOINT_KIND_INITIAL:
                existing_initial = session.execute(
                    select(BranchCheckpointModel).where(
                        BranchCheckpointModel.branch_id == record.branch_id,
                        BranchCheckpointModel.kind == BRANCH_CHECKPOINT_KIND_INITIAL,
                    )
                ).scalars().first()
                if existing_initial is not None:
                    raise ValueError(f"branch_id {record.branch_id} already has an initial checkpoint")
            if record.kind == BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED:
                existing_event = session.execute(select(BranchCheckpointModel).where(
                    BranchCheckpointModel.branch_id == record.branch_id,
                    BranchCheckpointModel.kind == BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED,
                    BranchCheckpointModel.event_sequence == record.event_sequence,
                )).scalars().first()
                if existing_event is not None:
                    raise ValueError(
                        f"branch_id {record.branch_id} already has an event_completed checkpoint "
                        f"for event_sequence {record.event_sequence}"
                    )
            if record.kind == BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED:
                existing_week = session.execute(select(BranchCheckpointModel).where(
                    BranchCheckpointModel.branch_id == record.branch_id,
                    BranchCheckpointModel.kind == BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED,
                    BranchCheckpointModel.season == record.season,
                    BranchCheckpointModel.week == record.week,
                )).scalars().first()
                if existing_week is not None:
                    raise ValueError(
                        f"branch_id {record.branch_id} already has a week_completed checkpoint "
                        f"for season {record.season} week {record.week}"
                    )
            expected = session.execute(select(func.max(BranchCheckpointModel.sequence)).where(BranchCheckpointModel.branch_id == record.branch_id)).scalar_one()
            if record.sequence != (1 if expected is None else int(expected) + 1): raise ValueError("branch checkpoint sequence must increase by one")
            if record.kind == BRANCH_CHECKPOINT_KIND_INITIAL and record.parent_checkpoint_id is not None: raise ValueError("initial checkpoint parent must be null")
            session.add(BranchCheckpointModel(
                checkpoint_id=record.checkpoint_id, run_id=record.run_id, branch_id=record.branch_id, parent_checkpoint_id=record.parent_checkpoint_id,
                sequence=record.sequence, kind=record.kind, season=record.season, week=record.week, event_id=record.event_id,
                event_sequence=record.event_sequence, command_id=record.command_id, command_kind=record.command_kind,
                command_boundary=record.command_boundary, config_version=record.config_version, config_fingerprint=record.config_fingerprint,
                world_id=record.world_id, world_fingerprint=record.world_fingerprint, global_seed=record.global_seed, branch_seed=record.branch_seed,
                seed_namespace_json=self.canonical_json(record.seed_namespace), payload_schema_version=record.payload_schema_version,
                content_hash_algorithm=record.content_hash_algorithm, content_hash=record.content_hash, payload_json=self.canonical_json(record.payload),
            ))
            try:
                session.flush()
            except IntegrityError as exc:
                raise ValueError(f"branch checkpoint boundary conflict for branch_id {record.branch_id}") from exc
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
            kind=BRANCH_CHECKPOINT_KIND_INITIAL,
            season=legacy.season,
            week=None,
            event_id=None,
            event_sequence=None,
            command_id=command_id,
            command_kind=BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_INITIAL,
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

    def capture_current_checkpoint_for_legacy_simulation_run(
        self, *, simulation_run_id: str, command_id: str | None = None
    ) -> BranchCheckpointRecord:
        """Capture the legacy run's current state as an immutable, non-forkable checkpoint.

        This intentionally reads the legacy ``season_state`` and does not make branch
        state authoritative for simulation or provide replay/fork behavior.
        """
        legacy = self.get_simulation_run(run_id=simulation_run_id)
        if legacy is None:
            raise KeyError(f"run_id {simulation_run_id} was not found")
        branch = self.ensure_default_branch_for_simulation_run(simulation_run_id=simulation_run_id)
        if branch is None:
            raise KeyError(f"default branch for run_id {simulation_run_id} was not found")
        state = self.load_season_state(run_id=simulation_run_id)
        if state is None:
            raise ValueError(f"run_id {simulation_run_id} has no season state")

        # BranchState is the mutable checkpoint-head locator.  Older branches may
        # not have one yet, in which case it is backfilled from run_branches.
        branch_state = self.get_branch_state(branch_id=branch.branch_id)
        if branch_state is None:
            branch_state = self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        effective_head_id = branch_state.head_checkpoint_id if branch_state is not None else branch.head_checkpoint_id
        if effective_head_id is None:
            raise ValueError(f"branch {branch.branch_id} has no existing head checkpoint; capture initial first")
        parent = self.get_branch_checkpoint(checkpoint_id=effective_head_id)
        if parent is None:
            raise ValueError(f"branch {branch.branch_id} head checkpoint {effective_head_id} was not found")

        actions = [action.__dict__ for action in self.list_admin_actions(run_id=simulation_run_id)]
        seed_namespace = {
            "hierarchy": ["global", "season", "entries", "draws", "tournament_progression"],
            "global_seed": legacy.seed,
            "branch_seed": branch.branch_seed,
        }
        serialized_state = state.model_dump(mode="json")
        payload: dict[str, object] = {
            "fork_capability": "not_forkable_player_state_not_migrated",
            "capture_mode": "legacy_current_state_capture_only",
            "payload_schema_version": "branch_checkpoint_payload_v1",
            "run_id": branch.run_id,
            "branch_id": branch.branch_id,
            "legacy_simulation_run_id": simulation_run_id,
            "parent_checkpoint_id": effective_head_id,
            "simulation_run": legacy.__dict__,
            "season_state": serialized_state,
            "admin": {"actions": actions, "admin_actions_hash": self.checkpoint_content_hash({"actions": actions})},
            "provenance": {
                "world_id": legacy.world_id,
                "world_fingerprint": legacy.world_generation_fingerprint,
                "config_version": legacy.config_version,
                "config_fingerprint": legacy.config_fingerprint,
                "global_seed": legacy.seed,
                "branch_seed": branch.branch_seed,
                "seed_namespace": seed_namespace,
            },
            "limitations": {
                "forkable": False,
                "player_state": "hash_only_or_not_migrated",
                "prospects": "legacy_run_scoped_not_captured_as_durable_identity",
                "simulation_source": "legacy_simulation_run_state",
            },
        }
        # The default command identity represents the captured logical legacy state,
        # not the mutable branch head.  Keeping the parent out makes a repeated
        # no-command capture idempotent even after its first call advances the head.
        state_fingerprint = self.checkpoint_content_hash({
            key: value for key, value in payload.items() if key != "parent_checkpoint_id"
        })
        command_id = command_id or f"legacy-current-capture:{simulation_run_id}:{state_fingerprint[:24]}"
        existing = self.get_branch_checkpoint_by_command_id(branch_id=branch.branch_id, command_id=command_id)
        if existing is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing

        checkpoint_suffix = hashlib.sha256(f"{branch.branch_id}\x00{command_id}".encode("utf-8")).hexdigest()[:24]
        active_event = state.active_tournament.event if state.active_tournament is not None else None
        checkpoint_without_hash = BranchCheckpointRecord(
            checkpoint_id=f"checkpoint-{checkpoint_suffix}", run_id=branch.run_id, branch_id=branch.branch_id,
            parent_checkpoint_id=effective_head_id, sequence=self.next_checkpoint_sequence(branch_id=branch.branch_id),
            kind=BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE, season=state.season,
            week=active_event.week if active_event is not None else None,
            event_id=active_event.event_id if active_event is not None else None,
            event_sequence=state.next_event_index if active_event is not None else None,
            command_id=command_id, command_kind=BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_CURRENT_LEGACY_STATE, command_boundary="after_legacy_state_load",
            config_version=legacy.config_version, config_fingerprint=legacy.config_fingerprint,
            world_id=legacy.world_id, world_fingerprint=legacy.world_generation_fingerprint,
            global_seed=legacy.seed, branch_seed=branch.branch_seed, seed_namespace=seed_namespace,
            payload_schema_version="branch_checkpoint_payload_v1", content_hash_algorithm="sha256", content_hash="",
            payload=payload,
        )
        checkpoint = BranchCheckpointRecord(**{
            **checkpoint_without_hash.__dict__,
            "content_hash": self.checkpoint_envelope_content_hash(checkpoint_without_hash),
        })
        created = self.create_branch_checkpoint(checkpoint)
        with self._session_factory.begin() as session:
            model = session.get(RunBranchModel, branch.branch_id)
            if model is not None:
                model.head_checkpoint_id = created.checkpoint_id
        self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        return created

    def capture_completed_event_checkpoint_for_legacy_simulation_run(
        self, *, simulation_run_id: str, event_id: str | None = None,
        event_sequence: int | None = None, command_id: str | None = None,
    ) -> BranchCheckpointRecord:
        """Capture an already persisted legacy event; this does not replay or fork it."""
        if event_id is None and event_sequence is None:
            raise ValueError("an event_id or event_sequence is required")
        legacy = self.get_simulation_run(run_id=simulation_run_id)
        if legacy is None:
            raise KeyError(f"run_id {simulation_run_id} was not found")
        branch = self.ensure_default_branch_for_simulation_run(simulation_run_id=simulation_run_id)
        if branch is None:
            raise KeyError(f"default branch for run_id {simulation_run_id} was not found")
        state = self.load_season_state(run_id=simulation_run_id)
        if state is None:
            raise ValueError(f"run_id {simulation_run_id} has no season state")
        events = self.list_completed_events(run_id=simulation_run_id)
        by_id = next((item for item in events if item.event_id == event_id), None) if event_id is not None else None
        by_sequence = next((item for item in events if item.event_sequence == event_sequence), None) if event_sequence is not None else None
        if event_id is not None and event_sequence is not None and (by_id is None or by_sequence is None or by_id.event_id != by_sequence.event_id):
            raise ValueError("event_id and event_sequence identify different completed events")
        target = by_id or by_sequence
        if target is None:
            raise ValueError("completed event locator was not found")
        if target.event_id not in state.completed_event_ids:
            raise ValueError(f"event_id {target.event_id} is not completed in the current season state")

        branch_state = self.get_branch_state(branch_id=branch.branch_id) or self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        effective_head_id = branch_state.head_checkpoint_id if branch_state is not None else branch.head_checkpoint_id
        if effective_head_id is None:
            raise ValueError(f"branch {branch.branch_id} has no existing head checkpoint; capture initial first")
        if self.get_branch_checkpoint(checkpoint_id=effective_head_id) is None:
            raise ValueError(f"branch {branch.branch_id} head checkpoint {effective_head_id} was not found")
        # A branch has one durable historical event boundary per legacy event.
        existing_event = self.get_event_completed_branch_checkpoint(branch_id=branch.branch_id, event_sequence=target.event_sequence)
        if existing_event is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing_event

        completed_input = next((item.model_dump(mode="json") for item in state.completed_tournament_inputs if item.event_id == target.event_id), None)
        actions = [action.__dict__ for action in self.list_admin_actions(run_id=simulation_run_id)]
        seed_namespace = {"hierarchy": ["global", "season", "entries", "draws", "tournament_progression"], "global_seed": legacy.seed, "branch_seed": branch.branch_seed}
        ranking_refs = [item.__dict__ for item in self.list_ranking_snapshot_records(run_id=simulation_run_id) if item.source_event_id == target.event_id]
        race_refs = [item.__dict__ for item in self.list_race_snapshot_records(run_id=simulation_run_id) if item.source_event_id == target.event_id]
        serialized_state = state.model_dump(mode="json")
        event_payload = {"event_id": target.event_id, "event_sequence": target.event_sequence, "season": target.season or state.season, "week": target.week, "template_id": target.template_id, "source": "legacy_completed_event"}
        payload: dict[str, object] = {
            "fork_capability": "not_forkable_player_state_not_migrated", "capture_mode": "legacy_event_completed_capture_only",
            "payload_schema_version": "branch_checkpoint_payload_v1", "run_id": branch.run_id, "branch_id": branch.branch_id,
            "legacy_simulation_run_id": simulation_run_id, "parent_checkpoint_id": effective_head_id, "event": event_payload,
            "simulation_run": legacy.__dict__, "season_state": serialized_state,
            "completed_event": {"record": target.__dict__, "metadata": {"season": target.season, "week": target.week, "template_id": target.template_id}, "tournament_result": target.tournament_result, "tournament_result_hash": self.checkpoint_content_hash(target.tournament_result or {}), "completed_tournament_input": completed_input, "completed_tournament_input_hash": self.checkpoint_content_hash(completed_input or {})},
            "publications": {"ranking_snapshot_references": ranking_refs, "race_snapshot_references": race_refs},
            "admin": {"actions": actions, "admin_actions_hash": self.checkpoint_content_hash({"actions": actions})},
            "provenance": {"world_id": legacy.world_id, "world_fingerprint": legacy.world_generation_fingerprint, "config_version": legacy.config_version, "config_fingerprint": legacy.config_fingerprint, "global_seed": legacy.seed, "branch_seed": branch.branch_seed, "seed_namespace": seed_namespace},
            "limitations": {"forkable": False, "replayable": False, "player_state": "hash_only_or_not_migrated", "prospects": "legacy_run_scoped_not_captured_as_durable_identity", "simulation_source": "legacy_simulation_run_state", "match_level_checkpoints": "declared_future_boundary_not_supported_by_current_precomputed_tournament_model"},
        }
        logical_fingerprint = self.checkpoint_content_hash({key: value for key, value in payload.items() if key != "parent_checkpoint_id"})
        command_id = command_id or f"legacy-event-completed-capture:{simulation_run_id}:{target.event_id}:{target.event_sequence}:{logical_fingerprint[:24]}"
        existing = self.get_branch_checkpoint_by_command_id(branch_id=branch.branch_id, command_id=command_id)
        if existing is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing
        suffix = hashlib.sha256(f"{branch.branch_id}\x00{command_id}".encode("utf-8")).hexdigest()[:24]
        incomplete = BranchCheckpointRecord(
            checkpoint_id=f"checkpoint-{suffix}", run_id=branch.run_id, branch_id=branch.branch_id, parent_checkpoint_id=effective_head_id,
            sequence=self.next_checkpoint_sequence(branch_id=branch.branch_id), kind=BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED, season=target.season or state.season,
            week=target.week, event_id=target.event_id, event_sequence=target.event_sequence, command_id=command_id,
            command_kind=BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_COMPLETED_EVENT_LEGACY_STATE, command_boundary="after_completed_event_persisted",
            config_version=legacy.config_version, config_fingerprint=legacy.config_fingerprint, world_id=legacy.world_id,
            world_fingerprint=legacy.world_generation_fingerprint, global_seed=legacy.seed, branch_seed=branch.branch_seed,
            seed_namespace=seed_namespace, payload_schema_version="branch_checkpoint_payload_v1", content_hash_algorithm="sha256", content_hash="", payload=payload)
        checkpoint = BranchCheckpointRecord(**{**incomplete.__dict__, "content_hash": self.checkpoint_envelope_content_hash(incomplete)})
        created = self.create_branch_checkpoint(checkpoint)
        with self._session_factory.begin() as session:
            model = session.get(RunBranchModel, branch.branch_id)
            if model is not None:
                model.head_checkpoint_id = created.checkpoint_id
        self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        return created

    def capture_completed_week_checkpoint_for_legacy_simulation_run(
        self, *, simulation_run_id: str, week: int, command_id: str | None = None,
    ) -> BranchCheckpointRecord:
        """Capture an already completed scheduled legacy week without replaying or forking it."""
        if not 1 <= week <= 61:
            raise ValueError("week must be within the FAX season range 1..61")
        legacy = self.get_simulation_run(run_id=simulation_run_id)
        if legacy is None:
            raise KeyError(f"run_id {simulation_run_id} was not found")
        branch = self.ensure_default_branch_for_simulation_run(simulation_run_id=simulation_run_id)
        if branch is None:
            raise KeyError(f"default branch for run_id {simulation_run_id} was not found")
        state = self.load_season_state(run_id=simulation_run_id)
        if state is None:
            raise ValueError(f"run_id {simulation_run_id} has no season state")
        scheduled = [event for event in state.ordered_events if event.week == week]
        if not scheduled:
            raise ValueError(f"week {week} has no scheduled events; empty-week checkpoints are not supported")
        scheduled_ids = [event.event_id for event in scheduled]
        incomplete = [event_id for event_id in scheduled_ids if event_id not in state.completed_event_ids]
        if incomplete:
            raise ValueError(f"week {week} is not completed; scheduled events are incomplete: {', '.join(incomplete)}")
        persisted_by_id = {item.event_id: item for item in self.list_completed_events(run_id=simulation_run_id)}
        missing = [event_id for event_id in scheduled_ids if event_id not in persisted_by_id]
        if missing:
            raise ValueError(f"week {week} has completed events without persisted completed-event records: {', '.join(missing)}")
        branch_state = self.get_branch_state(branch_id=branch.branch_id) or self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        effective_head_id = branch_state.head_checkpoint_id if branch_state is not None else branch.head_checkpoint_id
        if effective_head_id is None:
            raise ValueError(f"branch {branch.branch_id} has no existing head checkpoint; capture initial first")
        if self.get_branch_checkpoint(checkpoint_id=effective_head_id) is None:
            raise ValueError(f"branch {branch.branch_id} head checkpoint {effective_head_id} was not found")
        existing_week = self.get_week_completed_branch_checkpoint(branch_id=branch.branch_id, season=state.season, week=week)
        if existing_week is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing_week
        completed = [persisted_by_id[event_id] for event_id in scheduled_ids]
        completed.sort(key=lambda item: item.event_sequence)
        completed_inputs = {
            item.event_id: item.model_dump(mode="json") for item in state.completed_tournament_inputs
            if item.event_id in set(scheduled_ids)
        }
        actions = [action.__dict__ for action in self.list_admin_actions(run_id=simulation_run_id)]
        seed_namespace = {"hierarchy": ["global", "season", "entries", "draws", "tournament_progression"], "global_seed": legacy.seed, "branch_seed": branch.branch_seed}
        ranking_refs = [item.__dict__ for item in self.list_ranking_snapshot_records(run_id=simulation_run_id) if item.source_event_id in scheduled_ids]
        race_refs = [item.__dict__ for item in self.list_race_snapshot_records(run_id=simulation_run_id) if item.source_event_id in scheduled_ids]
        event_rows = [{"record": item.__dict__, "metadata": {"season": item.season, "week": item.week, "template_id": item.template_id}, "tournament_result": item.tournament_result, "tournament_result_hash": self.checkpoint_content_hash(item.tournament_result or {}), "completed_tournament_input": completed_inputs.get(item.event_id), "completed_tournament_input_hash": self.checkpoint_content_hash(completed_inputs.get(item.event_id) or {})} for item in completed]
        sequences = [item.event_sequence for item in completed]
        payload: dict[str, object] = {
            "fork_capability": "not_forkable_player_state_not_migrated", "capture_mode": "legacy_week_completed_capture_only",
            "payload_schema_version": "branch_checkpoint_payload_v1", "run_id": branch.run_id, "branch_id": branch.branch_id,
            "legacy_simulation_run_id": simulation_run_id, "parent_checkpoint_id": effective_head_id,
            "week": {"season": state.season, "week": week, "source": "legacy_completed_week", "scheduled_event_count": len(scheduled), "completed_event_count": len(completed), "completed_event_ids": scheduled_ids, "completed_event_sequences": sequences},
            "simulation_run": legacy.__dict__, "season_state": state.model_dump(mode="json"), "completed_events": event_rows,
            "publications": {"ranking_snapshot_references": ranking_refs, "race_snapshot_references": race_refs},
            "admin": {"actions": actions, "admin_actions_hash": self.checkpoint_content_hash({"actions": actions})},
            "provenance": {"world_id": legacy.world_id, "world_fingerprint": legacy.world_generation_fingerprint, "config_version": legacy.config_version, "config_fingerprint": legacy.config_fingerprint, "global_seed": legacy.seed, "branch_seed": branch.branch_seed, "seed_namespace": seed_namespace},
            "limitations": {"forkable": False, "replayable": False, "player_state": "hash_only_or_not_migrated", "prospects": "legacy_run_scoped_not_captured_as_durable_identity", "simulation_source": "legacy_simulation_run_state", "empty_week_checkpoints": "not_supported_until_calendar_week_state_exists", "match_level_checkpoints": "declared_future_boundary_not_supported_by_current_precomputed_tournament_model"},
        }
        logical_fingerprint = self.checkpoint_content_hash({key: value for key, value in payload.items() if key != "parent_checkpoint_id"})
        command_id = command_id or f"legacy-week-completed-capture:{simulation_run_id}:{state.season}:{week}:{','.join(scheduled_ids)}:{','.join(map(str, sequences))}:{logical_fingerprint[:24]}"
        existing = self.get_branch_checkpoint_by_command_id(branch_id=branch.branch_id, command_id=command_id)
        if existing is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing
        suffix = hashlib.sha256(f"{branch.branch_id}\x00{command_id}".encode("utf-8")).hexdigest()[:24]
        incomplete_checkpoint = BranchCheckpointRecord(
            checkpoint_id=f"checkpoint-{suffix}", run_id=branch.run_id, branch_id=branch.branch_id, parent_checkpoint_id=effective_head_id,
            sequence=self.next_checkpoint_sequence(branch_id=branch.branch_id), kind=BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED, season=state.season, week=week,
            event_id=None, event_sequence=max(sequences) if sequences else None, command_id=command_id,
            command_kind=BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_COMPLETED_WEEK_LEGACY_STATE, command_boundary="after_completed_week_persisted",
            config_version=legacy.config_version, config_fingerprint=legacy.config_fingerprint, world_id=legacy.world_id,
            world_fingerprint=legacy.world_generation_fingerprint, global_seed=legacy.seed, branch_seed=branch.branch_seed,
            seed_namespace=seed_namespace, payload_schema_version="branch_checkpoint_payload_v1", content_hash_algorithm="sha256", content_hash="", payload=payload,
        )
        checkpoint = BranchCheckpointRecord(**{**incomplete_checkpoint.__dict__, "content_hash": self.checkpoint_envelope_content_hash(incomplete_checkpoint)})
        created = self.create_branch_checkpoint(checkpoint)
        with self._session_factory.begin() as session:
            model = session.get(RunBranchModel, branch.branch_id)
            if model is not None:
                model.head_checkpoint_id = created.checkpoint_id
        self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        return created

    def capture_season_rollover_checkpoint_for_legacy_simulation_run(
        self, *, simulation_run_id: str, from_season: int | None = None,
        to_season: int | None = None, command_id: str | None = None,
    ) -> BranchCheckpointRecord:
        """Capture an already persisted legacy season rollover; never execute or replay it."""
        legacy = self.get_simulation_run(run_id=simulation_run_id)
        if legacy is None: raise KeyError(f"run_id {simulation_run_id} was not found")
        branch = self.ensure_default_branch_for_simulation_run(simulation_run_id=simulation_run_id)
        if branch is None: raise KeyError(f"default branch for run_id {simulation_run_id} was not found")
        state = self.load_season_state(run_id=simulation_run_id)
        if state is None: raise ValueError(f"run_id {simulation_run_id} has no season state")
        rollovers = self.list_season_rollovers(run_id=simulation_run_id)
        if not rollovers: raise ValueError(f"run_id {simulation_run_id} has no persisted season rollover artifact")
        matches = [row for row in rollovers if (from_season is None or row.from_season == from_season) and (to_season is None or row.to_season == to_season)]
        if not matches: raise ValueError("rollover locator does not match a persisted season rollover artifact")
        if len(matches) > 1: raise ValueError("season rollover locator is ambiguous; provide from_season and to_season")
        rollover = matches[0]
        branch_state = self.get_branch_state(branch_id=branch.branch_id) or self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        head_id = branch_state.head_checkpoint_id if branch_state is not None else branch.head_checkpoint_id
        if head_id is None: raise ValueError(f"branch {branch.branch_id} has no existing head checkpoint; capture initial first")
        if self.get_branch_checkpoint(checkpoint_id=head_id) is None: raise ValueError(f"branch {branch.branch_id} head checkpoint {head_id} was not found")
        existing_rollover = self.get_season_rollover_branch_checkpoint(branch_id=branch.branch_id, from_season=rollover.from_season, to_season=rollover.to_season)
        if existing_rollover is not None:
            # Keep both mutable head locators aligned with the durable branch head.
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing_rollover
        transitions = [row.__dict__ | {"transition": row.transition.model_dump(mode="json")} for row in self.list_player_transitions(run_id=simulation_run_id, to_season=rollover.to_season)]
        next_players = [row.__dict__ | {"state": row.state.model_dump(mode="json")} for row in self.list_next_season_players(run_id=simulation_run_id, to_season=rollover.to_season)]
        rollover_record = rollover.__dict__
        artifacts = {"player_transition_rows": transitions, "player_transition_rows_hash": self.checkpoint_content_hash({"rows": transitions}), "next_season_player_rows": next_players, "next_season_player_rows_hash": self.checkpoint_content_hash({"rows": next_players}), "rollover_summary": rollover_record}
        artifacts["rollover_artifacts_hash"] = self.checkpoint_content_hash(artifacts)
        actions = [action.__dict__ for action in self.list_admin_actions(run_id=simulation_run_id)]
        seed_namespace = {"hierarchy": ["global", "season", "entries", "draws", "tournament_progression"], "global_seed": legacy.seed, "branch_seed": branch.branch_seed}
        payload: dict[str, object] = {"fork_capability": "not_forkable_player_state_not_migrated", "capture_mode": "legacy_season_rollover_capture_only", "payload_schema_version": "branch_checkpoint_payload_v1", "run_id": branch.run_id, "branch_id": branch.branch_id, "legacy_simulation_run_id": simulation_run_id, "parent_checkpoint_id": head_id, "rollover": {"locator": {"from_season": rollover.from_season, "to_season": rollover.to_season}, "from_season": rollover.from_season, "to_season": rollover.to_season, "source_run_id": rollover.run_id, "target_run_id": None, "target_run_id_source": "not_available_in_legacy_rollover_artifact", "record": rollover_record, "source": "legacy_season_rollover"}, "simulation_run": legacy.__dict__, "season_state": state.model_dump(mode="json"), "rollover_artifacts": artifacts, "publications": {"latest_ranking_snapshot_references": [x.__dict__ for x in self.list_ranking_snapshot_records(run_id=simulation_run_id)][-1:], "latest_race_snapshot_references": [x.__dict__ for x in self.list_race_snapshot_records(run_id=simulation_run_id)][-1:]}, "admin": {"actions": actions, "admin_actions_hash": self.checkpoint_content_hash({"actions": actions})}, "provenance": {"world_id": legacy.world_id, "world_fingerprint": legacy.world_generation_fingerprint, "config_version": legacy.config_version, "config_fingerprint": legacy.config_fingerprint, "global_seed": legacy.seed, "branch_seed": branch.branch_seed, "seed_namespace": seed_namespace}, "limitations": {"forkable": False, "replayable": False, "player_state": "hash_only_or_not_migrated", "prospects": "legacy_run_scoped_not_captured_as_durable_identity", "simulation_source": "legacy_simulation_run_state", "rollover_replay": "not_supported_yet", "bootstrap_state": "not_captured_by_season_rollover_checkpoint"}}
        logical = self.checkpoint_content_hash({key: value for key, value in payload.items() if key != "parent_checkpoint_id"})
        command_id = command_id or f"legacy-season-rollover-capture:{simulation_run_id}:{rollover.from_season}:{rollover.to_season}:{artifacts['rollover_artifacts_hash'][:24]}:{logical[:16]}"
        existing = self.get_branch_checkpoint_by_command_id(branch_id=branch.branch_id, command_id=command_id)
        if existing is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing
        suffix = hashlib.sha256(f"{branch.branch_id}\x00{command_id}".encode()).hexdigest()[:24]
        incomplete = BranchCheckpointRecord(checkpoint_id=f"checkpoint-{suffix}", run_id=branch.run_id, branch_id=branch.branch_id, parent_checkpoint_id=head_id, sequence=self.next_checkpoint_sequence(branch_id=branch.branch_id), kind=BRANCH_CHECKPOINT_KIND_SEASON_ROLLOVER, season=rollover.from_season, week=61, event_id=None, event_sequence=None, command_id=command_id, command_kind=BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_SEASON_ROLLOVER_LEGACY_STATE, command_boundary="after_season_rollover_persisted", config_version=legacy.config_version, config_fingerprint=legacy.config_fingerprint, world_id=legacy.world_id, world_fingerprint=legacy.world_generation_fingerprint, global_seed=legacy.seed, branch_seed=branch.branch_seed, seed_namespace=seed_namespace, payload_schema_version="branch_checkpoint_payload_v1", content_hash_algorithm="sha256", content_hash="", payload=payload)
        checkpoint = BranchCheckpointRecord(**{**incomplete.__dict__, "content_hash": self.checkpoint_envelope_content_hash(incomplete)})
        created = self.create_branch_checkpoint(checkpoint)
        with self._session_factory.begin() as session:
            model = session.get(RunBranchModel, branch.branch_id)
            if model is not None: model.head_checkpoint_id = created.checkpoint_id
        self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        return created

    def get_bootstrap_start_branch_checkpoint(self, *, branch_id: str, simulation_run_id: str,
                                               source_run_id: str | None, from_season: int | None,
                                               to_season: int | None) -> BranchCheckpointRecord | None:
        """Find the single capture-only bootstrap boundary for its persisted locator."""
        for checkpoint in self.list_branch_checkpoints(branch_id=branch_id):
            bootstrap = checkpoint.payload.get("bootstrap", {})
            if checkpoint.kind == BRANCH_CHECKPOINT_KIND_BOOTSTRAP_START and isinstance(bootstrap, dict) and (
                bootstrap.get("simulation_run_id") == simulation_run_id
                and bootstrap.get("source_run_id") == source_run_id
                and bootstrap.get("from_season") == from_season
                and bootstrap.get("to_season") == to_season
            ):
                return checkpoint
        return None

    def capture_bootstrap_start_checkpoint_for_legacy_simulation_run(
        self, *, simulation_run_id: str, source_run_id: str | None = None,
        from_season: int | None = None, to_season: int | None = None,
        command_id: str | None = None,
    ) -> BranchCheckpointRecord:
        """Capture an already persisted rollover-bootstrap target state, without replaying it."""
        legacy = self.get_simulation_run(run_id=simulation_run_id)
        if legacy is None:
            raise KeyError(f"run_id {simulation_run_id} was not found")
        if legacy.source_type != "rollover_bootstrap" or not (
            legacy.parent_run_id or legacy.source_rollover_run_id
        ):
            raise ValueError(f"run_id {simulation_run_id} has no stable bootstrap/rollover provenance")
        persisted_source = legacy.source_rollover_run_id or legacy.parent_run_id
        if source_run_id is not None and source_run_id not in {legacy.parent_run_id, legacy.source_rollover_run_id}:
            raise ValueError("source_run_id does not match persisted bootstrap provenance")
        if from_season is not None and from_season != legacy.source_rollover_from_season:
            raise ValueError("from_season does not match persisted bootstrap provenance")
        if to_season is not None and to_season != legacy.source_rollover_to_season:
            raise ValueError("to_season does not match persisted bootstrap provenance")
        if legacy.source_rollover_from_season is None or legacy.source_rollover_to_season is None:
            raise ValueError(f"run_id {simulation_run_id} has incomplete stable bootstrap/rollover provenance")
        branch = self.ensure_default_branch_for_simulation_run(simulation_run_id=simulation_run_id)
        if branch is None:
            raise KeyError(f"default branch for run_id {simulation_run_id} was not found")
        state = self.load_season_state(run_id=simulation_run_id)
        if state is None:
            raise ValueError(f"run_id {simulation_run_id} has no season state")
        branch_state = self.get_branch_state(branch_id=branch.branch_id) or self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        head_id = branch_state.head_checkpoint_id if branch_state is not None else branch.head_checkpoint_id
        if head_id is None:
            raise ValueError(f"branch {branch.branch_id} has no existing head checkpoint; capture initial first")
        if self.get_branch_checkpoint(checkpoint_id=head_id) is None:
            raise ValueError(f"branch {branch.branch_id} head checkpoint {head_id} was not found")
        # Normalize omitted locators to durable target provenance for one-per-bootstrap identity.
        locator_source = source_run_id or persisted_source
        locator_from = from_season if from_season is not None else legacy.source_rollover_from_season
        locator_to = to_season if to_season is not None else legacy.source_rollover_to_season
        existing_bootstrap = self.get_bootstrap_start_branch_checkpoint(
            branch_id=branch.branch_id, simulation_run_id=simulation_run_id, source_run_id=locator_source,
            from_season=locator_from, to_season=locator_to,
        )
        if existing_bootstrap is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing_bootstrap
        transitions = [row.__dict__ | {"transition": row.transition.model_dump(mode="json")} for row in self.list_player_transitions(run_id=persisted_source, to_season=locator_to)]
        next_players = [row.__dict__ | {"state": row.state.model_dump(mode="json")} for row in self.list_next_season_players(run_id=persisted_source, to_season=locator_to)]
        source_rollovers = [row.__dict__ for row in self.list_season_rollovers(run_id=persisted_source) if row.from_season == locator_from and row.to_season == locator_to]
        initial_player_refs = [{"player_id": row["player_id"]} for row in next_players]
        artifacts: dict[str, object] = {
            "target_initial_player_state_refs": initial_player_refs,
            "source_rollover_references": source_rollovers,
            "source_transition_rows": transitions,
            "source_next_season_player_rows": next_players,
            "target_initial_player_state_refs_hash": self.checkpoint_content_hash({"rows": initial_player_refs}),
            "source_rollover_references_hash": self.checkpoint_content_hash({"rows": source_rollovers}),
            "source_transition_rows_hash": self.checkpoint_content_hash({"rows": transitions}),
            "source_next_season_player_rows_hash": self.checkpoint_content_hash({"rows": next_players}),
        }
        artifacts["bootstrap_artifacts_hash"] = self.checkpoint_content_hash(artifacts)
        actions = [action.__dict__ for action in self.list_admin_actions(run_id=simulation_run_id)]
        seed_namespace = {"hierarchy": ["global", "season", "entries", "draws", "tournament_progression"], "global_seed": legacy.seed, "branch_seed": branch.branch_seed}
        serialized_state = state.model_dump(mode="json")
        payload: dict[str, object] = {
            "fork_capability": "not_forkable_player_state_not_migrated", "capture_mode": "legacy_bootstrap_start_capture_only",
            "payload_schema_version": "branch_checkpoint_payload_v1", "run_id": branch.run_id, "branch_id": branch.branch_id,
            "legacy_simulation_run_id": simulation_run_id, "parent_checkpoint_id": head_id,
            "bootstrap": {"locator": {"source_run_id": locator_source, "from_season": locator_from, "to_season": locator_to}, "target_run_id": simulation_run_id, "simulation_run_id": simulation_run_id, "source_run_id": persisted_source, "from_season": locator_from, "to_season": locator_to, "source_type": legacy.source_type, "parent_run_id": legacy.parent_run_id, "source_rollover_run_id": legacy.source_rollover_run_id, "source_rollover_from_season": legacy.source_rollover_from_season, "source_rollover_to_season": legacy.source_rollover_to_season, "source": "legacy_bootstrap_start"},
            "simulation_run": legacy.__dict__, "season_state": serialized_state, "bootstrap_artifacts": artifacts,
            "publications": {"latest_ranking_snapshot_references": [x.__dict__ for x in self.list_ranking_snapshot_records(run_id=simulation_run_id)][-1:], "latest_race_snapshot_references": [x.__dict__ for x in self.list_race_snapshot_records(run_id=simulation_run_id)][-1:]},
            "admin": {"actions": actions, "admin_actions_hash": self.checkpoint_content_hash({"actions": actions})},
            "provenance": {"world_id": legacy.world_id, "world_fingerprint": legacy.world_generation_fingerprint, "config_version": legacy.config_version, "config_fingerprint": legacy.config_fingerprint, "global_seed": legacy.seed, "branch_seed": branch.branch_seed, "seed_namespace": seed_namespace},
            "limitations": {"forkable": False, "replayable": False, "player_state": "hash_only_or_not_migrated", "prospects": "legacy_run_scoped_not_captured_as_durable_identity", "simulation_source": "legacy_simulation_run_state", "bootstrap_replay": "not_supported_yet", "cross_run_parent_link": "not_supported_in_r3j", "branch_timeline_stitching": "not_supported_yet"},
        }
        logical = self.checkpoint_content_hash({key: value for key, value in payload.items() if key != "parent_checkpoint_id"})
        command_id = command_id or f"legacy-bootstrap-start-capture:{simulation_run_id}:{locator_source}:{locator_from}:{locator_to}:{artifacts['bootstrap_artifacts_hash'][:24]}:{logical[:16]}"
        existing = self.get_branch_checkpoint_by_command_id(branch_id=branch.branch_id, command_id=command_id)
        if existing is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing
        suffix = hashlib.sha256(f"{branch.branch_id}\x00{command_id}".encode()).hexdigest()[:24]
        incomplete = BranchCheckpointRecord(checkpoint_id=f"checkpoint-{suffix}", run_id=branch.run_id, branch_id=branch.branch_id, parent_checkpoint_id=head_id, sequence=self.next_checkpoint_sequence(branch_id=branch.branch_id), kind=BRANCH_CHECKPOINT_KIND_BOOTSTRAP_START, season=legacy.season, week=1 if state.next_event_index == 0 else None, event_id=None, event_sequence=None, command_id=command_id, command_kind=BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_BOOTSTRAP_START_LEGACY_STATE, command_boundary="after_bootstrap_start_persisted", config_version=legacy.config_version, config_fingerprint=legacy.config_fingerprint, world_id=legacy.world_id, world_fingerprint=legacy.world_generation_fingerprint, global_seed=legacy.seed, branch_seed=branch.branch_seed, seed_namespace=seed_namespace, payload_schema_version="branch_checkpoint_payload_v1", content_hash_algorithm="sha256", content_hash="", payload=payload)
        checkpoint = BranchCheckpointRecord(**{**incomplete.__dict__, "content_hash": self.checkpoint_envelope_content_hash(incomplete)})
        created = self.create_branch_checkpoint(checkpoint)
        with self._session_factory.begin() as session:
            model = session.get(RunBranchModel, branch.branch_id)
            if model is not None:
                model.head_checkpoint_id = created.checkpoint_id
        self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        return created

    def capture_admin_action_checkpoint_for_legacy_simulation_run(
        self, *, simulation_run_id: str, action_id: str | None = None,
        action_sequence: int | None = None, command_id: str | None = None,
    ) -> BranchCheckpointRecord:
        """Capture a persisted legacy admin action without replaying or applying it.

        Legacy actions have no durable action id.  ``action_sequence`` is therefore
        the deterministic one-based position in ``list_admin_actions(run_id=...)``
        (``legacy_admin_action_sequence``), whose order is event_id, local action
        sequence, then immutable database row order.
        """
        if action_id is not None:
            raise ValueError("legacy admin actions do not have stable action_id; use action_sequence")
        if action_sequence is None:
            raise ValueError("an action_id or action_sequence is required")
        if action_sequence < 1:
            raise ValueError("action_sequence must be positive")
        legacy = self.get_simulation_run(run_id=simulation_run_id)
        if legacy is None:
            raise KeyError(f"run_id {simulation_run_id} was not found")
        branch = self.ensure_default_branch_for_simulation_run(simulation_run_id=simulation_run_id)
        if branch is None:
            raise KeyError(f"default branch for run_id {simulation_run_id} was not found")
        state = self.load_season_state(run_id=simulation_run_id)
        if state is None:
            raise ValueError(f"run_id {simulation_run_id} has no season state")
        branch_state = self.get_branch_state(branch_id=branch.branch_id) or self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
        effective_head_id = branch_state.head_checkpoint_id if branch_state is not None else branch.head_checkpoint_id
        if effective_head_id is None:
            raise ValueError(f"branch {branch.branch_id} has no existing head checkpoint; capture initial first")
        if self.get_branch_checkpoint(checkpoint_id=effective_head_id) is None:
            raise ValueError(f"branch {branch.branch_id} head checkpoint {effective_head_id} was not found")
        actions = [action.__dict__ for action in self.list_admin_actions(run_id=simulation_run_id)]
        if action_sequence > len(actions):
            raise ValueError(f"legacy admin action sequence {action_sequence} was not found for run_id {simulation_run_id}")
        target = actions[action_sequence - 1]
        existing_action = self.get_admin_action_applied_branch_checkpoint(branch_id=branch.branch_id, action_sequence=action_sequence)
        if existing_action is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing_action
        target_hash = self.checkpoint_content_hash(target)
        active_event = state.active_tournament.event if state.active_tournament is not None else None
        event = next((item for item in state.ordered_events if item.event_id == target["event_id"]), None)
        event_sequence = state.ordered_events.index(event) if event is not None else None
        week = event.week if event is not None else (active_event.week if active_event is not None else None)
        serialized_state = state.model_dump(mode="json")
        seed_namespace = {"hierarchy": ["global", "season", "entries", "draws", "tournament_progression"], "global_seed": legacy.seed, "branch_seed": branch.branch_seed}
        payload: dict[str, object] = {
            "fork_capability": "not_forkable_player_state_not_migrated", "capture_mode": "legacy_admin_action_applied_capture_only",
            "payload_schema_version": "branch_checkpoint_payload_v1", "run_id": branch.run_id, "branch_id": branch.branch_id,
            "legacy_simulation_run_id": simulation_run_id, "parent_checkpoint_id": effective_head_id,
            "admin_action": {"locator": "legacy_admin_action_sequence", "action_id": None, "action_sequence": action_sequence, "record": target, "source": "legacy_admin_action"},
            "simulation_run": legacy.__dict__,
            "season_state": serialized_state,
            "admin": {"actions": actions, "admin_actions_hash": self.checkpoint_content_hash({"actions": actions}), "target_admin_action_hash": target_hash},
            "provenance": {"world_id": legacy.world_id, "world_fingerprint": legacy.world_generation_fingerprint, "config_version": legacy.config_version,
                "config_fingerprint": legacy.config_fingerprint, "global_seed": legacy.seed, "branch_seed": branch.branch_seed, "seed_namespace": seed_namespace},
            "limitations": {"forkable": False, "replayable": False, "player_state": "hash_only_or_not_migrated",
                "prospects": "legacy_run_scoped_not_captured_as_durable_identity", "simulation_source": "legacy_simulation_run_state", "admin_action_replay": "not_supported_yet"},
        }
        state_fingerprint = self.checkpoint_content_hash({key: value for key, value in payload.items() if key != "parent_checkpoint_id"})
        command_id = command_id or f"legacy-admin-action-capture:{simulation_run_id}:{action_sequence}:{target_hash[:24]}:{state_fingerprint[:24]}"
        existing = self.get_branch_checkpoint_by_command_id(branch_id=branch.branch_id, command_id=command_id)
        if existing is not None:
            self.ensure_branch_state_for_branch(branch_id=branch.branch_id)
            return existing
        suffix = hashlib.sha256(f"{branch.branch_id}\x00{command_id}".encode("utf-8")).hexdigest()[:24]
        incomplete = BranchCheckpointRecord(
            checkpoint_id=f"checkpoint-{suffix}", run_id=branch.run_id, branch_id=branch.branch_id, parent_checkpoint_id=effective_head_id,
            sequence=self.next_checkpoint_sequence(branch_id=branch.branch_id), kind=BRANCH_CHECKPOINT_KIND_ADMIN_ACTION_APPLIED,
            season=state.season, week=week, event_id=target["event_id"], event_sequence=event_sequence, command_id=command_id,
            command_kind=BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_ADMIN_ACTION_LEGACY_STATE, command_boundary="after_admin_action_persisted",
            config_version=legacy.config_version, config_fingerprint=legacy.config_fingerprint, world_id=legacy.world_id,
            world_fingerprint=legacy.world_generation_fingerprint, global_seed=legacy.seed, branch_seed=branch.branch_seed,
            seed_namespace=seed_namespace, payload_schema_version="branch_checkpoint_payload_v1", content_hash_algorithm="sha256", content_hash="", payload=payload,
        )
        checkpoint = BranchCheckpointRecord(**{**incomplete.__dict__, "content_hash": self.checkpoint_envelope_content_hash(incomplete)})
        created = self.create_branch_checkpoint(checkpoint)
        with self._session_factory.begin() as session:
            model = session.get(RunBranchModel, branch.branch_id)
            if model is not None:
                model.head_checkpoint_id = created.checkpoint_id
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
        world_id: str | None = None,
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
            if world_id is not None:
                statement = statement.join(
                    SimulationRunModel,
                    SimulationRunModel.run_id == RunGeneratedPlayerProvenanceModel.run_id,
                ).where(SimulationRunModel.world_id == world_id)
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
