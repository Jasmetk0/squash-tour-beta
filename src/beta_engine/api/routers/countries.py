from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import get_countries_config_service
from beta_engine.api.schemas import (
    CountriesDatasetResponse,
    CountriesListResponse,
    CountriesMetadataResponse,
    CountryResponse,
    CountryUpsertRequest,
)
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.domain.countries import CountriesConfig, Country

router = APIRouter(prefix="/world/countries", tags=["world"])


def _to_country_response(country: Country) -> CountryResponse:
    return CountryResponse.model_validate(country.model_dump(mode="json"))


@router.get("", response_model=CountriesListResponse)
def list_countries(service: CountriesConfigService = Depends(get_countries_config_service)) -> CountriesListResponse:
    countries = sorted(service.list_countries(), key=lambda country: country.code)
    return CountriesListResponse(countries=[_to_country_response(country) for country in countries])


@router.get("/metadata", response_model=CountriesMetadataResponse)
def get_countries_metadata(service: CountriesConfigService = Depends(get_countries_config_service)) -> CountriesMetadataResponse:
    return CountriesMetadataResponse.model_validate(service.get_metadata().__dict__)


@router.get("/{code}", response_model=CountryResponse)
def get_country(code: str, service: CountriesConfigService = Depends(get_countries_config_service)) -> CountryResponse:
    country = service.get_country(code)
    if country is None:
        raise HTTPException(status_code=404, detail=f"country '{code.upper()}' not found")
    return _to_country_response(country)


@router.post("", response_model=CountryResponse, status_code=201)
def create_country(
    payload: CountryUpsertRequest,
    service: CountriesConfigService = Depends(get_countries_config_service),
) -> CountryResponse:
    try:
        created = service.create_country(Country.model_validate(payload.model_dump()))
        return _to_country_response(created)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/{code}", response_model=CountryResponse)
def update_country(
    code: str,
    payload: CountryUpsertRequest,
    service: CountriesConfigService = Depends(get_countries_config_service),
) -> CountryResponse:
    try:
        updated = service.update_country(code, Country.model_validate(payload.model_dump()))
        return _to_country_response(updated)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{code}", status_code=204)
def delete_country(code: str, service: CountriesConfigService = Depends(get_countries_config_service)) -> None:
    try:
        service.delete_country(code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("", response_model=CountriesDatasetResponse)
def replace_dataset(
    payload: CountriesDatasetResponse,
    service: CountriesConfigService = Depends(get_countries_config_service),
) -> CountriesDatasetResponse:
    try:
        config = service.replace_dataset(
            CountriesConfig.model_validate(
                {
                    "dataset_status": payload.dataset_status,
                    "countries": [item.model_dump() for item in payload.countries],
                }
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CountriesDatasetResponse(
        dataset_status=config.dataset_status,
        countries=[_to_country_response(country) for country in sorted(config.countries, key=lambda item: item.code)],
    )
