from __future__ import annotations

from pathlib import Path

from beta_engine.application.season_week_simulation_execution_service import RunSeasonWeekRequest, SeasonWeekSimulationExecutionService
from test_season_event_simulation_service import make_simulation_service


def make_execution_service(tmp_path: Path) -> tuple[SeasonWeekSimulationExecutionService, str, int]:
    event_service, event_id = make_simulation_service(tmp_path)
    from beta_engine.application.season_week_simulation_preflight_service import SeasonWeekSimulationPreflightService

    preflight = SeasonWeekSimulationPreflightService(
        calendar_service=event_service.lifecycle_service.calendar_service,
        lifecycle_service=event_service.lifecycle_service,
        event_simulation_service=event_service,
        ranking_snapshot_service=event_service.ranking_snapshot_service,
    )
    week = event_service.lifecycle_service.get_event_lifecycle(event_id=event_id).event.season_week  # type: ignore[union-attr]
    return SeasonWeekSimulationExecutionService(preflight, event_service, event_service.lifecycle_service, event_service.ranking_snapshot_service), event_id, week


def _total_points(service: SeasonWeekSimulationExecutionService) -> tuple[int, int]:
    players = service.event_simulation_service.entry_list_service.active_players_service.get_active_players(season="2000/2001").players
    return sum(player.ranking_points for player in players), sum(player.race_points for player in players)


def test_preflight_unsafe_no_mutation(tmp_path: Path) -> None:
    service, event_id, week = make_execution_service(tmp_path)
    result = service.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, publish_snapshot=True, apply_points=False))
    assert result.summary.run_started is False
    assert result.summary.stop_reason == "preflight_not_safe"
    assert service.event_simulation_service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False
    assert result.metadata.read_only is False


def test_one_event_run_without_apply_points_generates_artifacts_only(tmp_path: Path) -> None:
    service, event_id, week = make_execution_service(tmp_path)
    before = _total_points(service)
    result = service.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=5))
    assert result.summary.run_started is True
    assert result.summary.run_completed is True
    assert result.summary.succeeded_event_count == 1
    assert result.events[0].event_id == event_id
    assert result.events[0].event_report.artifact_state_after.point_awards_exists is True
    assert _total_points(service) == before
    assert service.ranking_snapshot_service.get_snapshot(season="2000/2001", season_week=week).snapshot_exists is False


def test_one_event_run_with_apply_points_no_snapshot_by_default(tmp_path: Path) -> None:
    service, _, week = make_execution_service(tmp_path)
    before = _total_points(service)
    result = service.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=6, apply_points=True))
    assert result.summary.points_applied_event_count == 1
    assert result.summary.snapshot_published is False
    assert _total_points(service) != before
    assert service.ranking_snapshot_service.get_snapshot(season="2000/2001", season_week=week).snapshot_exists is False


def test_one_event_run_with_apply_points_and_publish_snapshot(tmp_path: Path) -> None:
    service, _, week = make_execution_service(tmp_path)
    result = service.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=7, apply_points=True, publish_snapshot=True))
    assert result.summary.snapshot_published is True
    assert result.summary.snapshot_skipped is False
    assert service.ranking_snapshot_service.get_snapshot(season="2000/2001", season_week=week).snapshot_exists is True
    assert all(not event.event_report.requested_publish_snapshot for event in result.events)


def test_multiple_events_same_week_deterministic_order_stops_on_overlap_blocker(tmp_path: Path) -> None:
    service, _, week = make_execution_service(tmp_path)
    calendar_service = service.lifecycle_service.calendar_service
    registry = calendar_service._load_registry()
    calendar = registry.calendars_by_season["2000/2001"]
    first = calendar.events[0]
    calendar.events.append(first.model_copy(update={"event_id": "EVT-2000-W01-aaa", "event_name": "AAA Event"}))
    calendar.events.append(first.model_copy(update={"event_id": "EVT-2000-W01-zzz", "event_name": "ZZZ Event"}))
    calendar_service._save_registry(type(registry)(calendars_by_season={"2000/2001": calendar}))

    result = service.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=8, apply_points=True, publish_snapshot=True))
    assert [event.event_id for event in result.events] == sorted(event.event_id for event in result.events)
    assert result.summary.event_count == 3
    assert result.summary.succeeded_event_count == 1
    assert result.summary.stopped_early is True
    assert result.summary.snapshot_published is False
    assert service.ranking_snapshot_service.get_snapshot(season="2000/2001", season_week=week).snapshot_exists is False


def test_event_blocked_stops_early_and_skips_snapshot(tmp_path: Path) -> None:
    service, event_id, week = make_execution_service(tmp_path)
    # Force a blocked lifecycle before the guarded run.
    from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, EntryListValidationIssue

    service.event_simulation_service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = service.event_simulation_service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[event_id]
    entry_list.validation_errors.append(EntryListValidationIssue(severity="error", code="forced_error", message="forced error", event_id=event_id))
    registry.entry_lists_by_event_id[event_id] = entry_list
    service.event_simulation_service.entry_list_service._save_registry(registry)

    result = service.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=9, apply_points=True, publish_snapshot=True))
    assert result.summary.run_started is False
    assert result.summary.stop_reason == "preflight_not_safe"
    assert service.ranking_snapshot_service.get_snapshot(season="2000/2001", season_week=week).snapshot_exists is False


def test_rerun_safety_no_duplicate_points_or_snapshot_overwrite(tmp_path: Path) -> None:
    service, _, week = make_execution_service(tmp_path)
    first = service.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=10, apply_points=True, publish_snapshot=True))
    points_after_first = _total_points(service)
    second = service.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=10, apply_points=True, publish_snapshot=True))
    assert first.summary.snapshot_published is True
    assert second.summary.snapshot_published is False
    assert second.summary.snapshot_skipped is True
    assert second.summary.snapshot_already_existed is True
    assert _total_points(service) == points_after_first


def test_determinism_same_starting_state_same_fingerprint(tmp_path: Path) -> None:
    service_a, _, week_a = make_execution_service(tmp_path / "a")
    service_b, _, week_b = make_execution_service(tmp_path / "b")
    first = service_a.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week_a, seed=11, apply_points=True))
    second = service_b.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week_b, seed=11, apply_points=True))
    assert [event.event_id for event in first.events] == [event.event_id for event in second.events]
    assert first.metadata.final_fingerprint == second.metadata.final_fingerprint
