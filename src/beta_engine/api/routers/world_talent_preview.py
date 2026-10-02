from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from beta_engine.api.deps import get_talent_calibration_service, get_world_talent_preview_service
from beta_engine.api.schemas import (TalentCalibrationCompareRequest,
    TalentCalibrationCompareResponse, TalentCalibrationMultiSeedRequest,
    TalentCalibrationMultiSeedResponse, TalentCalibrationResponse,
    TalentClassSummaryResponse, TalentClassYearPreviewResponse)
from beta_engine.application.talent_calibration_service import BAND_ORDER, TalentCalibrationService
from beta_engine.application.world_talent_preview_service import WorldTalentPreviewService

router = APIRouter(prefix="/world/talent-class", tags=["world"])


@router.get("/calibration", response_model=TalentCalibrationResponse)
def calibrate_talent_class(
    seed: int = Query(default=0),
    sample_count: int = Query(default=5000, ge=1, le=50_000),
    service: TalentCalibrationService = Depends(get_talent_calibration_service),
) -> TalentCalibrationResponse:
    return TalentCalibrationResponse.model_validate(asdict(service.calibrate(seed=seed, sample_count=sample_count)))


@router.post("/calibration/compare", response_model=TalentCalibrationCompareResponse)
def compare_talent_calibration(
    request: TalentCalibrationCompareRequest,
    service: TalentCalibrationService = Depends(get_talent_calibration_service),
) -> TalentCalibrationCompareResponse:
    ranges = {
        band: (
            getattr(request.candidate_ranges, band.value).potential_min,
            getattr(request.candidate_ranges, band.value).potential_max,
        )
        for band in BAND_ORDER
    }
    return TalentCalibrationCompareResponse.model_validate(asdict(service.compare(
        seed=request.seed, sample_count=request.sample_count, candidate_ranges=ranges,
    )))


@router.post("/calibration/compare-multi-seed", response_model=TalentCalibrationMultiSeedResponse)
def compare_talent_calibration_multi_seed(
    request: TalentCalibrationMultiSeedRequest,
    service: TalentCalibrationService = Depends(get_talent_calibration_service),
) -> TalentCalibrationMultiSeedResponse:
    ranges = {
        band: (getattr(request.candidate_ranges, band.value).potential_min,
               getattr(request.candidate_ranges, band.value).potential_max)
        for band in BAND_ORDER
    }
    result = service.compare_multi_seed(seed_start=request.seed_start,
        seed_count=request.seed_count, sample_count_per_seed=request.sample_count_per_seed,
        candidate_ranges=ranges)
    return TalentCalibrationMultiSeedResponse.model_validate(asdict(result))


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
