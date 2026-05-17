"""Explicit one-event orchestration using lifecycle preflight."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_draw_service import DrawGenerateRequest, SeasonDrawService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, SeasonEntryListService
from beta_engine.application.season_event_lifecycle_service import EventLifecycleStage, EventLifecycleStatus, SeasonEventLifecycleService
from beta_engine.application.season_event_results_service import EventResultExtractRequest, SeasonEventResultsService
from beta_engine.application.season_match_service import MatchPackageGenerateRequest, ProgressionCommandRequest, SeasonMatchService, SimulateDrawRequest
from beta_engine.application.season_point_awards_service import PointAwardApplyRequest, PointAwardGenerateRequest, SeasonPointAwardsService
from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService, WeeklyRankingSnapshotGenerateRequest

SimulateOneEventStep = Literal[
    "preflight_lifecycle",
    "generate_entries",
    "generate_draw",
    "generate_matches",
    "process_byes",
    "simulate_draw",
    "refresh_progression",
    "extract_results",
    "generate_point_awards",
    "apply_point_awards",
    "publish_ranking_snapshot",
    "final_lifecycle",
]
SimulateOneEventStepResultStatus = Literal["skipped", "planned", "succeeded", "failed", "blocked"]
SimulateDrawType = Literal["qualification_then_main", "qualification", "main"]


class SimulateOneEventPlanSummary(BaseModel):
    planned_step_count: int = 0
    executed_step_count: int = 0
    skipped_step_count: int = 0
    succeeded_step_count: int = 0
    failed_step_count: int = 0
    blocked_step_count: int = 0
    first_failed_step: str | None = None
    stop_reason: str | None = None
    next_safe_action: str | None = None


class SimulateOneEventArtifactState(BaseModel):
    entries_exists: bool = False
    draw_exists: bool = False
    matches_exists: bool = False
    results_exists: bool = False
    point_awards_exists: bool = False
    points_applied: bool = False
    ranking_snapshot_exists: bool = False


class SimulateOneEventRequest(BaseModel):
    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False
    max_steps: int = Field(default=20, ge=1, le=100)
    stop_after_stage: EventLifecycleStage | None = None
    apply_points: bool = False
    publish_snapshot: bool = False
    allow_incomplete_results: bool = False
    allow_blocked: bool = False
    include_not_entered: bool = False
    max_alternates: int = Field(default=16, ge=0, le=256)
    simulate_draw_type: SimulateDrawType = "qualification_then_main"


class SimulateOneEventStepStatus(BaseModel):
    step: SimulateOneEventStep
    status: SimulateOneEventStepResultStatus
    action_detail: str
    artifact_exists_before: bool | None = None
    artifact_exists_after: bool | None = None
    changed_ids: list[str] = Field(default_factory=list)
    fingerprint: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    lifecycle_stage_before_step: str | None = None
    lifecycle_stage_after_step: str | None = None
    stop_reason: str | None = None
    service_called: str | None = None
    request_seed: int | None = None
    mutates_active_players: bool = False
    mutates_ranking_snapshot: bool = False


class ChangedArtifacts(BaseModel):
    entries: bool = False
    draw: bool = False
    matches: bool = False
    results: bool = False
    point_awards: bool = False
    active_player_points: bool = False
    ranking_snapshot: bool = False


class SimulateOneEventMetadata(BaseModel):
    build_fingerprint: str
    read_only: bool = False
    lifecycle_preflight_fingerprint: str | None = None
    final_lifecycle_fingerprint: str | None = None


class SimulateOneEventReport(BaseModel):
    event_id: str
    season: str
    season_week: int
    calendar_year: int | None = None
    year_week: int | None = None
    event_name: str
    seed: int
    dry_run: bool
    requested_apply_points: bool
    requested_publish_snapshot: bool
    initial_lifecycle: EventLifecycleStatus | None = None
    final_lifecycle: EventLifecycleStatus | None = None
    steps: list[SimulateOneEventStepStatus] = Field(default_factory=list)
    changed_artifacts: ChangedArtifacts = Field(default_factory=ChangedArtifacts)
    plan_summary: SimulateOneEventPlanSummary = Field(default_factory=SimulateOneEventPlanSummary)
    artifact_state_before: SimulateOneEventArtifactState = Field(default_factory=SimulateOneEventArtifactState)
    artifact_state_after: SimulateOneEventArtifactState = Field(default_factory=SimulateOneEventArtifactState)
    lifecycle_stage_before: str | None = None
    lifecycle_stage_after: str | None = None
    lifecycle_next_action_after: str | None = None
    can_continue: bool = True
    safe_to_rerun: bool = True
    would_duplicate_points: bool = False
    would_overwrite_existing: bool = False
    completed: bool = False
    blocked: bool = False
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    metadata: SimulateOneEventMetadata


class SimulateOneEventResult(BaseModel):
    report: SimulateOneEventReport | None = None
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class SeasonEventSimulationService:
    """Coordinate existing event services; do not implement domain simulation logic here."""

    lifecycle_service: SeasonEventLifecycleService
    entry_list_service: SeasonEntryListService
    draw_service: SeasonDrawService
    match_service: SeasonMatchService
    result_service: SeasonEventResultsService
    point_awards_service: SeasonPointAwardsService
    ranking_snapshot_service: SeasonRankingSnapshotService

    def simulate_one_event(self, *, event_id: str, request: SimulateOneEventRequest) -> SimulateOneEventResult:
        validation_errors: list[str] = []
        validation_warnings: list[str] = []
        stop_reason: str | None = None
        if request.publish_snapshot and not request.apply_points:
            validation_errors.append("publish_snapshot=true requires apply_points=true for one-event orchestration.")
            stop_reason = "publish_snapshot_requires_apply_points"

        preflight = self.lifecycle_service.get_event_lifecycle(event_id=event_id)
        if preflight.event is None:
            errors = validation_errors + preflight.validation_errors + [f"Unknown persisted calendar event '{event_id}'."]
            return SimulateOneEventResult(report=None, validation_warnings=preflight.validation_warnings, validation_errors=self._dedupe(errors))

        event = preflight.event
        artifact_before = self._artifact_state(event)
        steps = [self._decorate_step(SimulateOneEventStepStatus(
            step="preflight_lifecycle",
            status="succeeded",
            action_detail=f"Initial lifecycle stage is {event.current_stage}; next action is {event.next_recommended_action}.",
            fingerprint=preflight.metadata.generated_fingerprint,
            warnings=list(event.validation_warnings),
            errors=list(event.validation_errors),
            lifecycle_stage_before_step=event.current_stage,
            lifecycle_stage_after_step=event.current_stage,
            service_called="SeasonEventLifecycleService.get_event_lifecycle",
        ))]
        report = self._report(event=event, request=request, preflight_fingerprint=preflight.metadata.generated_fingerprint, steps=steps)
        steps = report.steps
        report.artifact_state_before = artifact_before
        report.artifact_state_after = artifact_before
        report.lifecycle_stage_before = event.current_stage
        report.lifecycle_stage_after = event.current_stage
        report.lifecycle_next_action_after = event.next_recommended_action
        report.would_overwrite_existing = request.overwrite_existing and self._any_artifact_exists(artifact_before)
        report.would_duplicate_points = request.apply_points and event.points_applied
        report.validation_warnings.extend(validation_warnings)
        report.validation_errors.extend(validation_errors)

        planned = self._planned_steps(event, request)
        report.plan_summary.planned_step_count = len(planned)

        if validation_errors:
            report.blocked = True
            report.can_continue = False
            steps.append(self._decorate_step(SimulateOneEventStepStatus(
                step="final_lifecycle",
                status="blocked",
                action_detail=validation_errors[0],
                fingerprint=preflight.metadata.generated_fingerprint,
                errors=validation_errors,
                lifecycle_stage_before_step=event.current_stage,
                lifecycle_stage_after_step=event.current_stage,
                stop_reason=stop_reason,
            )))
            return self._finish(report, stop_reason or "validation_error")
        if event.is_blocked and not request.allow_blocked:
            msg = "Lifecycle preflight is blocked; resolve blocker or set allow_blocked=true."
            report.validation_errors.append(msg)
            report.blocked = True
            report.can_continue = False
            steps.append(self._decorate_step(SimulateOneEventStepStatus(step="final_lifecycle", status="blocked", action_detail=msg, fingerprint=preflight.metadata.generated_fingerprint, errors=event.block_reasons or [msg], lifecycle_stage_before_step=event.current_stage, lifecycle_stage_after_step=event.current_stage, stop_reason="lifecycle_blocked")))
            return self._finish(report, "lifecycle_blocked")
        if event.current_stage == "ranking_snapshot_published":
            report.completed = True
            report.final_lifecycle = event
            steps.append(self._decorate_step(SimulateOneEventStepStatus(step="final_lifecycle", status="succeeded", action_detail="Event lifecycle is already ranking_snapshot_published; no work required.", fingerprint=preflight.metadata.generated_fingerprint, lifecycle_stage_before_step=event.current_stage, lifecycle_stage_after_step=event.current_stage, stop_reason="already_complete")))
            return self._finish(report, "already_complete")
        if not planned:
            steps.append(self._decorate_step(SimulateOneEventStepStatus(step="final_lifecycle", status="skipped", action_detail="No orchestration steps are needed for the current request and lifecycle state.", fingerprint=preflight.metadata.generated_fingerprint, lifecycle_stage_before_step=event.current_stage, lifecycle_stage_after_step=event.current_stage, stop_reason="no_steps_needed")))
            return self._finish(report, "no_steps_needed")

        if request.dry_run:
            capped = planned[: request.max_steps]
            for step in capped:
                reason = self._dry_run_detail(step, event, request)
                steps.append(self._decorate_step(SimulateOneEventStepStatus(
                    step=step,
                    status="planned",
                    action_detail=reason,
                    artifact_exists_before=self._exists_for_step(event, step),
                    artifact_exists_after=self._exists_for_step(event, step),
                    lifecycle_stage_before_step=event.current_stage,
                    lifecycle_stage_after_step=event.current_stage,
                    request_seed=self._derive_seed(request.seed, event_id, step),
                )))
            if len(planned) > len(capped):
                stop_reason = "max_steps_reached"
                report.validation_warnings.append(f"Dry-run plan was capped at max_steps={request.max_steps}.")
            else:
                stop_reason = "dry_run_plan_only"
            if not request.apply_points:
                report.validation_warnings.append("apply_points=false means this command will stop after point awards are generated; next safe action is apply_point_awards.")
            steps.append(self._decorate_step(SimulateOneEventStepStatus(step="final_lifecycle", status="planned", action_detail="Dry run plan only; final lifecycle equals initial lifecycle.", fingerprint=preflight.metadata.generated_fingerprint, lifecycle_stage_before_step=event.current_stage, lifecycle_stage_after_step=event.current_stage, stop_reason=stop_reason)))
            return self._finish(report, stop_reason)

        executed = 0
        current = event
        for step_name in planned:
            if executed >= request.max_steps:
                warning = f"Stopped after max_steps={request.max_steps}."
                report.validation_warnings.append(warning)
                stop_reason = "max_steps_reached"
                steps.append(self._decorate_step(SimulateOneEventStepStatus(step="final_lifecycle", status="blocked", action_detail=warning, lifecycle_stage_before_step=current.current_stage, lifecycle_stage_after_step=current.current_stage, stop_reason=stop_reason)))
                break
            if self._should_stop(current, request):
                stop_reason = "stop_after_stage_reached"
                steps.append(self._decorate_step(SimulateOneEventStepStatus(step="final_lifecycle", status="skipped", action_detail=f"Requested stop_after_stage={request.stop_after_stage} reached before {step_name}.", lifecycle_stage_before_step=current.current_stage, lifecycle_stage_after_step=current.current_stage, stop_reason=stop_reason)))
                break
            before_stage = current.current_stage
            step = self._execute_step(event_id=event_id, step=step_name, request=request, lifecycle=current)
            step.lifecycle_stage_before_step = before_stage
            if step.request_seed is None:
                step.request_seed = self._derive_seed(request.seed, event_id, step_name)
            if step.service_called is None and step.status != "skipped":
                step.service_called = self._service_name(step_name)
            steps.append(self._decorate_step(step))
            executed += 1
            self._mark_changed(report.changed_artifacts, step_name, step)
            if step.status in {"failed", "blocked"} or step.errors:
                report.blocked = True
                report.can_continue = False
                report.validation_errors.extend(step.errors)
                stop_reason = step.stop_reason or ("step_blocked" if step.status == "blocked" else "step_failed")
                step.stop_reason = stop_reason
                break
            refreshed = self.lifecycle_service.get_event_lifecycle(event_id=event_id)
            if refreshed.event is not None:
                current = refreshed.event
                step.lifecycle_stage_after_step = current.current_stage
                if current.is_blocked and not request.allow_blocked:
                    msg = "Lifecycle became blocked after step execution."
                    report.blocked = True
                    report.can_continue = False
                    report.validation_errors.append(msg)
                    stop_reason = "lifecycle_blocked"
                    steps.append(self._decorate_step(SimulateOneEventStepStatus(step="final_lifecycle", status="blocked", action_detail=msg, fingerprint=refreshed.metadata.generated_fingerprint, errors=current.block_reasons or [msg], lifecycle_stage_before_step=current.current_stage, lifecycle_stage_after_step=current.current_stage, stop_reason=stop_reason)))
                    report.final_lifecycle = current
                    report.metadata.final_lifecycle_fingerprint = refreshed.metadata.generated_fingerprint
                    return self._finish(report, stop_reason)

        final = self.lifecycle_service.get_event_lifecycle(event_id=event_id)
        report.final_lifecycle = final.event
        report.metadata.final_lifecycle_fingerprint = final.metadata.generated_fingerprint
        final_stage = final.event.current_stage if final.event else "unknown"
        if stop_reason is None:
            if report.blocked:
                stop_reason = "step_blocked"
            elif request.stop_after_stage and final.event and final.event.current_stage == request.stop_after_stage:
                stop_reason = "stop_after_stage_reached"
            elif final.event and final.event.current_stage == "points_generated" and not request.apply_points:
                stop_reason = "points_not_applied"
            elif final.event and final.event.current_stage == "points_applied" and not request.publish_snapshot:
                stop_reason = "already_complete" if artifact_before.points_applied else "points_applied"
            elif final.event and final.event.current_stage == "ranking_snapshot_published":
                stop_reason = "already_complete"
            if stop_reason is None:
                stop_reason = "no_steps_needed" if executed == 0 else None
        final_status: SimulateOneEventStepResultStatus = "blocked" if report.blocked else "succeeded"
        steps.append(self._decorate_step(SimulateOneEventStepStatus(step="final_lifecycle", status=final_status, action_detail=f"Final lifecycle stage is {final_stage}.", fingerprint=final.metadata.generated_fingerprint, warnings=final.validation_warnings, errors=final.validation_errors, lifecycle_stage_before_step=final_stage, lifecycle_stage_after_step=final_stage, stop_reason=stop_reason)))
        report.completed = bool(final.event and final.event.current_stage in {"points_generated", "points_applied", "ranking_snapshot_published"} and not report.blocked)
        return self._finish(report, stop_reason)

    def _execute_step(self, *, event_id: str, step: SimulateOneEventStep, request: SimulateOneEventRequest, lifecycle: EventLifecycleStatus) -> SimulateOneEventStepStatus:
        before = self._exists_for_step(lifecycle, step)
        seed = self._derive_seed(request.seed, event_id, step)
        try:
            if step == "generate_entries":
                if lifecycle.entries.exists and not request.overwrite_existing:
                    return self._skipped(step, "Entry list already exists; overwrite_existing=false.", before)
                result = self.entry_list_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=seed, dry_run=False, overwrite_existing=request.overwrite_existing, max_alternates=request.max_alternates, include_not_entered=request.include_not_entered))
                return self._service_step(step, "Generated entry list.", before, result.metadata.build_fingerprint if result.metadata else None, [event_id], result.validation_warnings, result.validation_errors)
            if step == "generate_draw":
                if lifecycle.draw.exists and not request.overwrite_existing:
                    return self._skipped(step, "Draw package already exists; overwrite_existing=false.", before)
                result = self.draw_service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=seed, dry_run=False, overwrite_existing=request.overwrite_existing))
                return self._service_step(step, "Generated draw package.", before, result.metadata.build_fingerprint if result.metadata else None, [event_id], result.validation_warnings, result.validation_errors)
            if step == "generate_matches":
                if lifecycle.matches.exists and not request.overwrite_existing:
                    return self._skipped(step, "Match package already exists; overwrite_existing=false.", before)
                result = self.match_service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=seed, dry_run=False, overwrite_existing=request.overwrite_existing))
                return self._service_step(step, "Generated match package.", before, result.metadata.build_fingerprint if result.metadata else None, [event_id], result.validation_warnings, result.validation_errors)
            if step == "process_byes":
                result = self.match_service.process_byes(event_id=event_id, request=ProgressionCommandRequest(seed=seed))
                status: SimulateOneEventStepResultStatus = "skipped" if not result.changed_match_ids else "succeeded"
                return self._service_step(step, "Processed pending BYE auto-advances." if result.changed_match_ids else "No pending BYE auto-advances.", before, result.metadata.get("build_fingerprint"), result.changed_match_ids, result.validation_warnings, result.validation_errors, status=status)
            if step == "simulate_draw":
                changed: list[str] = []
                warnings: list[Any] = []
                errors: list[Any] = []
                if request.simulate_draw_type in {"qualification_then_main", "qualification"}:
                    result = self.match_service.simulate_draw(event_id=event_id, request=SimulateDrawRequest(seed=seed, draw_type="qualification"))
                    changed.extend(result.changed_match_ids); warnings.extend(result.validation_warnings); errors.extend(result.validation_errors)
                    promote = self.match_service.promote_qualifiers(event_id=event_id, request=ProgressionCommandRequest(seed=self._derive_seed(request.seed, event_id, "promote_qualifiers")))
                    changed.extend(promote.changed_match_ids); warnings.extend(promote.validation_warnings); errors.extend(promote.validation_errors)
                    self.match_service.refresh_progression(event_id=event_id, request=ProgressionCommandRequest(seed=self._derive_seed(request.seed, event_id, "refresh_after_qualification")))
                    self.match_service.process_byes(event_id=event_id, request=ProgressionCommandRequest(seed=self._derive_seed(request.seed, event_id, "process_byes_after_qualification")))
                if request.simulate_draw_type in {"qualification_then_main", "main"}:
                    result = self.match_service.simulate_draw(event_id=event_id, request=SimulateDrawRequest(seed=self._derive_seed(request.seed, event_id, "simulate_main"), draw_type="main"))
                    changed.extend(result.changed_match_ids); warnings.extend(result.validation_warnings); errors.extend(result.validation_errors)
                return self._service_step(step, f"Simulated draw using mode {request.simulate_draw_type}.", before, None, changed, warnings, errors)
            if step == "refresh_progression":
                result = self.match_service.refresh_progression(event_id=event_id, request=ProgressionCommandRequest(seed=seed))
                return self._service_step(step, "Refreshed progression propagation.", before, result.metadata.get("build_fingerprint"), result.changed_match_ids, result.validation_warnings, result.validation_errors)
            if step == "extract_results":
                if lifecycle.results.exists and not request.overwrite_existing:
                    return self._skipped(step, "Event results already exist; overwrite_existing=false.", before)
                status = lifecycle.progression_status or {}
                if status.get("event_status") != "completed" and not request.allow_incomplete_results:
                    return SimulateOneEventStepStatus(step=step, status="blocked", action_detail="Event is not complete; allow_incomplete_results=false.", artifact_exists_before=before, artifact_exists_after=before, errors=["Event is not complete; results were not extracted."], stop_reason="event_not_complete")
                result = self.result_service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=seed, dry_run=False, overwrite_existing=request.overwrite_existing))
                return self._service_step(step, "Extracted event results.", before, result.metadata.build_fingerprint if result.metadata else None, [event_id], result.validation_warnings, result.validation_errors)
            if step == "generate_point_awards":
                if lifecycle.point_awards.exists and not request.overwrite_existing:
                    return self._skipped(step, "Point awards already exist; overwrite_existing=false.", before)
                if lifecycle.points_applied:
                    return self._skipped(step, "Point awards have already been applied; refusing to overwrite applied awards.", before)
                result = self.point_awards_service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=seed, dry_run=False, overwrite_existing=request.overwrite_existing))
                return self._service_step(step, "Generated event point awards.", before, result.metadata.build_fingerprint if result.metadata else None, [event_id], result.validation_warnings, result.validation_errors)
            if step == "apply_point_awards":
                if lifecycle.points_applied:
                    return self._skipped(step, "Points already applied; not reapplying.", before)
                result = self.point_awards_service.apply_event_point_awards(event_id=event_id, request=PointAwardApplyRequest(seed=seed, allow_reapply=False))
                return self._service_step(step, "Applied point awards to active season players.", before, result.metadata.build_fingerprint if result.metadata else None, [item.player_id for item in result.updated_players], result.validation_warnings, result.validation_errors)
            if step == "publish_ranking_snapshot":
                if lifecycle.ranking_snapshot.exists and not request.overwrite_existing:
                    return self._skipped(step, "Ranking snapshot already exists; overwrite_existing=false.", before)
                if not lifecycle.points_applied:
                    refreshed = self.lifecycle_service.get_event_lifecycle(event_id=event_id).event
                    if not refreshed or not refreshed.points_applied:
                        return SimulateOneEventStepStatus(step=step, status="blocked", action_detail="Points must be applied before publishing a ranking snapshot.", artifact_exists_before=before, artifact_exists_after=before, errors=["Points must be applied before publishing snapshot."], stop_reason="points_not_applied")
                    lifecycle = refreshed
                result = self.ranking_snapshot_service.generate_snapshot(season=lifecycle.season, season_week=lifecycle.season_week, request=WeeklyRankingSnapshotGenerateRequest(seed=seed, dry_run=False, overwrite_existing=request.overwrite_existing))
                status = "failed" if result.validation_errors else "succeeded"
                return SimulateOneEventStepStatus(step=step, status=status, action_detail="Published weekly ranking/race snapshot.", artifact_exists_before=before, artifact_exists_after=not result.validation_errors, changed_ids=[f"{lifecycle.season}:{lifecycle.season_week}"], fingerprint=result.metadata.snapshot_fingerprint if result.metadata else None, warnings=result.validation_warnings, errors=result.validation_errors)
        except ValueError as exc:
            return SimulateOneEventStepStatus(step=step, status="failed", action_detail="Step failed in underlying service.", artifact_exists_before=before, artifact_exists_after=before, errors=[str(exc)], stop_reason="validation_error")
        return self._skipped(step, "No implementation for step in this slice.", before)

    def _planned_steps(self, event: EventLifecycleStatus, request: SimulateOneEventRequest) -> list[SimulateOneEventStep]:
        steps: list[SimulateOneEventStep] = []
        if not event.entries.exists or request.overwrite_existing:
            steps.append("generate_entries")
        if not event.draw.exists or request.overwrite_existing:
            steps.append("generate_draw")
        if not event.matches.exists or request.overwrite_existing:
            steps.append("generate_matches")
        if event.current_stage in {"matches_generated", "in_progress", "draw_generated", "entries_generated", "planned"} or not event.results.exists:
            steps.extend(["process_byes", "simulate_draw", "refresh_progression"])
        if not event.results.exists or request.overwrite_existing:
            steps.append("extract_results")
        if not event.point_awards.exists or (request.overwrite_existing and not event.points_applied):
            steps.append("generate_point_awards")
        if request.apply_points:
            steps.append("apply_point_awards")
        if request.publish_snapshot:
            steps.append("publish_ranking_snapshot")
        if request.stop_after_stage:
            cutoff = self._cutoff_step(request.stop_after_stage)
            if cutoff in steps:
                steps = steps[: steps.index(cutoff) + 1]
        return steps

    @staticmethod
    def _cutoff_step(stage: EventLifecycleStage) -> SimulateOneEventStep:
        return {
            "entries_generated": "generate_entries", "draw_generated": "generate_draw", "matches_generated": "generate_matches", "in_progress": "simulate_draw", "completed": "refresh_progression", "results_extracted": "extract_results", "points_generated": "generate_point_awards", "points_applied": "apply_point_awards", "ranking_snapshot_published": "publish_ranking_snapshot",
            "planned": "preflight_lifecycle", "missing_calendar": "preflight_lifecycle",
        }[stage]

    @staticmethod
    def _should_stop(lifecycle: EventLifecycleStatus, request: SimulateOneEventRequest) -> bool:
        return request.stop_after_stage is not None and lifecycle.current_stage == request.stop_after_stage

    @staticmethod
    def _exists_for_step(lifecycle: EventLifecycleStatus, step: SimulateOneEventStep) -> bool | None:
        return {
            "generate_entries": lifecycle.entries.exists,
            "generate_draw": lifecycle.draw.exists,
            "generate_matches": lifecycle.matches.exists,
            "extract_results": lifecycle.results.exists,
            "generate_point_awards": lifecycle.point_awards.exists,
            "apply_point_awards": lifecycle.points_applied,
            "publish_ranking_snapshot": lifecycle.ranking_snapshot.exists,
        }.get(step)

    def _finish(self, report: SimulateOneEventReport, stop_reason: str | None) -> SimulateOneEventResult:
        final_event = report.final_lifecycle or report.initial_lifecycle
        if final_event is not None:
            report.artifact_state_after = self._artifact_state(final_event)
            report.lifecycle_stage_after = final_event.current_stage
            report.lifecycle_next_action_after = final_event.next_recommended_action
        report.changed_artifacts = self._derive_changed_artifacts(report.artifact_state_before, report.artifact_state_after, report.changed_artifacts)
        applied_this_run = any(step.step == "apply_point_awards" and step.status == "succeeded" and step.changed_ids for step in report.steps)
        report.safe_to_rerun = not (applied_this_run and report.requested_apply_points)
        report.would_duplicate_points = report.would_duplicate_points or any(
            step.step == "apply_point_awards" and step.status == "skipped" and step.artifact_exists_before and report.requested_apply_points
            for step in report.steps
        )
        report.can_continue = not report.blocked and stop_reason not in {"validation_error", "lifecycle_blocked", "step_blocked", "step_failed", "publish_snapshot_requires_apply_points", "event_not_complete", "max_steps_reached"}
        report.plan_summary = self._plan_summary(report.steps, stop_reason, report.lifecycle_next_action_after)
        report.metadata.build_fingerprint = self._fingerprint(report.model_dump(mode="json", exclude={"metadata": {"build_fingerprint"}}))
        return SimulateOneEventResult(report=report, validation_warnings=report.validation_warnings, validation_errors=report.validation_errors)

    @staticmethod
    def _plan_summary(steps: list[SimulateOneEventStepStatus], stop_reason: str | None, next_action: str | None) -> SimulateOneEventPlanSummary:
        executable = [step for step in steps if step.step not in {"preflight_lifecycle", "final_lifecycle"}]
        first_failed = next((step.step for step in steps if step.status in {"failed", "blocked"}), None)
        return SimulateOneEventPlanSummary(
            planned_step_count=sum(1 for step in executable if step.status == "planned"),
            executed_step_count=sum(1 for step in executable if step.status in {"succeeded", "failed", "blocked", "skipped"}),
            skipped_step_count=sum(1 for step in executable if step.status == "skipped"),
            succeeded_step_count=sum(1 for step in executable if step.status == "succeeded"),
            failed_step_count=sum(1 for step in executable if step.status == "failed"),
            blocked_step_count=sum(1 for step in executable if step.status == "blocked") + sum(1 for step in steps if step.step == "final_lifecycle" and step.status == "blocked"),
            first_failed_step=first_failed,
            stop_reason=stop_reason,
            next_safe_action=SeasonEventSimulationService._next_safe_action(stop_reason, next_action),
        )

    @staticmethod
    def _next_safe_action(stop_reason: str | None, lifecycle_next_action: str | None) -> str | None:
        if stop_reason in {"validation_error", "lifecycle_blocked", "step_failed", "step_blocked", "event_not_complete", "publish_snapshot_requires_apply_points"}:
            return "resolve_blocker"
        if stop_reason == "points_not_applied":
            return "apply_point_awards"
        if stop_reason == "dry_run_plan_only":
            return "run_event_simulation"
        if stop_reason == "already_complete":
            return "review_completed_event"
        return lifecycle_next_action

    @staticmethod
    def _artifact_state(event: EventLifecycleStatus) -> SimulateOneEventArtifactState:
        return SimulateOneEventArtifactState(
            entries_exists=event.entries.exists,
            draw_exists=event.draw.exists,
            matches_exists=event.matches.exists,
            results_exists=event.results.exists,
            point_awards_exists=event.point_awards.exists,
            points_applied=event.points_applied,
            ranking_snapshot_exists=event.ranking_snapshot.exists,
        )

    @staticmethod
    def _any_artifact_exists(state: SimulateOneEventArtifactState) -> bool:
        return any(state.model_dump(mode="json").values())

    @staticmethod
    def _derive_changed_artifacts(before: SimulateOneEventArtifactState, after: SimulateOneEventArtifactState, changed: ChangedArtifacts) -> ChangedArtifacts:
        return ChangedArtifacts(
            entries=changed.entries or before.entries_exists != after.entries_exists,
            draw=changed.draw or before.draw_exists != after.draw_exists,
            matches=changed.matches or before.matches_exists != after.matches_exists,
            results=changed.results or before.results_exists != after.results_exists,
            point_awards=changed.point_awards or before.point_awards_exists != after.point_awards_exists,
            active_player_points=changed.active_player_points or before.points_applied != after.points_applied,
            ranking_snapshot=changed.ranking_snapshot or before.ranking_snapshot_exists != after.ranking_snapshot_exists,
        )

    @staticmethod
    def _decorate_step(step: SimulateOneEventStepStatus) -> SimulateOneEventStepStatus:
        step.mutates_active_players = step.mutates_active_players or step.step == "apply_point_awards"
        step.mutates_ranking_snapshot = step.mutates_ranking_snapshot or step.step == "publish_ranking_snapshot"
        if step.status == "failed" and step.stop_reason is None:
            step.stop_reason = "step_failed"
        if step.status == "blocked" and step.stop_reason is None:
            step.stop_reason = "step_blocked"
        return step

    @staticmethod
    def _service_name(step: SimulateOneEventStep) -> str | None:
        return {
            "preflight_lifecycle": "SeasonEventLifecycleService.get_event_lifecycle",
            "generate_entries": "SeasonEntryListService.generate_entry_list",
            "generate_draw": "SeasonDrawService.generate_draw_package",
            "generate_matches": "SeasonMatchService.generate_match_package",
            "process_byes": "SeasonMatchService.process_byes",
            "simulate_draw": "SeasonMatchService.simulate_draw",
            "refresh_progression": "SeasonMatchService.refresh_progression",
            "extract_results": "SeasonEventResultsService.extract_event_result",
            "generate_point_awards": "SeasonPointAwardsService.generate_event_point_awards",
            "apply_point_awards": "SeasonPointAwardsService.apply_event_point_awards",
            "publish_ranking_snapshot": "SeasonRankingSnapshotService.generate_snapshot",
            "final_lifecycle": "SeasonEventLifecycleService.get_event_lifecycle",
        }.get(step)

    @staticmethod
    def _dry_run_detail(step: SimulateOneEventStep, event: EventLifecycleStatus, request: SimulateOneEventRequest) -> str:
        existing = SeasonEventSimulationService._exists_for_step(event, step)
        if existing and not request.overwrite_existing:
            return "Dry-run plan only; artifact exists and overwrite_existing=false, so an execute run would skip this step."
        if step == "apply_point_awards":
            return "Dry-run plan only; would apply point awards to active season players if not already applied."
        if step == "publish_ranking_snapshot":
            return "Dry-run plan only; would publish the weekly ranking/race snapshot after points are applied."
        return "Dry-run plan only; no mutating service was called."

    @staticmethod
    def _service_step(step: SimulateOneEventStep, detail: str, before: bool | None, fingerprint: str | None, changed_ids: list[str], warnings: list[Any], errors: list[Any], *, status: SimulateOneEventStepResultStatus = "succeeded") -> SimulateOneEventStepStatus:
        normalized_errors = [SeasonEventSimulationService._issue_text(item) for item in errors]
        return SimulateOneEventStepStatus(step=step, status="failed" if normalized_errors else status, action_detail=detail, artifact_exists_before=before, artifact_exists_after=True if before is not None else None, changed_ids=sorted(set(changed_ids)), fingerprint=fingerprint, warnings=[SeasonEventSimulationService._issue_text(item) for item in warnings], errors=normalized_errors)

    @staticmethod
    def _skipped(step: SimulateOneEventStep, detail: str, before: bool | None) -> SimulateOneEventStepStatus:
        return SimulateOneEventStepStatus(step=step, status="skipped", action_detail=detail, artifact_exists_before=before, artifact_exists_after=before)

    @staticmethod
    def _mark_changed(changed: ChangedArtifacts, step: SimulateOneEventStep, status: SimulateOneEventStepStatus) -> None:
        if status.status != "succeeded" or not status.changed_ids:
            return
        mapping = {"generate_entries": "entries", "generate_draw": "draw", "generate_matches": "matches", "extract_results": "results", "generate_point_awards": "point_awards", "apply_point_awards": "active_player_points", "publish_ranking_snapshot": "ranking_snapshot"}
        field = mapping.get(step)
        if field:
            setattr(changed, field, True)
        if step in {"process_byes", "simulate_draw", "refresh_progression"}:
            changed.matches = True

    @staticmethod
    def _derive_seed(base_seed: int, event_id: str, step: str) -> int:
        digest = hashlib.sha256(f"{base_seed}:{event_id}:{step}".encode("utf-8")).hexdigest()
        return int(digest[:12], 16) % 2_147_483_647

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
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def _report(self, *, event: EventLifecycleStatus, request: SimulateOneEventRequest, preflight_fingerprint: str, steps: list[SimulateOneEventStepStatus]) -> SimulateOneEventReport:
        return SimulateOneEventReport(
            event_id=event.event_id,
            season=event.season,
            season_week=event.season_week,
            calendar_year=event.calendar_year,
            year_week=event.year_week,
            event_name=event.event_name,
            seed=request.seed,
            dry_run=request.dry_run,
            requested_apply_points=request.apply_points,
            requested_publish_snapshot=request.publish_snapshot,
            initial_lifecycle=event,
            final_lifecycle=event,
            steps=steps,
            blocked=False,
            metadata=SimulateOneEventMetadata(build_fingerprint="pending", read_only=False, lifecycle_preflight_fingerprint=preflight_fingerprint, final_lifecycle_fingerprint=preflight_fingerprint),
        )
