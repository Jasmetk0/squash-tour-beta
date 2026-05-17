from __future__ import annotations

import json
from pathlib import Path

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_week_simulation_preflight_service import SeasonWeekSimulationPreflightService, SimulateSeasonWeekPreflightRequest
from beta_engine.application.season_ranking_snapshot_service import WeeklyRankingSnapshotGenerateRequest
from test_season_event_simulation_service import make_simulation_service


def make_preflight_service(tmp_path: Path) -> tuple[SeasonWeekSimulationPreflightService, str]:
    event_service, event_id = make_simulation_service(tmp_path)
    return SeasonWeekSimulationPreflightService(
        calendar_service=event_service.lifecycle_service.calendar_service,
        lifecycle_service=event_service.lifecycle_service,
        event_simulation_service=event_service,
        ranking_snapshot_service=event_service.ranking_snapshot_service,
    ), event_id


def test_no_calendar_returns_validation_error(tmp_path: Path) -> None:
    event_service, _ = make_simulation_service(tmp_path)
    missing_calendar_service = SeasonCalendarService(template_service=event_service.lifecycle_service.calendar_service.template_service, calendar_registry_path=tmp_path / "missing-calendars.json")
    service = SeasonWeekSimulationPreflightService(missing_calendar_service, event_service.lifecycle_service, event_service, event_service.ranking_snapshot_service)
    result = service.preflight_week(season="2000/2001", season_week=1, request=SimulateSeasonWeekPreflightRequest())
    assert result.validation_errors
    assert result.summary.can_run_week is False
    assert result.events == []


def test_no_events_in_week_warns_and_cannot_run(tmp_path: Path) -> None:
    service, _ = make_preflight_service(tmp_path)
    result = service.preflight_week(season="2000/2001", season_week=61, request=SimulateSeasonWeekPreflightRequest())
    assert result.summary.event_count == 0
    assert result.summary.can_run_week is False
    assert "No persisted calendar events exist for this season week." in result.validation_warnings


def test_one_event_dry_run_does_not_persist_artifacts(tmp_path: Path) -> None:
    service, event_id = make_preflight_service(tmp_path)
    result = service.preflight_week(season="2000/2001", season_week=1, request=SimulateSeasonWeekPreflightRequest(seed=7))
    if result.summary.event_count == 0:
        week = service.lifecycle_service.get_event_lifecycle(event_id=event_id).event.season_week
        result = service.preflight_week(season="2000/2001", season_week=week, request=SimulateSeasonWeekPreflightRequest(seed=7))
    assert result.summary.event_count == 1
    assert result.events[0].event_id == event_id
    assert result.events[0].one_event_report.dry_run is True
    assert result.summary.can_run_week is True
    assert service.event_simulation_service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False


def test_multiple_events_same_week_are_summed(tmp_path: Path) -> None:
    service, _ = make_preflight_service(tmp_path)
    calendar = service.calendar_service._load_registry().calendars_by_season["2000/2001"]
    second = calendar.events[0].model_copy(update={"event_id": "EVT-2000-W01-wt_b", "event_name": "World B", "template_id": "wt_b"})
    calendar.events.append(second)
    service.calendar_service._save_registry(type(service.calendar_service._load_registry())(calendars_by_season={"2000/2001": calendar}))
    result = service.preflight_week(season="2000/2001", season_week=calendar.events[0].season_week, request=SimulateSeasonWeekPreflightRequest())
    assert result.summary.event_count == 2
    assert result.summary.week_has_multiple_events is True
    assert len(result.events) == 2
    assert result.summary.total_planned_steps == sum(event.planned_step_count for event in result.events)


def test_publish_snapshot_requires_apply_points(tmp_path: Path) -> None:
    service, event_id = make_preflight_service(tmp_path)
    week = service.lifecycle_service.get_event_lifecycle(event_id=event_id).event.season_week
    result = service.preflight_week(season="2000/2001", season_week=week, request=SimulateSeasonWeekPreflightRequest(publish_snapshot=True, apply_points=False))
    assert result.summary.can_run_week is False
    assert "publish_snapshot=true requires apply_points=true for week preflight." in result.validation_errors


def test_publish_snapshot_multiple_events_warns_without_mutation(tmp_path: Path) -> None:
    service, event_id = make_preflight_service(tmp_path)
    calendar = service.calendar_service._load_registry().calendars_by_season["2000/2001"]
    second = calendar.events[0].model_copy(update={"event_id": "EVT-2000-W01-wt_b", "event_name": "World B", "template_id": "wt_b"})
    calendar.events.append(second)
    service.calendar_service._save_registry(type(service.calendar_service._load_registry())(calendars_by_season={"2000/2001": calendar}))
    result = service.preflight_week(season="2000/2001", season_week=calendar.events[0].season_week, request=SimulateSeasonWeekPreflightRequest(apply_points=True, publish_snapshot=True))
    assert "All planned event point applications should complete before publishing the week snapshot." in result.validation_warnings
    assert result.summary.total_planned_snapshot_mutations == 1
    assert service.ranking_snapshot_service.get_snapshot(season="2000/2001", season_week=calendar.events[0].season_week).snapshot_exists is False
    assert service.event_simulation_service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False


def test_snapshot_already_exists_warns_when_publish_without_overwrite(tmp_path: Path) -> None:
    service, _ = make_preflight_service(tmp_path)
    service.ranking_snapshot_service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(seed=1, dry_run=False, overwrite_existing=False))
    result = service.preflight_week(season="2000/2001", season_week=1, request=SimulateSeasonWeekPreflightRequest(apply_points=True, publish_snapshot=True, overwrite_existing=False))
    assert result.summary.snapshot_already_exists is True
    assert "Ranking snapshot already exists for this week; later run-week execution should skip or require overwrite." in result.validation_warnings


def test_blocked_event_sets_first_blocked(tmp_path: Path) -> None:
    service, event_id = make_preflight_service(tmp_path)
    week = service.lifecycle_service.get_event_lifecycle(event_id=event_id).event.season_week
    result = service.preflight_week(season="2000/2001", season_week=week, request=SimulateSeasonWeekPreflightRequest(publish_snapshot=True, apply_points=False))
    assert result.summary.can_run_week is False
    assert result.summary.first_blocked_event_id == event_id


def test_event_id_filter_and_unknown_warning(tmp_path: Path) -> None:
    service, event_id = make_preflight_service(tmp_path)
    week = service.lifecycle_service.get_event_lifecycle(event_id=event_id).event.season_week
    result = service.preflight_week(season="2000/2001", season_week=week, request=SimulateSeasonWeekPreflightRequest(event_id_filter=[event_id, "missing"]))
    assert [event.event_id for event in result.events] == [event_id]
    assert any("Unknown event_id_filter" in warning for warning in result.validation_warnings)


def test_determinism_and_registry_not_mutated(tmp_path: Path) -> None:
    service, event_id = make_preflight_service(tmp_path)
    before = json.loads((tmp_path / "calendars.json").read_text())
    first = service.preflight_week(season="2000/2001", season_week=service.lifecycle_service.get_event_lifecycle(event_id=event_id).event.season_week, request=SimulateSeasonWeekPreflightRequest(seed=42))
    second = service.preflight_week(season="2000/2001", season_week=service.lifecycle_service.get_event_lifecycle(event_id=event_id).event.season_week, request=SimulateSeasonWeekPreflightRequest(seed=42))
    after = json.loads((tmp_path / "calendars.json").read_text())
    assert first.metadata.generated_fingerprint == second.metadata.generated_fingerprint
    assert before == after
    assert service.event_simulation_service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False
