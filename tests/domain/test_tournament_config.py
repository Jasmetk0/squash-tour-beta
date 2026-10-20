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
        load_tournament_templates_config(path=bad_template_path, trusted_root=tmp_path)


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


@pytest.mark.parametrize("season", ["../../private", True, -1, 0, 10000])
def test_calendar_season_cannot_be_untrusted_path_component(season) -> None:
    with pytest.raises(ValueError, match="season must be an integer"):
        load_season_calendar(season=season)


def test_config_loader_rejects_symlink_source(tmp_path) -> None:
    source = tmp_path / "data.json"
    source.write_text("{}")
    link = tmp_path / "external.json"
    try:
        link.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("file symlinks not supported")
    with pytest.raises(ValueError, match="not a symlink"):
        load_tournament_templates_config(path=link, trusted_root=tmp_path)


def test_configuration_loader_rejects_traversal_even_to_json(tmp_path) -> None:
    inner = tmp_path / "inner"
    inner.mkdir()
    source = tmp_path / "config.json"
    source.write_text("{}")
    with pytest.raises(ValueError, match="without traversal"):
        load_tournament_templates_config(path=inner / ".." / "config.json", trusted_root=tmp_path)


def test_configuration_loader_rejects_symlinked_parent(tmp_path) -> None:
    source = tmp_path / "real"
    source.mkdir()
    (source / "config.json").write_text("{}")
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(source, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks not supported")
    with pytest.raises(ValueError, match="symlink"):
        load_tournament_templates_config(path=alias / "config.json", trusted_root=tmp_path)



@pytest.mark.parametrize("path", [
    "../../secrets.json", "/etc/passwd", "config/calendar/other.json",
    "config/tournament_templates/../../private.json",
])
def test_untrusted_string_config_paths_rejected_before_filesystem_access(path: str) -> None:
    with pytest.raises(ValueError, match="unrecognized configuration path"):
        load_tournament_templates_config(path=path)


def test_configuration_loader_rejects_non_regular_directory(tmp_path) -> None:
    directory = tmp_path / "directory.json"
    directory.mkdir()
    with pytest.raises(ValueError, match="regular JSON file"):
        load_tournament_templates_config(path=directory, trusted_root=tmp_path)


def test_custom_config_path_needs_explicit_trusted_root(tmp_path) -> None:
    external = tmp_path / "external.json"
    external.write_text('{"templates": []}')
    with pytest.raises(ValueError, match="trusted root"):
        load_tournament_templates_config(path=external)
    config = load_tournament_templates_config(path=external, trusted_root=tmp_path)
    assert config.templates == []


def test_custom_config_path_cannot_escape_explicit_trusted_root(tmp_path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text('{"templates": []}')
    with pytest.raises(ValueError, match="trusted root"):
        load_tournament_templates_config(path=outside, trusted_root=allowed)


def test_custom_trusted_root_does_not_override_symlink_checks(tmp_path) -> None:
    outside = tmp_path / "external.json"
    outside.write_text('{"templates": []}')
    root = tmp_path / "allowed"
    root.mkdir()
    linked = root / "linked.json"
    try:
        linked.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("file symlinks not supported")
    with pytest.raises(ValueError, match="symlink"):
        load_tournament_templates_config(path=linked, trusted_root=root)
