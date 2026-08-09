"""Read-only planning-calendar template apply plan builder."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from beta_engine.application.calendar_template_compare_service import (
    CalendarTemplateCompareDryRunRequest,
    CalendarTemplateCompareService,
)
from beta_engine.application.calendar_template_service import CalendarTemplateEvent, CalendarTemplateService
from beta_engine.application.planning_calendar_apply_audit_service import canonical_json, deterministic_digest
from beta_engine.application.planning_season_calendar_service import PlanningCalendarEvent, PlanningSeasonCalendarService
from beta_engine.domain.calendar.season_labels import normalize_season_label, to_long_season_label

PlanningCalendarApplyTemplatePolicy = Literal["copy_missing_only", "replace_unlocked_only"]
PlanningCalendarApplyPlanAction = Literal["create", "update", "preserve_locked", "skip", "reject"]
REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION = "I understand this will apply reviewed template events to the planning calendar only."


def _digest(prefix: str, payload: Any) -> str:
    return f"{prefix}_{deterministic_digest(payload)[:24]}"


def _clean_text(value: str | None) -> str:
    return value.strip() if isinstance(value, str) else ""


def _identity_key(name: str, category_code: str) -> str:
    normalized_name = re.sub(r"\s+", " ", name.strip().casefold())
    return f"{normalized_name}|{category_code.strip().casefold()}"


def stable_planning_event_id(*, source_template_id: str, source_template_event_id: str) -> str:
    source = f"{source_template_id}__{source_template_event_id}".strip().casefold()
    slug = re.sub(r"[^a-z0-9]+", "_", source).strip("_")
    return f"tpl_{slug or deterministic_digest(source)[:16]}"


class PlanningCalendarApplyTemplatePlanRequest(BaseModel):
    target_season_label: str = Field(min_length=1)
    source_template_id: str = Field(min_length=1)
    policy: PlanningCalendarApplyTemplatePolicy = "copy_missing_only"
    selected_source_event_ids: list[str] | None = None
    expected_planning_calendar_fingerprint: str = Field(min_length=1)
    source_template_fingerprint: str = Field(min_length=1)
    reviewed_diff_fingerprint: str = Field(min_length=1)
    requested_by: str | None = None
    audit_reason: str | None = None
    explicit_confirmation: str | None = None
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def validate_selected_ids_are_unique(self) -> "PlanningCalendarApplyTemplatePlanRequest":
        if self.selected_source_event_ids is not None and len(self.selected_source_event_ids) != len(set(self.selected_source_event_ids)):
            raise ValueError("selected_source_event_ids must contain unique event ids.")
        return self


class PlanningCalendarApplyPlanCounts(BaseModel):
    selected_source_event_count: int = 0
    target_event_count: int = 0
    planned_create_count: int = 0
    planned_update_count: int = 0
    preserved_locked_event_count: int = 0
    skipped_event_count: int = 0
    rejected_event_count: int = 0
    target_only_event_count: int = 0


class PlanningCalendarApplyPlanItem(BaseModel):
    action: PlanningCalendarApplyPlanAction
    source_event_id: str | None = None
    target_event_id: str | None = None
    generated_target_event_id: str | None = None
    event_name: str
    category_code: str
    locked_target: bool = False
    identity_match_type: str
    reason: str
    source_event_fingerprint: str | None = None
    target_event_fingerprint: str | None = None


class PlanningCalendarApplyTemplatePlanResponse(BaseModel):
    command: str = "planning_calendar_apply_template_plan"
    dry_run: bool = True
    read_only: bool = True
    mutation_performed: bool = False
    target_season_label: str
    normalized_target_season_label: str
    source_template_id: str
    policy: PlanningCalendarApplyTemplatePolicy
    before_calendar_fingerprint: str | None = None
    source_template_fingerprint: str | None = None
    reviewed_diff_fingerprint: str | None = None
    recomputed_diff_fingerprint: str | None = None
    apply_plan_fingerprint: str | None = None
    counts: PlanningCalendarApplyPlanCounts = Field(default_factory=PlanningCalendarApplyPlanCounts)
    planned_items: list[PlanningCalendarApplyPlanItem] = Field(default_factory=list)
    skipped_items: list[PlanningCalendarApplyPlanItem] = Field(default_factory=list)
    rejected_items: list[PlanningCalendarApplyPlanItem] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    safety_summary: dict[str, Any] = Field(default_factory=dict)
    status: str = "ok"
    message: str = "Read-only planning calendar apply plan built; no mutation performed."


@dataclass(slots=True)
class PlanningCalendarApplyTemplatePlanService:
    template_service: CalendarTemplateService
    planning_calendar_service: PlanningSeasonCalendarService

    def build_plan(self, request: PlanningCalendarApplyTemplatePlanRequest) -> PlanningCalendarApplyTemplatePlanResponse:
        normalized_target = to_long_season_label(normalize_season_label(request.target_season_label))
        source_template = self.template_service.get_template(template_id=request.source_template_id).template
        if source_template is None:
            raise KeyError(request.source_template_id)
        target_calendar = self.planning_calendar_service.get_calendar(request.target_season_label)
        if target_calendar is None:
            raise KeyError(request.target_season_label)

        source_events = list(source_template.events)
        selected_ids = request.selected_source_event_ids
        validation_errors: list[str] = []
        validation_warnings: list[str] = []

        by_source_id = {event.id: event for event in source_events}
        if selected_ids is not None:
            missing_ids = [event_id for event_id in selected_ids if event_id not in by_source_id]
            if missing_ids:
                validation_errors.append(f"Unknown selected_source_event_id: {missing_ids[0]}")
            selected_set = set(selected_ids)
            selected_events = [event for event in source_events if event.id in selected_set]
        else:
            selected_events = source_events

        if request.source_template_fingerprint != source_template.template_fingerprint:
            validation_errors.append("source_template_fingerprint does not match the current source template fingerprint.")
        if request.expected_planning_calendar_fingerprint != target_calendar.calendar_fingerprint:
            validation_errors.append("expected_planning_calendar_fingerprint does not match the current planning calendar fingerprint.")
        if not _clean_text(request.requested_by):
            validation_errors.append("requested_by is required.")
        if not _clean_text(request.audit_reason):
            validation_errors.append("audit_reason is required.")
        if not _clean_text(request.explicit_confirmation):
            validation_errors.append("explicit_confirmation is required.")
        elif request.explicit_confirmation != REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION:
            validation_errors.append("explicit_confirmation does not match the required confirmation text.")

        recomputed_diff_fingerprint: str | None = None
        try:
            recomputed_diff_fingerprint = self._recompute_diff_fingerprint(request)
        except ValueError as exc:
            validation_errors.append(str(exc))
        if recomputed_diff_fingerprint is not None and request.reviewed_diff_fingerprint != recomputed_diff_fingerprint:
            validation_errors.append("reviewed_diff_fingerprint does not match the current server-side diff fingerprint.")

        planned_items, skipped_items, rejected_items, identity_errors = self._build_items(
            source_template_id=source_template.id,
            selected_events=selected_events,
            target_events=list(target_calendar.events),
            policy=request.policy,
        )
        validation_errors.extend(identity_errors)

        counts = PlanningCalendarApplyPlanCounts(
            selected_source_event_count=len(selected_events),
            target_event_count=len(target_calendar.events),
            planned_create_count=sum(1 for item in planned_items if item.action == "create"),
            planned_update_count=sum(1 for item in planned_items if item.action == "update"),
            preserved_locked_event_count=sum(1 for item in skipped_items if item.action == "preserve_locked"),
            skipped_event_count=sum(1 for item in skipped_items if item.action == "skip"),
            rejected_event_count=len(rejected_items) + len(identity_errors),
            target_only_event_count=self._target_only_count(
                source_template_id=source_template.id,
                selected_events=selected_events,
                target_events=list(target_calendar.events),
            ),
        )
        status = "rejected" if validation_errors else "ok"
        plan_payload = {
            "target_season_label": normalized_target,
            "source_template_id": request.source_template_id,
            "policy": request.policy,
            "selected_source_event_ids": selected_ids or [event.id for event in source_events],
            "before_calendar_fingerprint": target_calendar.calendar_fingerprint,
            "source_template_fingerprint": source_template.template_fingerprint,
            "reviewed_diff_fingerprint": request.reviewed_diff_fingerprint,
            "recomputed_diff_fingerprint": recomputed_diff_fingerprint,
            "counts": counts.model_dump(mode="json"),
            "planned_items": [item.model_dump(mode="json") for item in planned_items],
            "skipped_items": [item.model_dump(mode="json") for item in skipped_items],
            "rejected_items": [item.model_dump(mode="json") for item in rejected_items],
            "validation_errors": validation_errors,
            "phase": "read_only_plan",
        }
        safety = {
            "backend_only_application_service": True,
            "read_only": True,
            "mutation_performed": False,
            "planning_calendar_modified": False,
            "canonical_season_calendar_modified": False,
            "viewer_visible": False,
            "simulation_invoked": False,
            "planning_to_simulation_adapter": False,
            "replace_all_supported": False,
            "message": "Read-only apply planning only; no calendar files were modified.",
        }
        return PlanningCalendarApplyTemplatePlanResponse(
            target_season_label=request.target_season_label,
            normalized_target_season_label=normalized_target,
            source_template_id=request.source_template_id,
            policy=request.policy,
            before_calendar_fingerprint=target_calendar.calendar_fingerprint,
            source_template_fingerprint=source_template.template_fingerprint,
            reviewed_diff_fingerprint=request.reviewed_diff_fingerprint,
            recomputed_diff_fingerprint=recomputed_diff_fingerprint,
            apply_plan_fingerprint=_digest("plan", plan_payload),
            counts=counts,
            planned_items=planned_items,
            skipped_items=skipped_items,
            rejected_items=rejected_items,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            safety_summary=safety,
            status=status,
            message="Planning calendar apply plan rejected; no mutation performed." if validation_errors else "Read-only planning calendar apply plan built; no mutation performed.",
        )

    def _recompute_diff_fingerprint(self, request: PlanningCalendarApplyTemplatePlanRequest) -> str:
        compare_request = CalendarTemplateCompareDryRunRequest(
            target_season_label=request.target_season_label,
            source_template_id=request.source_template_id,
            target_source="planning_calendar",
            selected_source_event_ids=request.selected_source_event_ids,
            policy=request.policy,
        )
        return CalendarTemplateCompareService(
            template_service=self.template_service,
            planning_calendar_service=self.planning_calendar_service,
        ).compare_dry_run(compare_request).diff_fingerprint

    def _build_items(
        self,
        *,
        source_template_id: str,
        selected_events: list[CalendarTemplateEvent],
        target_events: list[PlanningCalendarEvent],
        policy: PlanningCalendarApplyTemplatePolicy,
    ) -> tuple[list[PlanningCalendarApplyPlanItem], list[PlanningCalendarApplyPlanItem], list[PlanningCalendarApplyPlanItem], list[str]]:
        planned: list[PlanningCalendarApplyPlanItem] = []
        skipped: list[PlanningCalendarApplyPlanItem] = []
        rejected: list[PlanningCalendarApplyPlanItem] = []
        errors: list[str] = []
        target_by_provenance: dict[tuple[str, str], list[PlanningCalendarEvent]] = {}
        target_by_id = {event.id: event for event in target_events}
        target_by_name_category: dict[str, list[PlanningCalendarEvent]] = {}
        for event in target_events:
            if event.source_template_id and event.source_template_event_id:
                target_by_provenance.setdefault((event.source_template_id, event.source_template_event_id), []).append(event)
            target_by_name_category.setdefault(_identity_key(event.name, event.category_code), []).append(event)

        selected_identity_keys: dict[str, list[CalendarTemplateEvent]] = {}
        for event in selected_events:
            selected_identity_keys.setdefault(_identity_key(event.name, event.category_code), []).append(event)
        for key, events in selected_identity_keys.items():
            if len(events) > 1:
                errors.append(f"Ambiguous source identity for normalized name/category: {key}")

        for source in selected_events:
            generated_id = stable_planning_event_id(source_template_id=source_template_id, source_template_event_id=source.id)
            match, match_type, match_errors = self._match_target(
                source_template_id=source_template_id,
                source_event=source,
                generated_id=generated_id,
                target_by_provenance=target_by_provenance,
                target_by_id=target_by_id,
                target_by_name_category=target_by_name_category,
            )
            errors.extend(match_errors)
            if match_errors:
                rejected.append(self._item("reject", source, match, generated_id, match_type, "; ".join(match_errors)))
                continue
            if match is None:
                planned.append(self._item("create", source, None, generated_id, "generated_target_id", "Source event is missing from the planning calendar and would be created."))
                continue
            if match.locked:
                skipped.append(self._item("preserve_locked", source, match, generated_id, match_type, "Matching target event is locked and would be preserved."))
                continue
            if match_type == "name_category_detection_only":
                skipped.append(self._item("skip", source, match, generated_id, match_type, "Possible target event detected by name/category only; read-only plan will not authorize updates without strong identity."))
                continue
            if policy == "copy_missing_only":
                skipped.append(self._item("skip", source, match, generated_id, match_type, "Target event already exists; copy_missing_only would not update it."))
            else:
                planned.append(self._item("update", source, match, generated_id, match_type, "Unlocked strong-identity target event would be updated."))
        return planned, skipped, rejected, errors

    def _match_target(
        self,
        *,
        source_template_id: str,
        source_event: CalendarTemplateEvent,
        generated_id: str,
        target_by_provenance: dict[tuple[str, str], list[PlanningCalendarEvent]],
        target_by_id: dict[str, PlanningCalendarEvent],
        target_by_name_category: dict[str, list[PlanningCalendarEvent]],
    ) -> tuple[PlanningCalendarEvent | None, str, list[str]]:
        errors: list[str] = []
        provenance_matches = target_by_provenance.get((source_template_id, source_event.id), [])
        if len(provenance_matches) > 1:
            return None, "source_provenance", [f"Ambiguous target identity for source event {source_event.id}: multiple provenance matches."]
        generated_match = target_by_id.get(generated_id)
        if provenance_matches and generated_match is not None and generated_match.id != provenance_matches[0].id:
            return None, "conflicting_generated_id", [f"Ambiguous target identity for source event {source_event.id}: provenance and generated id match different events."]
        if provenance_matches:
            return provenance_matches[0], "source_provenance", []
        if generated_match is not None:
            if generated_match.source_template_id and generated_match.source_template_id != source_template_id:
                errors.append(f"Generated target id {generated_id} has conflicting source_template_id.")
            if generated_match.source_template_event_id and generated_match.source_template_event_id != source_event.id:
                errors.append(f"Generated target id {generated_id} has conflicting source_template_event_id.")
            return generated_match if not errors else None, "generated_target_id", errors
        name_matches = target_by_name_category.get(_identity_key(source_event.name, source_event.category_code), [])
        if len(name_matches) > 1:
            return None, "name_category_detection_only", [f"Ambiguous target identity for source event {source_event.id}: multiple name/category matches."]
        if len(name_matches) == 1:
            return name_matches[0], "name_category_detection_only", []
        return None, "none", []

    def _item(
        self,
        action: PlanningCalendarApplyPlanAction,
        source: CalendarTemplateEvent,
        target: PlanningCalendarEvent | None,
        generated_id: str,
        identity_match_type: str,
        reason: str,
    ) -> PlanningCalendarApplyPlanItem:
        return PlanningCalendarApplyPlanItem(
            action=action,
            source_event_id=source.id,
            target_event_id=target.id if target is not None else None,
            generated_target_event_id=generated_id,
            event_name=source.name,
            category_code=source.category_code,
            locked_target=bool(target.locked) if target is not None else False,
            identity_match_type=identity_match_type,
            reason=reason,
            source_event_fingerprint=source.event_fingerprint,
            target_event_fingerprint=target.event_fingerprint if target is not None else None,
        )

    def _target_only_count(
        self,
        *,
        source_template_id: str,
        selected_events: list[CalendarTemplateEvent],
        target_events: list[PlanningCalendarEvent],
    ) -> int:
        selected_keys = {(source_template_id, event.id) for event in selected_events}
        selected_generated_ids = {stable_planning_event_id(source_template_id=source_template_id, source_template_event_id=event.id) for event in selected_events}
        count = 0
        for target in target_events:
            provenance_key = (target.source_template_id, target.source_template_event_id)
            if provenance_key in selected_keys or target.id in selected_generated_ids:
                continue
            count += 1
        return count


def request_payload_fingerprint(request: PlanningCalendarApplyTemplatePlanRequest) -> str:
    return _digest("req", request.model_dump(mode="json"))


def response_payload_fingerprint(response: PlanningCalendarApplyTemplatePlanResponse) -> str:
    return _digest("resp", response.model_dump(mode="json"))


class PlanningCalendarApplyTemplateCommandRequest(BaseModel):
    source_template_id: str = Field(min_length=1)
    policy: str = "copy_missing_only"
    selected_source_event_ids: list[str] | None = None
    expected_planning_calendar_fingerprint: str = Field(min_length=1)
    source_template_fingerprint: str = Field(min_length=1)
    reviewed_diff_fingerprint: str = Field(min_length=1)
    requested_by: str | None = None
    audit_reason: str | None = None
    explicit_confirmation: str | None = None
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def validate_selected_ids_are_unique(self) -> "PlanningCalendarApplyTemplateCommandRequest":
        if self.selected_source_event_ids is not None and len(self.selected_source_event_ids) != len(set(self.selected_source_event_ids)):
            raise ValueError("selected_source_event_ids must contain unique event ids.")
        return self

    def to_plan_request(self, *, target_season_label: str) -> PlanningCalendarApplyTemplatePlanRequest | None:
        if self.policy not in {"copy_missing_only", "replace_unlocked_only"}:
            return None
        return PlanningCalendarApplyTemplatePlanRequest(
            target_season_label=target_season_label,
            source_template_id=self.source_template_id,
            policy=self.policy,  # type: ignore[arg-type]
            selected_source_event_ids=self.selected_source_event_ids,
            expected_planning_calendar_fingerprint=self.expected_planning_calendar_fingerprint,
            source_template_fingerprint=self.source_template_fingerprint,
            reviewed_diff_fingerprint=self.reviewed_diff_fingerprint,
            requested_by=self.requested_by,
            audit_reason=self.audit_reason,
            explicit_confirmation=self.explicit_confirmation,
            idempotency_key=self.idempotency_key,
        )


class PlanningCalendarApplyBackupResult(BaseModel):
    backup_persisted: bool = True
    backup_path: str
    backup_storage_summary: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class PlanningCalendarApplyBackupService:
    backup_dir: Any = "config/simulation/planning_calendar_apply_backups"

    def __post_init__(self) -> None:
        from pathlib import Path

        if not isinstance(self.backup_dir, Path):
            self.backup_dir = Path(self.backup_dir)

    @classmethod
    def for_planning_registry_path(cls, planning_registry_path: str | Any | None) -> "PlanningCalendarApplyBackupService":
        from pathlib import Path

        if planning_registry_path is None:
            return cls()
        registry_path = Path(planning_registry_path)
        return cls(backup_dir=registry_path.parent / "planning_calendar_apply_backups")

    def write_before_backup(
        self,
        *,
        audit_record_id: str,
        created_at: str,
        normalized_target_season_label: str,
        before_calendar_fingerprint: str,
        calendar: Any,
    ) -> PlanningCalendarApplyBackupResult:
        season_slug = re.sub(r"[^0-9A-Za-z]+", "-", normalized_target_season_label).strip("-")
        backup_path = self.backup_dir / season_slug / f"{audit_record_id}.before.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "backup_schema_version": "planning_calendar_apply_before_backup.v1",
            "audit_record_id": audit_record_id,
            "created_at": created_at,
            "normalized_target_season_label": normalized_target_season_label,
            "before_calendar_fingerprint": before_calendar_fingerprint,
            "calendar": calendar.model_dump(mode="json"),
        }
        backup_path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        return PlanningCalendarApplyBackupResult(
            backup_path=str(backup_path),
            backup_storage_summary={
                "backend": "json_file",
                "filename": backup_path.name,
                "directory_name": backup_path.parent.name,
            },
        )


class PlanningCalendarApplyTemplateCommandResponse(BaseModel):
    command: str = "planning_calendar_apply_template"
    applied: bool = False
    mutation_performed: bool = False
    target_season_label: str
    normalized_target_season_label: str
    source_template_id: str
    policy: str
    audit_record_id: str | None = None
    audit_record_fingerprint: str | None = None
    audit_persisted: bool = False
    audit_persistence_status: str = "not_attempted"
    before_calendar_fingerprint: str | None = None
    after_calendar_fingerprint: str | None = None
    source_template_fingerprint: str | None = None
    reviewed_diff_fingerprint: str | None = None
    recomputed_diff_fingerprint: str | None = None
    apply_plan_fingerprint: str | None = None
    applied_event_count: int = 0
    created_event_count: int = 0
    updated_event_count: int = 0
    preserved_locked_event_count: int = 0
    skipped_event_count: int = 0
    rejected_event_count: int = 0
    created_items: list[PlanningCalendarApplyPlanItem] = Field(default_factory=list)
    updated_items: list[PlanningCalendarApplyPlanItem] = Field(default_factory=list)
    preserved_locked_items: list[PlanningCalendarApplyPlanItem] = Field(default_factory=list)
    skipped_items: list[PlanningCalendarApplyPlanItem] = Field(default_factory=list)
    rejected_items: list[PlanningCalendarApplyPlanItem] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    safety_summary: dict[str, Any] = Field(default_factory=dict)
    message: str = "Planning calendar apply command did not mutate."


@dataclass(slots=True)
class PlanningCalendarApplyTemplateCommandService:
    template_service: CalendarTemplateService
    planning_calendar_service: PlanningSeasonCalendarService
    audit_service: Any
    backup_service: PlanningCalendarApplyBackupService

    def apply_template(
        self,
        *,
        target_season_label: str,
        request: PlanningCalendarApplyTemplateCommandRequest,
    ) -> PlanningCalendarApplyTemplateCommandResponse:
        from beta_engine.application.planning_calendar_apply_audit_service import (
            PlanningCalendarApplyAuditRecord,
            build_audit_record_id,
            utc_now_iso,
        )
        from beta_engine.application.planning_season_calendar_service import (
            PlanningCalendarEvent,
            PlanningCalendarEventApplyMetadata,
            PlanningSeasonCalendar,
        )

        normalized_target = to_long_season_label(normalize_season_label(target_season_label))
        attempted_at = utc_now_iso()
        request_fp = request_payload_fingerprint_for_command(target_season_label=target_season_label, request=request)
        audit_record_id = build_audit_record_id(attempted_at=attempted_at, request_payload_fingerprint=request_fp)

        source_template = self.template_service.get_template(template_id=request.source_template_id).template
        if source_template is None:
            raise KeyError(request.source_template_id)
        before_calendar = self.planning_calendar_service.get_calendar(target_season_label)
        if before_calendar is None:
            raise KeyError(target_season_label)

        validation_errors: list[str] = []
        plan: PlanningCalendarApplyTemplatePlanResponse | None = None
        if request.policy != "copy_missing_only":
            validation_errors.append(f"policy '{request.policy}' is not supported for real apply in this phase; only copy_missing_only is enabled.")
        plan_request = request.to_plan_request(target_season_label=target_season_label)
        if plan_request is None:
            validation_errors.append(f"policy '{request.policy}' is not supported.")
        else:
            plan = PlanningCalendarApplyTemplatePlanService(
                template_service=self.template_service,
                planning_calendar_service=self.planning_calendar_service,
            ).build_plan(plan_request)
            validation_errors.extend(plan.validation_errors)
        if plan is not None:
            illegal_actions = [item.action for item in plan.planned_items if item.action != "create"]
            if illegal_actions:
                validation_errors.append("copy_missing_only apply may only execute create plan actions.")
            if not validation_errors and plan.counts.planned_create_count == 0:
                validation_errors.append("copy_missing_only apply found no missing source events to create; no mutation performed.")

        base_response = self._response(
            target_season_label=target_season_label,
            normalized_target=normalized_target,
            request=request,
            audit_record_id=audit_record_id,
            before_calendar_fingerprint=before_calendar.calendar_fingerprint,
            source_template_fingerprint=source_template.template_fingerprint,
            plan=plan,
            validation_errors=validation_errors,
            audit_persisted=False,
            audit_persistence_status="not_attempted",
            safety_overrides={},
        )
        if validation_errors:
            return self._audit_rejected(
                attempted_at=attempted_at,
                audit_record_id=audit_record_id,
                request_fp=request_fp,
                request=request,
                response=base_response,
                before_calendar_fingerprint=before_calendar.calendar_fingerprint,
                source_template_fingerprint=source_template.template_fingerprint,
                plan=plan,
            )

        pre_record = self._audit_record(
            audit_record_id=audit_record_id,
            attempted_at=attempted_at,
            audit_stage="pre_mutation_reserved",
            request_fp=request_fp,
            request=request,
            response=None,
            target_season_label=target_season_label,
            normalized_target=normalized_target,
            before_calendar_fingerprint=before_calendar.calendar_fingerprint,
            after_calendar_fingerprint=None,
            source_template_fingerprint=source_template.template_fingerprint,
            plan=plan,
        )
        try:
            pre_write = self.audit_service.append_record(pre_record)
        except Exception:
            return self._response(
                target_season_label=target_season_label,
                normalized_target=normalized_target,
                request=request,
                audit_record_id=audit_record_id,
                before_calendar_fingerprint=before_calendar.calendar_fingerprint,
                source_template_fingerprint=source_template.template_fingerprint,
                plan=plan,
                validation_errors=["audit pre-write failed before mutation; no mutation performed."],
                audit_persisted=False,
                audit_persistence_status="failed_closed_before_mutation",
                safety_overrides={"audit_prewrite_succeeded": False},
            )

        try:
            backup_result = self.backup_service.write_before_backup(
                audit_record_id=audit_record_id,
                created_at=attempted_at,
                normalized_target_season_label=normalized_target,
                before_calendar_fingerprint=before_calendar.calendar_fingerprint or "",
                calendar=before_calendar,
            )
        except Exception:
            response = self._response(
                target_season_label=target_season_label,
                normalized_target=normalized_target,
                request=request,
                audit_record_id=audit_record_id,
                before_calendar_fingerprint=before_calendar.calendar_fingerprint,
                source_template_fingerprint=source_template.template_fingerprint,
                plan=plan,
                validation_errors=["before-state backup failed before mutation; no mutation performed."],
                audit_persisted=True,
                audit_persistence_status=pre_write.audit_persistence_status,
                audit_record_fingerprint=pre_write.audit_record_fingerprint,
                safety_overrides={"audit_prewrite_succeeded": True, "before_backup_succeeded": False},
            )
            self._append_rejected_after_reservation(attempted_at, audit_record_id, request_fp, request, response, before_calendar.calendar_fingerprint, source_template.template_fingerprint, plan)
            return response

        current_calendar = self.planning_calendar_service.get_calendar(target_season_label)
        if current_calendar is None or current_calendar.calendar_fingerprint != request.expected_planning_calendar_fingerprint:
            response = self._response(
                target_season_label=target_season_label,
                normalized_target=normalized_target,
                request=request,
                audit_record_id=audit_record_id,
                before_calendar_fingerprint=before_calendar.calendar_fingerprint,
                source_template_fingerprint=source_template.template_fingerprint,
                plan=plan,
                validation_errors=["expected_planning_calendar_fingerprint changed after audit reservation; no mutation performed."],
                audit_persisted=True,
                audit_persistence_status=pre_write.audit_persistence_status,
                audit_record_fingerprint=pre_write.audit_record_fingerprint,
                safety_overrides={"audit_prewrite_succeeded": True, "before_backup_succeeded": True},
            )
            self._append_rejected_after_reservation(attempted_at, audit_record_id, request_fp, request, response, before_calendar.calendar_fingerprint, source_template.template_fingerprint, plan)
            return response

        source_by_id = {event.id: event for event in source_template.events}
        created_events = []
        assert plan is not None
        for item in plan.planned_items:
            if item.action != "create" or item.source_event_id is None:
                continue
            source_event = source_by_id[item.source_event_id]
            created_events.append(
                PlanningCalendarEvent(
                    id=item.generated_target_event_id or stable_planning_event_id(source_template_id=source_template.id, source_template_event_id=source_event.id),
                    name=source_event.name,
                    category_code=source_event.category_code,
                    weeks=list(source_event.weeks),
                    qualification_weeks=list(source_event.qualification_weeks),
                    locked=source_event.locked,
                    country_code=source_event.country_code,
                    city=source_event.city,
                    venue=source_event.venue,
                    notes=source_event.notes,
                    source_template_id=source_template.id,
                    source_template_fingerprint=source_template.template_fingerprint,
                    source_template_event_id=source_event.id,
                    source_template_event_fingerprint=source_event.event_fingerprint,
                    apply_metadata=PlanningCalendarEventApplyMetadata(
                        last_applied_at=attempted_at,
                        last_applied_by=request.requested_by,
                        last_apply_command_id=audit_record_id,
                        last_apply_audit_record_id=audit_record_id,
                        last_apply_policy=request.policy,
                        last_source_template_fingerprint=source_template.template_fingerprint,
                    ),
                )
            )
        next_calendar = PlanningSeasonCalendar.model_validate(
            current_calendar.model_dump(mode="json") | {"events": [event.model_dump(mode="json") for event in current_calendar.events + created_events]}
        )
        saved = self.planning_calendar_service.save_calendar(next_calendar)
        reloaded = self.planning_calendar_service.get_calendar(normalized_target) or saved

        success_response = self._response(
            target_season_label=target_season_label,
            normalized_target=normalized_target,
            request=request,
            audit_record_id=audit_record_id,
            before_calendar_fingerprint=before_calendar.calendar_fingerprint,
            after_calendar_fingerprint=reloaded.calendar_fingerprint,
            source_template_fingerprint=source_template.template_fingerprint,
            plan=plan,
            validation_errors=[],
            audit_persisted=True,
            audit_persistence_status=pre_write.audit_persistence_status,
            audit_record_fingerprint=pre_write.audit_record_fingerprint,
            safety_overrides={"audit_prewrite_succeeded": True, "before_backup_succeeded": backup_result.backup_persisted, "planning_calendar_modified": True},
            applied=True,
            mutation_performed=True,
            created_items=[item for item in plan.planned_items if item.action == "create"],
        )
        success_record = self._audit_record(
            audit_record_id=audit_record_id,
            attempted_at=attempted_at,
            audit_stage="succeeded",
            request_fp=request_fp,
            request=request,
            response=success_response,
            target_season_label=target_season_label,
            normalized_target=normalized_target,
            before_calendar_fingerprint=before_calendar.calendar_fingerprint,
            after_calendar_fingerprint=reloaded.calendar_fingerprint,
            source_template_fingerprint=source_template.template_fingerprint,
            plan=plan,
        )
        success_write = self.audit_service.append_record(success_record)
        return success_response.model_copy(update={"audit_record_fingerprint": success_write.audit_record_fingerprint})

    def _audit_rejected(self, *, attempted_at: str, audit_record_id: str, request_fp: str, request: PlanningCalendarApplyTemplateCommandRequest, response: PlanningCalendarApplyTemplateCommandResponse, before_calendar_fingerprint: str | None, source_template_fingerprint: str | None, plan: PlanningCalendarApplyTemplatePlanResponse | None) -> PlanningCalendarApplyTemplateCommandResponse:
        record = self._audit_record(
            audit_record_id=audit_record_id,
            attempted_at=attempted_at,
            audit_stage="rejected",
            request_fp=request_fp,
            request=request,
            response=response,
            target_season_label=response.target_season_label,
            normalized_target=response.normalized_target_season_label,
            before_calendar_fingerprint=before_calendar_fingerprint,
            after_calendar_fingerprint=None,
            source_template_fingerprint=source_template_fingerprint,
            plan=plan,
        )
        try:
            write = self.audit_service.append_record(record)
            return response.model_copy(update={"audit_persisted": True, "audit_persistence_status": write.audit_persistence_status, "audit_record_fingerprint": write.audit_record_fingerprint})
        except Exception:
            return response.model_copy(update={"audit_persisted": False, "audit_persistence_status": "failed_to_persist_rejection"})

    def _append_rejected_after_reservation(self, attempted_at: str, audit_record_id: str, request_fp: str, request: PlanningCalendarApplyTemplateCommandRequest, response: PlanningCalendarApplyTemplateCommandResponse, before_calendar_fingerprint: str | None, source_template_fingerprint: str | None, plan: PlanningCalendarApplyTemplatePlanResponse | None) -> None:
        try:
            self.audit_service.append_record(
                self._audit_record(
                    audit_record_id=audit_record_id,
                    attempted_at=attempted_at,
                    audit_stage="rejected",
                    request_fp=request_fp,
                    request=request,
                    response=response,
                    target_season_label=response.target_season_label,
                    normalized_target=response.normalized_target_season_label,
                    before_calendar_fingerprint=before_calendar_fingerprint,
                    after_calendar_fingerprint=None,
                    source_template_fingerprint=source_template_fingerprint,
                    plan=plan,
                )
            )
        except Exception:
            return

    def _response(self, *, target_season_label: str, normalized_target: str, request: PlanningCalendarApplyTemplateCommandRequest, audit_record_id: str, before_calendar_fingerprint: str | None, source_template_fingerprint: str | None, plan: PlanningCalendarApplyTemplatePlanResponse | None, validation_errors: list[str], audit_persisted: bool, audit_persistence_status: str, audit_record_fingerprint: str | None = None, after_calendar_fingerprint: str | None = None, safety_overrides: dict[str, Any] | None = None, applied: bool = False, mutation_performed: bool = False, created_items: list[PlanningCalendarApplyPlanItem] | None = None) -> PlanningCalendarApplyTemplateCommandResponse:
        created = created_items or []
        skipped = plan.skipped_items if plan is not None else []
        rejected = plan.rejected_items if plan is not None else []
        preserved_locked = [item for item in skipped if item.action == "preserve_locked"]
        ordinary_skipped = [item for item in skipped if item.action == "skip"]
        safety = {
            "planning_only": True,
            "viewer_visible": False,
            "simulation_consumed": False,
            "canonical_season_calendar_modified": False,
            "season_calendars_json_modified": False,
            "planning_calendar_modified": mutation_performed,
            "audit_prewrite_required": True,
            "audit_prewrite_succeeded": False,
            "before_backup_required": True,
            "before_backup_succeeded": False,
            "replace_all_blocked": True,
            "replace_unlocked_only_blocked_in_this_phase": True,
        }
        safety.update(safety_overrides or {})
        return PlanningCalendarApplyTemplateCommandResponse(
            applied=applied,
            mutation_performed=mutation_performed,
            target_season_label=target_season_label,
            normalized_target_season_label=normalized_target,
            source_template_id=request.source_template_id,
            policy=request.policy,
            audit_record_id=audit_record_id,
            audit_record_fingerprint=audit_record_fingerprint,
            audit_persisted=audit_persisted,
            audit_persistence_status=audit_persistence_status,
            before_calendar_fingerprint=before_calendar_fingerprint,
            after_calendar_fingerprint=after_calendar_fingerprint or before_calendar_fingerprint,
            source_template_fingerprint=source_template_fingerprint,
            reviewed_diff_fingerprint=request.reviewed_diff_fingerprint,
            recomputed_diff_fingerprint=plan.recomputed_diff_fingerprint if plan is not None else None,
            apply_plan_fingerprint=plan.apply_plan_fingerprint if plan is not None else None,
            applied_event_count=len(created),
            created_event_count=len(created),
            updated_event_count=0,
            preserved_locked_event_count=len(preserved_locked),
            skipped_event_count=len(ordinary_skipped),
            rejected_event_count=(plan.counts.rejected_event_count if plan is not None else 0) + len(validation_errors),
            created_items=created,
            updated_items=[],
            preserved_locked_items=preserved_locked,
            skipped_items=ordinary_skipped,
            rejected_items=rejected,
            validation_errors=validation_errors,
            validation_warnings=plan.validation_warnings if plan is not None else [],
            safety_summary=safety,
            message="Applied missing template events to planning calendar only." if mutation_performed else "Planning calendar apply rejected; no mutation performed.",
        )

    def _audit_record(self, *, audit_record_id: str, attempted_at: str, audit_stage: str, request_fp: str, request: PlanningCalendarApplyTemplateCommandRequest, response: PlanningCalendarApplyTemplateCommandResponse | None, target_season_label: str, normalized_target: str, before_calendar_fingerprint: str | None, after_calendar_fingerprint: str | None, source_template_fingerprint: str | None, plan: PlanningCalendarApplyTemplatePlanResponse | None) -> Any:
        from beta_engine.application.planning_calendar_apply_audit_service import PlanningCalendarApplyAuditRecord

        skipped_payload = [item.model_dump(mode="json") for item in (plan.skipped_items if plan else [])]
        rejected_payload = [item.model_dump(mode="json") for item in (plan.rejected_items if plan else [])]
        return PlanningCalendarApplyAuditRecord(
            audit_record_id=audit_record_id,
            attempted_at=attempted_at,
            audit_stage=audit_stage,  # type: ignore[arg-type]
            read_only=False,
            target_season_label=target_season_label,
            normalized_target_season_label=normalized_target,
            source_template_id=request.source_template_id,
            policy=request.policy,
            selected_source_event_ids_fingerprint=_digest("selected", request.selected_source_event_ids or []),
            expected_planning_calendar_fingerprint=request.expected_planning_calendar_fingerprint,
            before_calendar_fingerprint=before_calendar_fingerprint,
            after_calendar_fingerprint=after_calendar_fingerprint,
            source_template_fingerprint_requested=request.source_template_fingerprint,
            source_template_fingerprint_recomputed=source_template_fingerprint,
            reviewed_diff_fingerprint_requested=request.reviewed_diff_fingerprint,
            reviewed_diff_fingerprint_recomputed=plan.recomputed_diff_fingerprint if plan else None,
            apply_plan_fingerprint=plan.apply_plan_fingerprint if plan else None,
            counts=plan.counts.model_dump(mode="json") if plan else {},
            skipped_items_fingerprint=_digest("skip", skipped_payload),
            rejected_items_fingerprint=_digest("reject", rejected_payload),
            requested_by=request.requested_by,
            audit_reason=request.audit_reason,
            explicit_confirmation_present=bool(_clean_text(request.explicit_confirmation)),
            explicit_confirmation_valid=request.explicit_confirmation == REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION,
            validation_errors=response.validation_errors if response is not None else [],
            validation_warnings=response.validation_warnings if response is not None else [],
            request_payload_fingerprint=request_fp,
            response_payload_fingerprint=_digest("resp", response.model_dump(mode="json")) if response is not None else None,
            idempotency_key=request.idempotency_key,
        )


def request_payload_fingerprint_for_command(*, target_season_label: str, request: PlanningCalendarApplyTemplateCommandRequest) -> str:
    return _digest("req", {"target_season_label": target_season_label, "request": request.model_dump(mode="json")})
