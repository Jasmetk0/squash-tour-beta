from fastapi import APIRouter, Depends, Query

from beta_engine.api.deps import get_config_validation_service
from beta_engine.api.schemas import ConfigValidationResponse
from beta_engine.application.config_validation_service import ConfigValidationReport, ConfigValidationService

router = APIRouter(prefix="/config", tags=["config"])


def _to_validation_response(report: ConfigValidationReport) -> ConfigValidationResponse:
    return ConfigValidationResponse.model_validate(report, from_attributes=True)


@router.get("/validation", response_model=ConfigValidationResponse)
def validate_loaded_config(
    season: int = Query(default=2027, ge=1900),
    service: ConfigValidationService = Depends(get_config_validation_service),
) -> ConfigValidationResponse:
    return _to_validation_response(service.validate_current_config(season=season))
