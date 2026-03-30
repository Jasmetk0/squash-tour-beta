from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import FinalsSimulationResponse, RunSummaryResponse, SimulateResponse
from beta_engine.application.api_services import PersistedRunSummary, SimulationApiService

router = APIRouter(prefix="/runs/{run_id}/simulate", tags=["simulation"])


def _to_run_summary(summary: PersistedRunSummary) -> RunSummaryResponse:
    return RunSummaryResponse.model_validate(summary.__dict__)


def _run_step(*, run_id: str, mode: str, service: SimulationApiService) -> SimulateResponse:
    try:
        if mode == "next-tournament":
            step = service.simulate_next_tournament(run_id=run_id)
        elif mode == "next-week":
            step = service.simulate_next_week(run_id=run_id)
        elif mode == "full-season":
            step = service.simulate_full_season(run_id=run_id)
        else:
            raise ValueError(f"unsupported mode {mode}")

        summary = service.get_run_summary(run_id=run_id)
        return SimulateResponse(mode=mode, run=_to_run_summary(summary), step=step)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/next-tournament", response_model=SimulateResponse)
def simulate_next_tournament(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> SimulateResponse:
    return _run_step(run_id=run_id, mode="next-tournament", service=service)


@router.post("/next-week", response_model=SimulateResponse)
def simulate_next_week(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> SimulateResponse:
    return _run_step(run_id=run_id, mode="next-week", service=service)


@router.post("/full-season", response_model=SimulateResponse)
def simulate_full_season(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> SimulateResponse:
    return _run_step(run_id=run_id, mode="full-season", service=service)


@router.post("/world-tour-finals", response_model=FinalsSimulationResponse)
def simulate_world_tour_finals(
    run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)
) -> FinalsSimulationResponse:
    try:
        finals = service.simulate_world_tour_finals(run_id=run_id)
        summary = service.get_run_summary(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FinalsSimulationResponse(
        mode="simulate_world_tour_finals",
        run=_to_run_summary(summary),
        finals=finals,
    )
