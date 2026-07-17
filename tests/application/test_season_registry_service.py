from beta_engine.application.season_registry_service import SeasonRegistryService
from beta_engine.domain.calendar import season_week_to_calendar_position


def test_registry_shape_and_bounds() -> None:
    service = SeasonRegistryService()
    seasons = service.list_seasons()
    assert len(seasons) == 50
    assert seasons[0].label == '2000/01'
    assert seasons[-1].label == '2049/50'
    assert all(entry.week_count == 61 for entry in seasons)


def test_week_mapping_examples() -> None:
    service = SeasonRegistryService()
    assert service.season_week_to_year_week(1) == 37
    assert service.season_week_to_year_week(25) == 61
    assert service.season_week_to_year_week(26) == 1
    assert service.season_week_to_year_week(61) == 36


def test_registry_calendar_boundary_positions_use_shared_calendar_helpers() -> None:
    service = SeasonRegistryService()
    season = service.get_season(start_year=2000)

    assert season is not None
    assert season.week_count == 61
    assert season.season_week_start == 1
    assert season.season_week_end == 61
    assert season.year_week_start == 37
    assert season.year_week_end == 36

    boundary_positions = {
        season_week: season_week_to_calendar_position(season.season_start_year, season_week)
        for season_week in (1, 25, 26, 61)
    }
    assert (boundary_positions[1].calendar_year, boundary_positions[1].year_week) == (2000, 37)
    assert (boundary_positions[25].calendar_year, boundary_positions[25].year_week) == (2000, 61)
    assert (boundary_positions[26].calendar_year, boundary_positions[26].year_week) == (2001, 1)
    assert (boundary_positions[61].calendar_year, boundary_positions[61].year_week) == (2001, 36)


def test_registry_response_preserves_horizon_and_week_count() -> None:
    registry = SeasonRegistryService().build_registry()

    assert registry.start_season == '2000/01'
    assert registry.end_season == '2049/50'
    assert registry.season_count == 50
    assert registry.week_count == 61
    assert len(registry.seasons) == 50
    assert all(entry.week_count == 61 for entry in registry.seasons)
