"""Global Player Test Lab API."""

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import get_player_test_lab_service
from beta_engine.application.player_test_lab_service import (
    BuiltInPlayerLabScenario,
    PlayerLabRequest,
    PlayerLabResult,
    PlayerTestLabService,
)

router = APIRouter(prefix="/admin/labs/player", tags=["admin-labs"])


@router.get("/scenarios", response_model=list[BuiltInPlayerLabScenario])
def list_player_lab_built_in_scenarios(
    service: PlayerTestLabService = Depends(get_player_test_lab_service),
) -> list[BuiltInPlayerLabScenario]:
    return list(service.list_built_in_scenarios())


@router.post("/run", response_model=PlayerLabResult)
def run_player_lab(
    request: PlayerLabRequest,
    service: PlayerTestLabService = Depends(get_player_test_lab_service),
) -> PlayerLabResult:
    try:
        return service.run(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
