from beta_engine.application.season_template_service import SeasonTemplateService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService


def test_season_template_service_returns_read_only_foundation() -> None:
    service = SeasonTemplateService(template_service=TournamentTemplatesConfigService())
    payload = service.list_templates()
    assert payload.status == "read_only_foundation"
    assert payload.templates
    template = payload.templates[0]
    assert template.week_count == 61
    for slot in template.slots:
        assert 1 <= slot.season_week_start <= 61
        assert 1 <= slot.season_week_end <= 61
