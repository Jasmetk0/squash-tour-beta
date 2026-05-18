from __future__ import annotations

from pathlib import Path

from beta_engine.application.season_calendar_service import SeasonCalendarRegistry, SeasonCalendarService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, EntryListValidationIssue
from beta_engine.application.season_readiness_service import SeasonReadinessRequest, SeasonReadinessService
from beta_engine.application.season_week_recovery_service import SeasonWeekRecoveryService
from beta_engine.application.season_week_simulation_execution_service import RunSeasonWeekRequest
from test_season_week_simulation_execution_service import make_execution_service


def _service_from_execution(execution) -> SeasonReadinessService:
    return SeasonReadinessService(
        recovery_service=SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service),
        calendar_service=execution.lifecycle_service.calendar_service,
    )


def test_no_calendar_returns_build_calendar_action(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    missing_calendar = SeasonCalendarService(template_service=execution.lifecycle_service.calendar_service.template_service, calendar_registry_path=tmp_path / "missing-calendars.json")
    recovery = SeasonWeekRecoveryService(
        preflight_service=type(execution.preflight_service)(missing_calendar, execution.lifecycle_service, execution.event_simulation_service, execution.ranking_snapshot_service),
        lifecycle_service=execution.lifecycle_service,
        ranking_snapshot_service=execution.ranking_snapshot_service,
    )
    service = SeasonReadinessService(recovery_service=recovery, calendar_service=missing_calendar)
    result = service.inspect_season(SeasonReadinessRequest(season="2000/2001"))
    assert result.summary.next_safe_action == "build_calendar"
    assert result.metadata.read_only is True
    assert result.validation_errors


def test_empty_calendar_no_events_returns_61_empty_weeks(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    service = _service_from_execution(execution)
    calendar_result = service.calendar_service.get_calendar(season="2000/2001")
    empty_calendar = calendar_result.calendar.model_copy(update={"events": []})
    service.calendar_service._save_registry(SeasonCalendarRegistry(calendars_by_season={"2000/2001": empty_calendar}))

    result = service.inspect_season(SeasonReadinessRequest(season="2000/2001", include_empty_weeks=True))
    assert len(result.weeks) == 61
    assert all(row.status == "empty" for row in result.weeks)
    assert result.summary.empty_weeks == 61
    assert result.summary.next_safe_action == "no_events"


def test_planned_event_week_sets_next_week_to_run(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    result = _service_from_execution(execution).inspect_season(SeasonReadinessRequest(season="2000/2001"))
    row = next(row for row in result.weeks if row.season_week == week)
    assert row.status == "planned"
    assert result.summary.next_week_to_run == week
    assert result.summary.next_safe_action == "run_week"


def test_after_week_run_without_apply_points_ready_for_point_application(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=5))
    result = _service_from_execution(execution).inspect_season(SeasonReadinessRequest(season="2000/2001"))
    row = next(row for row in result.weeks if row.season_week == week)
    assert row.status == "ready_for_point_application"
    assert result.summary.next_safe_action == "apply_points"


def test_after_apply_points_no_snapshot_ready_for_snapshot_publication(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=6, apply_points=True))
    result = _service_from_execution(execution).inspect_season(SeasonReadinessRequest(season="2000/2001"))
    row = next(row for row in result.weeks if row.season_week == week)
    assert row.status == "ready_for_snapshot_publication"
    assert result.summary.next_safe_action == "publish_snapshot"


def test_completed_week_with_snapshot_completes_season_when_all_event_weeks_complete(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=7, apply_points=True, publish_snapshot=True))
    result = _service_from_execution(execution).inspect_season(SeasonReadinessRequest(season="2000/2001"))
    row = next(row for row in result.weeks if row.season_week == week)
    assert row.status == "complete"
    assert result.summary.season_complete is True
    assert result.summary.next_safe_action == "review_completed_season"


def test_blocked_week_sets_blocker_and_resolve_action(tmp_path: Path) -> None:
    execution, event_id, week = make_execution_service(tmp_path)
    execution.event_simulation_service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = execution.event_simulation_service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[event_id]
    entry_list.validation_errors.append(EntryListValidationIssue(severity="error", code="forced_error", message="forced error", event_id=event_id))
    registry.entry_lists_by_event_id[event_id] = entry_list
    execution.event_simulation_service.entry_list_service._save_registry(registry)

    result = _service_from_execution(execution).inspect_season(SeasonReadinessRequest(season="2000/2001"))
    assert result.summary.first_blocked_week == week
    assert result.summary.season_ready_to_continue is False
    assert result.summary.next_safe_action == "resolve_blockers"


def test_output_filters_do_not_change_summary_counts(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=7, apply_points=True, publish_snapshot=True))
    result = _service_from_execution(execution).inspect_season(SeasonReadinessRequest(season="2000/2001", include_empty_weeks=False, include_completed_weeks=False))
    assert result.weeks == []
    assert result.summary.total_weeks == 61
    assert result.summary.empty_weeks == 60
    assert result.summary.complete_weeks == 1


def test_determinism_same_persisted_state_same_fingerprint(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    service = _service_from_execution(execution)
    first = service.inspect_season(SeasonReadinessRequest(season="2000/2001"))
    second = service.inspect_season(SeasonReadinessRequest(season="2000/2001"))
    assert first.metadata.generated_fingerprint == second.metadata.generated_fingerprint


def test_read_only_does_not_change_registries(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    service = _service_from_execution(execution)
    paths = [tmp_path / name for name in ["calendars.json", "entries.json", "draws.json", "matches.json", "results.json", "points.json", "snapshots.json", "active.json"]]
    before = {path.name: path.read_text(encoding="utf-8") if path.exists() else None for path in paths}
    result = service.inspect_season(SeasonReadinessRequest(season="2000/2001"))
    after = {path.name: path.read_text(encoding="utf-8") if path.exists() else None for path in paths}
    assert result.metadata.read_only is True
    assert before == after
