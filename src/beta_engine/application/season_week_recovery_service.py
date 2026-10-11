"""Read-only week recovery diagnostics for partial or completed week runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_event_lifecycle_service import EventLifecycleStatus, SeasonEventLifecycleService
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService
from beta_engine.application.season_week_simulation_preflight_service import SimulateSeasonWeekPreflightRequest, SeasonWeekSimulationPreflightService
from beta_engine.domain.calendar import TOTAL_SEASON_WEEKS

RECOVERY_SOURCE = "persisted_artifact_recovery_read_model"
RECOVERY_READ_ONLY_WARNING = "Recovery diagnostics are read-only. No rollback, deletion, reversal, or overwrite is performed."

RecoveryEventAction = Literal[
    "generate_entries",
    "generate_draw",
    "generate_matches",
    "simulate_matches",
    "extract_results",
    "generate_point_awards",
    "apply_point_awards",
    "publish_week_snapshot",
    "rerun_event_safe",
    "resolve_blocker",
    "complete",
]

RecoveryNextSafeAction = Literal[
    "resolve_blockers",
    "rerun_week_without_overwrite",
    "rerun_week_with_apply_points",
    "publish_week_snapshot",
    "review_completed_week",
    "build_calendar",
    "no_events",
]


class SeasonWeekRecoveryRequest(BaseModel):
    season: str = "2000/2001"
    season_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)
    event_id_filter: list[str] = Field(default_factory=list)
    include_completed_events: bool = True


class SeasonWeekRecoveryRerunFlags(BaseModel):
    overwrite_existing: bool = False
    apply_points: bool = False
    publish_snapshot: bool = False
    allow_blocked: bool = False
    allow_incomplete_results: bool = False


class SeasonWeekRecoveryEvent(BaseModel):
    event_id: str
    event_name: str
    season: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    category: str
    tour_level: str | None = None
    host_country: str
    current_stage: str
    next_recommended_action: str
    is_blocked: bool
    block_reasons: list[str] = Field(default_factory=list)
    entries_exists: bool = False
    draw_exists: bool = False
    matches_exists: bool = False
    results_exists: bool = False
    point_awards_exists: bool = False
    points_applied: bool = False
    ranking_snapshot_exists: bool = False
    safe_to_rerun_event: bool = True
    duplicate_points_risk: bool = False
    overwrite_risk: bool = False
    needs_manual_attention: bool = False
    recommended_event_action: RecoveryEventAction
    recommended_rerun_flags: SeasonWeekRecoveryRerunFlags = Field(default_factory=SeasonWeekRecoveryRerunFlags)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SeasonWeekRecoverySummary(BaseModel):
    season: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    event_count: int = 0
    completed_event_count: int = 0
    partial_event_count: int = 0
    blocked_event_count: int = 0
    points_generated_count: int = 0
    points_applied_count: int = 0
    snapshot_exists: bool = False
    week_complete: bool = False
    week_partial: bool = False
    week_blocked: bool = False
    ready_for_point_application: bool = False
    ready_for_snapshot_publication: bool = False
    duplicate_points_risk_count: int = 0
    overwrite_risk_count: int = 0
    manual_attention_count: int = 0
    next_safe_action: RecoveryNextSafeAction | None = None
    recommended_week_rerun_flags: SeasonWeekRecoveryRerunFlags = Field(default_factory=SeasonWeekRecoveryRerunFlags)
    rollback_available: bool = False


class SeasonWeekRecoveryMetadata(BaseModel):
    season: str
    season_week: int
    source: Literal["persisted_artifact_recovery_read_model"] = RECOVERY_SOURCE
    generated_fingerprint: str
    read_only: bool = True


class SeasonWeekRecoveryResult(BaseModel):
    season: str
    season_week: int
    events: list[SeasonWeekRecoveryEvent] = Field(default_factory=list)
    summary: SeasonWeekRecoverySummary
    metadata: SeasonWeekRecoveryMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonWeekRecoveryService:
    """Build conservative persisted-artifact recovery diagnostics without mutation."""

    preflight_service: SeasonWeekSimulationPreflightService
    lifecycle_service: SeasonEventLifecycleService
    ranking_snapshot_service: SeasonRankingSnapshotService

    def recover_week(self, request: SeasonWeekRecoveryRequest) -> SeasonWeekRecoveryResult:
        warnings = [RECOVERY_READ_ONLY_WARNING]
        errors: list[str] = []
        preflight = self.preflight_service.preflight_week(
            season=request.season,
            season_week=request.season_week,
            request=SimulateSeasonWeekPreflightRequest(
                event_id_filter=request.event_id_filter,
                include_completed_events=request.include_completed_events,
            ),
        )
        warnings.extend(preflight.validation_warnings)
        errors.extend(preflight.validation_errors)

        snapshot_exists = self.ranking_snapshot_service.get_snapshot(season=request.season, season_week=request.season_week).snapshot_exists
        events: list[SeasonWeekRecoveryEvent] = []
        for planned in preflight.events:
            lifecycle = self.lifecycle_service.get_event_lifecycle(event_id=planned.event_id)
            if lifecycle.event is None:
                errors.extend(lifecycle.validation_errors)
                continue
            events.append(self._event(lifecycle.event, snapshot_exists=snapshot_exists))

        summary = self._summary(
            season=request.season,
            season_week=request.season_week,
            calendar_year=preflight.calendar_year,
            year_week=preflight.year_week,
            events=events,
            snapshot_exists=snapshot_exists,
            has_calendar=not any("No persisted season calendar exists" in error for error in errors),
            selected_count=preflight.summary.event_count,
            errors=errors,
        )
        result = SeasonWeekRecoveryResult(
            season=request.season,
            season_week=request.season_week,
            events=events,
            summary=summary,
            metadata=SeasonWeekRecoveryMetadata(season=request.season, season_week=request.season_week, generated_fingerprint="pending"),
            validation_warnings=self._dedupe(warnings),
            validation_errors=self._dedupe(errors),
        )
        result.metadata.generated_fingerprint = self._fingerprint(result.model_dump(mode="json", exclude={"metadata": {"generated_fingerprint"}}))
        return result

    def _event(self, lifecycle: EventLifecycleStatus, *, snapshot_exists: bool) -> SeasonWeekRecoveryEvent:
        warnings = list(lifecycle.validation_warnings)
        errors = list(lifecycle.validation_errors)
        flags = SeasonWeekRecoveryRerunFlags()
        duplicate_points_risk = lifecycle.points_applied
        overwrite_risk = self._has_artifacts(lifecycle)
        safe_to_rerun = not lifecycle.is_blocked
        needs_attention = lifecycle.is_blocked

        action = self._recommended_event_action(lifecycle)
        if action == "apply_point_awards":
            flags.apply_points = True
        elif action == "publish_week_snapshot":
            flags.apply_points = True
            flags.publish_snapshot = True
        elif action == "resolve_blocker":
            flags.allow_blocked = False
        if lifecycle.points_applied:
            warnings.append("Points are already applied; reruns should rely on duplicate-point protection and avoid forced reapplication.")
        if overwrite_risk:
            warnings.append("Existing persisted artifacts are present; recovery recommends overwrite_existing=false.")

        return SeasonWeekRecoveryEvent(
            event_id=lifecycle.event_id,
            event_name=lifecycle.event_name,
            season=lifecycle.season,
            season_week=lifecycle.season_week,
            calendar_year=lifecycle.calendar_year,
            year_week=lifecycle.year_week,
            category=lifecycle.category,
            tour_level=lifecycle.tour_level,
            host_country=lifecycle.host_country,
            current_stage=lifecycle.current_stage,
            next_recommended_action=lifecycle.next_recommended_action,
            is_blocked=lifecycle.is_blocked,
            block_reasons=list(lifecycle.block_reasons),
            entries_exists=lifecycle.entries.exists,
            draw_exists=lifecycle.draw.exists,
            matches_exists=lifecycle.matches.exists,
            results_exists=lifecycle.results.exists,
            point_awards_exists=lifecycle.point_awards.exists,
            points_applied=lifecycle.points_applied,
            ranking_snapshot_exists=snapshot_exists,
            safe_to_rerun_event=safe_to_rerun,
            duplicate_points_risk=duplicate_points_risk,
            overwrite_risk=overwrite_risk,
            needs_manual_attention=needs_attention,
            recommended_event_action=action,
            recommended_rerun_flags=flags,
            warnings=self._dedupe(warnings),
            errors=self._dedupe(errors),
        )

    @staticmethod
    def _recommended_event_action(lifecycle: EventLifecycleStatus) -> RecoveryEventAction:
        if lifecycle.is_blocked:
            return "resolve_blocker"
        if lifecycle.current_stage == "ranking_snapshot_published":
            return "complete"
        if lifecycle.points_applied and not lifecycle.ranking_snapshot.exists:
            return "publish_week_snapshot"
        if lifecycle.point_awards.exists and not lifecycle.points_applied:
            return "apply_point_awards"
        if lifecycle.results.exists and not lifecycle.point_awards.exists:
            return "generate_point_awards"
        if lifecycle.matches.exists:
            progression = lifecycle.progression_status or {}
            if progression.get("event_status") != "completed":
                return "simulate_matches"
            if not lifecycle.results.exists:
                return "extract_results"
        if lifecycle.draw.exists and not lifecycle.matches.exists:
            return "generate_matches"
        if lifecycle.entries.exists and not lifecycle.draw.exists:
            return "generate_draw"
        if not lifecycle.entries.exists:
            return "generate_entries"
        return "rerun_event_safe"

    def _summary(self, *, season: str, season_week: int, calendar_year: int | None, year_week: int | None, events: list[SeasonWeekRecoveryEvent], snapshot_exists: bool, has_calendar: bool, selected_count: int, errors: list[str]) -> SeasonWeekRecoverySummary:
        event_count = len(events)
        blocked = [event for event in events if event.is_blocked]
        completed_count = sum(1 for event in events if event.points_applied)
        partial_count = sum(1 for event in events if self._event_has_artifacts(event) and not event.points_applied)
        points_generated_count = sum(1 for event in events if event.point_awards_exists)
        points_applied_count = sum(1 for event in events if event.points_applied)
        week_complete = event_count > 0 and all(event.points_applied for event in events) and snapshot_exists
        week_blocked = bool(blocked)
        ready_for_point_application = event_count > 0 and not week_blocked and all(event.point_awards_exists for event in events) and any(not event.points_applied for event in events)
        ready_for_snapshot_publication = event_count > 0 and not week_blocked and all(event.points_applied for event in events) and not snapshot_exists
        week_partial = not week_complete and any(self._event_has_artifacts(event) for event in events)
        duplicate_count = sum(1 for event in events if event.duplicate_points_risk)
        overwrite_count = sum(1 for event in events if event.overwrite_risk)
        manual_count = sum(1 for event in events if event.needs_manual_attention)

        flags = SeasonWeekRecoveryRerunFlags()
        next_action: RecoveryNextSafeAction | None
        if not has_calendar or errors:
            next_action = "build_calendar" if not has_calendar else "resolve_blockers"
        elif selected_count == 0 or event_count == 0:
            next_action = "no_events"
        elif week_blocked:
            next_action = "resolve_blockers"
        elif ready_for_point_application:
            flags.apply_points = True
            next_action = "rerun_week_with_apply_points"
        elif ready_for_snapshot_publication:
            flags.apply_points = True
            flags.publish_snapshot = True
            next_action = "publish_week_snapshot"
        elif week_complete:
            next_action = "review_completed_week"
        else:
            next_action = "rerun_week_without_overwrite"

        return SeasonWeekRecoverySummary(
            season=season,
            season_week=season_week,
            calendar_year=calendar_year,
            year_week=year_week,
            event_count=event_count,
            completed_event_count=completed_count,
            partial_event_count=partial_count,
            blocked_event_count=len(blocked),
            points_generated_count=points_generated_count,
            points_applied_count=points_applied_count,
            snapshot_exists=snapshot_exists,
            week_complete=week_complete,
            week_partial=week_partial,
            week_blocked=week_blocked,
            ready_for_point_application=ready_for_point_application,
            ready_for_snapshot_publication=ready_for_snapshot_publication,
            duplicate_points_risk_count=duplicate_count,
            overwrite_risk_count=overwrite_count,
            manual_attention_count=manual_count,
            next_safe_action=next_action,
            recommended_week_rerun_flags=flags,
            rollback_available=False,
        )

    @staticmethod
    def _has_artifacts(lifecycle: EventLifecycleStatus) -> bool:
        return any([
            lifecycle.entries.exists,
            lifecycle.draw.exists,
            lifecycle.matches.exists,
            lifecycle.results.exists,
            lifecycle.point_awards.exists,
            lifecycle.points_applied,
            lifecycle.ranking_snapshot.exists,
        ])

    @staticmethod
    def _event_has_artifacts(event: SeasonWeekRecoveryEvent) -> bool:
        return any([
            event.entries_exists,
            event.draw_exists,
            event.matches_exists,
            event.results_exists,
            event.point_awards_exists,
            event.points_applied,
            event.ranking_snapshot_exists,
        ])

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
