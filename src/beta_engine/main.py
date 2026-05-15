"""FastAPI application entrypoint for the beta engine."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from beta_engine.api.deps import build_runtime
from beta_engine.api.routes import router as api_router

DEV_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app(
    *,
    database_url: str | None = None,
    countries_config_path: str | None = None,
    manual_player_overrides_config_path: str | None = None,
    tournament_templates_config_path: str | None = None,
    calendar_config_dir: str | None = None,
    initial_player_pool_config_path: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Squash Tour Beta Engine", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.runtime = build_runtime(database_url=database_url)
    if countries_config_path is not None:
        app.state.countries_config_path = countries_config_path
    if manual_player_overrides_config_path is not None:
        app.state.manual_player_overrides_config_path = manual_player_overrides_config_path
    if tournament_templates_config_path is not None:
        app.state.tournament_templates_config_path = tournament_templates_config_path
    if calendar_config_dir is not None:
        app.state.calendar_config_dir = calendar_config_dir
    if initial_player_pool_config_path is not None:
        app.state.initial_player_pool_config_path = initial_player_pool_config_path
    app.include_router(api_router)
    return app


app = create_app()
