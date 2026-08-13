import json
from pathlib import Path

import pytest

from beta_engine.application.season_calendar_service import SeasonCalendarRegistry, SeasonCalendarService, TournamentEditionRankingUpdate
from beta_engine.domain.tournaments.models import CalendarEvent, SeasonCalendar


class Templates:
    pass


def service(tmp_path: Path):
    return SeasonCalendarService(template_service=Templates(), calendar_registry_path=tmp_path / "calendars.json")


def event(**updates):
    data = dict(event_id="evt", season="2000/01", season_week=1, template_id="tpl", host_country="ENG", region="EUROPE", main_draw_size=2)
    data.update(updates)
    return CalendarEvent(**data)


def test_incomplete_ranked_draft_saves_and_update_round_trips(tmp_path):
    subject = service(tmp_path)
    subject._save_registry(SeasonCalendarRegistry(calendars_by_season={"2000/01": SeasonCalendar(season="2000/01", events=[event()])}))
    updated = subject.update_edition_ranking(season="2000/01", event_id="evt", request=TournamentEditionRankingUpdate(ranking_status="ranked", ranking_points_table={"champion": 10}))
    assert not updated.points_table_complete
    loaded = subject.get_calendar(season="2000/01").calendar.events[0]
    assert loaded.ranking_status.value == "ranked" and loaded.ranking_points_table == {"champion": 10}


def test_rejected_edit_after_competition_is_atomic(tmp_path):
    subject = service(tmp_path)
    original = event(status="active", ranking_status="ranked", ranking_points_table={"champion": 10, "finalist": 5})
    subject._save_registry(SeasonCalendarRegistry(calendars_by_season={"2000/01": SeasonCalendar(season="2000/01", events=[original])}))
    before = subject.calendar_registry_path.read_bytes()
    with pytest.raises(ValueError, match="after competition has begun"):
        subject.update_edition_ranking(season="2000/01", event_id="evt", request=TournamentEditionRankingUpdate(ranking_status="unranked"))
    assert subject.calendar_registry_path.read_bytes() == before

def test_unranked_awards_no_msa_points_while_result_history_remains(tmp_path, monkeypatch):
    from beta_engine.application.season_point_awards_service import PointAwardGenerateRequest
    from beta_engine.application.season_entry_list_service import SeasonEntryListService
    from beta_engine.domain.tournaments.models import TournamentEditionRankingStatus
    from tests.application.test_season_point_awards_service import make_points_service

    original_generate = SeasonEntryListService.generate_entry_list
    def generate_as_unranked(self, *, event_id, request):
        calendar = self.calendar_service._load_registry()
        for season_calendar in calendar.calendars_by_season.values():
            for calendar_event in season_calendar.events:
                if calendar_event.event_id == event_id:
                    calendar_event.ranking_status = TournamentEditionRankingStatus.UNRANKED
        self.calendar_service._save_registry(calendar)
        return original_generate(self, event_id=event_id, request=request)
    monkeypatch.setattr(SeasonEntryListService, "generate_entry_list", generate_as_unranked)
    points_service, event_id = make_points_service(tmp_path)
    calendar_service = points_service.calendar_service
    calendar_service.update_edition_ranking(season="2000/2001", event_id=event_id, request=TournamentEditionRankingUpdate(ranking_status="unranked", ranking_points_table={}))
    package = points_service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=7, dry_run=False)).award_package
    assert package is not None
    assert package.awards == []
    assert package.summary.awarded_player_count == 0
    assert any(issue.code == "unranked_edition_no_msa_result" for issue in package.validation_warnings)
    result = points_service.result_service.get_event_result(event_id=event_id).result_package
    assert result is not None and result.player_results and result.summary.champion_player_id

def test_new_edition_snapshots_only_authored_values_without_fallbacks(tmp_path):
    from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
    from beta_engine.domain.tournaments.models import SeasonCalendarBuildRequest

    templates_path = tmp_path / "templates.json"
    templates_path.write_text(json.dumps({"templates": [{
        "template_id": "authored", "tour_level": "WORLD_TOUR", "category": "OPEN", "event_name": "Authored",
        "region": "EUROPE", "host_country": "ENG", "main_draw_size": 8, "qualification_draw_size": 4,
        "seeds_count": 2, "qualifier_spots": 1, "wild_cards": 0, "byes": 0,
        "lucky_loser_rules": {"enabled": False, "max_spots": 0},
        "point_distribution": {"winner": 90, "finalist": 50, "semifinalist": 20, "quarterfinalist": 10},
        "event_duration_days": 5, "qualification_duration_days": 1
    }]}), encoding="utf-8")
    subject = SeasonCalendarService(
        template_service=TournamentTemplatesConfigService(config_path=templates_path, calendar_dir=tmp_path / "legacy"),
        calendar_registry_path=tmp_path / "calendars.json",
    )
    built = subject.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(dry_run=False))
    built_event = built.calendar.events[0]
    assert built_event.ranking_points_table == {
        "champion": 90, "finalist": 50, "semifinal": 20, "quarterfinal": 10,
    }
    assert "qualification_winner" not in built_event.ranking_points_table
    assert not built_event.points_table_complete
    assert built_event.missing_required_point_stages == ["qualification_winner", "qualification_final"]

@pytest.mark.parametrize(("draw_size", "missing_stage"), [(16, "round_of_16"), (32, "round_of_32")])
def test_inline_snapshot_does_not_materialize_omitted_default_stage(tmp_path, draw_size, missing_stage):
    from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
    from beta_engine.domain.tournaments.models import SeasonCalendarBuildRequest
    templates_path = tmp_path / "templates.json"
    templates_path.write_text(json.dumps({"templates": [{"template_id": "omitted", "tour_level": "WORLD_TOUR", "category": "OPEN", "event_name": "Omitted", "region": "EUROPE", "host_country": "ENG", "main_draw_size": draw_size, "qualification_draw_size": 0, "seeds_count": 4, "qualifier_spots": 0, "wild_cards": 0, "byes": 0, "lucky_loser_rules": {"enabled": False, "max_spots": 0}, "point_distribution": {"winner": 90, "finalist": 50, "semifinalist": 20, "quarterfinalist": 10}, "event_duration_days": 5, "qualification_duration_days": 0}]}), encoding="utf-8")
    subject = SeasonCalendarService(template_service=TournamentTemplatesConfigService(config_path=templates_path, calendar_dir=tmp_path / "legacy"), calendar_registry_path=tmp_path / "calendars.json")
    event = subject.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(dry_run=True)).calendar.events[0]
    assert missing_stage not in event.ranking_points_table
    assert missing_stage in event.missing_required_point_stages
    assert not event.points_table_complete


def test_inline_snapshot_preserves_explicit_zero(tmp_path):
    from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
    from beta_engine.domain.tournaments.models import SeasonCalendarBuildRequest
    templates_path = tmp_path / "templates.json"
    templates_path.write_text(json.dumps({"templates": [{"template_id": "zero", "tour_level": "WORLD_TOUR", "category": "OPEN", "event_name": "Zero", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 16, "qualification_draw_size": 0, "seeds_count": 4, "qualifier_spots": 0, "wild_cards": 0, "byes": 0, "lucky_loser_rules": {"enabled": False, "max_spots": 0}, "point_distribution": {"winner": 90, "finalist": 50, "semifinalist": 20, "quarterfinalist": 10, "round_of_16": 0}, "event_duration_days": 5, "qualification_duration_days": 0}]}), encoding="utf-8")
    subject = SeasonCalendarService(template_service=TournamentTemplatesConfigService(config_path=templates_path, calendar_dir=tmp_path / "legacy"), calendar_registry_path=tmp_path / "calendars.json")
    event = subject.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(dry_run=True)).calendar.events[0]
    assert event.ranking_points_table["round_of_16"] == 0
    assert event.points_table_complete
