from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_season_ranking_table_service
from beta_engine.application.season_ranking_table_service import RankingTableResponse, SeasonRankingTableService
from beta_engine.domain.calendar.season_labels import normalize_season_label, to_long_season_label

router = APIRouter(tags=["rankings"])
RankingTableType = Literal["ranking", "race"]


def _normalize_for_legacy_services(season: str) -> str:
    """Accept compact and legacy long season labels at API boundary."""
    try:
        return to_long_season_label(normalize_season_label(season))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _get_table(
    *,
    season: str,
    table_type: RankingTableType,
    limit: int | None,
    country_code: str | None,
    search: str | None,
    include_zero_points: bool,
    min_points: int | None,
    service: SeasonRankingTableService,
) -> RankingTableResponse:
    normalized_season = _normalize_for_legacy_services(season)
    try:
        return service.get_table(
            season=normalized_season,
            table_type=table_type,
            limit=limit,
            country_code=country_code,
            search=search,
            include_zero_points=include_zero_points,
            min_points=min_points,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/admin/rankings/{season:path}", response_model=RankingTableResponse, tags=["admin-rankings"])
def get_admin_ranking_table(
    season: str,
    table_type: RankingTableType = Query(default="ranking"),
    limit: int | None = Query(default=None, ge=1),
    country_code: str | None = None,
    search: str | None = None,
    include_zero_points: bool = True,
    min_points: int | None = Query(default=None, ge=0),
    service: SeasonRankingTableService = Depends(get_season_ranking_table_service),
) -> RankingTableResponse:
    return _get_table(
        season=season,
        table_type=table_type,
        limit=limit,
        country_code=country_code,
        search=search,
        include_zero_points=include_zero_points,
        min_points=min_points,
        service=service,
    )


@router.get("/viewer/rankings/{season:path}", response_model=RankingTableResponse, tags=["viewer-rankings"])
def get_viewer_ranking_table(
    season: str,
    table_type: RankingTableType = Query(default="ranking"),
    limit: int | None = Query(default=None, ge=1),
    country_code: str | None = None,
    search: str | None = None,
    include_zero_points: bool = True,
    min_points: int | None = Query(default=None, ge=0),
    service: SeasonRankingTableService = Depends(get_season_ranking_table_service),
) -> RankingTableResponse:
    return _get_table(
        season=season,
        table_type=table_type,
        limit=limit,
        country_code=country_code,
        search=search,
        include_zero_points=include_zero_points,
        min_points=min_points,
        service=service,
    )
