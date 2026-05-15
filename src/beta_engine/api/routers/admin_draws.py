from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_season_draw_service
from beta_engine.application.season_draw_service import DrawGenerateRequest, SeasonDrawService, SeasonEventDrawPackageResult

router = APIRouter(prefix="/admin/draws", tags=["admin-draws"])


@router.get("/{event_id}", response_model=SeasonEventDrawPackageResult)
def get_event_draw_package(
    event_id: str,
    service: SeasonDrawService = Depends(get_season_draw_service),
) -> SeasonEventDrawPackageResult:
    return service.get_draw_package(event_id=event_id)


@router.post("/{event_id}/generate", response_model=SeasonEventDrawPackageResult)
def generate_event_draw_package(
    event_id: str,
    payload: DrawGenerateRequest,
    service: SeasonDrawService = Depends(get_season_draw_service),
) -> SeasonEventDrawPackageResult:
    try:
        return service.generate_draw_package(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
