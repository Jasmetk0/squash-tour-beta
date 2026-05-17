"""Read-only week-level orchestration preflight built from one-event dry-run reports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_event_lifecycle_service import EventLifecycleStage, SeasonEventLifecycleService
from beta_engine.application.season_event_simulation_service import SimulateDrawType, SimulateOneEventReport, SimulateOneEventRequest, SeasonEventSimulationService
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService
from beta_engine.domain.calendar import DEFAULT_SEASON_START_YEAR_WEEK, TOTAL_SEASON_WEEKS, season_week_to_calendar_position
from beta_engine.domain.tournaments.models import SeasonCalendar, SeasonCalendarEvent

PREFLIGHT_READ_ONLY_WARNING = "Week preflight is read-only; no entries, draws, matches, points, or ranking snapshots are mutated."


class SimulateSeasonWeekPreflightRequest(BaseModel):
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


class SeasonWeekEventPreflight(BaseModel):
    event_id: str
    event_name: str
    season: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    category: str
    tour_level: str | None = None
    host_country: str
    lifecycle_stage_before: str | None = None
    next_recommended_action_before: str | None = None
    one_event_report: SimulateOneEventReport
    blocked: bool
    can_continue: bool
    stop_reason: str | None = None
    planned_step_count: int = 0
    planned_mutates_active_players: bool = False
    planned_mutates_ranking_snapshot: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SeasonWeekPreflightSummary(BaseModel):
    season: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    event_count: int = 0
    planned_event_count: int = 0
    completed_event_count: int = 0
    blocked_event_count: int = 0
    can_run_week: bool = False
    would_apply_points: bool = False
    would_publish_snapshot: bool = False
    snapshot_already_exists: bool = False
    week_has_multiple_events: bool = False
    total_planned_steps: int = 0
    total_planned_player_mutations: int = 0
    total_planned_snapshot_mutations: int = 0
    first_blocked_event_id: str | None = None
    stop_reason: str | None = None
    next_safe_action: str | None = None


class SeasonWeekPreflightMetadata(BaseModel):
    season: str
    season_week: int
    source: str = "calendar_events_plus_one_event_dry_run_reports"
    calendar_fingerprint: str | None = None
    generated_fingerprint: str
    read_only: bool = True


class SimulateSeasonWeekPreflightResult(BaseModel):
    season: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    events: list[SeasonWeekEventPreflight] = Field(default_factory=list)
    summary: SeasonWeekPreflightSummary
    metadata: SeasonWeekPreflightMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class SimulateSeasonWeekPreflightApiRequest(SimulateSeasonWeekPreflightRequest):
    season: str = "2000/2001"
    season_week: int = Field(..., ge=1, le=TOTAL_SEASON_WEEKS)


@dataclass(slots=True)
class SeasonWeekSimulationPreflightService:
    """Build deterministic week plans without writing any artifact registries."""

    calendar_service: SeasonCalendarService
    lifecycle_service: SeasonEventLifecycleService
    event_simulation_service: SeasonEventSimulationService
    ranking_snapshot_service: SeasonRankingSnapshotService | None = None

    def preflight_week(self, *, season: str, season_week: int, request: SimulateSeasonWeekPreflightRequest) -> SimulateSeasonWeekPreflightResult:
        warnings = [PREFLIGHT_READ_ONLY_WARNING]
        errors: list[str] = []
        calendar_year, year_week = self._calendar_position(season=season, season_week=season_week, calendar=None)
        calendar_result = self.calendar_service.get_calendar(season=season)
        calendar = calendar_result.calendar
        calendar_fingerprint = self._calendar_fingerprint(calendar) if calendar else None

        if not 1 <= season_week <= TOTAL_SEASON_WEEKS:
            errors.append("season_week must be between 1 and 61")
        if request.publish_snapshot and not request.apply_points:
            errors.append("publish_snapshot=true requires apply_points=true for week preflight.")
        if calendar is None:
            errors.append(f"No persisted season calendar exists for season '{season}'.")
        else:
            calendar_year, year_week = self._calendar_position(season=season, season_week=season_week, calendar=calendar)
            warnings.extend(self._issue_text(item) for item in calendar.validation_warnings)
            errors.extend(self._issue_text(item) for item in calendar.validation_errors)

        snapshot_already_exists = False
        if self.ranking_snapshot_service is not None and 1 <= season_week <= TOTAL_SEASON_WEEKS:
            snapshot = self.ranking_snapshot_service.get_snapshot(season=season, season_week=season_week)
            snapshot_already_exists = snapshot.snapshot_exists
            if snapshot.snapshot_exists and request.publish_snapshot and not request.overwrite_existing:
                warnings.append("Ranking snapshot already exists for this week; later run-week execution should skip or require overwrite.")

        events: list[SeasonWeekEventPreflight] = []
        selected_events: list[SeasonCalendarEvent] = []
        if calendar is not None and 1 <= season_week <= TOTAL_SEASON_WEEKS:
            week_events = [event for event in calendar.events if event.season_week == season_week]
            selected_events = self._filter_events(week_events, request.event_id_filter, warnings)
            if request.publish_snapshot and len(selected_events) > 1:
                warnings.append("All planned event point applications should complete before publishing the week snapshot.")
            if not selected_events:
                warnings.append("No persisted calendar events exist for this season week.")
            for event in selected_events:
                lifecycle = self.lifecycle_service.get_event_lifecycle(event_id=event.event_id).event
                if lifecycle is not None and not request.include_completed_events and lifecycle.current_stage == "ranking_snapshot_published":
                    continue
                event_request = SimulateOneEventRequest(
                    seed=self._event_seed(request.seed, season, season_week, event.event_id),
                    dry_run=True,
                    overwrite_existing=request.overwrite_existing,
                    max_steps=request.max_steps_per_event,
                    stop_after_stage=request.stop_after_stage,
                    apply_points=request.apply_points,
                    publish_snapshot=request.publish_snapshot,
                    allow_incomplete_results=request.allow_incomplete_results,
                    allow_blocked=request.allow_blocked,
                    include_not_entered=request.include_not_entered,
                    max_alternates=request.max_alternates,
                    simulate_draw_type=request.simulate_draw_type,
                )
                one_event_result = self.event_simulation_service.simulate_one_event(event_id=event.event_id, request=event_request)
                if one_event_result.report is None:
                    errors.extend(one_event_result.validation_errors)
                    continue
                report = one_event_result.report
                events.append(SeasonWeekEventPreflight(
                    event_id=event.event_id,
                    event_name=event.event_name,
                    season=event.season,
                    season_week=event.season_week,
                    calendar_year=event.calendar_year,
                    year_week=event.year_week,
                    category=event.category,
                    tour_level=event.tour_level,
                    host_country=event.host_country,
                    lifecycle_stage_before=report.lifecycle_stage_before or (report.initial_lifecycle.current_stage if report.initial_lifecycle else None),
                    next_recommended_action_before=report.initial_lifecycle.next_recommended_action if report.initial_lifecycle else None,
                    one_event_report=report,
                    blocked=report.blocked,
                    can_continue=report.can_continue,
                    stop_reason=report.plan_summary.stop_reason,
                    planned_step_count=report.plan_summary.planned_step_count,
                    planned_mutates_active_players=any(step.mutates_active_players for step in report.steps),
                    planned_mutates_ranking_snapshot=any(step.mutates_ranking_snapshot for step in report.steps),
                    warnings=one_event_result.validation_warnings,
                    errors=one_event_result.validation_errors,
                ))

        summary = self._summary(season=season, season_week=season_week, calendar_year=calendar_year, year_week=year_week, calendar_exists=calendar is not None, selected_count=len(selected_events), events=events, request=request, errors=errors, snapshot_already_exists=snapshot_already_exists)
        result = SimulateSeasonWeekPreflightResult(
            season=season,
            season_week=season_week,
            calendar_year=calendar_year,
            year_week=year_week,
            events=events,
            summary=summary,
            metadata=SeasonWeekPreflightMetadata(season=season, season_week=season_week, calendar_fingerprint=calendar_fingerprint, generated_fingerprint="pending"),
            validation_warnings=self._dedupe(warnings),
            validation_errors=self._dedupe(errors),
        )
        result.metadata.generated_fingerprint = self._fingerprint(result.model_dump(mode="json", exclude={"metadata": {"generated_fingerprint"}}))
        return result

    def _summary(self, *, season: str, season_week: int, calendar_year: int | None, year_week: int | None, calendar_exists: bool, selected_count: int, events: list[SeasonWeekEventPreflight], request: SimulateSeasonWeekPreflightRequest, errors: list[str], snapshot_already_exists: bool) -> SeasonWeekPreflightSummary:
        first_blocked = next((event for event in events if event.blocked or not event.can_continue), None)
        completed_count = sum(1 for event in events if event.one_event_report.completed or event.lifecycle_stage_before == "ranking_snapshot_published")
        can_run = calendar_exists and bool(events) and not errors and first_blocked is None and (not request.publish_snapshot or request.apply_points)
        return SeasonWeekPreflightSummary(
            season=season,
            season_week=season_week,
            calendar_year=calendar_year,
            year_week=year_week,
            event_count=selected_count,
            planned_event_count=len(events),
            completed_event_count=completed_count,
            blocked_event_count=sum(1 for event in events if event.blocked or not event.can_continue),
            can_run_week=can_run,
            would_apply_points=request.apply_points,
            would_publish_snapshot=request.publish_snapshot,
            snapshot_already_exists=snapshot_already_exists,
            week_has_multiple_events=selected_count > 1,
            total_planned_steps=sum(event.planned_step_count for event in events),
            total_planned_player_mutations=sum(1 for event in events if event.planned_mutates_active_players),
            total_planned_snapshot_mutations=1 if request.publish_snapshot else 0,
            first_blocked_event_id=first_blocked.event_id if first_blocked else None,
            stop_reason=(first_blocked.stop_reason or "event_blocked") if first_blocked else ("validation_error" if errors else None),
            next_safe_action="resolve_blocker" if (first_blocked or errors) else ("run_week_simulation" if can_run else None),
        )

    @staticmethod
    def _filter_events(events: list[SeasonCalendarEvent], event_id_filter: list[str], warnings: list[str]) -> list[SeasonCalendarEvent]:
        normalized = [item.strip() for item in event_id_filter if item.strip()]
        if not normalized:
            return list(events)
        ids = set(normalized)
        found = {event.event_id for event in events}
        unknown = sorted(ids - found)
        if unknown:
            warnings.append(f"Unknown event_id_filter values for this season week: {', '.join(unknown)}")
        return [event for event in events if event.event_id in ids]

    @staticmethod
    def _event_seed(base_seed: int, season: str, season_week: int, event_id: str) -> int:
        digest = hashlib.sha256(f"{base_seed}:{season}:{season_week}:{event_id}".encode("utf-8")).hexdigest()
        return int(digest[:12], 16) % 2_147_483_647

    @staticmethod
    def _calendar_position(*, season: str, season_week: int, calendar: SeasonCalendar | None) -> tuple[int | None, int | None]:
        if not 1 <= season_week <= TOTAL_SEASON_WEEKS:
            return None, None
        start_week = calendar.metadata.season_start_year_week if calendar and calendar.metadata else DEFAULT_SEASON_START_YEAR_WEEK
        try:
            position = season_week_to_calendar_position(season=season, season_week=season_week, season_start_year_week=start_week)
        except ValueError:
            return None, None
        return position.calendar_year, position.year_week

    @staticmethod
    def _calendar_fingerprint(calendar: SeasonCalendar | None) -> str | None:
        if calendar is None:
            return None
        if calendar.metadata and calendar.metadata.build_fingerprint:
            return calendar.metadata.build_fingerprint
        fps = [event.calendar_fingerprint for event in calendar.events if event.calendar_fingerprint]
        return hashlib.sha256(json.dumps(fps, sort_keys=True).encode("utf-8")).hexdigest() if fps else None

    @staticmethod
    def _issue_text(issue: Any) -> str:
        code = getattr(issue, "code", None)
        message = getattr(issue, "message", str(issue))
        return f"{code}: {message}" if code else str(message)

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
