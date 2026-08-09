"""Weekly ranking/race snapshot foundation derived from active season players."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.domain.calendar import DEFAULT_SEASON_START_YEAR_WEEK, TOTAL_SEASON_WEEKS, season_week_to_calendar_position
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.application.season_ranking_table_service import RankingTableResponse, RankingTableRow, RankingTableType, SeasonRankingTableService

SNAPSHOT_SOURCE = "active_season_players"
PUBLICATION_BASIS = "current active season player ranking_points/race_points"
FOUNDATION_WARNINGS = [
    "Rolling 61-week ranking not implemented.",
    "Best-N ranking selection not implemented.",
    "Snapshot is based on current active season player totals, not rolling expiry.",
]

MovementLabel = Literal["new", "up", "down", "same", "none"]


class RankingSnapshotRow(BaseModel):
    rank: int = Field(ge=1)
    dense_rank: int = Field(ge=1)
    ordinal_position: int = Field(ge=1)
    previous_rank: int | None = None
    movement: int | None = None
    movement_label: MovementLabel = "none"
    player_id: str
    player_name: str
    country_code: str
    nationality: str
    age_years_at_season_start: int
    career_stage: str
    current_ability: int
    potential_ability: int
    potential_tier: str
    archetype: str
    play_style: str
    ranking_points: int = Field(ge=0)
    race_points: int = Field(ge=0)
    table_points: int = Field(ge=0)
    source_generation: str
    manual_override: bool
    locked_from_initial_pool: bool
    player_fingerprint: str | None = None


class RankingSnapshotSummary(BaseModel):
    season: str
    season_week: int = Field(ge=1, le=TOTAL_SEASON_WEEKS)
    table_type: RankingTableType
    player_count: int = Field(ge=0)
    ranked_player_count: int = Field(ge=0)
    zero_point_players: int = Field(ge=0)
    countries_represented: int = Field(ge=0)
    leader_player_id: str | None = None
    leader_points: int | None = None
    previous_snapshot_key: str | None = None
    new_entries_count: int = Field(ge=0)
    moved_up_count: int = Field(ge=0)
    moved_down_count: int = Field(ge=0)
    unchanged_count: int = Field(ge=0)
    rolling_ranking_implemented: bool = False
    best_n_implemented: bool = False
    movement_implemented: bool = True


class RankingSnapshotMetadata(BaseModel):
    season: str
    season_week: int = Field(ge=1, le=TOTAL_SEASON_WEEKS)
    calendar_year: int | None = None
    year_week: int | None = None
    source: Literal["active_season_players"] = SNAPSHOT_SOURCE
    active_players_fingerprint: str
    point_awards_fingerprint: str | None = None
    ranking_table_fingerprint: str
    race_table_fingerprint: str
    snapshot_fingerprint: str
    previous_snapshot_fingerprint: str | None = None
    dry_run: bool
    persisted: bool
    generated_seed: int
    persistence_path: str | None = None
    publication_basis: str = PUBLICATION_BASIS
    rolling_ranking_implemented: bool = False
    best_n_implemented: bool = False


class RankingSnapshotTable(BaseModel):
    table_type: RankingTableType
    rows: list[RankingSnapshotRow]
    summary: RankingSnapshotSummary
    metadata: RankingSnapshotMetadata


class WeeklyRankingSnapshot(BaseModel):
    season: str
    season_week: int = Field(ge=1, le=TOTAL_SEASON_WEEKS)
    calendar_year: int | None = None
    year_week: int | None = None
    seed: int
    dry_run: bool
    persisted: bool
    ranking_table: RankingSnapshotTable
    race_table: RankingSnapshotTable
    summary: dict[str, RankingSnapshotSummary]
    metadata: RankingSnapshotMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class WeeklyRankingSnapshotResult(BaseModel):
    snapshot: WeeklyRankingSnapshot | None = None
    snapshot_exists: bool = False
    summary: dict[str, RankingSnapshotSummary] | None = None
    metadata: RankingSnapshotMetadata | None = None
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class WeeklyRankingSnapshotGenerateRequest(BaseModel):
    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False
    include_zero_points: bool = True
    limit: int | None = Field(default=None, ge=1)


class SeasonRankingSnapshotRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshots_by_key: dict[str, WeeklyRankingSnapshot] = Field(default_factory=dict)


@dataclass(slots=True)
class SeasonRankingSnapshotService:
    ranking_table_service: SeasonRankingTableService
    calendar_service: SeasonCalendarService | None = None
    point_awards_service: SeasonPointAwardsService | None = None
    snapshots_path: Path = Path("config/simulation/season_ranking_snapshots.json")

    def __post_init__(self) -> None:
        if not isinstance(self.snapshots_path, Path):
            self.snapshots_path = Path(self.snapshots_path)

    def get_snapshot(self, *, season: str, season_week: int) -> WeeklyRankingSnapshotResult:
        errors = self._validate_week(season_week)
        if errors:
            return WeeklyRankingSnapshotResult(snapshot=None, snapshot_exists=False, validation_errors=errors)
        snapshot = self._load_registry().snapshots_by_key.get(self._key(season, season_week))
        if snapshot is None:
            return WeeklyRankingSnapshotResult(snapshot=None, snapshot_exists=False, validation_warnings=["No published snapshot for this week."])
        return WeeklyRankingSnapshotResult(snapshot=snapshot, snapshot_exists=True, summary=snapshot.summary, metadata=snapshot.metadata, validation_warnings=snapshot.validation_warnings, validation_errors=snapshot.validation_errors)

    def list_snapshots(self, *, season: str) -> dict[str, Any]:
        registry = self._load_registry()
        snapshots = [snapshot for key, snapshot in registry.snapshots_by_key.items() if key.startswith(f"{season}:")]
        snapshots.sort(key=lambda snapshot: snapshot.season_week)
        return {"season": season, "snapshots": [{"snapshot_key": self._key(item.season, item.season_week), "season_week": item.season_week, "calendar_year": item.calendar_year, "year_week": item.year_week, "snapshot_fingerprint": item.metadata.snapshot_fingerprint, "ranking_leader_player_id": item.ranking_table.summary.leader_player_id, "race_leader_player_id": item.race_table.summary.leader_player_id} for item in snapshots], "count": len(snapshots)}

    def generate_snapshot(self, *, season: str, season_week: int, request: WeeklyRankingSnapshotGenerateRequest) -> WeeklyRankingSnapshotResult:
        errors = self._validate_week(season_week)
        warnings = list(FOUNDATION_WARNINGS)
        key = self._key(season, season_week)
        registry = self._load_registry()
        if key in registry.snapshots_by_key and not request.dry_run and not request.overwrite_existing:
            errors.append("Snapshot already exists for this season/week. Set overwrite_existing=true to replace it.")
        if request.limit is not None and request.limit < 1:
            errors.append("limit must be greater than or equal to 1")
        if errors:
            return WeeklyRankingSnapshotResult(snapshot=None, snapshot_exists=key in registry.snapshots_by_key, validation_warnings=warnings, validation_errors=errors)

        try:
            ranking = self.ranking_table_service.get_table(season=season, table_type="ranking", include_zero_points=request.include_zero_points, limit=request.limit)
            race = self.ranking_table_service.get_table(season=season, table_type="race", include_zero_points=request.include_zero_points, limit=request.limit)
        except ValueError as exc:
            return WeeklyRankingSnapshotResult(snapshot=None, snapshot_exists=key in registry.snapshots_by_key, validation_warnings=warnings, validation_errors=[str(exc)])

        previous_key, previous = self._previous_snapshot(registry, season=season, season_week=season_week)
        if previous is None:
            warnings.append("No previous snapshot exists for this season before the requested week.")
        calendar_year, year_week, calendar_warning = self._calendar_position(season=season, season_week=season_week)
        if calendar_warning:
            warnings.append(calendar_warning)
        point_awards_fingerprint = self._point_awards_fingerprint(season)
        if point_awards_fingerprint is None:
            warnings.append("Point awards fingerprint unavailable.")

        previous_fingerprint = previous.metadata.snapshot_fingerprint if previous else None
        ranking_rows = self._snapshot_rows(ranking.rows, previous.ranking_table.rows if previous else None)
        race_rows = self._snapshot_rows(race.rows, previous.race_table.rows if previous else None)
        ranking_summary = self._summary(season=season, season_week=season_week, table_type="ranking", rows=ranking_rows, previous_key=previous_key, previous_exists=previous is not None)
        race_summary = self._summary(season=season, season_week=season_week, table_type="race", rows=race_rows, previous_key=previous_key, previous_exists=previous is not None)
        raw_fp_payload = {
            "season": season,
            "season_week": season_week,
            "seed": request.seed,
            "active_players_fingerprint": ranking.metadata.active_players_fingerprint,
            "ranking_rows": [row.model_dump(mode="json") for row in ranking_rows],
            "race_rows": [row.model_dump(mode="json") for row in race_rows],
            "previous_snapshot_fingerprint": previous_fingerprint,
        }
        snapshot_fingerprint = self._fingerprint(raw_fp_payload)
        metadata = RankingSnapshotMetadata(
            season=season,
            season_week=season_week,
            calendar_year=calendar_year,
            year_week=year_week,
            active_players_fingerprint=ranking.metadata.active_players_fingerprint,
            point_awards_fingerprint=point_awards_fingerprint,
            ranking_table_fingerprint=ranking.metadata.generated_fingerprint,
            race_table_fingerprint=race.metadata.generated_fingerprint,
            snapshot_fingerprint=snapshot_fingerprint,
            previous_snapshot_fingerprint=previous_fingerprint,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            generated_seed=request.seed,
            persistence_path=None if request.dry_run else str(self.snapshots_path),
        )
        snapshot = WeeklyRankingSnapshot(
            season=season,
            season_week=season_week,
            calendar_year=calendar_year,
            year_week=year_week,
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            ranking_table=RankingSnapshotTable(table_type="ranking", rows=ranking_rows, summary=ranking_summary, metadata=metadata),
            race_table=RankingSnapshotTable(table_type="race", rows=race_rows, summary=race_summary, metadata=metadata),
            summary={"ranking": ranking_summary, "race": race_summary},
            metadata=metadata,
            validation_warnings=warnings,
            validation_errors=[],
        )
        if not request.dry_run:
            next_snapshots = dict(registry.snapshots_by_key)
            next_snapshots[key] = snapshot
            self._save_registry(SeasonRankingSnapshotRegistry(snapshots_by_key=next_snapshots))
        return WeeklyRankingSnapshotResult(snapshot=snapshot, snapshot_exists=key in registry.snapshots_by_key or not request.dry_run, summary=snapshot.summary, metadata=snapshot.metadata, validation_warnings=warnings, validation_errors=[])

    @staticmethod
    def _snapshot_rows(rows: list[RankingTableRow], previous_rows: list[RankingSnapshotRow] | None) -> list[RankingSnapshotRow]:
        previous_by_player = {row.player_id: row.rank for row in previous_rows or []}
        previous_exists = previous_rows is not None
        snapshot_rows: list[RankingSnapshotRow] = []
        for row in rows:
            previous_rank = previous_by_player.get(row.player_id)
            movement = None if previous_rank is None else previous_rank - row.rank
            if not previous_exists:
                label: MovementLabel = "none"
            elif previous_rank is None:
                label = "new"
            elif movement > 0:
                label = "up"
            elif movement < 0:
                label = "down"
            else:
                label = "same"
            snapshot_rows.append(RankingSnapshotRow(**row.model_dump(mode="json", exclude={"movement", "previous_rank", "events_counted"}), previous_rank=previous_rank, movement=movement, movement_label=label))
        return snapshot_rows

    @staticmethod
    def _summary(*, season: str, season_week: int, table_type: RankingTableType, rows: list[RankingSnapshotRow], previous_key: str | None, previous_exists: bool) -> RankingSnapshotSummary:
        leader = rows[0] if rows else None
        return RankingSnapshotSummary(
            season=season,
            season_week=season_week,
            table_type=table_type,
            player_count=len(rows),
            ranked_player_count=sum(1 for row in rows if row.table_points > 0),
            zero_point_players=sum(1 for row in rows if row.table_points == 0),
            countries_represented=len({row.country_code for row in rows}),
            leader_player_id=leader.player_id if leader else None,
            leader_points=leader.table_points if leader else None,
            previous_snapshot_key=previous_key,
            new_entries_count=sum(1 for row in rows if row.movement_label == "new"),
            moved_up_count=sum(1 for row in rows if row.movement_label == "up"),
            moved_down_count=sum(1 for row in rows if row.movement_label == "down"),
            unchanged_count=sum(1 for row in rows if row.movement_label == "same") if previous_exists else 0,
        )

    def _previous_snapshot(self, registry: SeasonRankingSnapshotRegistry, *, season: str, season_week: int) -> tuple[str | None, WeeklyRankingSnapshot | None]:
        candidates = [(snapshot.season_week, key, snapshot) for key, snapshot in registry.snapshots_by_key.items() if snapshot.season == season and snapshot.season_week < season_week]
        if not candidates:
            return None, None
        _, key, snapshot = max(candidates, key=lambda item: item[0])
        return key, snapshot

    def _calendar_position(self, *, season: str, season_week: int) -> tuple[int | None, int | None, str | None]:
        season_start_year_week = DEFAULT_SEASON_START_YEAR_WEEK
        if self.calendar_service is not None:
            result = self.calendar_service.get_calendar(season=season)
            if result.metadata is not None:
                season_start_year_week = result.metadata.season_start_year_week
        try:
            position = season_week_to_calendar_position(
                season=season,
                season_week=season_week,
                season_start_year_week=season_start_year_week,
            )
        except ValueError as exc:
            return None, None, f"Calendar year/week mapping failed: {exc}"
        return position.calendar_year, position.year_week, None

    def _point_awards_fingerprint(self, season: str) -> str | None:
        if self.point_awards_service is None:
            return None
        registry = self.point_awards_service._load_registry()
        relevant = {event_id: package.model_dump(mode="json") for event_id, package in registry.awards_by_event_id.items() if package.season == season}
        applied = {event_id: record.model_dump(mode="json") for event_id, record in registry.applied_events.items() if record.season == season}
        return self._fingerprint({"awards_by_event_id": relevant, "applied_events": applied})

    @staticmethod
    def _validate_week(season_week: int) -> list[str]:
        return [] if 1 <= season_week <= TOTAL_SEASON_WEEKS else ["season_week must be between 1 and 61"]

    @staticmethod
    def _key(season: str, season_week: int) -> str:
        return f"{season}:{season_week}"

    def _load_registry(self) -> SeasonRankingSnapshotRegistry:
        if not self.snapshots_path.exists():
            return SeasonRankingSnapshotRegistry()
        return SeasonRankingSnapshotRegistry.model_validate(json.loads(self.snapshots_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: SeasonRankingSnapshotRegistry) -> None:
        self.snapshots_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.snapshots_path.with_suffix(f"{self.snapshots_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.snapshots_path)

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
