from __future__ import annotations

from fastapi import APIRouter, Depends

from beta_engine.api.deps import get_tournament_master_service
from beta_engine.application.tournament_master_service import TournamentMasterService, TournamentMastersResponse

router = APIRouter(prefix="/admin/tournaments", tags=["admin-tournaments"])


@router.get("", response_model=TournamentMastersResponse)
def get_tournaments(service: TournamentMasterService = Depends(get_tournament_master_service)) -> TournamentMastersResponse:
    return service.list_tournaments()
