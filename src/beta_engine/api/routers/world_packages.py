from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import get_world_package_clone_service, get_world_package_registry_service, get_world_package_validation_service
from beta_engine.api.schemas import (
    WorldPackageCloneErrorResponse,
    WorldPackageCloneRequest,
    WorldPackageCloneResponse,
    WorldPackageDetailResponse,
    WorldPackageListResponse,
    WorldPackageSummaryResponse,
    WorldPackageValidationResponse,
)
from beta_engine.application.world_package_clone_service import WorldPackageCloneResult, WorldPackageCloneService
from beta_engine.application.world_package_registry_service import OFFICIAL_FAX_WORLD_ID, WorldPackageRegistryRecord, WorldPackageRegistryService
from beta_engine.application.world_package_validation_service import WorldPackageValidationResult, WorldPackageValidationService

router = APIRouter(prefix="/world/packages", tags=["world"])


def _to_summary(record: WorldPackageRegistryRecord) -> WorldPackageSummaryResponse:
    return WorldPackageSummaryResponse.model_validate(record, from_attributes=True)


def _to_detail(record: WorldPackageRegistryRecord) -> WorldPackageDetailResponse:
    return WorldPackageDetailResponse.model_validate(record, from_attributes=True)


def _to_validation(result: WorldPackageValidationResult) -> WorldPackageValidationResponse:
    return WorldPackageValidationResponse.model_validate(result, from_attributes=True)


def _to_clone_response(result: WorldPackageCloneResult) -> WorldPackageCloneResponse:
    return WorldPackageCloneResponse(
        ok=result.ok,
        dry_run=result.dry_run,
        source_world_id=result.source_world_id,
        new_world_id=result.new_world_id,
        target_path=result.target_path,
        created_files=result.created_files,
        package=_to_detail(result.package) if result.package is not None else None,
        validation=_to_validation(result.validation) if result.validation is not None else None,
        errors=[WorldPackageCloneErrorResponse(field=item.field, message=item.message) for item in result.errors],
    )


@router.get("", response_model=WorldPackageListResponse)
def list_world_packages(
    service: WorldPackageRegistryService = Depends(get_world_package_registry_service),
) -> WorldPackageListResponse:
    return WorldPackageListResponse(packages=[_to_summary(record) for record in service.list_packages()])


@router.post("/{world_id}/clone", response_model=WorldPackageCloneResponse)
def clone_world_package(
    world_id: str,
    payload: WorldPackageCloneRequest,
    service: WorldPackageCloneService = Depends(get_world_package_clone_service),
) -> WorldPackageCloneResponse:
    if world_id != OFFICIAL_FAX_WORLD_ID:
        raise HTTPException(status_code=404, detail=f"world package '{world_id}' clone is not supported")
    result = service.clone_official_world(
        new_world_id=payload.new_world_id,
        name=payload.name,
        description=payload.description,
        dry_run=payload.dry_run,
    )
    return _to_clone_response(result)


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
