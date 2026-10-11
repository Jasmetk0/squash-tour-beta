"""Read-only ranking/race table service derived from active season players."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService, SeasonActivePlayer

RankingTableType = Literal["ranking", "race"]

RANKING_TABLE_WARNINGS = [
    "Table is derived from current active season players.",
    "Rolling 61-week ranking not implemented.",
    "Best-N ranking selection not implemented.",
    "Weekly publication snapshots not implemented.",
    "Movement not implemented.",
]


class RankingTableFilters(BaseModel):
    country_code: str | None = None
    search: str | None = None
    include_zero_points: bool = True
    min_points: int | None = Field(default=None, ge=0)


class RankingTableRow(BaseModel):
    rank: int = Field(ge=1)
    dense_rank: int = Field(ge=1)
    ordinal_position: int = Field(ge=1)
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
    manual_override: bool
    source_generation: str
    locked_from_initial_pool: bool
    movement: None = None
    previous_rank: None = None
    events_counted: None = None
    player_fingerprint: str | None = None


class RankingTableSummary(BaseModel):
    season: str
    table_type: RankingTableType
    player_count: int = Field(ge=0)
    total_source_players: int = Field(ge=0)
    ranked_player_count: int = Field(ge=0)
    zero_point_players: int = Field(ge=0)
    countries_represented: int = Field(ge=0)
    leader_player_id: str | None = None
    leader_points: int | None = None
    generated_from_active_players_fingerprint: str
    rolling_ranking_implemented: bool = False
    best_n_implemented: bool = False
    movement_implemented: bool = False


class RankingTableMetadata(BaseModel):
    season: str
    table_type: RankingTableType
    source: str = "season_active_players"
    active_players_fingerprint: str
    generated_fingerprint: str
    ranking_basis: str
    filters: RankingTableFilters
    limit: int | None = None
    warnings: list[str] = Field(default_factory=list)


class RankingTableResponse(BaseModel):
    rows: list[RankingTableRow]
    summary: RankingTableSummary
    metadata: RankingTableMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonRankingTableService:
    """Build deterministic read-only ranking/race tables from persisted active players."""

    active_players_service: InitialPoolSeasonBootstrapService

    def get_table(
        self,
        *,
        season: str = "2000/2001",
        table_type: RankingTableType = "ranking",
        limit: int | None = None,
        country_code: str | None = None,
        search: str | None = None,
        include_zero_points: bool = True,
        min_points: int | None = None,
    ) -> RankingTableResponse:
        if table_type not in {"ranking", "race"}:
            raise ValueError("table_type must be 'ranking' or 'race'")
        if limit is not None and limit < 1:
            raise ValueError("limit must be greater than or equal to 1")
        if min_points is not None and min_points < 0:
            raise ValueError("min_points must be greater than or equal to 0")

        active_players = list(self.active_players_service.get_active_players(season=season).players)
        if not active_players:
            raise ValueError(f"No active season players found for season '{season}'. Persist active players before reading rankings.")

        active_fingerprint = self._fingerprint([player.model_dump(mode="json") for player in sorted(active_players, key=lambda item: item.player_id)])
        full_rows = self._rank_rows(players=active_players, table_type=table_type)
        filters = RankingTableFilters(
            country_code=country_code.strip().upper() if country_code and country_code.strip() else None,
            search=search.strip() if search and search.strip() else None,
            include_zero_points=include_zero_points,
            min_points=min_points,
        )
        rows = self._apply_filters(full_rows, filters=filters)
        if limit is not None:
            rows = rows[:limit]

        leader = rows[0] if rows else None
        summary = RankingTableSummary(
            season=season,
            table_type=table_type,
            player_count=len(rows),
            total_source_players=len(active_players),
            ranked_player_count=sum(1 for row in rows if row.table_points > 0),
            zero_point_players=sum(1 for row in rows if row.table_points == 0),
            countries_represented=len({row.country_code for row in rows}),
            leader_player_id=leader.player_id if leader else None,
            leader_points=leader.table_points if leader else None,
            generated_from_active_players_fingerprint=active_fingerprint,
        )
        basis = "current active season player ranking_points" if table_type == "ranking" else "current active season player race_points"
        generated_fingerprint = self._fingerprint(
            {
                "rows": [row.model_dump(mode="json") for row in rows],
                "summary": summary.model_dump(mode="json"),
                "active_players_fingerprint": active_fingerprint,
                "filters": filters.model_dump(mode="json"),
                "limit": limit,
                "ranking_basis": basis,
            }
        )
        metadata = RankingTableMetadata(
            season=season,
            table_type=table_type,
            active_players_fingerprint=active_fingerprint,
            generated_fingerprint=generated_fingerprint,
            ranking_basis=basis,
            filters=filters,
            limit=limit,
            warnings=list(RANKING_TABLE_WARNINGS),
        )
        return RankingTableResponse(
            rows=rows,
            summary=summary,
            metadata=metadata,
            validation_warnings=list(RANKING_TABLE_WARNINGS),
            validation_errors=[],
        )

    def _rank_rows(self, *, players: list[SeasonActivePlayer], table_type: RankingTableType) -> list[RankingTableRow]:
        ordered = sorted(players, key=self._sort_key(table_type))
        rows: list[RankingTableRow] = []
        previous_points: int | None = None
        previous_rank = 0
        dense_rank = 0
        for index, player in enumerate(ordered, start=1):
            table_points = player.ranking_points if table_type == "ranking" else player.race_points
            if previous_points is None or table_points != previous_points:
                rank = index
                dense_rank += 1
            else:
                rank = previous_rank
            rows.append(
                RankingTableRow(
                    rank=rank,
                    dense_rank=dense_rank,
                    ordinal_position=index,
                    player_id=player.player_id,
                    player_name=player.name,
                    country_code=player.country_code,
                    nationality=player.nationality,
                    age_years_at_season_start=player.age_years_at_season_start,
                    career_stage=player.career_stage,
                    current_ability=player.current_ability,
                    potential_ability=player.potential_ability,
                    potential_tier=str(player.potential_tier),
                    archetype=player.archetype,
                    play_style=player.play_style,
                    ranking_points=player.ranking_points,
                    race_points=player.race_points,
                    table_points=table_points,
                    manual_override=player.manual_override,
                    source_generation=player.source_generation,
                    locked_from_initial_pool=player.locked_from_initial_pool,
                    player_fingerprint=player.source_generation_fingerprint or player.bootstrap_fingerprint,
                )
            )
            previous_points = table_points
            previous_rank = rank
        return rows

    @staticmethod
    def _sort_key(table_type: RankingTableType):
        if table_type == "ranking":
            return lambda player: (-player.ranking_points, -player.race_points, -player.current_ability, player.name.casefold(), player.player_id)
        return lambda player: (-player.race_points, -player.ranking_points, -player.current_ability, player.name.casefold(), player.player_id)

    @staticmethod
    def _apply_filters(rows: list[RankingTableRow], *, filters: RankingTableFilters) -> list[RankingTableRow]:
        filtered = list(rows)
        if filters.country_code:
            filtered = [row for row in filtered if row.country_code == filters.country_code]
        if filters.search:
            needle = filters.search.casefold()
            filtered = [row for row in filtered if needle in row.player_name.casefold() or needle in row.player_id.casefold()]
        if not filters.include_zero_points:
            filtered = [row for row in filtered if row.table_points > 0]
        if filters.min_points is not None:
            filtered = [row for row in filtered if row.table_points >= filters.min_points]
        return filtered

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
