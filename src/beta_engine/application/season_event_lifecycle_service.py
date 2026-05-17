"""Read-only lifecycle status derivation for persisted season events."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_draw_service import SeasonDrawService
from beta_engine.application.season_entry_list_service import SeasonEntryListService
from beta_engine.application.season_event_results_service import SeasonEventResultsService
from beta_engine.application.season_match_service import SeasonMatchService, TournamentProgressionStatus
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService
from beta_engine.domain.tournaments import SeasonCalendar, SeasonCalendarEvent

EventLifecycleStage = Literal[
    "missing_calendar",
    "planned",
    "entries_generated",
    "draw_generated",
    "matches_generated",
    "in_progress",
    "completed",
    "results_extracted",
    "points_generated",
    "points_applied",
    "ranking_snapshot_published",
]

NextLifecycleAction = Literal[
    "build_calendar",
    "generate_entries",
    "generate_draw",
    "generate_matches",
    "process_byes_or_simulate_matches",
    "extract_results",
    "generate_point_awards",
    "apply_point_awards",
    "publish_ranking_snapshot",
    "complete",
    "resolve_blocker",
]


class EventArtifactStatus(BaseModel):
    exists: bool = False
    persisted: bool = False
    fingerprint: str | None = None
    validation_error_count: int = 0
    validation_warning_count: int = 0
    summary: dict[str, Any] | None = None


class LifecycleMetadata(BaseModel):
    season: str
    source: Literal["persisted_artifact_registries"] = "persisted_artifact_registries"
    calendar_fingerprint: str | None = None
    generated_fingerprint: str
    read_only: bool = True


class EventLifecycleStatus(BaseModel):
    event_id: str
    season: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    event_name: str
    category: str
    tour_level: str | None = None
    host_country: str
    template_id: str
    current_stage: EventLifecycleStage
    next_recommended_action: NextLifecycleAction
    is_blocked: bool = False
    block_reasons: list[str] = Field(default_factory=list)
    entries: EventArtifactStatus = Field(default_factory=EventArtifactStatus)
    draw: EventArtifactStatus = Field(default_factory=EventArtifactStatus)
    matches: EventArtifactStatus = Field(default_factory=EventArtifactStatus)
    progression_status: dict[str, Any] | None = None
    results: EventArtifactStatus = Field(default_factory=EventArtifactStatus)
    point_awards: EventArtifactStatus = Field(default_factory=EventArtifactStatus)
    points_applied: bool = False
    ranking_snapshot: EventArtifactStatus = Field(default_factory=EventArtifactStatus)
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class SeasonLifecycleSummary(BaseModel):
    season: str
    event_count: int = 0
    planned_count: int = 0
    entries_generated_count: int = 0
    draw_generated_count: int = 0
    matches_generated_count: int = 0
    in_progress_count: int = 0
    completed_count: int = 0
    results_extracted_count: int = 0
    points_generated_count: int = 0
    points_applied_count: int = 0
    ranking_snapshot_published_count: int = 0
    blocked_count: int = 0


class SeasonLifecycleResponse(BaseModel):
    season: str
    events: list[EventLifecycleStatus] = Field(default_factory=list)
    summary: SeasonLifecycleSummary
    metadata: LifecycleMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class EventLifecycleResponse(BaseModel):
    event: EventLifecycleStatus | None = None
    metadata: LifecycleMetadata
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonEventLifecycleService:
    """Read existing event artifact registries and derive a deterministic lifecycle read model."""

    calendar_service: SeasonCalendarService
    entry_list_service: SeasonEntryListService
    draw_service: SeasonDrawService
    match_service: SeasonMatchService
    result_service: SeasonEventResultsService
    point_awards_service: SeasonPointAwardsService
    ranking_snapshot_service: SeasonRankingSnapshotService | None = None

    def get_season_lifecycle(self, *, season: str) -> SeasonLifecycleResponse:
        calendar_result = self.calendar_service.get_calendar(season=season)
        calendar = calendar_result.calendar
        warnings = [self._issue_text(issue) for issue in calendar_result.validation_warnings]
        errors = [self._issue_text(issue) for issue in calendar_result.validation_errors]
        if calendar is None:
            errors.append(f"No persisted season calendar exists for season '{season}'.")
            metadata = LifecycleMetadata(season=season, calendar_fingerprint=None, generated_fingerprint=self._fingerprint({"season": season, "events": [], "errors": errors}))
            return SeasonLifecycleResponse(season=season, events=[], summary=SeasonLifecycleSummary(season=season), metadata=metadata, validation_warnings=warnings, validation_errors=errors)

        events = [self._status_for_event(event) for event in sorted(calendar.events, key=lambda item: (item.season_week, item.event_id))]
        metadata = LifecycleMetadata(season=season, calendar_fingerprint=self._calendar_fingerprint(calendar), generated_fingerprint=self._fingerprint({"season": season, "events": [event.model_dump(mode="json") for event in events], "warnings": warnings, "errors": errors}))
        return SeasonLifecycleResponse(season=season, events=events, summary=self._summary(season, events), metadata=metadata, validation_warnings=warnings, validation_errors=errors)

    def get_event_lifecycle(self, *, event_id: str) -> EventLifecycleResponse:
        calendar = self._find_calendar_for_event(event_id)
        if calendar is None:
            metadata = LifecycleMetadata(season="unknown", generated_fingerprint=self._fingerprint({"event_id": event_id, "event": None}))
            return EventLifecycleResponse(event=None, metadata=metadata, validation_errors=[f"Unknown persisted calendar event '{event_id}'."])
        event = next(event for event in calendar.events if event.event_id == event_id)
        status = self._status_for_event(event)
        metadata = LifecycleMetadata(season=str(calendar.season), calendar_fingerprint=self._calendar_fingerprint(calendar), generated_fingerprint=self._fingerprint({"event": status.model_dump(mode="json")}))
        return EventLifecycleResponse(event=status, metadata=metadata)

    def _status_for_event(self, event: SeasonCalendarEvent) -> EventLifecycleStatus:
        entries = self._entry_status(event.event_id)
        draw = self._draw_status(event.event_id)
        matches, progression = self._match_status(event.event_id)
        results = self._result_status(event.event_id)
        point_awards, points_applied = self._point_awards_status(event.event_id)
        ranking_snapshot = self._ranking_snapshot_status(str(event.season), event.season_week)

        warnings: list[str] = []
        errors: list[str] = []
        block_reasons: list[str] = []
        for label, artifact in [("entries", entries), ("draw", draw), ("matches", matches), ("results", results), ("point_awards", point_awards), ("ranking_snapshot", ranking_snapshot)]:
            if artifact.validation_error_count:
                block_reasons.append(f"{label} artifact has {artifact.validation_error_count} validation error(s)")
                errors.append(block_reasons[-1])

        if progression and progression.get("event_status") == "blocked" and progression.get("pending_matches", 0) == 0:
            block_reasons.append("match package is blocked with no pending matches")
        if results.exists and results.summary and results.summary.get("completion_status") != "complete":
            block_reasons.append("event result package is not complete")
        if ranking_snapshot.exists and not points_applied:
            warnings.append("Ranking snapshot exists for this week but this event’s points are not applied.")

        current_stage = self._stage(entries, draw, matches, progression, results, point_awards, points_applied, ranking_snapshot)
        is_blocked = bool(block_reasons)
        next_action = "resolve_blocker" if is_blocked else self._next_action(entries, draw, matches, progression, results, point_awards, points_applied, ranking_snapshot)

        return EventLifecycleStatus(
            event_id=event.event_id,
            season=str(event.season),
            season_week=event.season_week,
            calendar_year=event.calendar_year,
            year_week=event.year_week,
            event_name=event.event_name,
            category=event.category,
            tour_level=event.tour_level,
            host_country=event.host_country,
            template_id=event.template_id,
            current_stage=current_stage,
            next_recommended_action=next_action,  # type: ignore[arg-type]
            is_blocked=is_blocked,
            block_reasons=block_reasons,
            entries=entries,
            draw=draw,
            matches=matches,
            progression_status=progression,
            results=results,
            point_awards=point_awards,
            points_applied=points_applied,
            ranking_snapshot=ranking_snapshot,
            validation_warnings=warnings,
            validation_errors=errors,
        )

    def _entry_status(self, event_id: str) -> EventArtifactStatus:
        result = self.entry_list_service.get_entry_list(event_id=event_id)
        return self._artifact(result.entry_list_exists, result.metadata, result.summary, result.validation_warnings, result.validation_errors, "build_fingerprint")

    def _draw_status(self, event_id: str) -> EventArtifactStatus:
        result = self.draw_service.get_draw_package(event_id=event_id)
        return self._artifact(result.draw_package_exists, result.metadata, result.summary, result.validation_warnings, result.validation_errors, "build_fingerprint")

    def _match_status(self, event_id: str) -> tuple[EventArtifactStatus, dict[str, Any] | None]:
        result = self.match_service.get_match_package(event_id=event_id)
        progression: dict[str, Any] | None = None
        if result.match_package_exists:
            status: TournamentProgressionStatus = self.match_service.get_progression_status(event_id=event_id)
            progression = status.model_dump(mode="json")
        return self._artifact(result.match_package_exists, result.metadata, result.summary, result.validation_warnings, result.validation_errors, "build_fingerprint"), progression

    def _result_status(self, event_id: str) -> EventArtifactStatus:
        result = self.result_service.get_event_result(event_id=event_id)
        return self._artifact(result.result_package_exists, result.metadata, result.summary, result.validation_warnings, result.validation_errors, "build_fingerprint")

    def _point_awards_status(self, event_id: str) -> tuple[EventArtifactStatus, bool]:
        result = self.point_awards_service.get_event_point_awards(event_id=event_id)
        return self._artifact(result.award_package_exists, result.metadata, result.summary, result.validation_warnings, result.validation_errors, "build_fingerprint"), result.applied

    def _ranking_snapshot_status(self, season: str, season_week: int) -> EventArtifactStatus:
        if self.ranking_snapshot_service is None:
            return EventArtifactStatus()
        result = self.ranking_snapshot_service.get_snapshot(season=season, season_week=season_week)
        fp = result.metadata.snapshot_fingerprint if result.metadata else None
        summary = None if result.summary is None else {key: value.model_dump(mode="json") for key, value in result.summary.items()}
        return EventArtifactStatus(exists=result.snapshot_exists, persisted=bool(result.snapshot and result.snapshot.persisted), fingerprint=fp, validation_error_count=len(result.validation_errors), validation_warning_count=len(result.validation_warnings), summary=summary)

    def _artifact(self, exists: bool, metadata: Any, summary: Any, warnings: list[Any], errors: list[Any], fingerprint_field: str) -> EventArtifactStatus:
        fingerprint = getattr(metadata, fingerprint_field, None) if metadata is not None else None
        persisted = bool(getattr(metadata, "persisted", False)) if metadata is not None else False
        dumped_summary = summary.model_dump(mode="json") if hasattr(summary, "model_dump") else summary
        return EventArtifactStatus(exists=exists, persisted=persisted, fingerprint=fingerprint, validation_error_count=len(errors), validation_warning_count=len(warnings), summary=dumped_summary)

    def _stage(self, entries: EventArtifactStatus, draw: EventArtifactStatus, matches: EventArtifactStatus, progression: dict[str, Any] | None, results: EventArtifactStatus, point_awards: EventArtifactStatus, points_applied: bool, ranking_snapshot: EventArtifactStatus) -> EventLifecycleStage:
        if ranking_snapshot.exists:
            return "ranking_snapshot_published"
        if points_applied:
            return "points_applied"
        if point_awards.exists:
            return "points_generated"
        if results.exists:
            return "results_extracted"
        if matches.exists:
            event_status = progression.get("event_status") if progression else None
            if event_status == "completed" or progression and progression.get("champion_player_id"):
                return "completed"
            completed = int((matches.summary or {}).get("completed_matches", 0))
            incomplete = int((matches.summary or {}).get("pending_matches", 0)) + int((matches.summary or {}).get("blocked_matches", 0)) + int((matches.summary or {}).get("bye_auto_advances", 0))
            if completed > 0 and incomplete > 0:
                return "in_progress"
            return "matches_generated"
        if draw.exists:
            return "draw_generated"
        if entries.exists:
            return "entries_generated"
        return "planned"

    def _next_action(self, entries: EventArtifactStatus, draw: EventArtifactStatus, matches: EventArtifactStatus, progression: dict[str, Any] | None, results: EventArtifactStatus, point_awards: EventArtifactStatus, points_applied: bool, ranking_snapshot: EventArtifactStatus) -> NextLifecycleAction:
        if not entries.exists:
            return "generate_entries"
        if not draw.exists:
            return "generate_draw"
        if not matches.exists:
            return "generate_matches"
        if progression is None or progression.get("event_status") != "completed":
            return "process_byes_or_simulate_matches"
        if not results.exists:
            return "extract_results"
        if results.summary and results.summary.get("completion_status") != "complete":
            return "resolve_blocker"
        if not point_awards.exists:
            return "generate_point_awards"
        if not points_applied:
            return "apply_point_awards"
        if not ranking_snapshot.exists:
            return "publish_ranking_snapshot"
        return "complete"

    def _summary(self, season: str, events: list[EventLifecycleStatus]) -> SeasonLifecycleSummary:
        counts = {stage: 0 for stage in EventLifecycleStage.__args__}  # type: ignore[attr-defined]
        for event in events:
            counts[event.current_stage] += 1
        return SeasonLifecycleSummary(
            season=season,
            event_count=len(events),
            planned_count=counts["planned"],
            entries_generated_count=counts["entries_generated"],
            draw_generated_count=counts["draw_generated"],
            matches_generated_count=counts["matches_generated"],
            in_progress_count=counts["in_progress"],
            completed_count=counts["completed"],
            results_extracted_count=counts["results_extracted"],
            points_generated_count=counts["points_generated"],
            points_applied_count=counts["points_applied"],
            ranking_snapshot_published_count=counts["ranking_snapshot_published"],
            blocked_count=sum(1 for event in events if event.is_blocked),
        )

    def _find_calendar_for_event(self, event_id: str) -> SeasonCalendar | None:
        registry = self.calendar_service._load_registry()
        for calendar in registry.calendars_by_season.values():
            if any(event.event_id == event_id for event in calendar.events):
                return calendar
        return None

    @staticmethod
    def _calendar_fingerprint(calendar: SeasonCalendar) -> str | None:
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
    def _fingerprint(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
