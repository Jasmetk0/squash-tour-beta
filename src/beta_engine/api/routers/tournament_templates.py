from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import get_tournament_templates_config_service
from beta_engine.api.schemas import (
    TournamentTemplateResponse,
    TournamentTemplatesDatasetResponse,
    TournamentTemplatesImportRequest,
    TournamentTemplatesImportResponse,
    TournamentTemplatesListResponse,
    TournamentTemplatesMetadataResponse,
    TournamentTemplatesValidationIssueResponse,
    TournamentTemplateUpsertRequest,
)
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments import TournamentTemplate

router = APIRouter(prefix="/world/tournament-templates", tags=["world"])


def _to_template_response(template: TournamentTemplate) -> TournamentTemplateResponse:
    return TournamentTemplateResponse.model_validate(template.model_dump(mode="json"))


def _to_import_response(result) -> TournamentTemplatesImportResponse:
    return TournamentTemplatesImportResponse(
        ok=result.ok,
        dry_run=result.dry_run,
        template_count=result.template_count,
        errors=[TournamentTemplatesValidationIssueResponse(field=item.field, message=item.message) for item in result.errors],
    )


@router.get("", response_model=TournamentTemplatesListResponse)
def list_tournament_templates(
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> TournamentTemplatesListResponse:
    templates = sorted(service.list_templates(), key=lambda template: template.template_id)
    return TournamentTemplatesListResponse(templates=[_to_template_response(template) for template in templates])


@router.get("/metadata", response_model=TournamentTemplatesMetadataResponse)
def get_tournament_templates_metadata(
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> TournamentTemplatesMetadataResponse:
    return TournamentTemplatesMetadataResponse.model_validate(service.get_metadata().__dict__)


@router.get("/export", response_model=TournamentTemplatesDatasetResponse)
def export_tournament_templates(
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> TournamentTemplatesDatasetResponse:
    config = service.export_dataset()
    return TournamentTemplatesDatasetResponse(templates=[_to_template_response(template) for template in config.templates])


@router.post("/import", response_model=TournamentTemplatesImportResponse)
def import_tournament_templates(
    payload: TournamentTemplatesImportRequest,
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> TournamentTemplatesImportResponse:
    result = service.import_dataset(payload.dataset, dry_run=payload.dry_run)
    return _to_import_response(result)


@router.post("/validate", response_model=TournamentTemplatesImportResponse)
def validate_tournament_templates(
    payload: TournamentTemplatesImportRequest,
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> TournamentTemplatesImportResponse:
    result = service.import_dataset(payload.dataset, dry_run=True)
    return _to_import_response(result)


@router.get("/{template_id}", response_model=TournamentTemplateResponse)
def get_tournament_template(
    template_id: str,
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> TournamentTemplateResponse:
    template = service.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"tournament template '{template_id}' not found")
    return _to_template_response(template)


@router.post("", response_model=TournamentTemplateResponse, status_code=201)
def create_tournament_template(
    payload: TournamentTemplateUpsertRequest,
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> TournamentTemplateResponse:
    try:
        created = service.create_template(TournamentTemplate.model_validate(payload.model_dump(exclude_none=True)))
        return _to_template_response(created)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/{template_id}", response_model=TournamentTemplateResponse)
def update_tournament_template(
    template_id: str,
    payload: TournamentTemplateUpsertRequest,
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> TournamentTemplateResponse:
    try:
        updated = service.update_template(template_id, TournamentTemplate.model_validate(payload.model_dump(exclude_none=True)))
        return _to_template_response(updated)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{template_id}", status_code=204)
def delete_tournament_template(
    template_id: str,
    service: TournamentTemplatesConfigService = Depends(get_tournament_templates_config_service),
) -> None:
    try:
        service.delete_template(template_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
