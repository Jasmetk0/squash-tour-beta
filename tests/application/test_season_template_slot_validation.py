from beta_engine.application.season_template_service import SeasonTemplateService, SeasonTemplateSlot, SeasonTemplateSummary
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService


def test_validate_template_slots_reports_structured_errors(tmp_path):
    config_path = tmp_path / "templates.json"
    config_path.write_text('{"templates":[{"template_id":"tmp1","tour_level":"WORLD_TOUR","category":"PLATINUM","event_name":"A","region":"EUROPE","host_country":"ENG","main_draw_size":32,"qualification_draw_size":16,"seeds_count":8,"qualifier_spots":4,"wild_cards":2,"byes":0,"lucky_loser_rules":{"enabled":true,"max_spots":2,"replacement_window":"pre_main_draw_round_1"},"point_distribution_ref":"world","prize_money":1000,"prestige":1,"event_duration_days":6,"qualification_duration_days":2,"duration_in_season_weeks":1,"active":true}]}', encoding='utf-8')
    service = SeasonTemplateService(template_service=TournamentTemplatesConfigService(config_path=config_path))
    bad_slot = SeasonTemplateSlot.model_construct(
        slot_id="bad-1", season_week_start=10, season_week_end=9, duration_weeks=0,
        tournament_name="", category="", host_country=None, region=None, has_qualification=False,
        qualifying_week_start=None, main_draw_week_start=None, source_template_id=None, notes=None
    )
    summary = SeasonTemplateSummary.model_construct(
        template_id="default_msa_template_preview", name="bad", description="bad", week_count=61, slot_count=1, source="x", status="read_only_foundation", slots=[bad_slot]
    )
    issues = service.validate_template_slots(summary)
    codes = {i.code for i in issues if i.severity == "error"}
    assert "template_slot_event_name_missing" in codes
    assert "template_slot_category_missing" in codes
    assert "template_slot_start_after_end" in codes
    assert "template_slot_duration_invalid" in codes
