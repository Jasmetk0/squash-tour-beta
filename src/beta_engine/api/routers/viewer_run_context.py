"""Read-only Viewer resolution of a Product Run's official Branch."""

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import ViewerOfficialRunContextResponse
from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)

router = APIRouter(tags=["viewer-runs"])


@router.get("/viewer/runs/{product_run_id:path}/official-context", response_model=ViewerOfficialRunContextResponse)
def get_viewer_official_run_context(
    product_run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)
) -> ViewerOfficialRunContextResponse:
    try:
        context = service.get_viewer_official_run_context(product_run_id)
    except ViewerOfficialRunContextNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ViewerOfficialRunContextConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return ViewerOfficialRunContextResponse.model_validate(context.__dict__)
