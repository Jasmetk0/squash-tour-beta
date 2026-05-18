from __future__ import annotations

from pathlib import Path

from beta_engine.application.season_calendar_service import SeasonCalendarRegistry, SeasonCalendarService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, EntryListValidationIssue
from beta_engine.application.season_range_preflight_service import SeasonRangePreflightRequest, SeasonRangePreflightService
from beta_engine.application.season_readiness_service import SeasonReadinessService
from beta_engine.application.season_week_recovery_service import SeasonWeekRecoveryService
from beta_engine.application.season_week_simulation_execution_service import RunSeasonWeekRequest
from test_season_week_simulation_execution_service import make_execution_service


def _service_from_execution(execution) -> SeasonRangePreflightService:
    readiness = SeasonReadinessService(
        recovery_service=SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service),
        calendar_service=execution.lifecycle_service.calendar_service,
    )
    return SeasonRangePreflightService(readiness_service=readiness)


def test_invalid_range_returns_validation_error(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    result = _service_from_execution(execution).preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=10, end_week=1))
    assert result.validation_errors
    assert result.summary.range_safe_to_run is False
    assert result.summary.next_safe_action == "adjust_range"


def test_no_calendar_recommends_build_calendar(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    missing_calendar = SeasonCalendarService(template_service=execution.lifecycle_service.calendar_service.template_service, calendar_registry_path=tmp_path / "missing-calendars.json")
    recovery = SeasonWeekRecoveryService(
        preflight_service=type(execution.preflight_service)(missing_calendar, execution.lifecycle_service, execution.event_simulation_service, execution.ranking_snapshot_service),
        lifecycle_service=execution.lifecycle_service,
        ranking_snapshot_service=execution.ranking_snapshot_service,
    )
    readiness = SeasonReadinessService(recovery_service=recovery, calendar_service=missing_calendar)
    result = SeasonRangePreflightService(readiness_service=readiness).preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=1, end_week=10))
    assert result.summary.next_safe_action == "build_calendar"
    assert result.summary.range_safe_to_run is False
    assert result.metadata.read_only is True


def test_empty_range_no_event_weeks_recommends_nothing_to_run(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    service = _service_from_execution(execution)
    calendar_result = service.readiness_service.calendar_service.get_calendar(season="2000/2001")
    empty_calendar = calendar_result.calendar.model_copy(update={"events": []})
    service.readiness_service.calendar_service._save_registry(SeasonCalendarRegistry(calendars_by_season={"2000/2001": empty_calendar}))
    result = service.preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=1, end_week=10))
    assert result.summary.next_safe_action == "nothing_to_run"
    assert result.summary.range_safe_to_run is False
    assert all(week.range_action == "skip_empty" for week in result.weeks)


def test_planned_event_week_runs_and_is_safe(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    result = _service_from_execution(execution).preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=week, end_week=week))
    assert result.weeks[0].range_action == "run_week"
    assert result.summary.runnable_weeks == 1
    assert result.summary.range_safe_to_run is True
    assert result.summary.next_safe_action == "run_range"


def test_completed_week_is_skipped(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=7, apply_points=True, publish_snapshot=True))
    result = _service_from_execution(execution).preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=week, end_week=week))
    assert result.weeks[0].range_action == "skip_complete"
    assert result.summary.skipped_weeks == 1
    assert result.summary.range_safe_to_run is False


def test_ready_for_point_application_honors_apply_points_flag(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=5))
    service = _service_from_execution(execution)
    yes = service.preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=week, end_week=week, apply_points=True))
    no = service.preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=week, end_week=week, apply_points=False))
    assert yes.weeks[0].range_action == "apply_points"
    assert yes.summary.range_safe_to_run is True
    assert no.weeks[0].range_action == "recover_week"
    assert no.summary.range_safe_to_run is False
    assert no.summary.next_safe_action == "recover_week"


def test_ready_for_snapshot_publication_honors_publish_snapshot_flag(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=6, apply_points=True))
    service = _service_from_execution(execution)
    yes = service.preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=week, end_week=week, publish_snapshot=True))
    no = service.preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=week, end_week=week, publish_snapshot=False))
    assert yes.weeks[0].range_action == "publish_snapshot"
    assert yes.summary.range_safe_to_run is True
    assert no.weeks[0].range_action == "recover_week"
    assert no.summary.range_safe_to_run is False


def test_blocked_week_stop_on_blocked_is_unsafe(tmp_path: Path) -> None:
    execution, event_id, week = make_execution_service(tmp_path)
    execution.event_simulation_service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = execution.event_simulation_service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[event_id]
    entry_list.validation_errors.append(EntryListValidationIssue(severity="error", code="forced_error", message="forced error", event_id=event_id))
    registry.entry_lists_by_event_id[event_id] = entry_list
    execution.event_simulation_service.entry_list_service._save_registry(registry)
    result = _service_from_execution(execution).preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=week, end_week=week, stop_on_blocked=True))
    assert result.weeks[0].range_action == "blocked"
    assert result.summary.range_safe_to_run is False
    assert result.summary.first_unsafe_week == week
    assert result.summary.next_safe_action == "resolve_blockers"


def test_output_filters_affect_rows_not_summary(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=7, apply_points=True, publish_snapshot=True))
    result = _service_from_execution(execution).preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=1, end_week=3, include_empty_weeks=False, include_completed_weeks=False))
    assert result.weeks == []
    assert result.summary.empty_weeks == 2
    assert result.summary.completed_weeks == 1
    assert result.summary.total_weeks_in_range == 3


def test_determinism_same_persisted_state_same_generated_fingerprint(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    service = _service_from_execution(execution)
    first = service.preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=1, end_week=10))
    second = service.preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=1, end_week=10))
    assert first.metadata.generated_fingerprint == second.metadata.generated_fingerprint


def test_read_only_does_not_change_registries(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    service = _service_from_execution(execution)
    paths = [tmp_path / name for name in ["calendars.json", "entries.json", "draws.json", "matches.json", "results.json", "points.json", "snapshots.json", "active.json"]]
    before = {path.name: path.read_text(encoding="utf-8") if path.exists() else None for path in paths}
    result = service.preflight_range(SeasonRangePreflightRequest(season="2000/2001", start_week=1, end_week=10))
    after = {path.name: path.read_text(encoding="utf-8") if path.exists() else None for path in paths}
    assert result.metadata.read_only is True
    assert before == after
