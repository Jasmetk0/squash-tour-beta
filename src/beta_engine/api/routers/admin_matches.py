from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_season_match_service
from beta_engine.application.season_match_service import (
    MatchPackageGenerateRequest,
    MatchReplayResponse,
    MatchSimulateRequest,
    ProgressionCommandRequest,
    ProgressionCommandResult,
    SeasonEventMatchPackageResult,
    SeasonMatchService,
    SimulateDrawRequest,
    SimulateRoundRequest,
    TournamentProgressionStatus,
)

router = APIRouter(prefix="/admin/matches", tags=["admin-matches"])


@router.get("/{event_id}", response_model=SeasonEventMatchPackageResult)
def get_event_match_package(event_id: str, service: SeasonMatchService = Depends(get_season_match_service)) -> SeasonEventMatchPackageResult:
    return service.get_match_package(event_id=event_id)


@router.get("/{event_id}/replay/{match_id}", response_model=MatchReplayResponse)
def get_event_match_replay(
    event_id: str,
    match_id: str,
    service: SeasonMatchService = Depends(get_season_match_service),
) -> MatchReplayResponse:
    try:
        return service.get_match_replay(event_id=event_id, match_id=match_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/generate", response_model=SeasonEventMatchPackageResult)
def generate_event_match_package(event_id: str, payload: MatchPackageGenerateRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> SeasonEventMatchPackageResult:
    try:
        return service.generate_match_package(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{event_id}/progression", response_model=TournamentProgressionStatus)
def get_event_progression_status(event_id: str, service: SeasonMatchService = Depends(get_season_match_service)) -> TournamentProgressionStatus:
    try:
        return service.get_progression_status(event_id=event_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/process-byes", response_model=ProgressionCommandResult)
def process_event_byes(event_id: str, payload: ProgressionCommandRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> ProgressionCommandResult:
    try:
        return service.process_byes(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/refresh-progression", response_model=ProgressionCommandResult)
def refresh_event_progression(event_id: str, payload: ProgressionCommandRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> ProgressionCommandResult:
    try:
        return service.refresh_progression(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/promote-qualifiers", response_model=ProgressionCommandResult)
def promote_event_qualifiers(event_id: str, payload: ProgressionCommandRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> ProgressionCommandResult:
    try:
        return service.promote_qualifiers(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/simulate-round", response_model=ProgressionCommandResult)
def simulate_event_round(event_id: str, payload: SimulateRoundRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> ProgressionCommandResult:
    try:
        return service.simulate_round(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/simulate-draw", response_model=ProgressionCommandResult)
def simulate_event_draw(event_id: str, payload: SimulateDrawRequest, service: SeasonMatchService = Depends(get_season_match_service)) -> ProgressionCommandResult:
    try:
        return service.simulate_draw(event_id=event_id, request=payload)
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
