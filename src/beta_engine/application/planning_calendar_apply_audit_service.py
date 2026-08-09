"""Append-only audit persistence for planning-calendar template apply commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

PLANNING_CALENDAR_APPLY_AUDIT_SCHEMA_VERSION = "planning_calendar_apply_audit.v1"
PLANNING_CALENDAR_APPLY_COMMAND_TYPE = "planning_calendar_apply_template"
PLANNING_CALENDAR_APPLY_AUDIT_DEFAULT_PATH = Path("config/simulation/planning_calendar_apply_audit.jsonl")
PlanningCalendarApplyAuditStage = Literal["rejected", "pre_mutation_reserved", "succeeded"]


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def deterministic_digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class PlanningCalendarApplyAuditRecord(BaseModel):
    """Durable safe-scalar audit record for planning-calendar apply attempts."""

    audit_record_id: str
    audit_schema_version: str = PLANNING_CALENDAR_APPLY_AUDIT_SCHEMA_VERSION
    command_type: str = PLANNING_CALENDAR_APPLY_COMMAND_TYPE
    endpoint: str = "/admin/seasons/planning-calendars/{season_label}/apply-template"
    attempted_at: str
    audit_stage: PlanningCalendarApplyAuditStage
    read_only: bool = True
    target_season_label: str
    normalized_target_season_label: str | None = None
    source_template_id: str | None = None
    policy: str | None = None
    selected_source_event_ids_fingerprint: str | None = None
    expected_planning_calendar_fingerprint: str | None = None
    before_calendar_fingerprint: str | None = None
    after_calendar_fingerprint: str | None = None
    source_template_fingerprint_requested: str | None = None
    source_template_fingerprint_recomputed: str | None = None
    reviewed_diff_fingerprint_requested: str | None = None
    reviewed_diff_fingerprint_recomputed: str | None = None
    apply_plan_fingerprint: str | None = None
    counts: dict[str, Any] = Field(default_factory=dict)
    skipped_items_fingerprint: str | None = None
    rejected_items_fingerprint: str | None = None
    requested_by: str | None = None
    audit_reason: str | None = None
    explicit_confirmation_present: bool = False
    explicit_confirmation_valid: bool = False
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    request_payload_fingerprint: str
    response_payload_fingerprint: str | None = None
    audit_record_fingerprint: str | None = None
    idempotency_key: str | None = None

    def with_fingerprint(self) -> "PlanningCalendarApplyAuditRecord":
        payload = self.model_dump(mode="json")
        payload["audit_record_fingerprint"] = None
        return self.model_copy(update={"audit_record_fingerprint": f"aud_{deterministic_digest(payload)[:24]}"})


class PlanningCalendarApplyAuditWriteResult(BaseModel):
    audit_record_id: str
    audit_record_fingerprint: str
    audit_persisted: bool = True
    audit_persistence_status: str = "persisted"
    audit_storage_summary: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class PlanningCalendarApplyAuditService:
    """Append one canonical JSON planning-calendar apply audit record per line."""

    audit_log_path: Path = PLANNING_CALENDAR_APPLY_AUDIT_DEFAULT_PATH

    def __post_init__(self) -> None:
        if not isinstance(self.audit_log_path, Path):
            self.audit_log_path = Path(self.audit_log_path)

    @classmethod
    def for_planning_registry_path(cls, planning_registry_path: str | Path | None) -> "PlanningCalendarApplyAuditService":
        if planning_registry_path is None:
            return cls()
        registry_path = Path(planning_registry_path)
        return cls(audit_log_path=registry_path.with_name("planning_calendar_apply_audit.jsonl"))

    def append_record(self, record: PlanningCalendarApplyAuditRecord) -> PlanningCalendarApplyAuditWriteResult:
        persisted_record = record.with_fingerprint()
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        line = canonical_json(persisted_record.model_dump(mode="json")) + "\n"
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
        return PlanningCalendarApplyAuditWriteResult(
            audit_record_id=persisted_record.audit_record_id,
            audit_record_fingerprint=persisted_record.audit_record_fingerprint or "",
            audit_storage_summary=self.storage_summary(),
        )

    def storage_summary(self) -> dict[str, Any]:
        return {
            "backend": "append_only_jsonl",
            "filename": self.audit_log_path.name,
            "directory_name": self.audit_log_path.parent.name,
        }


def build_audit_record_id(*, attempted_at: str, request_payload_fingerprint: str) -> str:
    suffix = deterministic_digest({"attempted_at": attempted_at, "request_payload_fingerprint": request_payload_fingerprint})[:20]
    return f"aud_planning_apply_{suffix}"
