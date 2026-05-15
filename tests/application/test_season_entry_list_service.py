from __future__ import annotations

import json
from pathlib import Path

import pytest

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.initial_player_pool_service import InitialPlayerPoolService
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, SeasonEntryListService
from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService, SeasonActivePlayer, SeasonActivePlayersRegistry
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.players.initial_pool import GeneratedPlayerAttributes
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.domain.tournaments import SeasonCalendar, SeasonCalendarEvent, SeasonCalendarMetadata


def write_countries(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"countries": [
        {"code": "AAA", "name": "Alpha", "region": "EUROPE", "population": 5_000_000, "wealth_support": 5, "squash_popularity": 5, "squash_tradition": 5, "system_quality": 5, "travel_region": "EUROPE"},
        {"code": "BBB", "name": "Beta", "region": "ASIA", "population": 5_000_000, "wealth_support": 5, "squash_popularity": 5, "squash_tradition": 5, "system_quality": 5, "travel_region": "ASIA"},
    ]}), encoding="utf-8")


def write_templates(path: Path, *, main_draw_size: int = 8) -> None:
    path.write_text(json.dumps({"templates": [{
        "template_id": "wt_a", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "AAA", "main_draw_size": main_draw_size, "qualification_draw_size": 4, "seeds_count": 4, "qualifier_spots": 2, "wild_cards": 1, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True
    }]}), encoding="utf-8")


def active_player(index: int, country: str = "AAA", ability: int = 88) -> SeasonActivePlayer:
    return SeasonActivePlayer(
        player_id=f"P{index:03d}", name=f"Player {index:03d}", country_code=country, nationality=country,
        birth_year=1975, birth_year_week=1, age_years_at_season_start=25, age_weeks_at_season_start=1300,
        current_ability=ability, potential_ability=max(ability, 90), potential_tier="A", career_stage="prime", play_style="balanced", archetype="all_court",
        attributes=GeneratedPlayerAttributes(technique=ability, movement=ability, physical=ability, mental=ability, consistency=ability, clutch=ability, recovery=ability),
        hidden_career_traits=HiddenCareerTraits(potential_ceiling=max(ability, 90), growth_curve="steady", professionalism=0.9, ambition=0.9, travel_tolerance=0.9, schedule_aggression=0.9, injury_proneness=0.1, resilience=0.9),
        season="2000/2001", source_pool_player_id=f"P{index:03d}", source_generation_fingerprint=f"src-{index}", source_generation="initial_pool", manual_override=False, locked_from_initial_pool=True, bootstrap_fingerprint=f"boot-{index}", bootstrap_seed=1, bootstrap_id="BOOT-test"
    )


def write_active(path: Path, count: int = 20) -> None:
    players = [active_player(i, "AAA" if i % 2 else "BBB", 90 - (i % 10)) for i in range(1, count + 1)]
    registry = SeasonActivePlayersRegistry(players_by_season={"2000/2001": players}, bootstrap_metadata_by_season={})
    path.write_text(json.dumps(registry.model_dump(mode="json")), encoding="utf-8")


def make_service(tmp_path: Path, *, calendar: bool = True, active: bool = True, main_draw_size: int = 8) -> SeasonEntryListService:
    countries_path = tmp_path / "countries.json"; write_countries(countries_path)
    templates_path = tmp_path / "templates.json"; write_templates(templates_path, main_draw_size=main_draw_size)
    active_path = tmp_path / "active.json"
    if active:
        write_active(active_path)
    calendar_path = tmp_path / "calendars.json"
    template_service = TournamentTemplatesConfigService(config_path=templates_path, calendar_dir=tmp_path / "legacy")
    calendar_service = SeasonCalendarService(template_service=template_service, calendar_registry_path=calendar_path)
    if calendar:
        calendar_service.build_calendar(season="2000/2001", request=__import__('beta_engine.domain.tournaments', fromlist=['SeasonCalendarBuildRequest']).SeasonCalendarBuildRequest(seed=1, dry_run=False, overwrite_existing=False, max_events=1))
    bootstrap = InitialPoolSeasonBootstrapService(initial_pool_service=InitialPlayerPoolService(countries_service=CountriesConfigService(config_path=countries_path)), active_players_path=active_path)
    return SeasonEntryListService(active_players_service=bootstrap, calendar_service=calendar_service, countries_service=CountriesConfigService(config_path=countries_path), entry_lists_path=tmp_path / "entries.json")


def first_event_id(service: SeasonEntryListService) -> str:
    registry = service.calendar_service._load_registry()
    return next(iter(registry.calendars_by_season["2000/2001"].events)).event_id


def test_missing_prerequisites_and_unknown_event(tmp_path: Path) -> None:
    svc = make_service(tmp_path, calendar=False, active=True)
    with pytest.raises(ValueError, match="No persisted season calendar"):
        svc.generate_entry_list(event_id="missing", request=EntryListGenerateRequest())
    svc = make_service(tmp_path / "two", calendar=True, active=True)
    with pytest.raises(ValueError, match="Unknown persisted"):
        svc.generate_entry_list(event_id="missing", request=EntryListGenerateRequest())
    svc = make_service(tmp_path / "three", calendar=True, active=False)
    with pytest.raises(ValueError, match="No active season players"):
        svc.generate_entry_list(event_id=first_event_id(svc), request=EntryListGenerateRequest())


def test_dry_run_does_not_persist_and_persist_gets_entry_list(tmp_path: Path) -> None:
    svc = make_service(tmp_path)
    event_id = first_event_id(svc)
    preview = svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=True, include_not_entered=True))
    assert preview.entry_list is not None
    assert preview.summary.total_active_players == 20
    assert not (tmp_path / "entries.json").exists()
    persisted = svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=False, include_not_entered=True))
    assert persisted.entry_list is not None
    assert (tmp_path / "entries.json").exists()
    loaded = svc.get_entry_list(event_id=event_id)
    assert loaded.entry_list_exists is True
    assert loaded.metadata and loaded.metadata.build_fingerprint == persisted.metadata.build_fingerprint


def test_overwrite_safety_and_determinism(tmp_path: Path) -> None:
    svc = make_service(tmp_path)
    event_id = first_event_id(svc)
    a = svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=True))
    b = svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=True))
    assert a.metadata and b.metadata and a.metadata.build_fingerprint == b.metadata.build_fingerprint
    c = svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=124, dry_run=True))
    assert c.metadata and c.metadata.build_fingerprint != a.metadata.build_fingerprint
    svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=False))
    with pytest.raises(ValueError, match="already exists"):
        svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=False, overwrite_existing=False))
    svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=False, overwrite_existing=True))


def test_acceptance_counts_and_template_snapshot(tmp_path: Path) -> None:
    svc = make_service(tmp_path, main_draw_size=8)
    event_id = first_event_id(svc)
    result = svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=True, max_alternates=3))
    assert result.entry_list is not None
    assert result.summary.main_draw_acceptances <= 5  # 8 main - 2 qualifiers - 1 wildcard
    assert result.summary.qualification_acceptances <= 4
    assert result.summary.alternates <= 3
    # Mutating the current template config after calendar persistence must not change the event snapshot draw size.
    write_templates(tmp_path / "templates.json", main_draw_size=32)
    result_after_template_edit = svc.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=True, max_alternates=3))
    assert result_after_template_edit.summary.main_draw_acceptances <= 5


def test_one_event_per_week_overlap_rejects_persistence(tmp_path: Path) -> None:
    svc = make_service(tmp_path)
    registry = svc.calendar_service._load_registry()
    event = registry.calendars_by_season["2000/2001"].events[0]
    second = event.model_copy(update={"event_id": "EVT-2000-W01-wt_b", "template_id": "wt_b"})
    registry.calendars_by_season["2000/2001"] = SeasonCalendar(season="2000/2001", events=[event, second], metadata=SeasonCalendarMetadata(season="2000/2001", season_start_calendar_year=2000, season_start_year_week=35))
    svc.calendar_service._save_registry(registry)
    svc.generate_entry_list(event_id=event.event_id, request=EntryListGenerateRequest(seed=123, dry_run=False))
    preview = svc.generate_entry_list(event_id=second.event_id, request=EntryListGenerateRequest(seed=123, dry_run=True))
    assert any(issue.code == "player_week_overlap" for issue in preview.validation_errors)
    with pytest.raises(ValueError, match="player_week_overlap"):
        svc.generate_entry_list(event_id=second.event_id, request=EntryListGenerateRequest(seed=123, dry_run=False))
