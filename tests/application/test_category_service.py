import json

from beta_engine.application.category_service import CategoryService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService


def test_category_service_groups_templates_and_is_stable() -> None:
    service = CategoryService(template_service=TournamentTemplatesConfigService())
    payload = service.list_categories()
    payload_second = service.list_categories()

    assert payload.status == "read_only_foundation"
    assert payload == payload_second
    assert payload.categories
    assert all(item.source_template_ids == sorted(item.source_template_ids) for item in payload.categories)

    elite_major = next(item for item in payload.categories if item.name == "ELITE_MAJOR")
    assert elite_major.template_count == 1
    assert elite_major.main_draw_size == 32
    assert elite_major.qualification_draw_size == 16
    assert elite_major.schedule_footprint_weeks == 1


def test_category_service_mixed_fields_become_null_and_note(tmp_path) -> None:
    config_path = tmp_path / "templates.json"
    config_path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "template_id": "x_one",
                        "tour_level": "WORLD_TOUR",
                        "category": "DIAMOND",
                        "event_name": "Diamond One",
                        "region": "EUROPE",
                        "host_country": "ENG",
                        "main_draw_size": 32,
                        "qualification_draw_size": 16,
                        "seeds_count": 8,
                        "qualifier_spots": 4,
                        "wild_cards": 2,
                        "byes": 0,
                        "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"},
                        "point_distribution_ref": "world_tour_gold",
                        "event_duration_days": 6,
                        "qualification_duration_days": 2,
                        "duration_in_season_weeks": 1,
                    },
                    {
                        "template_id": "x_two",
                        "tour_level": "WORLD_TOUR",
                        "category": "DIAMOND",
                        "event_name": "Diamond Two",
                        "region": "EUROPE",
                        "host_country": "ENG",
                        "main_draw_size": 24,
                        "qualification_draw_size": 16,
                        "seeds_count": 8,
                        "qualifier_spots": 4,
                        "wild_cards": 2,
                        "byes": 0,
                        "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"},
                        "point_distribution_ref": "world_tour_gold",
                        "event_duration_days": 6,
                        "qualification_duration_days": 2,
                        "duration_in_season_weeks": 1,
                    },
                ]
            }
        )
    )

    service = CategoryService(template_service=TournamentTemplatesConfigService(config_path=config_path))
    payload = service.list_categories()
    category = payload.categories[0]

    assert category.name == "DIAMOND"
    assert category.main_draw_size is None
    assert any("mixed values across source templates for main_draw_size" in note for note in category.notes)
