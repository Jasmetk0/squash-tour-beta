from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from beta_engine.api.deps import get_world_package_service
from beta_engine.api.schemas import (
    WorldPackageImportErrorResponse,
    WorldPackageImportRequest,
    WorldPackageImportResponse,
    WorldPackageImportSummaryResponse,
)
from beta_engine.application.world_package_service import WorldPackageService

router = APIRouter(prefix="/world/package", tags=["world"])


@router.get("/export", response_class=Response)
def export_world_package(service: WorldPackageService = Depends(get_world_package_service)) -> Response:
    package_text = service.export_package_text()
    return Response(
        content=package_text,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="world-package-export.json"'},
    )


@router.post("/import", response_model=WorldPackageImportResponse)
def import_world_package(
    payload: WorldPackageImportRequest,
    service: WorldPackageService = Depends(get_world_package_service),
) -> WorldPackageImportResponse:
    result = service.import_package_text(package_text=payload.package_text, dry_run=payload.dry_run)
    return WorldPackageImportResponse(
        ok=result.ok,
        dry_run=result.dry_run,
        countries_summary=WorldPackageImportSummaryResponse(
            total_records=result.countries_summary.total_records,
            new_records=result.countries_summary.new_records,
            updated_records=result.countries_summary.updated_records,
            unchanged_records=result.countries_summary.unchanged_records,
        ),
        manual_overrides_summary=WorldPackageImportSummaryResponse(
            total_records=result.manual_overrides_summary.total_records,
            new_records=result.manual_overrides_summary.new_records,
            updated_records=result.manual_overrides_summary.updated_records,
            unchanged_records=result.manual_overrides_summary.unchanged_records,
        ),
        errors=[
            WorldPackageImportErrorResponse(field=item.field, message=item.message)
            for item in result.errors
        ],
    )
