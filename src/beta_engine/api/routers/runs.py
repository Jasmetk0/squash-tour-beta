from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_run_weekly_intake_cohort_preview_service, get_simulation_api_service
from beta_engine.api.schemas import (
    BootstrapNextSeasonApiResponse,
    BootstrapNextSeasonRequest,
    RunIndexResponse,
    RunWeeklyIntakeCohortSeasonPreviewResponse,
    RunIndexSummaryResponse,
    RunStatusSummaryResponse,
    RunSummaryResponse,
    CreateRunRequest,
    SeasonStateResponse,
)
from beta_engine.application.api_services import PersistedRunSummary, RunStatusSummary, RunIndexSummary, SimulationApiService
from beta_engine.application.run_weekly_intake_cohort_preview_service import RunWeeklyIntakeCohortPreviewService

router = APIRouter(prefix="/runs", tags=["runs"])


def _to_run_summary(summary: PersistedRunSummary) -> RunSummaryResponse:
    return RunSummaryResponse.model_validate(summary.__dict__)


def _to_run_status_summary(summary: RunStatusSummary) -> RunStatusSummaryResponse:
    return RunStatusSummaryResponse.model_validate(summary, from_attributes=True)


def _to_run_index_summary(summary: RunIndexSummary) -> RunIndexSummaryResponse:
    return RunIndexSummaryResponse.model_validate(summary, from_attributes=True)


@router.post("", response_model=RunSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_run(payload: CreateRunRequest, service: SimulationApiService = Depends(get_simulation_api_service)) -> RunSummaryResponse:
    try:
        summary = service.initialize_run(
            run_id=payload.run_id,
            season=payload.season,
            seed=payload.seed,
            config_version=payload.config_version,
            config_fingerprint=payload.config_fingerprint,
            world_id=payload.world_id,
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


@router.get(
    "/{run_id}/weekly-intake/cohort-season/preview",
    response_model=RunWeeklyIntakeCohortSeasonPreviewResponse,
)
def preview_run_weekly_intake_cohort_season(
    run_id: str,
    base_annual_intake_target: int = Query(200, ge=0),
    season_growth_rate: float = Query(0.015, ge=0.0, le=0.10),
    country_code: str | None = None,
    region: str | None = None,
    service: RunWeeklyIntakeCohortPreviewService = Depends(get_run_weekly_intake_cohort_preview_service),
) -> RunWeeklyIntakeCohortSeasonPreviewResponse:
    try:
        result = service.preview_season(
            run_id=run_id,
            base_annual_intake_target=base_annual_intake_target,
            season_growth_rate=season_growth_rate,
            country_code=country_code,
            region=region,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return RunWeeklyIntakeCohortSeasonPreviewResponse.model_validate(result, from_attributes=True)


@router.get("/{run_id}/status-summary", response_model=RunStatusSummaryResponse)
def get_run_status_summary(
    run_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunStatusSummaryResponse:
    try:
        summary = service.get_run_status_summary(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_run_status_summary(summary)


@router.get("", response_model=RunIndexResponse)
def list_runs(service: SimulationApiService = Depends(get_simulation_api_service)) -> RunIndexResponse:
    runs = service.list_runs_index()
    return RunIndexResponse(runs=[_to_run_index_summary(summary) for summary in runs])


@router.post("/{run_id}/bootstrap-next-season", response_model=BootstrapNextSeasonApiResponse)
def bootstrap_next_season_run(
    run_id: str,
    payload: BootstrapNextSeasonRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> BootstrapNextSeasonApiResponse:
    try:
        bootstrap = service.bootstrap_next_season_run(
            run_id=run_id,
            child_run_id=payload.child_run_id,
            child_seed=payload.child_seed,
        )
        run = service.get_run_summary(run_id=payload.child_run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return BootstrapNextSeasonApiResponse(
        run=_to_run_summary(run),
        bootstrap=bootstrap,
    )
