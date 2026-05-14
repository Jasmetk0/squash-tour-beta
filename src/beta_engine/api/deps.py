"""Dependency wiring for FastAPI routers."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.config_validation_service import ConfigValidationService
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.application.world_package_service import WorldPackageService
from beta_engine.application.world_talent_preview_service import WorldTalentPreviewService
from beta_engine.infrastructure.config import load_settings
from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine


@dataclass(slots=True)
class ApiRuntime:
    repository: SimulationPersistenceRepository


def build_runtime(*, database_url: str | None = None) -> ApiRuntime:
    settings = load_settings()
    effective_database_url = database_url or settings.database.url

    engine = create_sqlite_engine(DatabaseSettings(url=effective_database_url))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    repository.bootstrap_schema()
    return ApiRuntime(repository=repository)


def get_runtime(request: Request) -> ApiRuntime:
    return request.app.state.runtime


def get_simulation_api_service(request: Request) -> SimulationApiService:
    runtime = get_runtime(request)
    return SimulationApiService(
        repository=runtime.repository,
        manual_overrides_service=get_manual_player_overrides_service(request),
        countries_service=get_countries_config_service(request),
    )


def get_config_validation_service(_: Request) -> ConfigValidationService:
    return ConfigValidationService()


def get_countries_config_service(request: Request) -> CountriesConfigService:
    configured_path = getattr(request.app.state, "countries_config_path", None)
    if configured_path is None:
        return CountriesConfigService()
    return CountriesConfigService(config_path=configured_path)


def get_tournament_templates_config_service(request: Request) -> TournamentTemplatesConfigService:
    configured_path = getattr(request.app.state, "tournament_templates_config_path", None)
    calendar_dir = getattr(request.app.state, "calendar_config_dir", None)
    if configured_path is None and calendar_dir is None:
        return TournamentTemplatesConfigService()
    kwargs = {}
    if configured_path is not None:
        kwargs["config_path"] = configured_path
    if calendar_dir is not None:
        kwargs["calendar_dir"] = calendar_dir
    return TournamentTemplatesConfigService(**kwargs)


def get_world_talent_preview_service(request: Request) -> WorldTalentPreviewService:
    return WorldTalentPreviewService(countries_service=get_countries_config_service(request))


def get_manual_player_overrides_service(request: Request) -> ManualPlayerOverridesService:
    configured_path = getattr(request.app.state, "manual_player_overrides_config_path", None)
    if configured_path is None:
        return ManualPlayerOverridesService()
    return ManualPlayerOverridesService(config_path=configured_path)


def get_world_package_service(request: Request) -> WorldPackageService:
    return WorldPackageService(
        countries_service=get_countries_config_service(request),
        manual_overrides_service=get_manual_player_overrides_service(request),
    )
