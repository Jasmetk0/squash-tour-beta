from beta_engine.application.season_template_service import SeasonTemplateService, SeasonTemplateSlot, SeasonTemplateSummary, SeasonTemplateValidationIssue
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


def test_validate_template_by_id_reports_structured_summary_errors(tmp_path):
    config_path = tmp_path / "templates.json"
    config_path.write_text('{"templates":[{"template_id":"tmp1","tour_level":"WORLD_TOUR","category":"PLATINUM","event_name":"A","region":"EUROPE","host_country":"ENG","main_draw_size":32,"qualification_draw_size":16,"seeds_count":8,"qualifier_spots":4,"wild_cards":2,"byes":0,"lucky_loser_rules":{"enabled":true,"max_spots":2,"replacement_window":"pre_main_draw_round_1"},"point_distribution_ref":"world","prize_money":1000,"prestige":1,"event_duration_days":6,"qualification_duration_days":2,"duration_in_season_weeks":1,"active":true}]}', encoding='utf-8')
    service = SeasonTemplateService(template_service=TournamentTemplatesConfigService(config_path=config_path))
    response = service.validate_template_by_id("not_real")
    assert response.template_exists is False
    assert response.read_only is True
    assert response.summary.status == "errors"
    assert response.summary.error_count == 1
    assert any(issue.code == "template_not_found" for issue in response.issues)


def test_build_slot_validation_preview_uses_unique_codes_but_occurrence_counts(tmp_path):
    config_path = tmp_path / "templates.json"
    config_path.write_text('{"templates":[]}', encoding="utf-8")
    service = SeasonTemplateService(template_service=TournamentTemplatesConfigService(config_path=config_path))
    issues = [
        SeasonTemplateValidationIssue(severity="warning", code="template_slot_duration_long", message="w1", slot_id="s1"),
        SeasonTemplateValidationIssue(severity="warning", code="template_slot_duration_long", message="w2", slot_id="s2"),
    ]
    preview = service.build_slot_validation_preview(
        issues=issues,
        template_id="default_msa_template_preview",
        template_exists=True,
    )
    assert preview is not None
    assert preview.status == "warnings"
    assert preview.warning_count == 2
    assert preview.issue_count == 2
    assert preview.warning_codes == ["template_slot_duration_long"]
    assert preview.issue_codes == ["template_slot_duration_long"]


def test_build_slot_validation_preview_returns_none_when_template_missing(tmp_path):
    config_path = tmp_path / "templates.json"
    config_path.write_text('{"templates":[]}', encoding="utf-8")
    service = SeasonTemplateService(template_service=TournamentTemplatesConfigService(config_path=config_path))
    preview = service.build_slot_validation_preview(
        issues=[],
        template_id="not_real",
        template_exists=False,
    )
    assert preview is None


def test_build_slot_validation_preview_prefers_errors_for_mixed_issues(tmp_path):
    config_path = tmp_path / "templates.json"
    config_path.write_text('{"templates":[]}', encoding="utf-8")
    service = SeasonTemplateService(template_service=TournamentTemplatesConfigService(config_path=config_path))
    issues = [
        SeasonTemplateValidationIssue(severity="warning", code="template_slot_duration_long", message="w", slot_id="s1"),
        SeasonTemplateValidationIssue(severity="error", code="template_slot_category_missing", message="e", slot_id="s1"),
    ]
    preview = service.build_slot_validation_preview(
        issues=issues,
        template_id="default_msa_template_preview",
        template_exists=True,
    )
    assert preview is not None
    assert preview.status == "errors"
    assert preview.error_count == 1
    assert preview.warning_count == 1
    assert preview.issue_count == 2
