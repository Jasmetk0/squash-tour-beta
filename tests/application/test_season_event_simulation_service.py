from __future__ import annotations

import json
from pathlib import Path

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.initial_player_pool_service import InitialPlayerPoolService
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_category_points_service import SeasonCategoryPointsService
from beta_engine.application.season_draw_service import SeasonDrawService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, SeasonEntryListService
from beta_engine.application.season_event_lifecycle_service import SeasonEventLifecycleService
from beta_engine.application.season_event_results_service import SeasonEventResultsService
from beta_engine.application.season_event_simulation_service import SeasonEventSimulationService, SimulateOneEventRequest
from beta_engine.application.season_match_service import SeasonMatchService
from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService
from beta_engine.application.season_ranking_table_service import SeasonRankingTableService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments import SeasonCalendarBuildRequest
from test_season_entry_list_service import write_active, write_countries
from test_season_event_lifecycle_service import lifecycle_service


def write_complete_templates(path: Path) -> None:
    path.write_text(json.dumps({"templates": [{
        "template_id": "wt_complete", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World Complete", "region": "EUROPE", "host_country": "AAA", "main_draw_size": 4, "qualification_draw_size": 0, "seeds_count": 2, "qualifier_spots": 0, "wild_cards": 0, "byes": 0,
        "lucky_loser_rules": {"enabled": False, "max_spots": 0, "replacement_window": "pre_main_draw_round_1"}, "point_distribution": {"winner": 100, "finalist": 60, "semifinalist": 30, "quarterfinalist": 10}, "prize_money": 100000, "prestige": 9, "event_duration_days": 4, "qualification_duration_days": 0, "duration_in_season_weeks": 1, "active": True
    }]}), encoding="utf-8")


def make_simulation_service(tmp_path: Path, *, complete_template: bool = True) -> tuple[SeasonEventSimulationService, str]:
    if not complete_template:
        lifecycle, event_id = lifecycle_service(tmp_path)
        assert event_id is not None
    else:
        countries_path = tmp_path / "countries.json"; write_countries(countries_path)
        templates_path = tmp_path / "templates.json"; write_complete_templates(templates_path)
        active_path = tmp_path / "active.json"; write_active(active_path, count=12)
        template_service = TournamentTemplatesConfigService(config_path=templates_path, calendar_dir=tmp_path / "legacy")
        points_service = SeasonCategoryPointsService(template_service, tmp_path / "category_points.json")
        points_service.initialize("2000/2001")
        calendar_service = SeasonCalendarService(template_service=template_service, calendar_registry_path=tmp_path / "calendars.json", category_points_service=points_service)
        calendar_service.build_calendar(season="2000/2001", request=SeasonCalendarBuildRequest(seed=1, dry_run=False, overwrite_existing=False, max_events=1))
        bootstrap = InitialPoolSeasonBootstrapService(initial_pool_service=InitialPlayerPoolService(countries_service=CountriesConfigService(config_path=countries_path)), active_players_path=active_path)
        entry_service = SeasonEntryListService(active_players_service=bootstrap, calendar_service=calendar_service, countries_service=CountriesConfigService(config_path=countries_path), entry_lists_path=tmp_path / "entries.json")
        draw_service = SeasonDrawService(entry_list_service=entry_service, calendar_service=calendar_service, draws_path=tmp_path / "draws.json")
        match_service = SeasonMatchService(draw_service=draw_service, active_players_service=bootstrap, matches_path=tmp_path / "matches.json")
        result_service = SeasonEventResultsService(match_service=match_service, draw_service=draw_service, calendar_service=calendar_service, results_path=tmp_path / "results.json")
        point_service = SeasonPointAwardsService(result_service=result_service, active_players_service=bootstrap, calendar_service=calendar_service, template_service=template_service, awards_path=tmp_path / "points.json", points_config_path=tmp_path / "missing-points.json")
        snapshot_service = SeasonRankingSnapshotService(ranking_table_service=SeasonRankingTableService(active_players_service=bootstrap), calendar_service=calendar_service, point_awards_service=point_service, snapshots_path=tmp_path / "snapshots.json")
        lifecycle = SeasonEventLifecycleService(calendar_service, entry_service, draw_service, match_service, result_service, point_service, snapshot_service)
        event_id = next(iter(calendar_service._load_registry().calendars_by_season["2000/2001"].events)).event_id
    assert lifecycle.ranking_snapshot_service is not None
    return SeasonEventSimulationService(lifecycle, lifecycle.entry_list_service, lifecycle.draw_service, lifecycle.match_service, lifecycle.result_service, lifecycle.point_awards_service, lifecycle.ranking_snapshot_service), event_id


def test_unknown_event_returns_validation_error(tmp_path: Path) -> None:
    service, _ = make_simulation_service(tmp_path)
    result = service.simulate_one_event(event_id="missing", request=SimulateOneEventRequest())
    assert result.report is None
    assert result.validation_errors


def test_dry_run_plans_without_persisting_artifacts(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    initial = service.lifecycle_service.get_event_lifecycle(event_id=event_id).event
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=True, seed=7))
    assert result.report is not None
    assert any(step.status == "planned" and step.step == "generate_entries" for step in result.report.steps)
    assert result.report.final_lifecycle == initial
    assert service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False
    assert service.draw_service.get_draw_package(event_id=event_id).draw_package_exists is False
    assert service.match_service.get_match_package(event_id=event_id).match_package_exists is False


def test_execute_event_without_apply_points_stops_after_point_awards(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=11))
    assert result.report is not None, result.validation_errors
    steps = {step.step: step.status for step in result.report.steps}
    assert steps["generate_entries"] == "succeeded"
    assert steps["generate_draw"] == "succeeded"
    assert steps["generate_matches"] == "succeeded"
    assert steps["generate_point_awards"] == "succeeded"
    assert "apply_point_awards" not in steps
    assert result.report.final_lifecycle is not None
    assert result.report.final_lifecycle.current_stage == "points_generated"


def test_execute_with_apply_points_and_snapshot(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=11, apply_points=True, publish_snapshot=True))
    assert result.report is not None, result.validation_errors
    assert result.report.final_lifecycle is not None
    assert result.report.final_lifecycle.current_stage == "ranking_snapshot_published"
    assert result.report.changed_artifacts.active_player_points is True
    assert result.report.changed_artifacts.ranking_snapshot is True


def test_publish_snapshot_requires_apply_points(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, publish_snapshot=True, apply_points=False))
    assert result.report is not None
    assert result.validation_errors
    assert "requires apply_points=true" in result.validation_errors[0]
    assert service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False


def test_second_run_skips_existing_and_does_not_reapply(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    first = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=1, apply_points=True))
    assert first.report and first.report.final_lifecycle and first.report.final_lifecycle.current_stage == "points_applied"
    second = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=1, apply_points=True))
    assert second.report is not None
    apply_steps = [step for step in second.report.steps if step.step == "apply_point_awards"]
    assert apply_steps and apply_steps[-1].status == "skipped"


def test_blocked_lifecycle_stops_by_default(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path, complete_template=False)
    service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[event_id]
    issue = __import__('beta_engine.application.season_entry_list_service', fromlist=['EntryListValidationIssue']).EntryListValidationIssue(severity="error", code="forced_error", message="forced error", event_id=event_id)
    entry_list.validation_errors.append(issue)
    registry.entry_lists_by_event_id[event_id] = entry_list
    service.entry_list_service._save_registry(registry)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False))
    assert result.report is not None
    assert result.report.blocked is True
    assert any("Lifecycle preflight is blocked" in error for error in result.report.validation_errors)


def test_same_seed_same_starting_state_has_same_dry_run_fingerprint(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    first = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(seed=99, dry_run=True)).report
    second = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(seed=99, dry_run=True)).report
    assert first and second
    assert first.metadata.build_fingerprint == second.metadata.build_fingerprint


def _total_points(service: SeasonEventSimulationService) -> tuple[int, int]:
    players = service.entry_list_service.active_players_service.get_active_players(season="2000/2001").players
    return sum(player.ranking_points for player in players), sum(player.race_points for player in players)


def test_dry_run_report_has_full_diagnostics_and_no_artifacts(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    before = service.lifecycle_service.get_event_lifecycle(event_id=event_id).event
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=True, seed=17))
    report = result.report
    assert report is not None
    assert report.plan_summary.stop_reason == "dry_run_plan_only"
    assert report.artifact_state_before == report.artifact_state_after
    assert report.lifecycle_stage_before == before.current_stage
    assert report.lifecycle_stage_after == before.current_stage
    assert all(step.service_called is None for step in report.steps if step.status == "planned")
    assert service.entry_list_service.get_entry_list(event_id=event_id).entry_list_exists is False
    assert service.draw_service.get_draw_package(event_id=event_id).draw_package_exists is False
    assert service.match_service.get_match_package(event_id=event_id).match_package_exists is False


def test_execute_without_apply_points_keeps_active_points_and_reports_next_action(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    before_points = _total_points(service)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=23))
    report = result.report
    assert report is not None
    assert report.final_lifecycle is not None
    assert report.final_lifecycle.current_stage == "points_generated"
    assert _total_points(service) == before_points
    assert report.plan_summary.stop_reason == "points_not_applied"
    assert report.plan_summary.next_safe_action == "apply_point_awards"
    assert report.safe_to_rerun is True
    assert report.artifact_state_after.point_awards_exists is True


def test_execute_with_apply_points_flags_player_mutation_and_rerun_risk(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    before_points = _total_points(service)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=29, apply_points=True))
    report = result.report
    assert report is not None
    assert report.final_lifecycle is not None
    assert report.final_lifecycle.current_stage == "points_applied"
    assert _total_points(service) != before_points
    apply_steps = [step for step in report.steps if step.step == "apply_point_awards"]
    assert apply_steps and apply_steps[-1].mutates_active_players is True
    assert report.safe_to_rerun is False

    rerun = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=29, apply_points=True)).report
    assert rerun is not None
    assert rerun.would_duplicate_points is True
    assert rerun.safe_to_rerun is True


def test_execute_with_apply_points_and_publish_snapshot_flags_snapshot_mutation(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=31, apply_points=True, publish_snapshot=True))
    report = result.report
    assert report is not None
    assert report.final_lifecycle is not None
    assert report.final_lifecycle.current_stage == "ranking_snapshot_published"
    snapshot_steps = [step for step in report.steps if step.step == "publish_ranking_snapshot"]
    assert snapshot_steps and snapshot_steps[-1].mutates_ranking_snapshot is True
    assert report.artifact_state_after.ranking_snapshot_exists is True


def test_blocker_report_has_stop_reason_failed_step_and_cannot_continue(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path, complete_template=False)
    service.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=1, dry_run=False))
    registry = service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[event_id]
    issue = __import__('beta_engine.application.season_entry_list_service', fromlist=['EntryListValidationIssue']).EntryListValidationIssue(severity="error", code="forced_error", message="forced error", event_id=event_id)
    entry_list.validation_errors.append(issue)
    registry.entry_lists_by_event_id[event_id] = entry_list
    service.entry_list_service._save_registry(registry)
    result = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False))
    report = result.report
    assert report is not None
    assert report.plan_summary.stop_reason == "lifecycle_blocked"
    assert report.plan_summary.first_failed_step == "final_lifecycle"
    assert report.can_continue is False


def test_existing_artifacts_rerun_reports_skips_and_duplicate_points(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    first = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=37, apply_points=True)).report
    assert first is not None
    rerun = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=37, apply_points=True)).report
    assert rerun is not None
    assert rerun.would_duplicate_points is True
    assert any(step.step == "apply_point_awards" and step.status == "skipped" and "already applied" in step.action_detail.lower() for step in rerun.steps)
    assert rerun.plan_summary.skipped_step_count >= 1
    assert rerun.artifact_state_before.entries_exists is True
    assert rerun.artifact_state_before.draw_exists is True
    assert rerun.artifact_state_before.matches_exists is True
    assert rerun.artifact_state_before.points_applied is True


def test_completed_state_noop_report_is_stable(tmp_path: Path) -> None:
    service, event_id = make_simulation_service(tmp_path)
    service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=41, apply_points=True, publish_snapshot=True))
    first = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=41, apply_points=True, publish_snapshot=True)).report
    second = service.simulate_one_event(event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=41, apply_points=True, publish_snapshot=True)).report
    assert first and second
    assert first.plan_summary.stop_reason == "already_complete"
    assert first.metadata.build_fingerprint == second.metadata.build_fingerprint
