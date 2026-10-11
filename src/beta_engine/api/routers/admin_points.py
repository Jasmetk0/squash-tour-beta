from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_season_point_awards_service
from beta_engine.application.season_point_awards_service import (
    EventPointAwardPackageResult,
    PointAwardApplyRequest,
    PointAwardApplyResult,
    PointAwardGenerateRequest,
    SeasonPointAwardsService,
)

router = APIRouter(prefix="/admin/points", tags=["admin-points"])


@router.get("/{event_id}", response_model=EventPointAwardPackageResult)
def get_event_point_awards(event_id: str, service: SeasonPointAwardsService = Depends(get_season_point_awards_service)) -> EventPointAwardPackageResult:
    return service.get_event_point_awards(event_id=event_id)


@router.post("/{event_id}/generate", response_model=EventPointAwardPackageResult)
def generate_event_point_awards(event_id: str, payload: PointAwardGenerateRequest, service: SeasonPointAwardsService = Depends(get_season_point_awards_service)) -> EventPointAwardPackageResult:
    try:
        return service.generate_event_point_awards(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/apply", response_model=PointAwardApplyResult)
def apply_event_point_awards(event_id: str, payload: PointAwardApplyRequest, service: SeasonPointAwardsService = Depends(get_season_point_awards_service)) -> PointAwardApplyResult:
    try:
        return service.apply_event_point_awards(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
