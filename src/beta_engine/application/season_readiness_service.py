"""Read-only season-level readiness aggregation across all FAX season weeks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_week_recovery_service import SeasonWeekRecoveryRequest, SeasonWeekRecoveryRerunFlags, SeasonWeekRecoveryResult, SeasonWeekRecoveryService
from beta_engine.domain.calendar import TOTAL_SEASON_WEEKS, season_week_to_calendar_position

SEASON_READINESS_SOURCE = "season_week_recovery_aggregation"
SEASON_READINESS_READ_ONLY_WARNING = "Season readiness is read-only. It aggregates week recovery reports and does not run events, apply points, or publish snapshots."

SeasonWeekReadinessStatus = Literal[
    "empty",
    "planned",
    "partial",
    "blocked",
    "ready_for_point_application",
    "ready_for_snapshot_publication",
    "complete",
]

SeasonReadinessNextSafeAction = Literal[
    "build_calendar",
    "run_week",
    "recover_week",
    "apply_points",
    "publish_snapshot",
    "resolve_blockers",
    "review_completed_season",
    "no_events",
]


class SeasonReadinessRequest(BaseModel):
    season: str = "2000/2001"
    include_empty_weeks: bool = True
    include_completed_weeks: bool = True
    event_id_filter: list[str] = Field(default_factory=list)


class SeasonWeekReadinessRow(BaseModel):
    season: str
    season_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    calendar_year: int
    year_week: int
    event_count: int
    has_events: bool
    status: SeasonWeekReadinessStatus
    week_complete: bool
    week_partial: bool
    week_blocked: bool
    ready_for_point_application: bool
    ready_for_snapshot_publication: bool
    snapshot_exists: bool
    completed_event_count: int
    partial_event_count: int
    blocked_event_count: int
    points_generated_count: int
    points_applied_count: int
    duplicate_points_risk_count: int
    overwrite_risk_count: int
    manual_attention_count: int
    next_safe_action: SeasonReadinessNextSafeAction
    recommended_week_rerun_flags: SeasonWeekRecoveryRerunFlags = Field(default_factory=SeasonWeekRecoveryRerunFlags)
    representative_event_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    recovery_fingerprint: str | None = None


class SeasonReadinessSummary(BaseModel):
    season: str
    total_weeks: int = TOTAL_SEASON_WEEKS
    weeks_with_events: int = 0
    empty_weeks: int = 0
    complete_weeks: int = 0
    partial_weeks: int = 0
    blocked_weeks: int = 0
    ready_for_point_application_weeks: int = 0
    ready_for_snapshot_publication_weeks: int = 0
    weeks_missing_snapshot_after_points: int = 0
    total_events: int = 0
    total_blocked_events: int = 0
    total_manual_attention_count: int = 0
    first_incomplete_week: int | None = None
    first_blocked_week: int | None = None
    next_week_to_run: int | None = None
    season_ready_to_continue: bool = False
    season_complete: bool = False
    next_safe_action: SeasonReadinessNextSafeAction


class SeasonReadinessMetadata(BaseModel):
    season: str
    source: Literal["season_week_recovery_aggregation"] = SEASON_READINESS_SOURCE
    generated_fingerprint: str
    read_only: bool = True


class SeasonReadinessResult(BaseModel):
    season: str
    weeks: list[SeasonWeekReadinessRow]
    summary: SeasonReadinessSummary
    metadata: SeasonReadinessMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonReadinessService:
    """Aggregate all 61 week recovery reports into a deterministic read-only dashboard."""

    recovery_service: SeasonWeekRecoveryService
    calendar_service: SeasonCalendarService

    def inspect_season(self, request: SeasonReadinessRequest) -> SeasonReadinessResult:
        calendar_result = self.calendar_service.get_calendar(season=request.season)
        calendar_missing = calendar_result.calendar is None
        calendar_errors = [self._issue_text(issue) for issue in calendar_result.validation_errors]
        warnings = self._dedupe([SEASON_READINESS_READ_ONLY_WARNING, *[self._issue_text(issue) for issue in calendar_result.validation_warnings]])
        errors = self._dedupe(calendar_errors)

        all_rows: list[SeasonWeekReadinessRow] = []
        for season_week in range(1, TOTAL_SEASON_WEEKS + 1):
            recovery = self.recovery_service.recover_week(
                SeasonWeekRecoveryRequest(
                    season=request.season,
                    season_week=season_week,
                    event_id_filter=request.event_id_filter,
                    include_completed_events=True,
                )
            )
            warnings.extend(recovery.validation_warnings)
            errors.extend(recovery.validation_errors)
            all_rows.append(self._row(request.season, season_week, recovery, calendar_missing=calendar_missing))

        summary = self._summary(season=request.season, rows=all_rows, calendar_missing=calendar_missing, calendar_errors=calendar_errors)
        filtered_rows = [
            row for row in all_rows
            if (request.include_empty_weeks or row.status != "empty")
            and (request.include_completed_weeks or row.status != "complete")
        ]
        result = SeasonReadinessResult(
            season=request.season,
            weeks=filtered_rows,
            summary=summary,
            metadata=SeasonReadinessMetadata(season=request.season, generated_fingerprint="pending"),
            validation_warnings=self._dedupe(warnings),
            validation_errors=self._dedupe(errors),
        )
        result.metadata.generated_fingerprint = self._fingerprint(result.model_dump(mode="json", exclude={"metadata": {"generated_fingerprint"}}))
        return result

    def _row(self, season: str, season_week: int, recovery: SeasonWeekRecoveryResult, *, calendar_missing: bool) -> SeasonWeekReadinessRow:
        summary = recovery.summary
        position = season_week_to_calendar_position(season=season, season_week=season_week)
        calendar_year = summary.calendar_year or position.calendar_year
        year_week = summary.year_week or position.year_week
        status = self._status(recovery)
        return SeasonWeekReadinessRow(
            season=season,
            season_week=season_week,
            calendar_year=calendar_year,
            year_week=year_week,
            event_count=summary.event_count,
            has_events=summary.event_count > 0,
            status=status,
            week_complete=summary.week_complete,
            week_partial=summary.week_partial,
            week_blocked=summary.week_blocked,
            ready_for_point_application=summary.ready_for_point_application,
            ready_for_snapshot_publication=summary.ready_for_snapshot_publication,
            snapshot_exists=summary.snapshot_exists,
            completed_event_count=summary.completed_event_count,
            partial_event_count=summary.partial_event_count,
            blocked_event_count=summary.blocked_event_count,
            points_generated_count=summary.points_generated_count,
            points_applied_count=summary.points_applied_count,
            duplicate_points_risk_count=summary.duplicate_points_risk_count,
            overwrite_risk_count=summary.overwrite_risk_count,
            manual_attention_count=summary.manual_attention_count,
            next_safe_action=self._row_next_safe_action(status=status, calendar_missing=calendar_missing),
            recommended_week_rerun_flags=summary.recommended_week_rerun_flags,
            representative_event_ids=[event.event_id for event in recovery.events[:5]],
            warnings=self._dedupe([*recovery.validation_warnings, *[warning for event in recovery.events for warning in event.warnings]]),
            errors=self._dedupe([*recovery.validation_errors, *[error for event in recovery.events for error in event.errors]]),
            recovery_fingerprint=recovery.metadata.generated_fingerprint,
        )

    @staticmethod
    def _status(recovery: SeasonWeekRecoveryResult) -> SeasonWeekReadinessStatus:
        summary = recovery.summary
        if summary.week_blocked:
            return "blocked"
        if summary.week_complete:
            return "complete"
        if summary.ready_for_snapshot_publication:
            return "ready_for_snapshot_publication"
        if summary.ready_for_point_application:
            return "ready_for_point_application"
        if summary.week_partial:
            return "partial"
        if summary.event_count > 0:
            return "planned"
        return "empty"

    @staticmethod
    def _row_next_safe_action(*, status: SeasonWeekReadinessStatus, calendar_missing: bool) -> SeasonReadinessNextSafeAction:
        if calendar_missing:
            return "build_calendar"
        if status == "blocked":
            return "resolve_blockers"
        if status == "ready_for_point_application":
            return "apply_points"
        if status == "ready_for_snapshot_publication":
            return "publish_snapshot"
        if status in {"planned", "partial"}:
            return "run_week"
        if status == "complete":
            return "review_completed_season"
        return "no_events"

    def _summary(self, *, season: str, rows: list[SeasonWeekReadinessRow], calendar_missing: bool, calendar_errors: list[str]) -> SeasonReadinessSummary:
        weeks_with_events = sum(1 for row in rows if row.has_events)
        first_incomplete_week = next((row.season_week for row in rows if row.has_events and row.status != "complete"), None)
        first_blocked_week = next((row.season_week for row in rows if row.status == "blocked"), None)
        next_week_to_run = next((row.season_week for row in rows if row.has_events and row.status in {"planned", "partial", "ready_for_point_application", "ready_for_snapshot_publication"} and not row.week_blocked), None)
        season_ready_to_continue = next_week_to_run is not None and not (first_blocked_week is not None and first_blocked_week < next_week_to_run)
        season_complete = weeks_with_events > 0 and all(row.status == "complete" for row in rows if row.has_events)
        next_status = next((row.status for row in rows if row.season_week == next_week_to_run), None)
        if calendar_missing or calendar_errors:
            next_action: SeasonReadinessNextSafeAction = "build_calendar"
        elif first_blocked_week is not None:
            next_action = "resolve_blockers"
        elif next_status == "ready_for_point_application":
            next_action = "apply_points"
        elif next_status == "ready_for_snapshot_publication":
            next_action = "publish_snapshot"
        elif next_week_to_run is not None:
            next_action = "run_week"
        elif season_complete:
            next_action = "review_completed_season"
        elif weeks_with_events == 0:
            next_action = "no_events"
        else:
            next_action = "recover_week"

        return SeasonReadinessSummary(
            season=season,
            weeks_with_events=weeks_with_events,
            empty_weeks=sum(1 for row in rows if row.status == "empty"),
            complete_weeks=sum(1 for row in rows if row.status == "complete"),
            partial_weeks=sum(1 for row in rows if row.status == "partial"),
            blocked_weeks=sum(1 for row in rows if row.status == "blocked"),
            ready_for_point_application_weeks=sum(1 for row in rows if row.status == "ready_for_point_application"),
            ready_for_snapshot_publication_weeks=sum(1 for row in rows if row.status == "ready_for_snapshot_publication"),
            weeks_missing_snapshot_after_points=sum(1 for row in rows if row.points_applied_count > 0 and not row.snapshot_exists),
            total_events=sum(row.event_count for row in rows),
            total_blocked_events=sum(row.blocked_event_count for row in rows),
            total_manual_attention_count=sum(row.manual_attention_count for row in rows),
            first_incomplete_week=first_incomplete_week,
            first_blocked_week=first_blocked_week,
            next_week_to_run=next_week_to_run,
            season_ready_to_continue=season_ready_to_continue,
            season_complete=season_complete,
            next_safe_action=next_action,
        )

    @staticmethod
    def _issue_text(issue: Any) -> str:
        code = getattr(issue, "code", None)
        message = getattr(issue, "message", None)
        if code and message:
            return f"{code}: {message}"
        return str(issue)

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
