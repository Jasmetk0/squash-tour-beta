from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_initial_player_pool_service
from beta_engine.api.schemas import (
    CustomInitialPoolPlayerCreateRequest,
    InitialPoolGenerateRequest,
    InitialPoolPlayerUpdateRequest,
    InitialPoolRegenerateRequest,
)
from beta_engine.application.initial_player_pool_service import InitialPlayerPoolService
from beta_engine.domain.players.initial_pool import InitialPoolAuditList, InitialPoolGeneratedPlayer, InitialPoolResult

router = APIRouter(prefix="/admin/players", tags=["admin-players"])


@router.get("/initial-pool", response_model=InitialPoolResult)
def get_initial_pool(
    season: str = "2000/2001",
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolResult:
    return service.get_pool(season=season)


@router.post("/initial-pool/generate", response_model=InitialPoolResult)
def generate_initial_pool(
    payload: InitialPoolGenerateRequest,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolResult:
    try:
        return service.generate_pool(
            season=payload.season,
            seed=payload.seed,
            target_pool_size=payload.target_pool_size or 128,
            dry_run=payload.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/initial-pool/regenerate-unlocked", response_model=InitialPoolResult)
def regenerate_initial_pool_unlocked(
    payload: InitialPoolRegenerateRequest,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolResult:
    try:
        return service.regenerate_unlocked(
            season=payload.season,
            seed=payload.seed,
            target_pool_size=payload.target_pool_size,
            country_code=payload.country_code,
            region=payload.region,
            dry_run=payload.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/custom", response_model=InitialPoolGeneratedPlayer)
def create_custom_player(
    payload: CustomInitialPoolPlayerCreateRequest,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolGeneratedPlayer:
    try:
        return service.create_custom_player(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{player_id}", response_model=InitialPoolGeneratedPlayer)
def update_player(
    player_id: str,
    payload: InitialPoolPlayerUpdateRequest,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolGeneratedPlayer:
    try:
        return service.update_player(player_id=player_id, payload=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/audit", response_model=InitialPoolAuditList)
def get_audit_events(
    season: str | None = None,
    player_id: str | None = None,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolAuditList:
    return service.get_audit_events(season=season, player_id=player_id)


@router.post("/{player_id}/lock", response_model=InitialPoolGeneratedPlayer)
def lock_player(
    player_id: str,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolGeneratedPlayer:
    try:
        return service.set_lock(player_id=player_id, locked=True)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{player_id}/unlock", response_model=InitialPoolGeneratedPlayer)
def unlock_player(
    player_id: str,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolGeneratedPlayer:
    try:
        return service.set_lock(player_id=player_id, locked=False)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
