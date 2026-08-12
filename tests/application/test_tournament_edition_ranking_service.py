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

def test_unranked_awards_no_msa_points_while_result_history_remains(tmp_path):
    from beta_engine.application.season_point_awards_service import PointAwardGenerateRequest
    from tests.application.test_season_point_awards_service import make_points_service

    points_service, event_id = make_points_service(tmp_path)
    calendar_service = points_service.calendar_service
    calendar = calendar_service.get_calendar(season="2000/2001").calendar
    original = next(item for item in calendar.events if item.event_id == event_id)
    calendar_service.update_edition_ranking(season="2000/2001", event_id=event_id, request=TournamentEditionRankingUpdate(ranking_status="unranked", ranking_points_table={}))
    package = points_service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=7, dry_run=False)).award_package
    assert package is not None
    assert package.awards and all(award.ranking_points_awarded == 0 and award.race_points_awarded == 0 for award in package.awards)
    assert package.summary.awarded_player_count == 0
    result = points_service.result_service.get_event_result(event_id=event_id).result_package
    assert result is not None and result.player_results and result.summary.champion_player_id
