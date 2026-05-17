from __future__ import annotations

from fastapi import APIRouter, Depends

from beta_engine.api.deps import get_season_event_simulation_service
from beta_engine.application.season_event_simulation_service import SeasonEventSimulationService, SimulateOneEventRequest, SimulateOneEventResult

router = APIRouter(prefix="/admin/events", tags=["admin-events"])


@router.post("/{event_id}/simulate", response_model=SimulateOneEventResult)
def simulate_one_event(
    event_id: str,
    payload: SimulateOneEventRequest,
    service: SeasonEventSimulationService = Depends(get_season_event_simulation_service),
) -> SimulateOneEventResult:
    return service.simulate_one_event(event_id=event_id, request=payload)
