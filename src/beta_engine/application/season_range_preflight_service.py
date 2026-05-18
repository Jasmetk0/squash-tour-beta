"""Read-only season-week range preflight built from season readiness rows."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_readiness_service import SeasonReadinessRequest, SeasonReadinessService, SeasonWeekReadinessRow
from beta_engine.application.season_week_recovery_service import SeasonWeekRecoveryRerunFlags
from beta_engine.domain.calendar import TOTAL_SEASON_WEEKS

SEASON_RANGE_PREFLIGHT_SOURCE = "season_readiness_range_preflight"
SEASON_RANGE_PREFLIGHT_READ_ONLY_WARNING = "Range preflight is read-only. It plans a future range run but does not run weeks, apply points, or publish snapshots."

SeasonRangeAction = Literal[
    "skip_empty",
    "skip_complete",
    "run_week",
    "apply_points",
    "publish_snapshot",
    "blocked",
    "recover_week",
]

SeasonRangeNextSafeAction = Literal[
    "run_range",
    "resolve_blockers",
    "apply_points",
    "publish_snapshots",
    "recover_week",
    "nothing_to_run",
    "adjust_range",
    "build_calendar",
]


class SeasonRangePreflightRequest(BaseModel):
    season: str = "2000/2001"
    start_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    end_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    include_empty_weeks: bool = True
    include_completed_weeks: bool = True
    event_id_filter: list[str] = Field(default_factory=list)
    apply_points: bool = True
    publish_snapshot: bool = True
    stop_on_blocked: bool = True


class SeasonRangePreflightWeek(BaseModel):
    season: str
    season_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    calendar_year: int
    year_week: int
    status: str
    event_count: int
    has_events: bool
    week_complete: bool
    week_blocked: bool
    week_partial: bool
    ready_for_point_application: bool
    ready_for_snapshot_publication: bool
    snapshot_exists: bool
    next_safe_action: str
    recommended_week_rerun_flags: SeasonWeekRecoveryRerunFlags = Field(default_factory=SeasonWeekRecoveryRerunFlags)
    range_action: SeasonRangeAction
    would_mutate_if_executed: bool
    would_apply_points_if_executed: bool
    would_publish_snapshot_if_executed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SeasonRangePreflightSummary(BaseModel):
    season: str
    start_week: int
    end_week: int
    total_weeks_in_range: int
    empty_weeks: int
    completed_weeks: int
    runnable_weeks: int
    point_application_weeks: int
    snapshot_publication_weeks: int
    blocked_weeks: int
    recoverable_weeks: int
    skipped_weeks: int
    first_unsafe_week: int | None = None
    first_blocked_week: int | None = None
    first_runnable_week: int | None = None
    range_safe_to_run: bool
    would_apply_points: bool
    would_publish_snapshots: bool
    next_safe_action: SeasonRangeNextSafeAction
    recommended_run_flags: SeasonWeekRecoveryRerunFlags = Field(default_factory=SeasonWeekRecoveryRerunFlags)
    mutation_warning: str = SEASON_RANGE_PREFLIGHT_READ_ONLY_WARNING


class SeasonRangePreflightMetadata(BaseModel):
    season: str
    source: Literal["season_readiness_range_preflight"] = SEASON_RANGE_PREFLIGHT_SOURCE
    season_readiness_fingerprint: str | None = None
    generated_fingerprint: str
    read_only: bool = True


class SeasonRangePreflightResult(BaseModel):
    season: str
    start_week: int
    end_week: int
    weeks: list[SeasonRangePreflightWeek]
    summary: SeasonRangePreflightSummary
    metadata: SeasonRangePreflightMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonRangePreflightService:
    """Plan a future season-week range command without mutating state."""

    readiness_service: SeasonReadinessService

    def preflight_range(self, request: SeasonRangePreflightRequest) -> SeasonRangePreflightResult:
        validation_warnings = [SEASON_RANGE_PREFLIGHT_READ_ONLY_WARNING]
        validation_errors: list[str] = []
        if request.start_week > request.end_week:
            validation_errors.append("start_week must be less than or equal to end_week.")

        readiness = self.readiness_service.inspect_season(
            SeasonReadinessRequest(
                season=request.season,
                include_empty_weeks=True,
                include_completed_weeks=True,
                event_id_filter=request.event_id_filter,
            )
        )
        validation_warnings.extend(readiness.validation_warnings)
        validation_errors.extend(readiness.validation_errors)

        selected_rows = [row for row in readiness.weeks if request.start_week <= row.season_week <= request.end_week]
        all_week_plans = [self._week_plan(row, request=request) for row in selected_rows]
        visible_week_plans = [
            week for week in all_week_plans
            if (request.include_empty_weeks or week.range_action != "skip_empty")
            and (request.include_completed_weeks or week.range_action != "skip_complete")
        ]

        summary = self._summary(
            request=request,
            readiness_next_action=readiness.summary.next_safe_action,
            weeks=all_week_plans,
            validation_errors=validation_errors,
        )
        result = SeasonRangePreflightResult(
            season=request.season,
            start_week=request.start_week,
            end_week=request.end_week,
            weeks=visible_week_plans,
            summary=summary,
            metadata=SeasonRangePreflightMetadata(
                season=request.season,
                season_readiness_fingerprint=readiness.metadata.generated_fingerprint,
                generated_fingerprint="pending",
            ),
            validation_warnings=self._dedupe(validation_warnings),
            validation_errors=self._dedupe(validation_errors),
        )
        result.metadata.generated_fingerprint = self._fingerprint(result.model_dump(mode="json", exclude={"metadata": {"generated_fingerprint"}}))
        return result

    def _week_plan(self, row: SeasonWeekReadinessRow, *, request: SeasonRangePreflightRequest) -> SeasonRangePreflightWeek:
        warnings = list(row.warnings)
        errors = list(row.errors)
        action: SeasonRangeAction
        if row.status == "empty":
            action = "skip_empty"
        elif row.status == "complete":
            action = "skip_complete"
        elif row.status == "blocked":
            action = "blocked"
        elif row.status == "ready_for_point_application":
            if request.apply_points:
                action = "apply_points"
            else:
                action = "recover_week"
                warnings.append("apply_points=false would not advance this week because it is ready for point application.")
        elif row.status == "ready_for_snapshot_publication":
            if request.publish_snapshot:
                action = "publish_snapshot"
            else:
                action = "recover_week"
                warnings.append("publish_snapshot=false would not complete this week because it is ready for snapshot publication.")
        elif row.status in {"planned", "partial"}:
            action = "run_week"
        else:
            action = "recover_week"

        would_apply_points = action == "apply_points" or (action == "run_week" and request.apply_points)
        would_publish_snapshot = action == "publish_snapshot" or (action == "run_week" and request.publish_snapshot)
        return SeasonRangePreflightWeek(
            season=row.season,
            season_week=row.season_week,
            calendar_year=row.calendar_year,
            year_week=row.year_week,
            status=row.status,
            event_count=row.event_count,
            has_events=row.has_events,
            week_complete=row.week_complete,
            week_blocked=row.week_blocked,
            week_partial=row.week_partial,
            ready_for_point_application=row.ready_for_point_application,
            ready_for_snapshot_publication=row.ready_for_snapshot_publication,
            snapshot_exists=row.snapshot_exists,
            next_safe_action=row.next_safe_action,
            recommended_week_rerun_flags=row.recommended_week_rerun_flags,
            range_action=action,
            would_mutate_if_executed=action in {"run_week", "apply_points", "publish_snapshot"},
            would_apply_points_if_executed=would_apply_points,
            would_publish_snapshot_if_executed=would_publish_snapshot,
            warnings=self._dedupe(warnings),
            errors=self._dedupe(errors),
        )

    def _summary(self, *, request: SeasonRangePreflightRequest, readiness_next_action: str, weeks: list[SeasonRangePreflightWeek], validation_errors: list[str]) -> SeasonRangePreflightSummary:
        actionable = [week for week in weeks if week.range_action in {"run_week", "apply_points", "publish_snapshot"}]
        blocked = [week for week in weeks if week.range_action == "blocked"]
        recoverable = [week for week in weeks if week.range_action == "recover_week"]
        empty_weeks = sum(1 for week in weeks if week.range_action == "skip_empty")
        completed_weeks = sum(1 for week in weeks if week.range_action == "skip_complete")
        point_weeks = sum(1 for week in weeks if week.range_action == "apply_points")
        snapshot_weeks = sum(1 for week in weeks if week.range_action == "publish_snapshot")
        first_blocked_week = blocked[0].season_week if blocked else None
        first_runnable_week = actionable[0].season_week if actionable else None
        first_recoverable_week = recoverable[0].season_week if recoverable else None
        has_event_weeks = any(week.has_events for week in weeks)
        blocked_stops_range = request.stop_on_blocked and first_blocked_week is not None
        range_safe_to_run = not validation_errors and bool(actionable) and not blocked_stops_range and first_recoverable_week is None

        recommended_flags = SeasonWeekRecoveryRerunFlags(
            apply_points=request.apply_points,
            publish_snapshot=request.publish_snapshot,
            overwrite_existing=False,
            allow_blocked=False,
            allow_incomplete_results=False,
        )
        if any(week.ready_for_point_application for week in weeks):
            recommended_flags.apply_points = True
        if any(week.ready_for_snapshot_publication for week in weeks):
            recommended_flags.apply_points = True
            recommended_flags.publish_snapshot = True

        first_unsafe_week = first_blocked_week if blocked_stops_range else first_recoverable_week
        if validation_errors and request.start_week > request.end_week:
            next_action: SeasonRangeNextSafeAction = "adjust_range"
        elif readiness_next_action == "build_calendar":
            next_action = "build_calendar"
            range_safe_to_run = False
        elif not has_event_weeks:
            next_action = "nothing_to_run"
            range_safe_to_run = False
        elif blocked_stops_range:
            next_action = "resolve_blockers"
            first_unsafe_week = first_blocked_week
        elif first_recoverable_week is not None:
            next_action = "recover_week"
        elif point_weeks > 0 and not any(week.range_action == "run_week" for week in weeks):
            next_action = "apply_points"
        elif snapshot_weeks > 0 and not any(week.range_action in {"run_week", "apply_points"} for week in weeks):
            next_action = "publish_snapshots"
        elif actionable:
            next_action = "run_range"
        else:
            next_action = "nothing_to_run"
            range_safe_to_run = False

        return SeasonRangePreflightSummary(
            season=request.season,
            start_week=request.start_week,
            end_week=request.end_week,
            total_weeks_in_range=max(0, request.end_week - request.start_week + 1),
            empty_weeks=empty_weeks,
            completed_weeks=completed_weeks,
            runnable_weeks=sum(1 for week in weeks if week.range_action == "run_week"),
            point_application_weeks=point_weeks,
            snapshot_publication_weeks=snapshot_weeks,
            blocked_weeks=len(blocked),
            recoverable_weeks=len(recoverable),
            skipped_weeks=empty_weeks + completed_weeks,
            first_unsafe_week=first_unsafe_week,
            first_blocked_week=first_blocked_week,
            first_runnable_week=first_runnable_week,
            range_safe_to_run=range_safe_to_run,
            would_apply_points=any(week.would_apply_points_if_executed for week in actionable),
            would_publish_snapshots=any(week.would_publish_snapshot_if_executed for week in actionable),
            next_safe_action=next_action,
            recommended_run_flags=recommended_flags,
        )

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
