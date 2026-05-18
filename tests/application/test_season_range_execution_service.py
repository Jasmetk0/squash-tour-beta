from __future__ import annotations

from pathlib import Path

from beta_engine.application.season_calendar_service import SeasonCalendarRegistry
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, EntryListValidationIssue
from beta_engine.application.season_range_execution_service import RunSeasonRangeRequest, SeasonRangeExecutionService
from beta_engine.application.season_range_preflight_service import SeasonRangePreflightService
from beta_engine.application.season_readiness_service import SeasonReadinessService
from beta_engine.application.season_week_recovery_service import SeasonWeekRecoveryService
from beta_engine.application.season_week_simulation_execution_service import RunSeasonWeekRequest, SeasonWeekSimulationExecutionService
from test_season_week_simulation_execution_service import make_execution_service


def make_range_service(tmp_path: Path) -> tuple[SeasonRangeExecutionService, SeasonWeekSimulationExecutionService, str, int]:
    execution, event_id, week = make_execution_service(tmp_path)
    readiness = SeasonReadinessService(
        recovery_service=SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service),
        calendar_service=execution.lifecycle_service.calendar_service,
    )
    return SeasonRangeExecutionService(SeasonRangePreflightService(readiness), execution), execution, event_id, week


def _total_points(execution: SeasonWeekSimulationExecutionService) -> tuple[int, int]:
    players = execution.event_simulation_service.entry_list_service.active_players_service.get_active_players(season="2000/2001").players
    return sum(player.ranking_points for player in players), sum(player.race_points for player in players)


def _add_second_week_event(execution: SeasonWeekSimulationExecutionService, week: int) -> int:
    calendar_service = execution.lifecycle_service.calendar_service
    registry = calendar_service._load_registry()
    calendar = registry.calendars_by_season["2000/2001"]
    first = calendar.events[0]
    second_week = week + 1
    calendar.events.append(first.model_copy(update={"event_id": "EVT-2000-W02-second", "event_name": "Second Event", "season_week": second_week, "year_week": first.year_week + 1}))
    calendar_service._save_registry(SeasonCalendarRegistry(calendars_by_season={"2000/2001": calendar}))
    return second_week


def test_unsafe_preflight_no_mutation(tmp_path: Path) -> None:
    service, execution, event_id, week = make_range_service(tmp_path)
    result = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=week, apply_points=False, publish_snapshot=True))
    assert result.summary.run_started is False
    assert result.summary.stop_reason == "range_preflight_not_safe"
    assert execution.event_simulation_service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False


def test_planned_week_executes(tmp_path: Path) -> None:
    service, _, _, week = make_range_service(tmp_path)
    result = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=week, seed=5, apply_points=False, publish_snapshot=False))
    assert result.summary.executed_week_count == 1
    assert result.weeks[0].week_run_result is not None
    assert result.summary.run_completed is True


def test_empty_and_complete_weeks_skipped(tmp_path: Path) -> None:
    service, execution, _, week = make_range_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=7, apply_points=True, publish_snapshot=True))
    result = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=week + 1))
    assert result.summary.skipped_complete_week_count == 1
    assert result.summary.skipped_empty_week_count == 1
    assert result.summary.executed_week_count == 0


def test_ready_for_point_application(tmp_path: Path) -> None:
    service, execution, _, week = make_range_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=5))
    before = _total_points(execution)
    result = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=week, seed=5, apply_points=True, publish_snapshot=False))
    assert result.summary.point_application_week_count == 1
    assert _total_points(execution) != before


def test_ready_for_snapshot_publication(tmp_path: Path) -> None:
    service, execution, _, week = make_range_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=6, apply_points=True))
    result = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=week, seed=6, apply_points=True, publish_snapshot=True))
    assert result.summary.snapshot_publication_week_count == 1
    assert execution.ranking_snapshot_service.get_snapshot(season="2000/2001", season_week=week).snapshot_exists is True


def test_multiple_week_deterministic_order(tmp_path: Path) -> None:
    service, execution, first_event_id, week = make_range_service(tmp_path)
    second_week = _add_second_week_event(execution, week)
    result = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=second_week, seed=8, apply_points=False, publish_snapshot=False))
    assert [row.season_week for row in result.weeks if row.week_run_result] == [week, second_week]
    assert [row.run_order for row in result.weeks if row.week_run_result] == [1, 2]


def test_stop_on_blocked(tmp_path: Path) -> None:
    service, execution, event_id, week = make_range_service(tmp_path)
    second_week = _add_second_week_event(execution, week)
    execution.event_simulation_service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = execution.event_simulation_service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[event_id]
    entry_list.validation_errors.append(EntryListValidationIssue(severity="error", code="forced_error", message="forced error", event_id=event_id))
    registry.entry_lists_by_event_id[event_id] = entry_list
    execution.event_simulation_service.entry_list_service._save_registry(registry)
    result = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=second_week, allow_unsafe_run=True))
    assert result.summary.stopped_early is True
    assert result.summary.blocked_week_count == 1
    assert all(row.season_week != second_week for row in result.weeks)


def test_max_weeks_to_run_and_stop_after_week(tmp_path: Path) -> None:
    service, execution, first_event_id, week = make_range_service(tmp_path)
    second_week = _add_second_week_event(execution, week)
    limited = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=second_week, max_weeks_to_run=1, apply_points=False, publish_snapshot=False))
    assert limited.summary.executed_week_count == 1
    assert limited.summary.stop_reason == "max_weeks_to_run_reached"
    service2, execution2, _, week2 = make_range_service(tmp_path / "b")
    second_week2 = _add_second_week_event(execution2, week2)
    stopped = service2.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week2, end_week=second_week2, stop_after_week=week2, apply_points=False, publish_snapshot=False))
    assert stopped.summary.executed_week_count == 1
    assert stopped.summary.stop_reason == "stop_after_week_reached"


def test_rerun_safety_no_duplicate_points_or_snapshot_overwrite(tmp_path: Path) -> None:
    service, execution, _, week = make_range_service(tmp_path)
    first = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=week, seed=10, apply_points=True, publish_snapshot=True))
    points_after_first = _total_points(execution)
    second = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=week, seed=10, apply_points=True, publish_snapshot=True))
    assert first.summary.snapshot_publication_week_count == 1
    assert second.summary.skipped_complete_week_count == 1
    assert second.summary.executed_week_count == 0
    assert _total_points(execution) == points_after_first


def test_determinism_same_starting_state_same_fingerprint(tmp_path: Path) -> None:
    service_a, _, _, week_a = make_range_service(tmp_path / "a")
    service_b, _, _, week_b = make_range_service(tmp_path / "b")
    first = service_a.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week_a, end_week=week_a, seed=11, apply_points=True, publish_snapshot=False))
    second = service_b.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week_b, end_week=week_b, seed=11, apply_points=True, publish_snapshot=False))
    assert first.metadata.final_fingerprint == second.metadata.final_fingerprint


def test_partial_range_no_rollback(tmp_path: Path) -> None:
    service, execution, first_event_id, week = make_range_service(tmp_path)
    second_week = _add_second_week_event(execution, week)
    second_event_id = "EVT-2000-W02-second"
    execution.event_simulation_service.entry_list_service.generate_entry_list(event_id=second_event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = execution.event_simulation_service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[second_event_id]
    entry_list.validation_errors.append(EntryListValidationIssue(severity="error", code="forced_error", message="forced error", event_id=second_event_id))
    registry.entry_lists_by_event_id[second_event_id] = entry_list
    execution.event_simulation_service.entry_list_service._save_registry(registry)
    result = service.run_range(RunSeasonRangeRequest(season="2000/2001", start_week=week, end_week=second_week, apply_points=False, publish_snapshot=False, allow_unsafe_run=True))
    assert "no rollback" in result.summary.no_rollback_warning
    assert result.summary.executed_week_count == 1
    assert execution.event_simulation_service.entry_list_service.get_entry_list(event_id=second_event_id).entry_list_exists is True
