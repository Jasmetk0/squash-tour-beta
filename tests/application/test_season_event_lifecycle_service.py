from __future__ import annotations

from pathlib import Path

from beta_engine.application.season_draw_service import DrawGenerateRequest
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest
from beta_engine.application.season_event_lifecycle_service import SeasonEventLifecycleService
from beta_engine.application.season_event_results_service import EventResultExtractRequest
from beta_engine.application.season_match_service import MatchPackageGenerateRequest, SeasonMatchesRegistry
from beta_engine.application.season_point_awards_service import PointAwardApplyRequest, PointAwardGenerateRequest
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService, WeeklyRankingSnapshotGenerateRequest
from test_season_entry_list_service import first_event_id, make_service
from test_season_event_results_service import _persist_synthetic_package
from test_season_point_awards_service import make_points_service


def lifecycle_service(tmp_path: Path, *, calendar: bool = True) -> tuple[SeasonEventLifecycleService, str | None]:
    entry_service = make_service(tmp_path, calendar=calendar, active=True)
    event_id = first_event_id(entry_service) if calendar else None
    draw_service = __import__('beta_engine.application.season_draw_service', fromlist=['SeasonDrawService']).SeasonDrawService(entry_list_service=entry_service, calendar_service=entry_service.calendar_service, draws_path=tmp_path / 'draws.json')
    match_service = __import__('beta_engine.application.season_match_service', fromlist=['SeasonMatchService']).SeasonMatchService(draw_service=draw_service, active_players_service=entry_service.active_players_service, matches_path=tmp_path / 'matches.json')
    result_service = __import__('beta_engine.application.season_event_results_service', fromlist=['SeasonEventResultsService']).SeasonEventResultsService(match_service=match_service, draw_service=draw_service, calendar_service=entry_service.calendar_service, results_path=tmp_path / 'results.json')
    point_service = __import__('beta_engine.application.season_point_awards_service', fromlist=['SeasonPointAwardsService']).SeasonPointAwardsService(result_service=result_service, active_players_service=entry_service.active_players_service, calendar_service=entry_service.calendar_service, awards_path=tmp_path / 'points.json', points_config_path=tmp_path / 'missing-points.json')
    snapshot_service = SeasonRankingSnapshotService(ranking_table_service=__import__('beta_engine.application.season_ranking_table_service', fromlist=['SeasonRankingTableService']).SeasonRankingTableService(active_players_service=entry_service.active_players_service), calendar_service=entry_service.calendar_service, point_awards_service=point_service, snapshots_path=tmp_path / 'snapshots.json')
    return SeasonEventLifecycleService(entry_service.calendar_service, entry_service, draw_service, match_service, result_service, point_service, snapshot_service), event_id


def first_status(service: SeasonEventLifecycleService):
    return service.get_season_lifecycle(season='2000/2001').events[0]


def test_no_calendar_returns_empty_read_only_response(tmp_path: Path) -> None:
    service, _ = lifecycle_service(tmp_path, calendar=False)
    response = service.get_season_lifecycle(season='2000/2001')
    assert response.events == []
    assert response.metadata.read_only is True
    assert response.validation_errors
    assert response.metadata.generated_fingerprint == service.get_season_lifecycle(season='2000/2001').metadata.generated_fingerprint


def test_planned_entries_draw_and_matches_stages(tmp_path: Path) -> None:
    service, event_id = lifecycle_service(tmp_path)
    assert event_id is not None
    planned = first_status(service)
    assert planned.current_stage == 'planned'
    assert planned.next_recommended_action == 'generate_entries'

    service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    entries = first_status(service)
    assert entries.current_stage == 'entries_generated'
    assert entries.next_recommended_action == 'generate_draw'

    service.draw_service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=2, dry_run=False))
    draw = first_status(service)
    assert draw.current_stage == 'draw_generated'
    assert draw.next_recommended_action == 'generate_matches'

    service.match_service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=3, dry_run=False))
    matches = first_status(service)
    assert matches.current_stage in {'matches_generated', 'in_progress'}
    assert matches.next_recommended_action == 'process_byes_or_simulate_matches'


def test_completed_results_points_applied_snapshot_stages(tmp_path: Path) -> None:
    point_service, event_id = make_points_service(tmp_path)
    lifecycle = SeasonEventLifecycleService(
        calendar_service=point_service.calendar_service,
        entry_list_service=point_service.result_service.match_service.draw_service.entry_list_service,
        draw_service=point_service.result_service.match_service.draw_service,
        match_service=point_service.result_service.match_service,
        result_service=point_service.result_service,
        point_awards_service=point_service,
        ranking_snapshot_service=SeasonRankingSnapshotService(
            ranking_table_service=__import__('beta_engine.application.season_ranking_table_service', fromlist=['SeasonRankingTableService']).SeasonRankingTableService(active_players_service=point_service.active_players_service),
            calendar_service=point_service.calendar_service,
            point_awards_service=point_service,
            snapshots_path=tmp_path / 'snapshots.json',
        ),
    )
    status = first_status(lifecycle)
    assert status.current_stage == 'results_extracted'
    assert status.next_recommended_action == 'generate_point_awards'

    point_service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=False))
    status = first_status(lifecycle)
    assert status.current_stage == 'points_generated'
    assert status.next_recommended_action == 'apply_point_awards'

    point_service.apply_event_point_awards(event_id=event_id, request=PointAwardApplyRequest(seed=88))
    status = first_status(lifecycle)
    assert status.current_stage == 'points_applied'
    assert status.next_recommended_action == 'publish_ranking_snapshot'

    lifecycle.ranking_snapshot_service.generate_snapshot(season='2000/2001', season_week=status.season_week, request=WeeklyRankingSnapshotGenerateRequest(seed=99, dry_run=False))  # type: ignore[union-attr]
    status = first_status(lifecycle)
    assert status.current_stage == 'ranking_snapshot_published'
    assert status.next_recommended_action == 'complete'


def test_completed_match_package_stage_before_results(tmp_path: Path) -> None:
    result_service, _ = _persist_synthetic_package(tmp_path)
    point_service = __import__('beta_engine.application.season_point_awards_service', fromlist=['SeasonPointAwardsService']).SeasonPointAwardsService(result_service=result_service, active_players_service=result_service.match_service.active_players_service, calendar_service=result_service.calendar_service, awards_path=tmp_path / 'points.json')
    lifecycle = SeasonEventLifecycleService(result_service.calendar_service, result_service.match_service.draw_service.entry_list_service, result_service.match_service.draw_service, result_service.match_service, result_service, point_service)
    status = first_status(lifecycle)
    assert status.current_stage == 'completed'
    assert status.next_recommended_action == 'extract_results'


def test_validation_errors_block_and_determinism(tmp_path: Path) -> None:
    service, event_id = lifecycle_service(tmp_path)
    assert event_id is not None
    service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = service.entry_list_service._load_registry()
    entry = registry.entry_lists_by_event_id[event_id]
    entry.validation_errors.append(service.entry_list_service._issue('error', 'synthetic', 'synthetic error', event_id=event_id))
    service.entry_list_service._save_registry(registry)

    first = service.get_season_lifecycle(season='2000/2001')
    second = service.get_season_lifecycle(season='2000/2001')
    status = first.events[0]
    assert status.is_blocked is True
    assert status.next_recommended_action == 'resolve_blocker'
    assert first.metadata.generated_fingerprint == second.metadata.generated_fingerprint


def test_shared_week_snapshot_marks_all_events_in_week(tmp_path: Path) -> None:
    service, event_id = lifecycle_service(tmp_path)
    assert event_id is not None
    registry = service.calendar_service._load_registry()
    calendar = registry.calendars_by_season['2000/2001']
    calendar.events.append(calendar.events[0].model_copy(update={'event_id': 'EVT-2000-W01-second', 'event_name': 'Second Event'}))
    registry.calendars_by_season['2000/2001'] = calendar
    service.calendar_service._save_registry(registry)
    service.ranking_snapshot_service.generate_snapshot(season='2000/2001', season_week=calendar.events[0].season_week, request=WeeklyRankingSnapshotGenerateRequest(seed=5, dry_run=False))  # type: ignore[union-attr]
    response = service.get_season_lifecycle(season='2000/2001')
    assert len(response.events) == 2
    assert {event.current_stage for event in response.events} == {'ranking_snapshot_published'}
    assert all(any('points are not applied' in warning for warning in event.validation_warnings) for event in response.events)
