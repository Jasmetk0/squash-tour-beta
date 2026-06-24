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
