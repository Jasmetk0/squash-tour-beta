"""Read-only apply-contract readiness for Admin calendar templates."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from beta_engine.application.calendar_template_service import CalendarTemplateService
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.domain.calendar.season_labels import normalize_season_label, to_long_season_label

CalendarTemplateApplyPolicy = Literal["replace_unlocked_only", "copy_missing_only", "replace_all"]
REQUIRED_CALENDAR_TEMPLATE_APPLY_CONFIRMATION = "I understand this will apply reviewed template events to the canonical season calendar."


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _digest(prefix: str, payload: Any) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()[:24]}"


class CalendarTemplateApplyContractReadinessRequest(BaseModel):
    target_season_label: str = Field(min_length=1)
    source_template_id: str = Field(min_length=1)
    policy: CalendarTemplateApplyPolicy = "replace_unlocked_only"
    selected_source_event_ids: list[str] | None = None
    reviewed_diff_fingerprint: str | None = None
    source_template_fingerprint: str | None = None
    target_fingerprint: str | None = None
    requested_by: str | None = None
    audit_reason: str | None = None
    explicit_confirmation: str | None = None
    mutation_scope: str | None = None

    @model_validator(mode="after")
    def validate_selected_ids_are_unique(self) -> "CalendarTemplateApplyContractReadinessRequest":
        if self.selected_source_event_ids is not None and len(self.selected_source_event_ids) != len(set(self.selected_source_event_ids)):
            raise ValueError("selected_source_event_ids must contain unique event ids.")
        return self


class CalendarTemplateApplyContractReadinessResponse(BaseModel):
    command: str = "calendar_template_apply_contract_readiness"
    enabled: bool = False
    can_execute: bool = False
    can_mutate: bool = False
    dry_run: bool = True
    mutation_performed: bool = False
    target_season_label: str
    normalized_target_season_label: str
    source_template_id: str
    policy: CalendarTemplateApplyPolicy
    source_template_fingerprint: str | None = None
    target_calendar_exists: bool = False
    target_fingerprint: str | None = None
    reviewed_diff_fingerprint: str | None = None
    readiness_summary: dict[str, Any] = Field(default_factory=dict)
    adapter_gap_summary: dict[str, Any] = Field(default_factory=dict)
    apply_gate_summary: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    safety: dict[str, Any] = Field(default_factory=dict)
    status: str = "read_only"
    message: str = "Apply-contract readiness only; no calendar template events were applied."


@dataclass(slots=True)
class CalendarTemplateApplyContractService:
    template_service: CalendarTemplateService
    calendar_service: SeasonCalendarService

    def build_readiness(
        self,
        request: CalendarTemplateApplyContractReadinessRequest,
    ) -> CalendarTemplateApplyContractReadinessResponse:
        source_template = self.template_service.get_template(template_id=request.source_template_id).template
        if source_template is None:
            raise KeyError(request.source_template_id)

        normalized_target = request.target_season_label
        errors: list[str] = []
        warnings: list[str] = []
        try:
            normalized_target = to_long_season_label(normalize_season_label(request.target_season_label))
        except ValueError as exc:
            errors.append(f"Invalid target season label '{request.target_season_label}': {exc}")

        by_id = {event.id: event for event in source_template.events}
        selected_ids = request.selected_source_event_ids
        selected_valid = True
        if selected_ids is not None:
            missing_ids = [event_id for event_id in selected_ids if event_id not in by_id]
            if missing_ids:
                raise ValueError(f"Unknown selected_source_event_id: {missing_ids[0]}")
        selected_events = [event for event in source_template.events if selected_ids is None or event.id in set(selected_ids)]

        calendar_result = self.calendar_service.get_calendar(season=normalized_target) if not errors else None
        target_calendar = calendar_result.calendar if calendar_result is not None else None
        target_calendar_exists = target_calendar is not None
        target_fp = _digest("target", target_calendar.model_dump(mode="json") if target_calendar is not None else None) if target_calendar_exists else None
        selected_fp = _digest("selected", selected_ids or [event.id for event in source_template.events])
        plan_payload = {
            "target_season_label": normalized_target,
            "source_template_id": request.source_template_id,
            "policy": request.policy,
            "selected_source_event_ids_fingerprint": selected_fp,
            "source_template_fingerprint": source_template.template_fingerprint,
            "target_fingerprint": target_fp,
            "source_event_fingerprints": [event.event_fingerprint for event in selected_events],
            "phase": "read_only_contract_readiness",
        }
        recomputed_diff_fingerprint = _digest("diff", plan_payload)

        source_template_fingerprint_matched = request.source_template_fingerprint is not None and request.source_template_fingerprint == source_template.template_fingerprint
        if request.source_template_fingerprint and not source_template_fingerprint_matched:
            warnings.append("source_template_fingerprint mismatch; future apply would be rejected.")

        target_fingerprint_matched = request.target_fingerprint is not None and request.target_fingerprint == target_fp
        if request.target_fingerprint and not target_fingerprint_matched:
            warnings.append("target_fingerprint mismatch; future apply would be rejected.")

        reviewed_diff_fingerprint_present = bool(request.reviewed_diff_fingerprint and request.reviewed_diff_fingerprint.strip())
        reviewed_diff_fingerprint_matched = request.reviewed_diff_fingerprint is not None and request.reviewed_diff_fingerprint == recomputed_diff_fingerprint
        if request.reviewed_diff_fingerprint and not reviewed_diff_fingerprint_matched:
            warnings.append("reviewed_diff_fingerprint mismatch; future apply would be rejected.")

        requested_by_present = bool(request.requested_by and request.requested_by.strip())
        audit_reason_present = bool(request.audit_reason and request.audit_reason.strip())
        explicit_confirmation_present = bool(request.explicit_confirmation and request.explicit_confirmation.strip())
        explicit_confirmation_valid = request.explicit_confirmation == REQUIRED_CALENDAR_TEMPLATE_APPLY_CONFIRMATION
        if explicit_confirmation_present and not explicit_confirmation_valid:
            warnings.append("explicit_confirmation does not match the future required confirmation text.")

        policy_supported_for_future_apply = request.policy in {"replace_unlocked_only", "copy_missing_only"}
        if request.policy == "replace_all":
            warnings.append("replace_all is blocked/deferred until destructive apply, lock, audit, and backup safeguards exist.")

        readiness_summary = {
            "source_template_exists": True,
            "target_calendar_lookup_attempted": not errors,
            "target_calendar_exists": target_calendar_exists,
            "source_template_fingerprint_matched": source_template_fingerprint_matched,
            "target_fingerprint_matched": target_fingerprint_matched,
            "reviewed_diff_fingerprint_present": reviewed_diff_fingerprint_present,
            "reviewed_diff_fingerprint_matched": reviewed_diff_fingerprint_matched,
            "requested_by_present": requested_by_present,
            "audit_reason_present": audit_reason_present,
            "explicit_confirmation_present": explicit_confirmation_present,
            "explicit_confirmation_valid": explicit_confirmation_valid,
            "selected_source_event_ids_valid": selected_valid,
            "policy_supported_for_future_apply": policy_supported_for_future_apply,
            "adapter_ready_for_weeks": False,
            "adapter_ready_for_qualification_weeks": False,
            "adapter_ready_for_locked_events": False,
            "audit_ready": False,
            "mutation_allowed": False,
        }
        adapter_gap_summary = {
            "direct_apply_blocked": True,
            "blocked_until_resolved": [
                "weeks list to SeasonCalendarEvent scalar fields adapter",
                "qualification_weeks persistence/adapter",
                "locked target event persistence",
                "stronger mutation identity rules if needed",
                "audit JSONL service for calendar-template apply",
                "before-state backup strategy",
            ],
            "weeks_adapter": {"ready": False, "message": "Template events use weeks lists; SeasonCalendarEvent uses scalar season_week/start/end/duration fields."},
            "qualification_weeks_adapter": {"ready": False, "message": "Template qualification_weeks have no first-class canonical season calendar field yet."},
            "locked_events_adapter": {"ready": False, "message": "Template locked state has no first-class target SeasonCalendarEvent persistence yet."},
            "identity_rules": {"ready": False, "message": "Future mutation needs stronger server-side identity matching than local preview rows."},
            "audit_jsonl": {"ready": False, "message": "Calendar-template apply audit JSONL is not implemented in this phase."},
            "before_state_backup": {"ready": False, "message": "Before-state backup strategy is not implemented in this phase."},
        }
        apply_gate_summary = {
            **readiness_summary,
            "enabled": False,
            "can_execute": False,
            "can_mutate": False,
            "mutation_performed": False,
            "mutation_scope": request.mutation_scope,
            "mutation_scope_present": bool(request.mutation_scope and request.mutation_scope.strip()),
            "selected_source_event_count": len(selected_events),
            "source_event_count": len(source_template.events),
            "replace_all_blocked": request.policy == "replace_all",
            "recomputed_diff_fingerprint": recomputed_diff_fingerprint,
        }
        safety = {
            "read_only": True,
            "mutation_performed": False,
            "apply_endpoint_enabled": False,
            "canonical_season_calendar_modified": False,
            "viewer_unchanged": True,
            "simulation_unchanged": True,
            "audit_written": False,
            "message": "Apply-contract readiness only; no calendar template events were applied.",
        }
        return CalendarTemplateApplyContractReadinessResponse(
            target_season_label=request.target_season_label,
            normalized_target_season_label=normalized_target,
            source_template_id=request.source_template_id,
            policy=request.policy,
            source_template_fingerprint=source_template.template_fingerprint,
            target_calendar_exists=target_calendar_exists,
            target_fingerprint=target_fp,
            reviewed_diff_fingerprint=request.reviewed_diff_fingerprint,
            readiness_summary=readiness_summary,
            adapter_gap_summary=adapter_gap_summary,
            apply_gate_summary=apply_gate_summary,
            validation_errors=errors,
            validation_warnings=warnings,
            safety=safety,
        )
