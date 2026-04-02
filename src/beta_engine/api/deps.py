"""Dependency wiring for FastAPI routers."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.config_validation_service import ConfigValidationService
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
    return SimulationApiService(repository=runtime.repository)


def get_config_validation_service(_: Request) -> ConfigValidationService:
    return ConfigValidationService()
