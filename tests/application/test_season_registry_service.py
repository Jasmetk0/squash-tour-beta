from beta_engine.application.season_registry_service import SeasonRegistryService


def test_registry_shape_and_bounds() -> None:
    service = SeasonRegistryService()
    seasons = service.list_seasons()
    assert len(seasons) == 40
    assert seasons[0].label == '2000/01'
    assert seasons[-1].label == '2039/40'
    assert all(entry.week_count == 61 for entry in seasons)


def test_week_mapping_examples() -> None:
    service = SeasonRegistryService()
    assert service.season_week_to_year_week(1) == 37
    assert service.season_week_to_year_week(25) == 61
    assert service.season_week_to_year_week(26) == 1
    assert service.season_week_to_year_week(61) == 36
