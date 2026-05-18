"""Dependency wiring for FastAPI routers."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.config_validation_service import ConfigValidationService
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.initial_player_pool_service import InitialPlayerPoolService
from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_entry_list_service import SeasonEntryListService
from beta_engine.application.season_draw_service import SeasonDrawService
from beta_engine.application.season_match_service import SeasonMatchService
from beta_engine.application.season_event_results_service import SeasonEventResultsService
from beta_engine.application.season_event_lifecycle_service import SeasonEventLifecycleService
from beta_engine.application.season_event_simulation_service import SeasonEventSimulationService
from beta_engine.application.season_week_simulation_preflight_service import SeasonWeekSimulationPreflightService
from beta_engine.application.season_week_simulation_execution_service import SeasonWeekSimulationExecutionService
from beta_engine.application.season_week_recovery_service import SeasonWeekRecoveryService
from beta_engine.application.season_readiness_service import SeasonReadinessService
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.application.season_point_breakdown_service import SeasonPointBreakdownService
from beta_engine.application.season_ranking_table_service import SeasonRankingTableService
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService
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


def get_initial_player_pool_service(request: Request) -> InitialPlayerPoolService:
    configured_path = getattr(request.app.state, "initial_player_pool_config_path", None)
    kwargs = {"countries_service": get_countries_config_service(request)}
    if configured_path is not None:
        kwargs["config_path"] = configured_path
    return InitialPlayerPoolService(**kwargs)


def get_initial_pool_season_bootstrap_service(request: Request) -> InitialPoolSeasonBootstrapService:
    configured_path = getattr(request.app.state, "season_active_players_config_path", None)
    kwargs = {"initial_pool_service": get_initial_player_pool_service(request)}
    if configured_path is not None:
        kwargs["active_players_path"] = configured_path
    return InitialPoolSeasonBootstrapService(**kwargs)


def get_season_calendar_service(request: Request) -> SeasonCalendarService:
    configured_path = getattr(request.app.state, "season_calendar_registry_path", None)
    kwargs = {"template_service": get_tournament_templates_config_service(request)}
    if configured_path is not None:
        kwargs["calendar_registry_path"] = configured_path
    return SeasonCalendarService(**kwargs)


def get_season_entry_list_service(request: Request) -> SeasonEntryListService:
    configured_path = getattr(request.app.state, "season_entry_lists_registry_path", None)
    entry_tuning_path = getattr(request.app.state, "entry_tuning_config_path", None)
    kwargs = {
        "active_players_service": get_initial_pool_season_bootstrap_service(request),
        "calendar_service": get_season_calendar_service(request),
        "countries_service": get_countries_config_service(request),
    }
    if configured_path is not None:
        kwargs["entry_lists_path"] = configured_path
    if entry_tuning_path is not None:
        kwargs["entry_tuning_path"] = entry_tuning_path
    return SeasonEntryListService(**kwargs)


def get_season_draw_service(request: Request) -> SeasonDrawService:
    configured_path = getattr(request.app.state, "season_draws_registry_path", None)
    kwargs = {
        "entry_list_service": get_season_entry_list_service(request),
        "calendar_service": get_season_calendar_service(request),
    }
    if configured_path is not None:
        kwargs["draws_path"] = configured_path
    return SeasonDrawService(**kwargs)


def get_world_package_service(request: Request) -> WorldPackageService:
    return WorldPackageService(
        countries_service=get_countries_config_service(request),
        manual_overrides_service=get_manual_player_overrides_service(request),
    )


def get_season_match_service(request: Request) -> SeasonMatchService:
    configured_path = getattr(request.app.state, "season_matches_registry_path", None)
    kwargs = {
        "draw_service": get_season_draw_service(request),
        "active_players_service": get_initial_pool_season_bootstrap_service(request),
    }
    if configured_path is not None:
        kwargs["matches_path"] = configured_path
    return SeasonMatchService(**kwargs)


def get_season_event_results_service(request: Request) -> SeasonEventResultsService:
    configured_path = getattr(request.app.state, "season_event_results_registry_path", None)
    kwargs = {
        "match_service": get_season_match_service(request),
        "draw_service": get_season_draw_service(request),
        "calendar_service": get_season_calendar_service(request),
    }
    if configured_path is not None:
        kwargs["results_path"] = configured_path
    return SeasonEventResultsService(**kwargs)


def get_season_point_awards_service(request: Request) -> SeasonPointAwardsService:
    configured_path = getattr(request.app.state, "season_point_awards_registry_path", None)
    points_config_path = getattr(request.app.state, "points_config_path", None)
    kwargs = {
        "result_service": get_season_event_results_service(request),
        "active_players_service": get_initial_pool_season_bootstrap_service(request),
        "calendar_service": get_season_calendar_service(request),
        "template_service": get_tournament_templates_config_service(request),
    }
    if configured_path is not None:
        kwargs["awards_path"] = configured_path
    if points_config_path is not None:
        kwargs["points_config_path"] = points_config_path
    return SeasonPointAwardsService(**kwargs)


def get_season_ranking_table_service(request: Request) -> SeasonRankingTableService:
    return SeasonRankingTableService(active_players_service=get_initial_pool_season_bootstrap_service(request))


def get_season_ranking_snapshot_service(request: Request) -> SeasonRankingSnapshotService:
    configured_path = getattr(request.app.state, "season_ranking_snapshots_registry_path", None)
    kwargs = {
        "ranking_table_service": get_season_ranking_table_service(request),
        "calendar_service": get_season_calendar_service(request),
        "point_awards_service": get_season_point_awards_service(request),
    }
    if configured_path is not None:
        kwargs["snapshots_path"] = configured_path
    return SeasonRankingSnapshotService(**kwargs)


def get_season_event_lifecycle_service(request: Request) -> SeasonEventLifecycleService:
    return SeasonEventLifecycleService(
        calendar_service=get_season_calendar_service(request),
        entry_list_service=get_season_entry_list_service(request),
        draw_service=get_season_draw_service(request),
        match_service=get_season_match_service(request),
        result_service=get_season_event_results_service(request),
        point_awards_service=get_season_point_awards_service(request),
        ranking_snapshot_service=get_season_ranking_snapshot_service(request),
    )


def get_season_event_simulation_service(request: Request) -> SeasonEventSimulationService:
    return SeasonEventSimulationService(
        lifecycle_service=get_season_event_lifecycle_service(request),
        entry_list_service=get_season_entry_list_service(request),
        draw_service=get_season_draw_service(request),
        match_service=get_season_match_service(request),
        result_service=get_season_event_results_service(request),
        point_awards_service=get_season_point_awards_service(request),
        ranking_snapshot_service=get_season_ranking_snapshot_service(request),
    )


def get_season_week_simulation_preflight_service(request: Request) -> SeasonWeekSimulationPreflightService:
    return SeasonWeekSimulationPreflightService(
        calendar_service=get_season_calendar_service(request),
        lifecycle_service=get_season_event_lifecycle_service(request),
        event_simulation_service=get_season_event_simulation_service(request),
        ranking_snapshot_service=get_season_ranking_snapshot_service(request),
    )


def get_season_week_simulation_execution_service(request: Request) -> SeasonWeekSimulationExecutionService:
    return SeasonWeekSimulationExecutionService(
        preflight_service=get_season_week_simulation_preflight_service(request),
        event_simulation_service=get_season_event_simulation_service(request),
        lifecycle_service=get_season_event_lifecycle_service(request),
        ranking_snapshot_service=get_season_ranking_snapshot_service(request),
    )


def get_season_week_recovery_service(request: Request) -> SeasonWeekRecoveryService:
    return SeasonWeekRecoveryService(
        preflight_service=get_season_week_simulation_preflight_service(request),
        lifecycle_service=get_season_event_lifecycle_service(request),
        ranking_snapshot_service=get_season_ranking_snapshot_service(request),
    )


def get_season_readiness_service(request: Request) -> SeasonReadinessService:
    return SeasonReadinessService(
        recovery_service=get_season_week_recovery_service(request),
        calendar_service=get_season_calendar_service(request),
    )


def get_season_point_breakdown_service(request: Request) -> SeasonPointBreakdownService:
    return SeasonPointBreakdownService(
        point_awards_service=get_season_point_awards_service(request),
        active_players_service=get_initial_pool_season_bootstrap_service(request),
        calendar_service=get_season_calendar_service(request),
    )
