from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_season_match_service
from beta_engine.application.season_match_service import MatchPackageGenerateRequest, MatchSimulateRequest, SeasonEventMatchPackageResult, SeasonMatchService

router = APIRouter(prefix="/admin/matches", tags=["admin-matches"])


@router.get("/{event_id}", response_model=SeasonEventMatchPackageResult)
def get_event_match_package(event_id: str, service: SeasonMatchService = Depends(get_season_match_service)) -> SeasonEventMatchPackageResult:
    return service.get_match_package(event_id=event_id)


@router.post("/{event_id}/generate", response_model=SeasonEventMatchPackageResult)
def generate_event_match_package(event_id: str, payload: MatchPackageGenerateRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> SeasonEventMatchPackageResult:
    try:
        return service.generate_match_package(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/simulate-next", response_model=SeasonEventMatchPackageResult)
def simulate_next_event_match(event_id: str, payload: MatchSimulateRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> SeasonEventMatchPackageResult:
    try:
        return service.simulate_next_match(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/simulate/{match_id}", response_model=SeasonEventMatchPackageResult)
def simulate_event_match(event_id: str, match_id: str, payload: MatchSimulateRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> SeasonEventMatchPackageResult:
    try:
        return service.simulate_match(event_id=event_id, match_id=match_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
