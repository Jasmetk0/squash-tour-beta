from beta_engine.application.category_service import CategoryService
from beta_engine.application.season_registry_service import SeasonRegistryService
from beta_engine.application.season_template_service import SeasonTemplateService
from beta_engine.application.tour_seasons_validation_service import TourSeasonsValidationService
from beta_engine.application.tournament_master_service import TournamentMasterService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService


def test_tour_seasons_validation_service_read_only_foundation() -> None:
    template_service = TournamentTemplatesConfigService()
    service = TourSeasonsValidationService(
        registry_service=SeasonRegistryService(),
        category_service=CategoryService(template_service=template_service),
        tournament_service=TournamentMasterService(template_service=template_service),
        season_template_service=SeasonTemplateService(template_service=template_service),
    )

    first = service.validate()
    second = service.validate()

    assert first.status == "read_only_foundation"
    assert first == second
    assert first.summary.total_checks == first.summary.warning_count + first.summary.info_count + first.summary.ok_count
    assert first.summary.registry_loaded is True
    section_titles = {section.title for section in first.sections}
    assert section_titles == {"Registry", "Category", "Tournament", "Season Template"}
    assert first.planned_future
