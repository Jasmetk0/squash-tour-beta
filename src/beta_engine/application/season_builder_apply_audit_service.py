"""Append-only audit persistence for real season-builder apply commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


CREATE_ONLY_APPLY_AUDIT_SCHEMA_VERSION = "season_builder_apply_create_only_audit.v1"
CREATE_ONLY_APPLY_COMMAND_TYPE = "season_builder_apply_create_only"
CREATE_ONLY_APPLY_ENDPOINT = "/admin/seasons/builder/apply-create-only-command"


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def deterministic_digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class SeasonBuilderApplyCreateOnlyAuditRecord(BaseModel):
    """Durable safe-scalar audit record for real create-only apply attempts."""

    audit_record_id: str
    audit_schema_version: str = CREATE_ONLY_APPLY_AUDIT_SCHEMA_VERSION
    command_type: str = CREATE_ONLY_APPLY_COMMAND_TYPE
    endpoint: str = CREATE_ONLY_APPLY_ENDPOINT
    attempted_at: str
    audit_stage: Literal["rejected", "pre_mutation_reserved", "succeeded"]
    read_only: bool = False
    target_season_label: str
    normalized_target_season_label: str | None = None
    source_type: str
    source_template_id: str | None = None
    overwrite_policy: str | None = None
    mutation_scope: str | None = None
    requested_by: str | None = None
    audit_reason: str | None = None
    explicit_confirmation_present: bool = False
    explicit_confirmation_valid: bool = False
    preflight_fingerprint: str | None = None
    reviewed_diff_id: str | None = None
    dry_run_result_fingerprint: str | None = None
    dry_run_result_id: str | None = None
    requested_candidate_identity_reference_id: str | None = None
    requested_candidate_identity_fingerprint: str | None = None
    requested_candidate_identity_reference_type: str | None = None
    expected_candidate_identity_reference_id: str | None = None
    expected_candidate_identity_fingerprint: str | None = None
    expected_candidate_identity_reference_type: str | None = None
    dry_run_identity: dict[str, Any] = Field(default_factory=dict)
    apply_gate_summary: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    applied: bool = False
    mutation_performed: bool = False
    applied_event_count: int = 0
    created_calendar_event_ids_fingerprint: str | None = None
    created_calendar_identity: dict[str, Any] = Field(default_factory=dict)
    rejection_status_code: int | None = None
    rejection_reason: str | None = None
    request_payload_fingerprint: str
    response_payload_fingerprint: str | None = None
    audit_record_fingerprint: str | None = None
    idempotency_key: str | None = None

    def with_fingerprint(self) -> "SeasonBuilderApplyCreateOnlyAuditRecord":
        payload = self.model_dump(mode="json")
        payload["audit_record_fingerprint"] = None
        fingerprint = f"aud_{deterministic_digest(payload)[:24]}"
        return self.model_copy(update={"audit_record_fingerprint": fingerprint})


class SeasonBuilderApplyCreateOnlyAuditWriteResult(BaseModel):
    audit_record_id: str
    audit_record_fingerprint: str
    audit_persisted: bool = True
    audit_persistence_status: str = "persisted"
    audit_storage_summary: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class SeasonBuilderApplyAuditService:
    """Append one canonical JSON audit record per line."""

    audit_log_path: Path = Path("config/simulation/season_builder_apply_create_only_audit.jsonl")

    def __post_init__(self) -> None:
        if not isinstance(self.audit_log_path, Path):
            self.audit_log_path = Path(self.audit_log_path)

    @classmethod
    def for_calendar_registry_path(cls, calendar_registry_path: str | Path | None) -> "SeasonBuilderApplyAuditService":
        if calendar_registry_path is None:
            return cls()
        registry_path = Path(calendar_registry_path)
        return cls(audit_log_path=registry_path.with_name("season_builder_apply_create_only_audit.jsonl"))

    def append_record(
        self,
        record: SeasonBuilderApplyCreateOnlyAuditRecord,
    ) -> SeasonBuilderApplyCreateOnlyAuditWriteResult:
        persisted_record = record.with_fingerprint()
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        line = canonical_json(persisted_record.model_dump(mode="json")) + "\n"
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
        return SeasonBuilderApplyCreateOnlyAuditWriteResult(
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
    return f"aud_create_only_{suffix}"
