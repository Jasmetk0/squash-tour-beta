from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_season_ranking_snapshot_service
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService, WeeklyRankingSnapshotGenerateRequest, WeeklyRankingSnapshotResult

router = APIRouter(tags=["ranking-snapshots"])


def _raise_on_errors(result: WeeklyRankingSnapshotResult) -> WeeklyRankingSnapshotResult:
    if result.validation_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(result.validation_errors))
    return result


@router.get("/admin/ranking-snapshots/{season:path}", response_model=WeeklyRankingSnapshotResult, tags=["admin-ranking-snapshots"])
def get_admin_ranking_snapshot(
    season: str,
    season_week: int = Query(..., ge=1, le=61),
    service: SeasonRankingSnapshotService = Depends(get_season_ranking_snapshot_service),
) -> WeeklyRankingSnapshotResult:
    return _raise_on_errors(service.get_snapshot(season=season, season_week=season_week))


@router.post("/admin/ranking-snapshots/{season:path}/generate", response_model=WeeklyRankingSnapshotResult, tags=["admin-ranking-snapshots"])
def generate_admin_ranking_snapshot(
    season: str,
    request: WeeklyRankingSnapshotGenerateRequest,
    season_week: int = Query(..., ge=1, le=61),
    service: SeasonRankingSnapshotService = Depends(get_season_ranking_snapshot_service),
) -> WeeklyRankingSnapshotResult:
    return _raise_on_errors(service.generate_snapshot(season=season, season_week=season_week, request=request))


@router.get("/viewer/ranking-snapshots/{season:path}", response_model=WeeklyRankingSnapshotResult, tags=["viewer-ranking-snapshots"])
def get_viewer_ranking_snapshot(
    season: str,
    season_week: int = Query(..., ge=1, le=61),
    service: SeasonRankingSnapshotService = Depends(get_season_ranking_snapshot_service),
) -> WeeklyRankingSnapshotResult:
    return _raise_on_errors(service.get_snapshot(season=season, season_week=season_week))
