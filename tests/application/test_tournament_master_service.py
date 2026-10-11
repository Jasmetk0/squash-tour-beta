import json

from beta_engine.application.tournament_master_service import TournamentMasterService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService


def test_tournament_master_service_groups_and_is_stable() -> None:
    service = TournamentMasterService(template_service=TournamentTemplatesConfigService())
    payload = service.list_tournaments()
    payload_second = service.list_tournaments()

    assert payload.status == "read_only_foundation"
    assert payload == payload_second
    assert payload.tournaments
    assert all(item.source_template_ids == sorted(item.source_template_ids) for item in payload.tournaments)


def test_tournament_master_service_mixed_defaults_safe(tmp_path) -> None:
    config_path = tmp_path / "templates.json"
    config_path.write_text(json.dumps({"templates": [
        {"template_id": "aaa", "tour_level": "WORLD_TOUR", "category": "GOLD", "event_name": "Alpha Open", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 24, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 8, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world_tour_gold", "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1},
        {"template_id": "bbb", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "Alpha Open", "region": "ASIA", "host_country": "QAT", "main_draw_size": 24, "qualification_draw_size": 0, "seeds_count": 8, "qualifier_spots": 0, "wild_cards": 2, "byes": 8, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world_tour_gold", "event_duration_days": 6, "qualification_duration_days": 0, "duration_in_season_weeks": 2}
    ]}))
    service = TournamentMasterService(template_service=TournamentTemplatesConfigService(config_path=config_path))
    t = service.list_tournaments().tournaments[0]
    assert t.name == "Alpha Open"
    assert t.template_count == 2
    assert t.default_category is None
    assert t.default_host_country is None
    assert t.default_region is None
    assert t.default_duration_weeks is None
    assert t.has_qualification is None
    assert any("mixed values across source templates" in note for note in t.notes)
