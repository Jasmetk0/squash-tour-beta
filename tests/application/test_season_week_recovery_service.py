from __future__ import annotations

from pathlib import Path

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, EntryListValidationIssue
from beta_engine.application.season_week_recovery_service import SeasonWeekRecoveryRequest, SeasonWeekRecoveryService
from beta_engine.application.season_week_simulation_execution_service import RunSeasonWeekRequest
from test_season_week_simulation_execution_service import make_execution_service


def make_recovery_service(tmp_path: Path) -> tuple[SeasonWeekRecoveryService, str, int]:
    execution, event_id, week = make_execution_service(tmp_path)
    return SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service), event_id, week


def test_no_calendar_returns_build_calendar_action(tmp_path: Path) -> None:
    execution, _, _ = make_execution_service(tmp_path)
    missing_calendar = SeasonCalendarService(template_service=execution.lifecycle_service.calendar_service.template_service, calendar_registry_path=tmp_path / "missing-calendars.json")
    service = SeasonWeekRecoveryService(
        preflight_service=type(execution.preflight_service)(missing_calendar, execution.lifecycle_service, execution.event_simulation_service, execution.ranking_snapshot_service),
        lifecycle_service=execution.lifecycle_service,
        ranking_snapshot_service=execution.ranking_snapshot_service,
    )
    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=1))
    assert result.validation_errors
    assert result.summary.next_safe_action == "build_calendar"
    assert result.metadata.read_only is True


def test_no_events_returns_warning_and_no_events_action(tmp_path: Path) -> None:
    service, _, _ = make_recovery_service(tmp_path)
    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=61))
    assert result.summary.event_count == 0
    assert result.summary.next_safe_action == "no_events"
    assert any("No persisted calendar events" in warning for warning in result.validation_warnings)


def test_planned_event_recommends_generate_entries(tmp_path: Path) -> None:
    service, event_id, week = make_recovery_service(tmp_path)
    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    assert result.events[0].event_id == event_id
    assert result.events[0].recommended_event_action == "generate_entries"
    assert result.summary.next_safe_action == "rerun_week_without_overwrite"


def test_run_without_apply_points_ready_for_point_application(tmp_path: Path) -> None:
    execution, event_id, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=5))
    service = SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service)
    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    event = result.events[0]
    assert event.event_id == event_id
    assert event.point_awards_exists is True
    assert event.points_applied is False
    assert event.recommended_event_action == "apply_point_awards"
    assert event.recommended_rerun_flags.apply_points is True
    assert result.summary.ready_for_point_application is True
    assert result.summary.recommended_week_rerun_flags.apply_points is True


def test_apply_points_without_snapshot_ready_for_snapshot_publication(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=6, apply_points=True))
    service = SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service)
    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    assert result.events[0].points_applied is True
    assert result.summary.snapshot_exists is False
    assert result.summary.ready_for_snapshot_publication is True
    assert result.events[0].recommended_event_action == "publish_week_snapshot"
    assert result.summary.next_safe_action == "publish_week_snapshot"
    assert result.summary.recommended_week_rerun_flags.publish_snapshot is True


def test_completed_week_with_snapshot_reviews_completed_week(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=7, apply_points=True, publish_snapshot=True))
    service = SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service)
    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    assert result.summary.week_complete is True
    assert result.summary.next_safe_action == "review_completed_week"
    assert result.events[0].recommended_event_action == "complete"


def test_blocked_event_requires_manual_attention(tmp_path: Path) -> None:
    service, event_id, week = make_recovery_service(tmp_path)
    service.lifecycle_service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = service.lifecycle_service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[event_id]
    entry_list.validation_errors.append(EntryListValidationIssue(severity="error", code="forced_error", message="forced error", event_id=event_id))
    registry.entry_lists_by_event_id[event_id] = entry_list
    service.lifecycle_service.entry_list_service._save_registry(registry)

    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    assert result.summary.week_blocked is True
    assert result.summary.manual_attention_count > 0
    assert result.summary.next_safe_action == "resolve_blockers"
    assert result.events[0].safe_to_rerun_event is False
    assert result.events[0].recommended_event_action == "resolve_blocker"


def test_duplicate_points_risk_after_points_applied(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=8, apply_points=True))
    service = SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service)
    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    assert result.events[0].duplicate_points_risk is True
    assert result.summary.duplicate_points_risk_count == 1


def test_determinism_same_persisted_state_same_fingerprint(tmp_path: Path) -> None:
    execution, _, week = make_execution_service(tmp_path)
    execution.run_week(RunSeasonWeekRequest(season="2000/2001", season_week=week, seed=9))
    service = SeasonWeekRecoveryService(execution.preflight_service, execution.lifecycle_service, execution.ranking_snapshot_service)
    first = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    second = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    assert first.metadata.generated_fingerprint == second.metadata.generated_fingerprint


def test_recovery_is_read_only(tmp_path: Path) -> None:
    service, _, week = make_recovery_service(tmp_path)
    paths = [tmp_path / name for name in ["calendars.json", "entries.json", "draws.json", "matches.json", "results.json", "points.json", "snapshots.json", "active.json"]]
    before = {path.name: path.read_text(encoding="utf-8") if path.exists() else None for path in paths}
    result = service.recover_week(SeasonWeekRecoveryRequest(season="2000/2001", season_week=week))
    after = {path.name: path.read_text(encoding="utf-8") if path.exists() else None for path in paths}
    assert result.metadata.read_only is True
    assert before == after
