from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from beta_engine.api.deps import get_talent_calibration_service, get_world_talent_preview_service
from beta_engine.api.schemas import TalentCalibrationResponse, TalentClassSummaryResponse, TalentClassYearPreviewResponse
from beta_engine.application.talent_calibration_service import TalentCalibrationService
from beta_engine.application.world_talent_preview_service import WorldTalentPreviewService

router = APIRouter(prefix="/world/talent-class", tags=["world"])


@router.get("/calibration", response_model=TalentCalibrationResponse)
def calibrate_talent_class(
    seed: int = Query(default=0),
    sample_count: int = Query(default=5000, ge=1, le=50_000),
    service: TalentCalibrationService = Depends(get_talent_calibration_service),
) -> TalentCalibrationResponse:
    return TalentCalibrationResponse.model_validate(asdict(service.calibrate(seed=seed, sample_count=sample_count)))


@router.get("/preview", response_model=TalentClassYearPreviewResponse)
def preview_talent_class_for_year(
    year: int = Query(ge=1900),
    seed: int = Query(default=0),
    service: WorldTalentPreviewService = Depends(get_world_talent_preview_service),
) -> TalentClassYearPreviewResponse:
    return TalentClassYearPreviewResponse.model_validate(asdict(service.preview_year(year=year, seed=seed)))


@router.get("/summary", response_model=TalentClassSummaryResponse)
def preview_talent_class_summary(
    year_start: int = Query(ge=1900),
    years: int = Query(default=10, ge=1, le=100),
    seed: int = Query(default=0),
    service: WorldTalentPreviewService = Depends(get_world_talent_preview_service),
) -> TalentClassSummaryResponse:
    return TalentClassSummaryResponse.model_validate(asdict(service.summary(year_start=year_start, years=years, seed=seed)))
