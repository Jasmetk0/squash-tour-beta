from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_season_point_breakdown_service
from beta_engine.application.season_point_breakdown_service import PlayerPointBreakdownResponse, SeasonPointBreakdownService

router = APIRouter(tags=["point-breakdowns"])
PointBreakdownTableType = Literal["ranking", "race", "both"]


def _get_breakdown(
    *,
    season: str,
    player_id: str | None,
    search: str | None,
    country_code: str | None,
    applied_only: bool,
    table_type: PointBreakdownTableType,
    limit: int | None,
    include_zero_point_awards: bool,
    service: SeasonPointBreakdownService,
) -> PlayerPointBreakdownResponse:
    try:
        return service.get_player_point_breakdown(
            season=season,
            player_id=player_id,
            search=search,
            country_code=country_code,
            applied_only=applied_only,
            table_type=table_type,
            limit=limit,
            include_zero_point_awards=include_zero_point_awards,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/admin/point-breakdowns/{season:path}", response_model=PlayerPointBreakdownResponse, tags=["admin-point-breakdowns"])
def get_admin_point_breakdown(
    season: str,
    player_id: str | None = None,
    search: str | None = None,
    country_code: str | None = None,
    applied_only: bool = True,
    table_type: PointBreakdownTableType = Query(default="both"),
    limit: int | None = Query(default=None, ge=1),
    include_zero_point_awards: bool = False,
    service: SeasonPointBreakdownService = Depends(get_season_point_breakdown_service),
) -> PlayerPointBreakdownResponse:
    return _get_breakdown(
        season=season,
        player_id=player_id,
        search=search,
        country_code=country_code,
        applied_only=applied_only,
        table_type=table_type,
        limit=limit,
        include_zero_point_awards=include_zero_point_awards,
        service=service,
    )


@router.get("/viewer/point-breakdowns/{season:path}", response_model=PlayerPointBreakdownResponse, tags=["viewer-point-breakdowns"])
def get_viewer_point_breakdown(
    season: str,
    player_id: str | None = None,
    search: str | None = None,
    country_code: str | None = None,
    applied_only: bool = True,
    table_type: PointBreakdownTableType = Query(default="both"),
    limit: int | None = Query(default=None, ge=1),
    include_zero_point_awards: bool = False,
    service: SeasonPointBreakdownService = Depends(get_season_point_breakdown_service),
) -> PlayerPointBreakdownResponse:
    return _get_breakdown(
        season=season,
        player_id=player_id,
        search=search,
        country_code=country_code,
        applied_only=applied_only,
        table_type=table_type,
        limit=limit,
        include_zero_point_awards=include_zero_point_awards,
        service=service,
    )
