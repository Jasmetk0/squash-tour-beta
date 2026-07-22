"""SQLAlchemy persistence models for deterministic simulation history."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from beta_engine.infrastructure.db.checkpoint_boundaries import (
    BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED,
    BRANCH_CHECKPOINT_KIND_INITIAL,
    BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED,
)


class Base(DeclarativeBase):
    """Declarative SQLAlchemy base for persistence tables."""


class SimulationRunModel(Base):
    __tablename__ = "simulation_runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    world_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    world_generation_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    parent_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="fresh_seed")
    source_rollover_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_rollover_from_season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_rollover_to_season: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RunContainerModel(Base):
    """Product-level save/world container; distinct from legacy season attempts."""

    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint("storage_kind IN ('built_in', 'custom_local')", name="ck_runs_storage_kind"),
    )

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    storage_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="built_in")
    read_only: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    world_id: Mapped[str] = mapped_column(String(128), nullable=False)
    world_package_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    config_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    global_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeline_start_season: Mapped[int] = mapped_column(Integer, nullable=False)
    timeline_end_season: Mapped[int] = mapped_column(Integer, nullable=False)
    official_branch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class LegacySimulationRunMappingModel(Base):
    """One-to-one compatibility mapping from legacy season attempts to Runs."""

    __tablename__ = "legacy_simulation_run_mappings"

    simulation_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    mapping_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="legacy_single_attempt")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class RunBranchModel(Base):
    """Metadata for a timeline inside a product-level Run."""

    __tablename__ = "run_branches"

    branch_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    read_only: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    branch_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forked_from_branch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    forked_from_checkpoint_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    head_checkpoint_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    legacy_simulation_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class BranchStateModel(Base):
    """Mutable branch-head metadata; not a simulation state source."""

    __tablename__ = "branch_states"

    branch_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    head_checkpoint_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    current_season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_event_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state_schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="branch_state_v1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class BranchCheckpointModel(Base):
    """Immutable, capture-only checkpoint for a product Run branch."""

    __tablename__ = "branch_checkpoints"
    __table_args__ = (
        UniqueConstraint("branch_id", "sequence", name="uq_branch_checkpoints_branch_sequence"),
        UniqueConstraint("branch_id", "command_id", name="uq_branch_checkpoints_branch_command"),
        CheckConstraint("content_hash_algorithm = 'sha256'", name="ck_branch_checkpoints_sha256"),
        Index(
            "uq_branch_checkpoints_one_initial_per_branch",
            "branch_id",
            unique=True,
            sqlite_where=text(f"kind = '{BRANCH_CHECKPOINT_KIND_INITIAL}'"),
        ),
        Index(
            "uq_branch_checkpoints_one_event_completed_per_branch_event_sequence",
            "branch_id",
            "event_sequence",
            unique=True,
            sqlite_where=text(f"kind = '{BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED}'"),
        ),
        Index(
            "uq_branch_checkpoints_one_week_completed_per_branch_season_week",
            "branch_id",
            "season",
            "week",
            unique=True,
            sqlite_where=text(f"kind = '{BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED}'"),
        ),
    )

    checkpoint_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parent_checkpoint_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    command_id: Mapped[str] = mapped_column(String(128), nullable=False)
    command_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    command_boundary: Mapped[str] = mapped_column(String(64), nullable=False)
    config_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    world_id: Mapped[str] = mapped_column(String(128), nullable=False)
    world_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    global_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed_namespace_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash_algorithm: Mapped[str] = mapped_column(String(16), nullable=False, default="sha256")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class BranchForkCommandModel(Base):
    """Durable idempotency record for one atomic internal Branch fork."""

    __tablename__ = "branch_fork_commands"

    command_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    product_run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    source_branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_checkpoint_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_branch_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    target_legacy_simulation_run_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    result_branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    result_checkpoint_id: Mapped[str] = mapped_column(String(128), nullable=False)
    result_legacy_simulation_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class OfficialBranchSelectionCommandModel(Base):
    """Durable idempotency and audit record for official Branch selection."""

    __tablename__ = "official_branch_selection_commands"

    command_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    product_run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_previous_official_branch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    result_previous_official_branch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result_official_branch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audit_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class SeasonStateModel(Base):
    __tablename__ = "season_state"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    next_event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    ordered_events_json: Mapped[str] = mapped_column(Text, nullable=False)
    completed_event_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    ranking_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    race_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_tournament_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class CompletedEventModel(Base):
    __tablename__ = "completed_events"
    __table_args__ = (UniqueConstraint("run_id", "event_sequence", name="uq_completed_events_run_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)


class CompletedEventMetadataModel(Base):
    __tablename__ = "completed_event_metadata"
    __table_args__ = (UniqueConstraint("run_id", "event_id", name="uq_completed_event_metadata_run_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tournament_result_json: Mapped[str] = mapped_column(Text, nullable=False)


class CompletedTournamentInputModel(Base):
    __tablename__ = "completed_tournament_inputs"
    __table_args__ = (UniqueConstraint("run_id", "event_id", name="uq_completed_tournament_input_run_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class RankingSnapshotModel(Base):
    __tablename__ = "ranking_snapshots"
    __table_args__ = (UniqueConstraint("run_id", "snapshot_sequence", name="uq_ranking_snapshots_run_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    snapshot_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    as_of_season: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class RaceSnapshotModel(Base):
    __tablename__ = "race_snapshots"
    __table_args__ = (UniqueConstraint("run_id", "snapshot_sequence", name="uq_race_snapshots_run_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    snapshot_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    as_of_season: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class FinalsQualificationModel(Base):
    __tablename__ = "finals_qualification"
    __table_args__ = (UniqueConstraint("run_id", "season", name="uq_finals_qualification_run_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    source_as_of_season: Mapped[int] = mapped_column(Integer, nullable=False)
    source_as_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class FinalsResultModel(Base):
    __tablename__ = "finals_results"
    __table_args__ = (UniqueConstraint("run_id", "season", name="uq_finals_results_run_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_as_of_season: Mapped[int] = mapped_column(Integer, nullable=False)
    source_as_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class SeasonRolloverModel(Base):
    __tablename__ = "season_rollovers"
    __table_args__ = (UniqueConstraint("run_id", "to_season", name="uq_season_rollovers_run_to_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    from_season: Mapped[int] = mapped_column(Integer, nullable=False)
    to_season: Mapped[int] = mapped_column(Integer, nullable=False)
    transitioned_players: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)


class PlayerSeasonTransitionModel(Base):
    __tablename__ = "player_season_transitions"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "to_season",
            "player_id",
            name="uq_player_season_transitions_run_to_season_player",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    from_season: Mapped[int] = mapped_column(Integer, nullable=False)
    to_season: Mapped[int] = mapped_column(Integer, nullable=False)
    player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class NextSeasonPlayerModel(Base):
    __tablename__ = "next_season_players"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "to_season",
            "player_id",
            name="uq_next_season_players_run_to_season_player",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    from_season: Mapped[int] = mapped_column(Integer, nullable=False)
    to_season: Mapped[int] = mapped_column(Integer, nullable=False)
    player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class AdminActionModel(Base):
    __tablename__ = "admin_actions"
    __table_args__ = (UniqueConstraint("run_id", "event_id", "action_sequence", name="uq_admin_actions_run_event_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class RunTalentPlanModel(Base):
    __tablename__ = "run_talent_plans"
    __table_args__ = (UniqueConstraint("run_id", "season", name="uq_run_talent_plan_run_season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    total_talents: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)


class RunTalentCountryAllocationModel(Base):
    __tablename__ = "run_talent_country_allocations"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "season",
            "country_code",
            name="uq_run_talent_country_allocation_run_season_country",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    planned_count: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_weights_json: Mapped[str] = mapped_column(Text, nullable=False)
    actual_band_counts_json: Mapped[str] = mapped_column(Text, nullable=False)
    bias_profile_json: Mapped[str] = mapped_column(Text, nullable=False)
    dampener_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class RunProspectModel(Base):
    __tablename__ = "run_prospects"
    __table_args__ = (UniqueConstraint("run_id", "prospect_id", name="uq_run_prospects_run_prospect"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prospect_id: Mapped[str] = mapped_column(String(160), nullable=False)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    world_id: Mapped[str] = mapped_column(String(128), nullable=False)
    season_start_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    season_label: Mapped[str] = mapped_column(String(32), nullable=False)
    season_week: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    calendar_year: Mapped[int] = mapped_column(Integer, nullable=False)
    year_week: Mapped[int] = mapped_column(Integer, nullable=False)
    birth_year: Mapped[int] = mapped_column(Integer, nullable=False)
    birth_year_week: Mapped[int] = mapped_column(Integer, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    country_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="prospect")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="weekly_15yo_cohort")
    cohort_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_version: Mapped[str] = mapped_column(String(64), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    identity_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    development_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    potential_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    trait_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    development_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    potential_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    trait_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class RunGeneratedPlayerProvenanceModel(Base):
    __tablename__ = "run_generated_player_provenance"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "season",
            "player_id",
            name="uq_run_generated_player_provenance_run_season_player",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    talent_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    talent_seed_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    quality_band: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_top_band: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="planner_generated")
    override_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    origin_source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    origin_quality_band: Mapped[str | None] = mapped_column(String(64), nullable=True)
    origin_override_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    origin_season: Mapped[int | None] = mapped_column(Integer, nullable=True)
