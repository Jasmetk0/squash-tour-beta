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
        if request.publish_snapshot and not request.apply_points:
            validation_errors.append("publish_snapshot=true requires apply_points=true for one-event orchestration.")

        preflight = self.lifecycle_service.get_event_lifecycle(event_id=event_id)
        if preflight.event is None:
            errors = validation_errors + preflight.validation_errors + [f"Unknown persisted calendar event '{event_id}'."]
            return SimulateOneEventResult(report=None, validation_warnings=preflight.validation_warnings, validation_errors=self._dedupe(errors))

        event = preflight.event
        steps = [SimulateOneEventStepStatus(
            step="preflight_lifecycle",
            status="succeeded",
            action_detail=f"Initial lifecycle stage is {event.current_stage}; next action is {event.next_recommended_action}.",
            fingerprint=preflight.metadata.generated_fingerprint,
            warnings=list(event.validation_warnings),
            errors=list(event.validation_errors),
        )]
        report = self._report(event=event, request=request, preflight_fingerprint=preflight.metadata.generated_fingerprint, steps=steps)
        steps = report.steps
        report.validation_warnings.extend(validation_warnings)
        report.validation_errors.extend(validation_errors)

        if validation_errors:
            report.blocked = True
            return SimulateOneEventResult(report=report, validation_warnings=validation_warnings, validation_errors=validation_errors)
        if event.is_blocked and not request.allow_blocked:
            msg = "Lifecycle preflight is blocked; resolve blocker or set allow_blocked=true."
            report.validation_errors.append(msg)
            report.blocked = True
            steps.append(SimulateOneEventStepStatus(step="final_lifecycle", status="blocked", action_detail=msg, fingerprint=preflight.metadata.generated_fingerprint, errors=event.block_reasons or [msg]))
            return SimulateOneEventResult(report=report, validation_warnings=report.validation_warnings, validation_errors=report.validation_errors)
        if event.current_stage == "ranking_snapshot_published":
            report.completed = True
            report.final_lifecycle = event
            steps.append(SimulateOneEventStepStatus(step="final_lifecycle", status="succeeded", action_detail="Event lifecycle is already ranking_snapshot_published; no work required.", fingerprint=preflight.metadata.generated_fingerprint))
            report.metadata.build_fingerprint = self._fingerprint(report.model_dump(mode="json", exclude={"metadata": {"build_fingerprint"}}))
            return SimulateOneEventResult(report=report)

        planned = self._planned_steps(event, request)
        if request.dry_run:
            for step in planned[: request.max_steps]:
                steps.append(SimulateOneEventStepStatus(step=step, status="planned", action_detail="Dry-run plan only; no mutating service was called.", artifact_exists_before=self._exists_for_step(event, step), artifact_exists_after=self._exists_for_step(event, step)))
            report.final_lifecycle = event
            steps.append(SimulateOneEventStepStatus(step="final_lifecycle", status="planned", action_detail="Dry run plan only; final lifecycle equals initial lifecycle.", fingerprint=preflight.metadata.generated_fingerprint))
            report.metadata.final_lifecycle_fingerprint = preflight.metadata.generated_fingerprint
            report.metadata.build_fingerprint = self._fingerprint(report.model_dump(mode="json", exclude={"metadata": {"build_fingerprint"}}))
            return SimulateOneEventResult(report=report)

        executed = 0
        current = event
        for step_name in planned:
            if executed >= request.max_steps:
                warning = f"Stopped after max_steps={request.max_steps}."
                report.validation_warnings.append(warning)
                break
            if self._should_stop(current, request):
                break
            step = self._execute_step(event_id=event_id, step=step_name, request=request, lifecycle=current)
            steps.append(step)
            executed += 1
            self._mark_changed(report.changed_artifacts, step_name, step)
            if step.status in {"failed", "blocked"} or step.errors:
                report.blocked = True
                report.validation_errors.extend(step.errors)
                break
            refreshed = self.lifecycle_service.get_event_lifecycle(event_id=event_id)
            if refreshed.event is not None:
                current = refreshed.event
                if current.is_blocked and not request.allow_blocked:
                    msg = "Lifecycle became blocked after step execution."
                    report.blocked = True
                    report.validation_errors.append(msg)
                    steps.append(SimulateOneEventStepStatus(step="final_lifecycle", status="blocked", action_detail=msg, fingerprint=refreshed.metadata.generated_fingerprint, errors=current.block_reasons or [msg]))
                    report.final_lifecycle = current
                    report.metadata.final_lifecycle_fingerprint = refreshed.metadata.generated_fingerprint
                    report.metadata.build_fingerprint = self._fingerprint(report.model_dump(mode="json", exclude={"metadata": {"build_fingerprint"}}))
                    return SimulateOneEventResult(report=report, validation_warnings=report.validation_warnings, validation_errors=report.validation_errors)

        final = self.lifecycle_service.get_event_lifecycle(event_id=event_id)
        report.final_lifecycle = final.event
        report.metadata.final_lifecycle_fingerprint = final.metadata.generated_fingerprint
        final_status: SimulateOneEventStepResultStatus = "blocked" if report.blocked else "succeeded"
        steps.append(SimulateOneEventStepStatus(step="final_lifecycle", status=final_status, action_detail=f"Final lifecycle stage is {final.event.current_stage if final.event else 'unknown'}.", fingerprint=final.metadata.generated_fingerprint, warnings=final.validation_warnings, errors=final.validation_errors))
        report.completed = bool(final.event and final.event.current_stage in {"points_generated", "points_applied", "ranking_snapshot_published"} and not report.blocked)
        report.metadata.build_fingerprint = self._fingerprint(report.model_dump(mode="json", exclude={"metadata": {"build_fingerprint"}}))
        return SimulateOneEventResult(report=report, validation_warnings=report.validation_warnings, validation_errors=report.validation_errors)

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
                    return SimulateOneEventStepStatus(step=step, status="blocked", action_detail="Event is not complete; allow_incomplete_results=false.", artifact_exists_before=before, artifact_exists_after=before, errors=["Event is not complete; results were not extracted."])
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
                        return SimulateOneEventStepStatus(step=step, status="blocked", action_detail="Points must be applied before publishing a ranking snapshot.", artifact_exists_before=before, artifact_exists_after=before, errors=["Points must be applied before publishing snapshot."])
                    lifecycle = refreshed
                result = self.ranking_snapshot_service.generate_snapshot(season=lifecycle.season, season_week=lifecycle.season_week, request=WeeklyRankingSnapshotGenerateRequest(seed=seed, dry_run=False, overwrite_existing=request.overwrite_existing))
                status = "failed" if result.validation_errors else "succeeded"
                return SimulateOneEventStepStatus(step=step, status=status, action_detail="Published weekly ranking/race snapshot.", artifact_exists_before=before, artifact_exists_after=not result.validation_errors, changed_ids=[f"{lifecycle.season}:{lifecycle.season_week}"], fingerprint=result.metadata.snapshot_fingerprint if result.metadata else None, warnings=result.validation_warnings, errors=result.validation_errors)
        except ValueError as exc:
            return SimulateOneEventStepStatus(step=step, status="failed", action_detail="Step failed in underlying service.", artifact_exists_before=before, artifact_exists_after=before, errors=[str(exc)])
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
