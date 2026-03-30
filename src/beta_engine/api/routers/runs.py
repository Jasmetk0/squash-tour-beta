from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import CreateRunRequest, RunSummaryResponse, SeasonStateResponse
from beta_engine.application.api_services import PersistedRunSummary, SimulationApiService

router = APIRouter(prefix="/runs", tags=["runs"])


def _to_run_summary(summary: PersistedRunSummary) -> RunSummaryResponse:
    return RunSummaryResponse.model_validate(summary.__dict__)


@router.post("", response_model=RunSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_run(payload: CreateRunRequest, service: SimulationApiService = Depends(get_simulation_api_service)) -> RunSummaryResponse:
    try:
        summary = service.initialize_run(
            run_id=payload.run_id,
            season=payload.season,
            seed=payload.seed,
            config_version=payload.config_version,
            config_fingerprint=payload.config_fingerprint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_run_summary(summary)


@router.get("/{run_id}", response_model=SeasonStateResponse)
def get_run(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> SeasonStateResponse:
    try:
        summary = service.get_run_summary(run_id=run_id)
        state = service.get_season_state(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return SeasonStateResponse(run=_to_run_summary(summary), season_state=state)
