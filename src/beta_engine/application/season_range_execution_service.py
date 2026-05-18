"""Guarded mutating season-week range execution built from range preflight plus week execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_event_simulation_service import SimulateDrawType
from beta_engine.application.season_range_preflight_service import SeasonRangePreflightRequest, SeasonRangePreflightResult, SeasonRangePreflightService, SeasonRangePreflightWeek
from beta_engine.application.season_week_simulation_execution_service import NO_ROLLBACK_WARNING, RunSeasonWeekRequest, RunSeasonWeekResult, SeasonWeekSimulationExecutionService
from beta_engine.domain.calendar import TOTAL_SEASON_WEEKS

RANGE_RUN_SOURCE = "range_preflight_plus_week_execution_reports"
RANGE_NO_ROLLBACK_WARNING = "Range execution is mutating and no rollback is implemented; earlier successful weeks remain persisted if a later week blocks or fails."

SeasonRangeRunNextSafeAction = Literal[
    "inspect_range_preflight",
    "resolve_blockers",
    "inspect_recovery",
    "rerun_range",
    "inspect_season_readiness",
    "review_completed_range",
]


class RunSeasonRangeRequest(BaseModel):
    season: str = "2000/2001"
    start_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    end_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    seed: int = 12345
    apply_points: bool = True
    publish_snapshot: bool = True
    overwrite_existing: bool = False
    include_empty_weeks: bool = True
    include_completed_weeks: bool = True
    event_id_filter: list[str] = Field(default_factory=list)
    stop_on_blocked: bool = True
    allow_unsafe_run: bool = False
    allow_blocked: bool = False
    allow_incomplete_results: bool = False
    include_not_entered: bool = False
    max_alternates: int = Field(default=16, ge=0, le=256)
    max_steps_per_event: int = Field(default=20, ge=1, le=100)
    simulate_draw_type: SimulateDrawType = "qualification_then_main"
    stop_after_week: int | None = Field(default=None, ge=1, le=TOTAL_SEASON_WEEKS)
    max_weeks_to_run: int | None = Field(default=None, ge=1, le=TOTAL_SEASON_WEEKS)


class SeasonRangeRunWeekResult(BaseModel):
    season_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    calendar_year: int
    year_week: int
    status_before: str
    range_action: str
    run_order: int | None = None
    skipped: bool
    skip_reason: str | None = None
    week_run_result: RunSeasonWeekResult | None = None
    succeeded: bool
    blocked: bool
    failed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SeasonRangeRunSummary(BaseModel):
    season: str
    start_week: int
    end_week: int
    attempted_week_count: int = 0
    skipped_empty_week_count: int = 0
    skipped_complete_week_count: int = 0
    executed_week_count: int = 0
    succeeded_week_count: int = 0
    blocked_week_count: int = 0
    failed_week_count: int = 0
    point_application_week_count: int = 0
    snapshot_publication_week_count: int = 0
    run_started: bool = False
    run_completed: bool = False
    stopped_early: bool = False
    first_failed_week: int | None = None
    first_blocked_week: int | None = None
    stop_reason: str | None = None
    next_safe_action: SeasonRangeRunNextSafeAction = "inspect_range_preflight"
    no_rollback_warning: str = RANGE_NO_ROLLBACK_WARNING
    range_safe_to_run_preflight: bool = False


class SeasonRangeRunMetadata(BaseModel):
    season: str
    source: Literal["range_preflight_plus_week_execution_reports"] = RANGE_RUN_SOURCE
    range_preflight_fingerprint: str
    final_fingerprint: str
    read_only: bool = False


class RunSeasonRangeResult(BaseModel):
    preflight: SeasonRangePreflightResult
    weeks: list[SeasonRangeRunWeekResult] = Field(default_factory=list)
    summary: SeasonRangeRunSummary
    metadata: SeasonRangeRunMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonRangeExecutionService:
    """Run selected season weeks only after backend-owned range preflight."""

    preflight_service: SeasonRangePreflightService
    week_execution_service: SeasonWeekSimulationExecutionService

    def run_range(self, request: RunSeasonRangeRequest) -> RunSeasonRangeResult:
        warnings = [RANGE_NO_ROLLBACK_WARNING, NO_ROLLBACK_WARNING]
        errors: list[str] = []
        preflight = self.preflight_service.preflight_range(SeasonRangePreflightRequest(
            season=request.season,
            start_week=request.start_week,
            end_week=request.end_week,
            include_empty_weeks=True,
            include_completed_weeks=True,
            event_id_filter=request.event_id_filter,
            apply_points=request.apply_points,
            publish_snapshot=request.publish_snapshot,
            stop_on_blocked=request.stop_on_blocked,
        ))
        warnings.extend(preflight.validation_warnings)
        errors.extend(preflight.validation_errors)
        if request.publish_snapshot and not request.apply_points:
            errors.append("publish_snapshot=true requires apply_points=true for range execution.")
        summary = SeasonRangeRunSummary(
            season=request.season,
            start_week=request.start_week,
            end_week=request.end_week,
            attempted_week_count=len(preflight.weeks),
            range_safe_to_run_preflight=preflight.summary.range_safe_to_run,
        )

        unsafe_non_skip_weeks = [week for week in preflight.weeks if week.range_action not in {"skip_empty", "skip_complete"}]
        if (errors or (not preflight.summary.range_safe_to_run and unsafe_non_skip_weeks)) and not request.allow_unsafe_run:
            summary.run_started = False
            summary.run_completed = False
            summary.stopped_early = False
            summary.stop_reason = "range_preflight_not_safe"
            summary.first_blocked_week = preflight.summary.first_blocked_week
            summary.next_safe_action = self._next_safe_action(summary=summary)
            return self._finish(preflight=preflight, weeks=[], summary=summary, warnings=warnings, errors=errors)

        weeks: list[SeasonRangeRunWeekResult] = []
        executed_count = 0
        run_order = 0
        for planned in sorted(preflight.weeks, key=lambda week: week.season_week):
            if request.stop_after_week is not None and planned.season_week > request.stop_after_week:
                summary.stopped_early = True
                summary.stop_reason = "stop_after_week_reached"
                break
            if planned.range_action == "skip_empty":
                weeks.append(self._skipped(planned, skip_reason="empty_week"))
                continue
            if planned.range_action == "skip_complete":
                weeks.append(self._skipped(planned, skip_reason="completed_week"))
                continue
            if planned.range_action == "blocked" and request.stop_on_blocked and not request.allow_blocked:
                weeks.append(self._blocked(planned, reason="range_action_blocked"))
                summary.stopped_early = True
                summary.stop_reason = "blocked_week"
                break
            if planned.range_action == "recover_week" and not request.allow_unsafe_run:
                weeks.append(self._blocked(planned, reason="recover_week_requires_manual_inspection"))
                summary.stopped_early = True
                summary.stop_reason = "recover_week"
                break
            if planned.range_action not in {"run_week", "apply_points", "publish_snapshot", "blocked", "recover_week"}:
                weeks.append(self._skipped(planned, skip_reason=f"unsupported_range_action:{planned.range_action}"))
                continue
            if request.max_weeks_to_run is not None and executed_count >= request.max_weeks_to_run:
                summary.stopped_early = True
                summary.stop_reason = "max_weeks_to_run_reached"
                break

            run_order += 1
            executed_count += 1
            summary.run_started = True
            week_result = self.week_execution_service.run_week(RunSeasonWeekRequest(
                season=request.season,
                season_week=planned.season_week,
                seed=self._week_seed(request.seed, request.season, request.start_week, request.end_week, planned.season_week),
                apply_points=request.apply_points,
                publish_snapshot=request.publish_snapshot,
                overwrite_existing=request.overwrite_existing,
                include_not_entered=request.include_not_entered,
                max_alternates=request.max_alternates,
                simulate_draw_type=request.simulate_draw_type,
                max_steps_per_event=request.max_steps_per_event,
                allow_blocked=request.allow_blocked,
                allow_incomplete_results=request.allow_incomplete_results,
                event_id_filter=request.event_id_filter,
                include_completed_events=True,
                allow_unsafe_run=request.allow_unsafe_run,
            ))
            warnings.extend(week_result.validation_warnings)
            errors.extend(week_result.validation_errors)
            blocked = week_result.summary.blocked_event_count > 0 or (not week_result.summary.run_started and week_result.summary.stop_reason == "preflight_not_safe")
            failed = bool(week_result.validation_errors) or week_result.summary.failed_event_count > 0
            succeeded = week_result.summary.run_started and week_result.summary.run_completed and not blocked and not failed
            weeks.append(SeasonRangeRunWeekResult(
                season_week=planned.season_week,
                calendar_year=planned.calendar_year,
                year_week=planned.year_week,
                status_before=planned.status,
                range_action=planned.range_action,
                run_order=run_order,
                skipped=False,
                week_run_result=week_result,
                succeeded=succeeded,
                blocked=blocked,
                failed=failed,
                warnings=self._dedupe(planned.warnings + week_result.validation_warnings),
                errors=self._dedupe(planned.errors + week_result.validation_errors),
            ))
            if failed:
                summary.stopped_early = True
                summary.stop_reason = week_result.summary.stop_reason or "week_failed"
                break
            if week_result.summary.stopped_early:
                summary.stopped_early = True
                summary.stop_reason = week_result.summary.stop_reason or "week_stopped_early"
                break
            if blocked and request.stop_on_blocked:
                summary.stopped_early = True
                summary.stop_reason = week_result.summary.stop_reason or "week_blocked"
                break

        self._populate_counts(summary, weeks)
        summary.run_completed = summary.run_started and not summary.stopped_early and summary.blocked_week_count == 0 and summary.failed_week_count == 0
        if not summary.run_started and summary.stop_reason is None:
            summary.run_completed = True
            summary.stop_reason = None
        summary.next_safe_action = self._next_safe_action(summary=summary)
        return self._finish(preflight=preflight, weeks=weeks, summary=summary, warnings=warnings, errors=errors)

    @staticmethod
    def _skipped(planned: SeasonRangePreflightWeek, *, skip_reason: str) -> SeasonRangeRunWeekResult:
        return SeasonRangeRunWeekResult(
            season_week=planned.season_week,
            calendar_year=planned.calendar_year,
            year_week=planned.year_week,
            status_before=planned.status,
            range_action=planned.range_action,
            skipped=True,
            skip_reason=skip_reason,
            succeeded=True,
            blocked=False,
            failed=False,
            warnings=planned.warnings,
            errors=planned.errors,
        )

    @staticmethod
    def _blocked(planned: SeasonRangePreflightWeek, *, reason: str) -> SeasonRangeRunWeekResult:
        return SeasonRangeRunWeekResult(
            season_week=planned.season_week,
            calendar_year=planned.calendar_year,
            year_week=planned.year_week,
            status_before=planned.status,
            range_action=planned.range_action,
            skipped=True,
            skip_reason=reason,
            succeeded=False,
            blocked=True,
            failed=False,
            warnings=planned.warnings,
            errors=planned.errors,
        )

    @staticmethod
    def _populate_counts(summary: SeasonRangeRunSummary, weeks: list[SeasonRangeRunWeekResult]) -> None:
        summary.skipped_empty_week_count = sum(1 for week in weeks if week.skip_reason == "empty_week")
        summary.skipped_complete_week_count = sum(1 for week in weeks if week.skip_reason == "completed_week")
        summary.executed_week_count = sum(1 for week in weeks if week.week_run_result is not None)
        summary.succeeded_week_count = sum(1 for week in weeks if week.week_run_result is not None and week.succeeded)
        summary.blocked_week_count = sum(1 for week in weeks if week.blocked)
        summary.failed_week_count = sum(1 for week in weeks if week.failed)
        summary.point_application_week_count = sum(1 for week in weeks if week.week_run_result is not None and week.week_run_result.summary.points_applied_event_count > 0)
        summary.snapshot_publication_week_count = sum(1 for week in weeks if week.week_run_result is not None and week.week_run_result.summary.snapshot_published)
        blocked = [week.season_week for week in weeks if week.blocked]
        failed = [week.season_week for week in weeks if week.failed]
        summary.first_blocked_week = blocked[0] if blocked else summary.first_blocked_week
        summary.first_failed_week = failed[0] if failed else summary.first_failed_week

    @staticmethod
    def _next_safe_action(*, summary: SeasonRangeRunSummary) -> SeasonRangeRunNextSafeAction:
        if not summary.range_safe_to_run_preflight and not summary.run_started:
            return "inspect_range_preflight"
        if summary.blocked_week_count:
            return "resolve_blockers"
        if summary.failed_week_count or summary.stopped_early:
            return "inspect_recovery"
        if summary.run_completed:
            return "review_completed_range"
        if summary.run_started:
            return "rerun_range"
        return "inspect_season_readiness"

    @staticmethod
    def _week_seed(base_seed: int, season: str, start_week: int, end_week: int, season_week: int) -> int:
        digest = hashlib.sha256(f"{base_seed}:{season}:{start_week}:{end_week}:{season_week}:range_week".encode("utf-8")).hexdigest()
        return int(digest[:12], 16) % 2_147_483_647

    def _finish(self, *, preflight: SeasonRangePreflightResult, weeks: list[SeasonRangeRunWeekResult], summary: SeasonRangeRunSummary, warnings: list[str], errors: list[str]) -> RunSeasonRangeResult:
        result = RunSeasonRangeResult(
            preflight=preflight,
            weeks=weeks,
            summary=summary,
            metadata=SeasonRangeRunMetadata(season=summary.season, range_preflight_fingerprint=preflight.metadata.generated_fingerprint, final_fingerprint="pending"),
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
