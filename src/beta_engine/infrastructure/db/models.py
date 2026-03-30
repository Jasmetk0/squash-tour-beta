"""SQLAlchemy persistence models for deterministic simulation history."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative SQLAlchemy base for persistence tables."""


class SimulationRunModel(Base):
    __tablename__ = "simulation_runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)


class SeasonStateModel(Base):
    __tablename__ = "season_state"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    next_event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    ordered_events_json: Mapped[str] = mapped_column(Text, nullable=False)
    completed_event_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    ranking_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    race_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)


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
