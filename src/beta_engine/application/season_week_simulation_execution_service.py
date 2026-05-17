"""Guarded mutating week-level simulation built from week preflight plus one-event execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from beta_engine.application.season_event_lifecycle_service import EventLifecycleStage, SeasonEventLifecycleService
from beta_engine.application.season_event_simulation_service import ChangedArtifacts, SimulateDrawType, SimulateOneEventReport, SimulateOneEventRequest, SeasonEventSimulationService
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService, WeeklyRankingSnapshotGenerateRequest
from beta_engine.application.season_week_simulation_preflight_service import SimulateSeasonWeekPreflightRequest, SimulateSeasonWeekPreflightResult, SeasonWeekEventPreflight, SeasonWeekSimulationPreflightService
from beta_engine.domain.calendar import TOTAL_SEASON_WEEKS

WEEK_RUN_SOURCE = "week_preflight_plus_one_event_execution_reports"
NO_ROLLBACK_WARNING = "Week execution is mutating and no rollback is implemented; partial week runs must be inspected and rerun manually after resolving blockers."

_STAGE_ORDER = {
    "missing_calendar": 0,
    "planned": 1,
    "entries_generated": 2,
    "draw_generated": 3,
    "matches_generated": 4,
    "in_progress": 5,
    "completed": 6,
    "results_extracted": 7,
    "points_generated": 8,
    "points_applied": 9,
    "ranking_snapshot_published": 10,
}


class RunSeasonWeekRequest(BaseModel):
    season: str = "2000/2001"
    season_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    seed: int = 12345
    apply_points: bool = False
    publish_snapshot: bool = False
    overwrite_existing: bool = False
    include_not_entered: bool = False
    max_alternates: int = Field(default=16, ge=0, le=256)
    simulate_draw_type: SimulateDrawType = "qualification_then_main"
    max_steps_per_event: int = Field(default=20, ge=1, le=100)
    stop_after_stage: EventLifecycleStage | None = None
    allow_blocked: bool = False
    allow_incomplete_results: bool = False
    event_id_filter: list[str] = Field(default_factory=list)
    include_completed_events: bool = True
    allow_unsafe_run: bool = False


class SeasonWeekRunEventResult(BaseModel):
    event_id: str
    event_name: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    run_order: int
    preflight_stop_reason: str | None = None
    initial_stage: str | None = None
    final_stage: str | None = None
    event_report: SimulateOneEventReport
    succeeded: bool
    blocked: bool
    changed_artifacts: ChangedArtifacts = Field(default_factory=ChangedArtifacts)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SeasonWeekRunSummary(BaseModel):
    season: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    event_count: int = 0
    attempted_event_count: int = 0
    succeeded_event_count: int = 0
    blocked_event_count: int = 0
    failed_event_count: int = 0
    points_applied_event_count: int = 0
    snapshot_published: bool = False
    snapshot_skipped: bool = False
    snapshot_already_existed: bool = False
    can_run_preflight: bool = False
    run_started: bool = False
    run_completed: bool = False
    stopped_early: bool = False
    first_failed_event_id: str | None = None
    stop_reason: str | None = None
    next_safe_action: str | None = None


class SeasonWeekRunMetadata(BaseModel):
    season: str
    season_week: int
    source: str = WEEK_RUN_SOURCE
    preflight_fingerprint: str
    final_fingerprint: str
    read_only: bool = False


class RunSeasonWeekResult(BaseModel):
    preflight: SimulateSeasonWeekPreflightResult
    events: list[SeasonWeekRunEventResult] = Field(default_factory=list)
    summary: SeasonWeekRunSummary
    metadata: SeasonWeekRunMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonWeekSimulationExecutionService:
    """Run one season week only after backend-owned week preflight."""

    preflight_service: SeasonWeekSimulationPreflightService
    event_simulation_service: SeasonEventSimulationService
    lifecycle_service: SeasonEventLifecycleService
    ranking_snapshot_service: SeasonRankingSnapshotService

    def run_week(self, request: RunSeasonWeekRequest) -> RunSeasonWeekResult:
        warnings = [NO_ROLLBACK_WARNING]
        errors: list[str] = []
        preflight_request = SimulateSeasonWeekPreflightRequest(
            seed=request.seed,
            apply_points=request.apply_points,
            publish_snapshot=request.publish_snapshot,
            overwrite_existing=request.overwrite_existing,
            include_not_entered=request.include_not_entered,
            max_alternates=request.max_alternates,
            simulate_draw_type=request.simulate_draw_type,
            max_steps_per_event=request.max_steps_per_event,
            stop_after_stage=request.stop_after_stage,
            allow_blocked=request.allow_blocked,
            allow_incomplete_results=request.allow_incomplete_results,
            event_id_filter=request.event_id_filter,
            include_completed_events=request.include_completed_events,
        )
        preflight = self.preflight_service.preflight_week(season=request.season, season_week=request.season_week, request=preflight_request)
        warnings.extend(preflight.validation_warnings)
        errors.extend(preflight.validation_errors)
        summary = SeasonWeekRunSummary(
            season=request.season,
            season_week=request.season_week,
            calendar_year=preflight.calendar_year,
            year_week=preflight.year_week,
            event_count=preflight.summary.event_count,
            can_run_preflight=preflight.summary.can_run_week,
            snapshot_already_existed=preflight.summary.snapshot_already_exists,
        )

        if not preflight.summary.can_run_week and not request.allow_unsafe_run:
            summary.run_started = False
            summary.run_completed = False
            summary.stopped_early = False
            summary.stop_reason = "preflight_not_safe"
            summary.first_failed_event_id = preflight.summary.first_blocked_event_id
            summary.next_safe_action = "resolve_preflight_blocker"
            return self._finish(preflight=preflight, events=[], summary=summary, warnings=warnings, errors=errors)

        if not preflight.events:
            summary.stop_reason = "no_events_selected"
            summary.next_safe_action = "build_calendar_or_adjust_event_filter"
            return self._finish(preflight=preflight, events=[], summary=summary, warnings=warnings, errors=errors)

        summary.run_started = True
        selected = self._sort_events(preflight.events)
        run_events: list[SeasonWeekRunEventResult] = []
        blocked_or_failed = False
        stop_reason: str | None = None

        for index, planned_event in enumerate(selected, start=1):
            event_request = SimulateOneEventRequest(
                seed=self._event_seed(request.seed, request.season, request.season_week, planned_event.event_id),
                dry_run=False,
                overwrite_existing=request.overwrite_existing,
                max_steps=request.max_steps_per_event,
                stop_after_stage=request.stop_after_stage,
                apply_points=request.apply_points,
                publish_snapshot=False,
                allow_incomplete_results=request.allow_incomplete_results,
                allow_blocked=request.allow_blocked,
                include_not_entered=request.include_not_entered,
                max_alternates=request.max_alternates,
                simulate_draw_type=request.simulate_draw_type,
            )
            one_event = self.event_simulation_service.simulate_one_event(event_id=planned_event.event_id, request=event_request)
            if one_event.report is None:
                event_errors = one_event.validation_errors or [f"Event '{planned_event.event_id}' did not return an execution report."]
                errors.extend(event_errors)
                blocked_or_failed = True
                stop_reason = "event_failed"
                summary.first_failed_event_id = summary.first_failed_event_id or planned_event.event_id
                if not request.allow_blocked:
                    break
                continue
            report = one_event.report
            event_errors = self._dedupe(one_event.validation_errors + report.validation_errors)
            event_warnings = self._dedupe(one_event.validation_warnings + report.validation_warnings)
            event_blocked = report.blocked or bool(event_errors)
            event_succeeded = not event_blocked and bool(report.completed or report.can_continue)
            run_events.append(SeasonWeekRunEventResult(
                event_id=planned_event.event_id,
                event_name=planned_event.event_name,
                season_week=planned_event.season_week,
                calendar_year=planned_event.calendar_year,
                year_week=planned_event.year_week,
                run_order=index,
                preflight_stop_reason=planned_event.stop_reason,
                initial_stage=report.lifecycle_stage_before,
                final_stage=report.lifecycle_stage_after,
                event_report=report,
                succeeded=event_succeeded,
                blocked=event_blocked,
                changed_artifacts=report.changed_artifacts,
                warnings=event_warnings,
                errors=event_errors,
            ))
            if event_blocked:
                errors.extend(event_errors)
                blocked_or_failed = True
                stop_reason = report.plan_summary.stop_reason or "event_blocked"
                summary.first_failed_event_id = summary.first_failed_event_id or planned_event.event_id
                if not request.allow_blocked:
                    break

        summary.attempted_event_count = len(run_events)
        summary.succeeded_event_count = sum(1 for item in run_events if item.succeeded)
        summary.blocked_event_count = sum(1 for item in run_events if item.blocked)
        summary.failed_event_count = sum(1 for item in run_events if item.errors and not item.blocked)
        summary.points_applied_event_count = sum(1 for item in run_events if item.event_report.artifact_state_after.points_applied)
        summary.stopped_early = len(run_events) < len(selected)

        if request.publish_snapshot:
            self._maybe_publish_week_snapshot(request=request, summary=summary, run_events=run_events, selected_count=len(selected), blocked_or_failed=blocked_or_failed, warnings=warnings, errors=errors)

        if summary.stop_reason is None:
            if blocked_or_failed:
                summary.stop_reason = stop_reason or "event_blocked_or_failed"
            elif summary.stopped_early:
                summary.stop_reason = stop_reason or "stopped_early"
            elif request.publish_snapshot and summary.snapshot_skipped:
                summary.stop_reason = "snapshot_skipped"
            else:
                summary.stop_reason = None
        summary.run_completed = summary.run_started and not summary.stopped_early and not blocked_or_failed and not (request.publish_snapshot and not (summary.snapshot_published or summary.snapshot_skipped))
        summary.next_safe_action = self._next_safe_action(summary=summary, request=request, blocked_or_failed=blocked_or_failed)
        return self._finish(preflight=preflight, events=run_events, summary=summary, warnings=warnings, errors=errors)

    def _maybe_publish_week_snapshot(self, *, request: RunSeasonWeekRequest, summary: SeasonWeekRunSummary, run_events: list[SeasonWeekRunEventResult], selected_count: int, blocked_or_failed: bool, warnings: list[str], errors: list[str]) -> None:
        if not request.apply_points:
            summary.snapshot_skipped = True
            summary.stop_reason = "publish_snapshot_requires_apply_points"
            errors.append("publish_snapshot=true requires apply_points=true for week execution.")
            return
        if blocked_or_failed or len(run_events) != selected_count:
            summary.snapshot_skipped = True
            summary.stop_reason = "event_blocked_or_failed"
            warnings.append("Week snapshot was not published because one or more selected events were blocked, failed, or not attempted.")
            return
        incomplete = [item.event_id for item in run_events if not self._stage_at_least(item.final_stage, "points_applied")]
        if incomplete:
            summary.snapshot_skipped = True
            summary.stop_reason = "points_not_applied_for_all_events"
            errors.append(f"Week snapshot requires all selected events to reach points_applied or later; incomplete events: {', '.join(incomplete)}")
            return
        existing = self.ranking_snapshot_service.get_snapshot(season=request.season, season_week=request.season_week)
        summary.snapshot_already_existed = existing.snapshot_exists
        if existing.snapshot_exists and not request.overwrite_existing:
            summary.snapshot_skipped = True
            warnings.append("Ranking snapshot already exists for this week; overwrite_existing=false so week execution skipped snapshot publication.")
            return
        snapshot = self.ranking_snapshot_service.generate_snapshot(
            season=request.season,
            season_week=request.season_week,
            request=WeeklyRankingSnapshotGenerateRequest(seed=self._snapshot_seed(request.seed, request.season, request.season_week), dry_run=False, overwrite_existing=request.overwrite_existing),
        )
        warnings.extend(snapshot.validation_warnings)
        errors.extend(snapshot.validation_errors)
        if snapshot.validation_errors:
            summary.snapshot_skipped = True
            summary.stop_reason = "snapshot_failed"
            return
        summary.snapshot_published = snapshot.snapshot is not None
        summary.snapshot_skipped = not summary.snapshot_published

    @staticmethod
    def _sort_events(events: list[SeasonWeekEventPreflight]) -> list[SeasonWeekEventPreflight]:
        return sorted(events, key=lambda event: (event.season_week, event.calendar_year or 0, event.year_week or 0, event.event_id))

    @staticmethod
    def _stage_at_least(stage: str | None, minimum: str) -> bool:
        return _STAGE_ORDER.get(stage or "missing_calendar", -1) >= _STAGE_ORDER[minimum]

    @staticmethod
    def _event_seed(base_seed: int, season: str, season_week: int, event_id: str) -> int:
        digest = hashlib.sha256(f"{base_seed}:{season}:{season_week}:{event_id}".encode("utf-8")).hexdigest()
        return int(digest[:12], 16) % 2_147_483_647

    @staticmethod
    def _snapshot_seed(base_seed: int, season: str, season_week: int) -> int:
        digest = hashlib.sha256(f"{base_seed}:{season}:{season_week}:week_snapshot".encode("utf-8")).hexdigest()
        return int(digest[:12], 16) % 2_147_483_647

    @staticmethod
    def _next_safe_action(*, summary: SeasonWeekRunSummary, request: RunSeasonWeekRequest, blocked_or_failed: bool) -> str | None:
        if not summary.run_started:
            return summary.next_safe_action or "resolve_preflight_blocker"
        if blocked_or_failed or summary.stopped_early:
            return "resolve_blocker_and_rerun_week_no_rollback_available"
        if request.publish_snapshot and summary.snapshot_skipped:
            if summary.snapshot_already_existed:
                return "review_existing_snapshot_or_rerun_with_overwrite_existing"
            return "resolve_snapshot_blocker_and_rerun_week"
        if not request.apply_points:
            return "rerun_week_with_apply_points_when_ready"
        if request.apply_points and not request.publish_snapshot:
            return "publish_week_snapshot_when_ready"
        return "review_week_report"

    def _finish(self, *, preflight: SimulateSeasonWeekPreflightResult, events: list[SeasonWeekRunEventResult], summary: SeasonWeekRunSummary, warnings: list[str], errors: list[str]) -> RunSeasonWeekResult:
        result = RunSeasonWeekResult(
            preflight=preflight,
            events=events,
            summary=summary,
            metadata=SeasonWeekRunMetadata(season=summary.season, season_week=summary.season_week, preflight_fingerprint=preflight.metadata.generated_fingerprint, final_fingerprint="pending"),
            validation_warnings=self._dedupe(warnings),
            validation_errors=self._dedupe(errors),
        )
        result.metadata.final_fingerprint = self._fingerprint(result.model_dump(mode="json", exclude={"metadata": {"final_fingerprint"}}))
        return result

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
