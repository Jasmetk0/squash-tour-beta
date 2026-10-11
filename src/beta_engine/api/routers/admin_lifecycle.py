from __future__ import annotations

from fastapi import APIRouter, Depends

from beta_engine.api.deps import get_season_event_lifecycle_service
from beta_engine.application.season_event_lifecycle_service import EventLifecycleResponse, SeasonEventLifecycleService, SeasonLifecycleResponse

router = APIRouter(prefix="/admin/lifecycle", tags=["admin-lifecycle"])


@router.get("/event/{event_id}", response_model=EventLifecycleResponse)
def get_event_lifecycle(
    event_id: str,
    service: SeasonEventLifecycleService = Depends(get_season_event_lifecycle_service),
) -> EventLifecycleResponse:
    return service.get_event_lifecycle(event_id=event_id)


@router.get("/{season:path}", response_model=SeasonLifecycleResponse)
def get_season_lifecycle(
    season: str,
    service: SeasonEventLifecycleService = Depends(get_season_event_lifecycle_service),
) -> SeasonLifecycleResponse:
    return service.get_season_lifecycle(season=season)
