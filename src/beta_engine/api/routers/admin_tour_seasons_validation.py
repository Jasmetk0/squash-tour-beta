from __future__ import annotations

from fastapi import APIRouter, Depends

from beta_engine.application.tour_seasons_validation_service import TourSeasonsValidationResponse, TourSeasonsValidationService
from beta_engine.api.deps import get_tour_seasons_validation_service

router = APIRouter(prefix="/admin/tour-seasons", tags=["admin-tour-seasons-validation"])


@router.get("/validation", response_model=TourSeasonsValidationResponse)
def get_tour_seasons_validation(
    service: TourSeasonsValidationService = Depends(get_tour_seasons_validation_service),
) -> TourSeasonsValidationResponse:
    return service.validate()
