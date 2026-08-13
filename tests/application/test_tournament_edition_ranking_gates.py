from __future__ import annotations

import pytest

from beta_engine.application.season_calendar_service import TournamentEditionRankingUpdate
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest
from beta_engine.application.season_event_simulation_service import SimulateOneEventRequest
from tests.application.test_season_entry_list_service import first_event_id, make_service
from tests.application.test_season_event_simulation_service import make_simulation_service


def complete_table(event):
    return {stage: 10 for stage in event.required_ranking_point_stages}


def test_incomplete_ranked_blocks_ranking_dependent_entries_atomically(tmp_path):
    service = make_service(tmp_path)
    event_id = first_event_id(service)
    event = service.calendar_service.get_calendar(season="2000/2001").calendar.events[0]
    assert not event.points_table_complete
    with pytest.raises(ValueError, match="incomplete points table"):
        service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(dry_run=False))
    assert not service.entry_lists_path.exists()


def test_incomplete_ranked_blocks_simulation_before_mutation(tmp_path):
    service, event_id = make_simulation_service(tmp_path)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False))
    assert result.report is not None
    assert result.report.plan_summary.stop_reason == "ranked_points_table_incomplete"
    assert service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False
    assert service.draw_service.get_draw_package(event_id=event_id).draw_package_exists is False
    assert service.match_service.get_match_package(event_id=event_id).match_package_exists is False


def test_complete_ranked_and_unranked_pass_ranking_prerequisite(tmp_path):
    ranked = make_service(tmp_path / "ranked")
    ranked_id = first_event_id(ranked)
    ranked_event = ranked.calendar_service.get_calendar(season="2000/2001").calendar.events[0]
    ranked.calendar_service.update_edition_ranking(season="2000/2001", event_id=ranked_id, request=TournamentEditionRankingUpdate(ranking_status="ranked", ranking_points_table=complete_table(ranked_event)))
    assert ranked.generate_entry_list(event_id=ranked_id, request=EntryListGenerateRequest(dry_run=True)).entry_list is not None

    unranked = make_service(tmp_path / "unranked")
    unranked_id = first_event_id(unranked)
    unranked.calendar_service.update_edition_ranking(season="2000/2001", event_id=unranked_id, request=TournamentEditionRankingUpdate(ranking_status="unranked", ranking_points_table={}))
    assert unranked.generate_entry_list(event_id=unranked_id, request=EntryListGenerateRequest(dry_run=True)).entry_list is not None
