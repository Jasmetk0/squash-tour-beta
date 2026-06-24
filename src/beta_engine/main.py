"""FastAPI application entrypoint for the beta engine."""

from contextlib import asynccontextmanager

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
    season_active_players_config_path: str | None = None,
    season_calendar_registry_path: str | None = None,
    calendar_templates_registry_path: str | None = None,
    season_builder_apply_audit_log_path: str | None = None,
    season_entry_lists_registry_path: str | None = None,
    season_draws_registry_path: str | None = None,
    season_matches_registry_path: str | None = None,
    season_event_results_registry_path: str | None = None,
    season_point_awards_registry_path: str | None = None,
    season_ranking_snapshots_registry_path: str | None = None,
    points_config_path: str | None = None,
    entry_tuning_config_path: str | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime = build_runtime(database_url=database_url)
        yield

    app = FastAPI(title="Squash Tour Beta Engine", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
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
    if season_active_players_config_path is not None:
        app.state.season_active_players_config_path = season_active_players_config_path
    if season_calendar_registry_path is not None:
        app.state.season_calendar_registry_path = season_calendar_registry_path
    if calendar_templates_registry_path is not None:
        app.state.calendar_templates_registry_path = calendar_templates_registry_path
    if season_builder_apply_audit_log_path is not None:
        app.state.season_builder_apply_audit_log_path = season_builder_apply_audit_log_path
    if season_entry_lists_registry_path is not None:
        app.state.season_entry_lists_registry_path = season_entry_lists_registry_path
    if season_draws_registry_path is not None:
        app.state.season_draws_registry_path = season_draws_registry_path
    if entry_tuning_config_path is not None:
        app.state.entry_tuning_config_path = entry_tuning_config_path
    if season_matches_registry_path is not None:
        app.state.season_matches_registry_path = season_matches_registry_path
    if season_event_results_registry_path is not None:
        app.state.season_event_results_registry_path = season_event_results_registry_path
    if season_point_awards_registry_path is not None:
        app.state.season_point_awards_registry_path = season_point_awards_registry_path
    if season_ranking_snapshots_registry_path is not None:
        app.state.season_ranking_snapshots_registry_path = season_ranking_snapshots_registry_path
    if points_config_path is not None:
        app.state.points_config_path = points_config_path
    app.include_router(api_router)
    return app


app = create_app()
