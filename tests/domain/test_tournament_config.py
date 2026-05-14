from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from beta_engine.domain.tournaments import validate_calendar_template_references
from beta_engine.infrastructure.tournament_config import (
    load_season_calendar,
    load_tournament_templates_config,
)


def test_templates_load_correctly() -> None:
    templates = load_tournament_templates_config()

    assert len(templates.templates) >= 4
    assert {t.tour_level for t in templates.templates} == {"WORLD_TOUR", "ELITE_TOUR"}


def test_season_calendar_loads_correctly() -> None:
    calendar = load_season_calendar()

    assert calendar.season == 2027
    assert len(calendar.events) >= 5


def test_multiple_tournaments_can_exist_in_same_week() -> None:
    calendar = load_season_calendar()

    week_one_events = [event for event in calendar.events if event.week == 1]
    week_three_events = [event for event in calendar.events if event.week == 3]

    assert len(week_one_events) == 2
    assert len(week_three_events) == 2


def test_template_reuse_across_multiple_events() -> None:
    templates = load_tournament_templates_config()
    calendar = load_season_calendar()

    validate_calendar_template_references(templates, calendar)

    gold_events = [event for event in calendar.events if event.template_id == "wt_gold_24"]
    assert len(gold_events) == 2


def test_required_tournament_fields_are_validated(tmp_path) -> None:
    bad_template_path = tmp_path / "bad_templates.json"
    bad_template_path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "template_id": "bad",
                        "tour_level": "WORLD_TOUR",
                        "category": "GOLD",
                        "event_name": "Bad Event",
                        "region": "EUROPE",
                        "host_country": "ENG",
                        "main_draw_size": 32,
                        "qualification_draw_size": 16,
                        "seeds_count": 8,
                        "qualifier_spots": 4,
                        "wild_cards": 2,
                        "byes": 0,
                        "lucky_loser_rules": {
                            "enabled": True,
                            "max_spots": 2,
                            "replacement_window": "pre_main_draw_round_1",
                        },
                        "event_duration_days": 6,
                        "qualification_duration_days": 2,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_tournament_templates_config(path=bad_template_path)


def test_tournament_template_config_rejects_duplicate_template_ids(tmp_path) -> None:
    duplicate_template_path = tmp_path / "duplicate_templates.json"
    template = {
        "template_id": "dup_template",
        "tour_level": "WORLD_TOUR",
        "category": "CUSTOM",
        "event_name": "Custom",
        "region": "EUROPE",
        "host_country": "ENG",
        "main_draw_size": 16,
        "qualification_draw_size": 0,
        "seeds_count": 4,
        "qualifier_spots": 0,
        "wild_cards": 2,
        "byes": 0,
        "lucky_loser_rules": {"enabled": True, "max_spots": 0, "replacement_window": "pre_main_draw_round_1"},
        "point_distribution_ref": "custom_points",
        "event_duration_days": 4,
        "qualification_duration_days": 0,
    }
    duplicate_template_path.write_text(json.dumps({"templates": [template, template]}, indent=2), encoding="utf-8")

    from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService

    service = TournamentTemplatesConfigService(config_path=duplicate_template_path, calendar_dir=tmp_path / "calendars")
    result = service.validate_current_dataset()
    assert result.ok is False
    assert "duplicate template_id" in result.errors[0].message
