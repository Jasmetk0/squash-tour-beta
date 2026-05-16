from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_season_event_results_service
from beta_engine.application.season_event_results_service import (
    EventResultExtractRequest,
    SeasonEventResultPackageResult,
    SeasonEventResultsService,
)

router = APIRouter(prefix="/admin/results", tags=["admin-results"])


@router.get("/{event_id}", response_model=SeasonEventResultPackageResult)
def get_event_result_package(event_id: str, service: SeasonEventResultsService = Depends(get_season_event_results_service)) -> SeasonEventResultPackageResult:
    return service.get_event_result(event_id=event_id)


@router.post("/{event_id}/extract", response_model=SeasonEventResultPackageResult)
def extract_event_result_package(event_id: str, payload: EventResultExtractRequest, service: SeasonEventResultsService = Depends(get_season_event_results_service)) -> SeasonEventResultPackageResult:
    try:
        return service.extract_event_result(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
