from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from beta_engine.api.deps import get_countries_config_service, get_manual_player_overrides_service
from beta_engine.api.schemas import (
    ManualPlayerOverrideRequest,
    ManualPlayerOverrideResponse,
    ManualPlayerOverridesListResponse,
)
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.domain.players import ManualPlayerOverride

router = APIRouter(prefix="/world/manual-player-overrides", tags=["world"])


def _ensure_country_exists(*, country_code: str, countries_service: CountriesConfigService) -> None:
    country = countries_service.get_country(country_code)
    if country is None:
        raise HTTPException(
            status_code=422,
            detail=f"country_code '{country_code.upper()}' does not exist in countries dataset",
        )


@router.get("", response_model=ManualPlayerOverridesListResponse)
def list_manual_player_overrides(
    season: int | None = Query(default=None, ge=1900),
    country_code: str | None = Query(default=None, min_length=3, max_length=3),
    enabled: bool | None = Query(default=None),
    service: ManualPlayerOverridesService = Depends(get_manual_player_overrides_service),
) -> ManualPlayerOverridesListResponse:
    overrides = service.list_overrides(season=season, country_code=country_code, enabled=enabled)
    return ManualPlayerOverridesListResponse(
        overrides=[ManualPlayerOverrideResponse.model_validate(item.model_dump(mode="json")) for item in overrides]
    )


@router.get("/{override_id}", response_model=ManualPlayerOverrideResponse)
def get_manual_player_override(
    override_id: str,
    service: ManualPlayerOverridesService = Depends(get_manual_player_overrides_service),
) -> ManualPlayerOverrideResponse:
    override = service.get_override(override_id)
    if override is None:
        raise HTTPException(status_code=404, detail=f"override '{override_id}' not found")
    return ManualPlayerOverrideResponse.model_validate(override.model_dump(mode="json"))


@router.post("", response_model=ManualPlayerOverrideResponse, status_code=201)
def create_manual_player_override(
    payload: ManualPlayerOverrideRequest,
    service: ManualPlayerOverridesService = Depends(get_manual_player_overrides_service),
    countries_service: CountriesConfigService = Depends(get_countries_config_service),
) -> ManualPlayerOverrideResponse:
    _ensure_country_exists(country_code=payload.country_code, countries_service=countries_service)
    try:
        created = service.create_override(ManualPlayerOverride.model_validate(payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ManualPlayerOverrideResponse.model_validate(created.model_dump(mode="json"))


@router.put("/{override_id}", response_model=ManualPlayerOverrideResponse)
def update_manual_player_override(
    override_id: str,
    payload: ManualPlayerOverrideRequest,
    service: ManualPlayerOverridesService = Depends(get_manual_player_overrides_service),
    countries_service: CountriesConfigService = Depends(get_countries_config_service),
) -> ManualPlayerOverrideResponse:
    _ensure_country_exists(country_code=payload.country_code, countries_service=countries_service)
    try:
        updated = service.update_override(override_id, ManualPlayerOverride.model_validate(payload.model_dump()))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ManualPlayerOverrideResponse.model_validate(updated.model_dump(mode="json"))


@router.delete("/{override_id}", status_code=204)
def delete_manual_player_override(
    override_id: str,
    service: ManualPlayerOverridesService = Depends(get_manual_player_overrides_service),
) -> None:
    try:
        service.delete_override(override_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
