from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import get_world_package_registry_service, get_world_package_validation_service
from beta_engine.api.schemas import (
    WorldPackageDetailResponse,
    WorldPackageListResponse,
    WorldPackageSummaryResponse,
    WorldPackageValidationResponse,
)
from beta_engine.application.world_package_registry_service import WorldPackageRegistryRecord, WorldPackageRegistryService
from beta_engine.application.world_package_validation_service import WorldPackageValidationResult, WorldPackageValidationService

router = APIRouter(prefix="/world/packages", tags=["world"])


def _to_summary(record: WorldPackageRegistryRecord) -> WorldPackageSummaryResponse:
    return WorldPackageSummaryResponse.model_validate(record, from_attributes=True)


def _to_detail(record: WorldPackageRegistryRecord) -> WorldPackageDetailResponse:
    return WorldPackageDetailResponse.model_validate(record, from_attributes=True)


def _to_validation(result: WorldPackageValidationResult) -> WorldPackageValidationResponse:
    return WorldPackageValidationResponse.model_validate(result, from_attributes=True)


@router.get("", response_model=WorldPackageListResponse)
def list_world_packages(
    service: WorldPackageRegistryService = Depends(get_world_package_registry_service),
) -> WorldPackageListResponse:
    return WorldPackageListResponse(packages=[_to_summary(record) for record in service.list_packages()])


@router.get("/{world_id}/validation", response_model=WorldPackageValidationResponse)
def validate_world_package(
    world_id: str,
    service: WorldPackageValidationService = Depends(get_world_package_validation_service),
) -> WorldPackageValidationResponse:
    result = service.validate_package(world_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
    return _to_validation(result)


@router.get("/{world_id}", response_model=WorldPackageDetailResponse)
def get_world_package(
    world_id: str,
    service: WorldPackageRegistryService = Depends(get_world_package_registry_service),
) -> WorldPackageDetailResponse:
    record = service.get_package(world_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' not found")
    return _to_detail(record)
