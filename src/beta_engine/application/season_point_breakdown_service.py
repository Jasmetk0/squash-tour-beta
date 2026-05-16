"""Read-only player point breakdowns from persisted season point award packages."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService, SeasonActivePlayer
from beta_engine.application.season_point_awards_service import EventPointAwardPackage, SeasonPointAwardsService

PointBreakdownTableType = Literal["ranking", "race", "both"]

FOUNDATION_WARNINGS = [
    "Point breakdowns are read from persisted point award packages.",
    "Rolling 61-week ranking not implemented.",
    "Best-N ranking selection not implemented.",
    "Movement/history not implemented.",
]


class PlayerPointBreakdownFilters(BaseModel):
    player_id: str | None = None
    search: str | None = None
    country_code: str | None = None
    include_zero_point_awards: bool = False


class PlayerPointBreakdownEntry(BaseModel):
    event_id: str
    season: str
    season_week: int | None = None
    calendar_year: int | None = None
    year_week: int | None = None
    event_name: str | None = None
    category: str | None = None
    tour_level: str | None = None
    template_id: str | None = None
    host_country: str | None = None
    reached_stage: str
    qualifier: bool
    seed_number: int | None = None
    ranking_points_awarded: int = Field(ge=0)
    race_points_awarded: int = Field(ge=0)
    applied: bool
    point_distribution_source: str | None = None
    source_result_fingerprint: str
    source_player_result_fingerprint: str
    award_fingerprint: str
    award_package_fingerprint: str
    result_package_fingerprint: str | None = None


class PlayerPointBreakdownConsistency(BaseModel):
    ranking_points_match_active_player: bool
    race_points_match_active_player: bool
    ranking_points_delta: int
    race_points_delta: int


class PlayerPointBreakdown(BaseModel):
    player_id: str
    player_name: str
    country_code: str
    nationality: str | None = None
    season: str
    current_ranking_points: int = Field(ge=0)
    current_race_points: int = Field(ge=0)
    breakdown_ranking_points_total: int = Field(ge=0)
    breakdown_race_points_total: int = Field(ge=0)
    applied_ranking_points_total: int = Field(ge=0)
    applied_race_points_total: int = Field(ge=0)
    unapplied_ranking_points_total: int = Field(ge=0)
    unapplied_race_points_total: int = Field(ge=0)
    applied_event_count: int = Field(ge=0)
    total_event_count: int = Field(ge=0)
    consistency: PlayerPointBreakdownConsistency
    entries: list[PlayerPointBreakdownEntry]


class PlayerPointBreakdownSummaryRow(BaseModel):
    player_id: str
    player_name: str
    country_code: str
    ranking_points: int = Field(ge=0)
    race_points: int = Field(ge=0)
    breakdown_ranking_points_total: int = Field(ge=0)
    breakdown_race_points_total: int = Field(ge=0)
    applied_event_count: int = Field(ge=0)
    total_event_count: int = Field(ge=0)
    consistency_ok: bool
    top_result_stage: str | None = None
    top_result_event_id: str | None = None


class PlayerPointBreakdownMetadata(BaseModel):
    season: str
    source: str = "season_point_awards"
    active_players_fingerprint: str
    point_awards_fingerprint: str
    generated_fingerprint: str
    applied_only: bool
    table_type: PointBreakdownTableType
    filters: PlayerPointBreakdownFilters
    limit: int | None = None
    rolling_ranking_implemented: bool = False
    best_n_implemented: bool = False
    movement_implemented: bool = False


class PlayerPointBreakdownResponse(BaseModel):
    breakdown: PlayerPointBreakdown | None = None
    summary_rows: list[PlayerPointBreakdownSummaryRow] = Field(default_factory=list)
    metadata: PlayerPointBreakdownMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonPointBreakdownService:
    """Build deterministic read-only point source explanations from persisted awards."""

    point_awards_service: SeasonPointAwardsService
    active_players_service: InitialPoolSeasonBootstrapService
    calendar_service: SeasonCalendarService | None = None

    def __post_init__(self) -> None:
        if self.calendar_service is None:
            self.calendar_service = self.point_awards_service.calendar_service

    def get_player_point_breakdown(
        self,
        *,
        season: str = "2000/2001",
        player_id: str | None = None,
        search: str | None = None,
        country_code: str | None = None,
        applied_only: bool = True,
        table_type: PointBreakdownTableType = "both",
        limit: int | None = None,
        include_zero_point_awards: bool = False,
    ) -> PlayerPointBreakdownResponse:
        if table_type not in {"ranking", "race", "both"}:
            raise ValueError("table_type must be 'ranking', 'race', or 'both'")
        if limit is not None and limit < 1:
            raise ValueError("limit must be greater than or equal to 1")

        normalized_player_id = player_id.strip() if player_id and player_id.strip() else None
        normalized_search = search.strip() if search and search.strip() else None
        normalized_country = country_code.strip().upper() if country_code and country_code.strip() else None
        filters = PlayerPointBreakdownFilters(
            player_id=normalized_player_id,
            search=normalized_search,
            country_code=normalized_country,
            include_zero_point_awards=include_zero_point_awards,
        )

        active_players = list(self.active_players_service.get_active_players(season=season).players)
        if not active_players:
            raise ValueError(f"No active season players found for season '{season}'. Persist active players before reading point breakdowns.")
        active_by_id = {player.player_id: player for player in active_players}
        if normalized_player_id is not None and normalized_player_id not in active_by_id:
            raise ValueError(f"Player '{normalized_player_id}' was not found in active season players for season '{season}'.")

        registry = self.point_awards_service._load_registry()
        season_packages = [
            package for package in registry.awards_by_event_id.values()
            if package.season == season and package.persisted and not package.dry_run
        ]
        season_packages = sorted(season_packages, key=lambda package: package.event_id)
        applied_event_ids = {event_id for event_id, record in registry.applied_events.items() if record.applied and record.season == season}
        selected_packages = [package for package in season_packages if (self._package_applied(package, applied_event_ids) or not applied_only)]

        calendar_events = self._calendar_events_by_id(season)
        entries_by_player: dict[str, list[PlayerPointBreakdownEntry]] = {player.player_id: [] for player in active_players}
        for package in selected_packages:
            applied = self._package_applied(package, applied_event_ids)
            for award in sorted(package.awards, key=lambda item: item.player_id):
                if award.player_id not in entries_by_player:
                    continue
                if not include_zero_point_awards and self._is_zero_award(award.ranking_points_awarded, award.race_points_awarded, table_type):
                    continue
                event = calendar_events.get(package.event_id)
                entries_by_player[award.player_id].append(PlayerPointBreakdownEntry(
                    event_id=package.event_id,
                    season=package.season,
                    season_week=getattr(event, "season_week", None),
                    calendar_year=getattr(event, "calendar_year", None),
                    year_week=getattr(event, "year_week", None),
                    event_name=package.event_name,
                    category=package.category,
                    tour_level=package.tour_level,
                    template_id=package.template_id,
                    host_country=getattr(event, "host_country", None),
                    reached_stage=award.reached_stage,
                    qualifier=award.qualifier,
                    seed_number=award.seed_number,
                    ranking_points_awarded=award.ranking_points_awarded,
                    race_points_awarded=award.race_points_awarded,
                    applied=applied,
                    point_distribution_source=package.metadata.point_distribution_source,
                    source_result_fingerprint=award.source_result_fingerprint,
                    source_player_result_fingerprint=award.source_player_result_fingerprint,
                    award_fingerprint=award.award_fingerprint,
                    award_package_fingerprint=package.metadata.build_fingerprint,
                    result_package_fingerprint=package.metadata.result_package_fingerprint,
                ))

        breakdowns = {player.player_id: self._build_breakdown(player, entries_by_player[player.player_id], season=season) for player in active_players}
        warnings = list(FOUNDATION_WARNINGS)
        if not season_packages:
            warnings.append(f"No persisted point award packages found for season '{season}'.")
        elif applied_only and not any(self._package_applied(package, applied_event_ids) for package in season_packages):
            warnings.append(f"No applied point award packages found for season '{season}'.")
        if not applied_only:
            warnings.append("Unapplied persisted point award packages are included because applied_only=false.")

        filtered_players = self._filter_players(active_players, filters=filters)
        if normalized_player_id is not None:
            selected_breakdown = breakdowns[normalized_player_id]
        elif normalized_search is not None and len(filtered_players) == 1:
            selected_breakdown = breakdowns[filtered_players[0].player_id]
        else:
            selected_breakdown = None

        summary_rows = [self._summary_row(player, breakdowns[player.player_id]) for player in filtered_players]
        summary_rows = sorted(summary_rows, key=lambda row: (-row.ranking_points, -row.race_points, -row.breakdown_ranking_points_total, row.player_name.casefold(), row.player_id))
        if limit is not None:
            summary_rows = summary_rows[:limit]

        for breakdown in breakdowns.values():
            if not breakdown.consistency.ranking_points_match_active_player or not breakdown.consistency.race_points_match_active_player:
                warnings.append(
                    f"Active player points do not match applied breakdown total for {breakdown.player_id}: "
                    f"ranking_delta={breakdown.consistency.ranking_points_delta}, race_delta={breakdown.consistency.race_points_delta}."
                )

        active_fingerprint = self._fingerprint([player.model_dump(mode="json") for player in sorted(active_players, key=lambda item: item.player_id)])
        point_awards_fingerprint = self._fingerprint([package.model_dump(mode="json") for package in season_packages])
        generated_payload = {
            "breakdown": selected_breakdown.model_dump(mode="json") if selected_breakdown else None,
            "summary_rows": [row.model_dump(mode="json") for row in summary_rows],
            "active_players_fingerprint": active_fingerprint,
            "point_awards_fingerprint": point_awards_fingerprint,
            "applied_only": applied_only,
            "table_type": table_type,
            "filters": filters.model_dump(mode="json"),
            "limit": limit,
            "warnings": warnings,
        }
        generated_fingerprint = self._fingerprint(generated_payload)
        metadata = PlayerPointBreakdownMetadata(
            season=season,
            active_players_fingerprint=active_fingerprint,
            point_awards_fingerprint=point_awards_fingerprint,
            generated_fingerprint=generated_fingerprint,
            applied_only=applied_only,
            table_type=table_type,
            filters=filters,
            limit=limit,
        )
        return PlayerPointBreakdownResponse(
            breakdown=selected_breakdown,
            summary_rows=summary_rows,
            metadata=metadata,
            validation_warnings=warnings,
            validation_errors=[],
        )

    def _build_breakdown(self, player: SeasonActivePlayer, entries: list[PlayerPointBreakdownEntry], *, season: str) -> PlayerPointBreakdown:
        sorted_entries = sorted(entries, key=self._entry_sort_key)
        applied_entries = [entry for entry in sorted_entries if entry.applied]
        unapplied_entries = [entry for entry in sorted_entries if not entry.applied]
        applied_ranking = sum(entry.ranking_points_awarded for entry in applied_entries)
        applied_race = sum(entry.race_points_awarded for entry in applied_entries)
        ranking_delta = player.ranking_points - applied_ranking
        race_delta = player.race_points - applied_race
        return PlayerPointBreakdown(
            player_id=player.player_id,
            player_name=player.name,
            country_code=player.country_code,
            nationality=player.nationality,
            season=season,
            current_ranking_points=player.ranking_points,
            current_race_points=player.race_points,
            breakdown_ranking_points_total=sum(entry.ranking_points_awarded for entry in sorted_entries),
            breakdown_race_points_total=sum(entry.race_points_awarded for entry in sorted_entries),
            applied_ranking_points_total=applied_ranking,
            applied_race_points_total=applied_race,
            unapplied_ranking_points_total=sum(entry.ranking_points_awarded for entry in unapplied_entries),
            unapplied_race_points_total=sum(entry.race_points_awarded for entry in unapplied_entries),
            applied_event_count=len({entry.event_id for entry in applied_entries}),
            total_event_count=len({entry.event_id for entry in sorted_entries}),
            consistency=PlayerPointBreakdownConsistency(
                ranking_points_match_active_player=ranking_delta == 0,
                race_points_match_active_player=race_delta == 0,
                ranking_points_delta=ranking_delta,
                race_points_delta=race_delta,
            ),
            entries=sorted_entries,
        )

    @staticmethod
    def _summary_row(player: SeasonActivePlayer, breakdown: PlayerPointBreakdown) -> PlayerPointBreakdownSummaryRow:
        top_entry = max(breakdown.entries, key=lambda entry: (entry.ranking_points_awarded, entry.race_points_awarded, entry.event_id), default=None)
        return PlayerPointBreakdownSummaryRow(
            player_id=player.player_id,
            player_name=player.name,
            country_code=player.country_code,
            ranking_points=player.ranking_points,
            race_points=player.race_points,
            breakdown_ranking_points_total=breakdown.breakdown_ranking_points_total,
            breakdown_race_points_total=breakdown.breakdown_race_points_total,
            applied_event_count=breakdown.applied_event_count,
            total_event_count=breakdown.total_event_count,
            consistency_ok=breakdown.consistency.ranking_points_match_active_player and breakdown.consistency.race_points_match_active_player,
            top_result_stage=top_entry.reached_stage if top_entry else None,
            top_result_event_id=top_entry.event_id if top_entry else None,
        )

    @staticmethod
    def _filter_players(players: list[SeasonActivePlayer], *, filters: PlayerPointBreakdownFilters) -> list[SeasonActivePlayer]:
        filtered = list(players)
        if filters.player_id:
            filtered = [player for player in filtered if player.player_id == filters.player_id]
        if filters.country_code:
            filtered = [player for player in filtered if player.country_code == filters.country_code]
        if filters.search:
            needle = filters.search.casefold()
            filtered = [player for player in filtered if needle in player.name.casefold() or needle in player.player_id.casefold()]
        return filtered

    def _calendar_events_by_id(self, season: str) -> dict[str, Any]:
        if self.calendar_service is None:
            return {}
        calendar_result = self.calendar_service.get_calendar(season=season)
        if calendar_result.calendar is None:
            return {}
        return {event.event_id: event for event in calendar_result.calendar.events}

    @staticmethod
    def _package_applied(package: EventPointAwardPackage, applied_event_ids: set[str]) -> bool:
        return package.applied or package.event_id in applied_event_ids

    @staticmethod
    def _is_zero_award(ranking_points: int, race_points: int, table_type: PointBreakdownTableType) -> bool:
        if table_type == "ranking":
            return ranking_points == 0
        if table_type == "race":
            return race_points == 0
        return ranking_points == 0 and race_points == 0

    @staticmethod
    def _entry_sort_key(entry: PlayerPointBreakdownEntry) -> tuple[int, int, int, str, str]:
        none_last = 9999
        return (
            entry.season_week if entry.season_week is not None else none_last,
            entry.calendar_year if entry.calendar_year is not None else none_last,
            entry.year_week if entry.year_week is not None else none_last,
            (entry.event_name or "").casefold(),
            entry.event_id,
        )

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
