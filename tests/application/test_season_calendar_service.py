from __future__ import annotations

import json
from pathlib import Path

import pytest

from beta_engine.application.season_calendar_service import SeasonCalendarService, map_season_week_to_calendar_week
from beta_engine.domain.calendar import season_week_to_calendar_position
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments import SeasonCalendarBuildRequest, SeasonCalendarEvent


def write_templates(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"templates": [
        {"template_id": "wt_a", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True},
        {"template_id": "et_a", "tour_level": "ELITE_TOUR", "category": "ELITE", "event_name": "Elite A", "region": "ASIA", "host_country": "MAS", "main_draw_size": 24, "qualification_draw_size": 8, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "elite", "prize_money": 25000, "prestige": 4, "event_duration_days": 5, "qualification_duration_days": 2, "duration_in_season_weeks": 2, "active": True},
        {"template_id": "inactive_a", "tour_level": "ELITE_TOUR", "category": "FUTURE", "event_name": "Inactive", "region": "AMERICAS", "host_country": "USA", "main_draw_size": 16, "qualification_draw_size": 0, "seeds_count": 4, "qualifier_spots": 0, "wild_cards": 1, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 1, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "future", "event_duration_days": 4, "qualification_duration_days": 0, "active": False}
    ]}), encoding="utf-8")


def service(tmp_path: Path) -> SeasonCalendarService:
    template_path = tmp_path / "templates.json"
    write_templates(template_path)
    return SeasonCalendarService(
        template_service=TournamentTemplatesConfigService(config_path=template_path, calendar_dir=tmp_path / "legacy_calendars"),
        calendar_registry_path=tmp_path / "season_calendars.json",
    )


def test_season_week_mapping_default_and_rollover() -> None:
    assert map_season_week_to_calendar_week(season="2000/2001", season_week=1, season_start_calendar_year=2000) == (2000, 37)
    assert map_season_week_to_calendar_week(season="2000/2001", season_week=25, season_start_calendar_year=2000) == (2000, 61)
    assert map_season_week_to_calendar_week(season="2000/2001", season_week=26, season_start_calendar_year=2000) == (2001, 1)
    assert season_week_to_calendar_position("2000/2001", 61).year_week == 36
    with pytest.raises(ValueError, match="season_week"):
        map_season_week_to_calendar_week(season="2000/2001", season_week=62)


def test_dry_run_calendar_build_does_not_persist(tmp_path: Path) -> None:
    svc = service(tmp_path)
    result = svc.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=12345, dry_run=True))
    assert result.summary.event_count == 2
    assert result.calendar is not None
    assert result.metadata is not None
    assert result.metadata.season_start_year_week == 37
    assert all(event.calendar_year and event.year_week for event in result.calendar.events)
    assert not (tmp_path / "season_calendars.json").exists()
    assert svc.get_calendar(season="2000/2001").calendar is None


def test_calendar_build_default_maps_first_event_to_year_week_37(tmp_path: Path) -> None:
    svc = service(tmp_path)
    result = svc.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=0, dry_run=True, max_events=1))

    assert result.calendar is not None
    event = result.calendar.events[0]
    assert event.season_week == 1
    assert event.calendar_year == 2000
    assert event.year_week == 37


def test_calendar_build_rollover_uses_61_week_fax_year(tmp_path: Path) -> None:
    svc = service(tmp_path)
    template = svc.template_service.get_config().templates[0]
    templates = [template.model_copy(update={"template_id": f"wt_{week:02d}", "event_name": f"World {week:02d}"}) for week in range(1, 62)]

    events = svc._build_events(
        season="2000/2001",
        templates=templates,
        seed=0,
        season_start_calendar_year=2000,
        season_start_year_week=37,
    )
    events_by_week = {event.season_week: event for event in events}

    assert events_by_week[25].calendar_year == 2000
    assert events_by_week[25].year_week == 61
    assert events_by_week[26].calendar_year == 2001
    assert events_by_week[26].year_week == 1


def test_persist_calendar_and_overwrite_safety(tmp_path: Path) -> None:
    svc = service(tmp_path)
    result = svc.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=1, dry_run=False))
    assert result.summary.persisted is True
    loaded = svc.get_calendar(season="2000/2001")
    assert loaded.summary.event_count == 2
    with pytest.raises(ValueError, match="already exists"):
        svc.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=2, dry_run=False, overwrite_existing=False))
    svc.build_calendar(season="2001/2002", request=SeasonCalendarBuildRequest(seed=3, dry_run=False))
    overwritten = svc.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=2, dry_run=False, overwrite_existing=True))
    assert overwritten.metadata is not None
    assert svc.get_calendar(season="2001/2002").summary.event_count == 2


def test_template_snapshot_and_determinism(tmp_path: Path) -> None:
    svc = service(tmp_path)
    a = svc.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=44, dry_run=True))
    b = svc.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=44, dry_run=True))
    c = svc.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=45, dry_run=True))
    assert a.metadata is not None and b.metadata is not None and c.metadata is not None
    assert a.metadata.build_fingerprint == b.metadata.build_fingerprint
    assert a.metadata.build_fingerprint != c.metadata.build_fingerprint
    event = a.calendar.events[0]  # type: ignore[union-attr]
    assert event.template_id
    assert event.template_snapshot["template_id"] == event.template_id
    assert event.template_snapshot_fingerprint


def test_validation_detects_duplicates_and_draw_constraints(tmp_path: Path) -> None:
    svc = service(tmp_path)
    event = SeasonCalendarEvent(event_id="dup", season="2000/2001", season_week=1, calendar_year=2000, year_week=37, template_id="wt_a", event_name="Bad", category="BAD", tour_level="WORLD_TOUR", host_country="ENG", region="EUROPE", main_draw_size=8, seeds_count=9)
    warnings, errors = svc.validate_calendar_events([event, event])
    assert any(issue.code == "duplicate_event_id" for issue in errors)
    assert any(issue.code == "seeds_count_exceeds_main_draw" for issue in errors)
    assert any(issue.code == "no_elite_tour_events" for issue in warnings)
