from __future__ import annotations

import json
from pathlib import Path

from beta_engine.application.planning_calendar_apply_audit_service import (
    PlanningCalendarApplyAuditRecord,
    PlanningCalendarApplyAuditService,
    canonical_json,
)


def record(record_id: str = "aud-test") -> PlanningCalendarApplyAuditRecord:
    return PlanningCalendarApplyAuditRecord(
        audit_record_id=record_id,
        attempted_at="2026-06-24T00:00:00Z",
        audit_stage="rejected",
        target_season_label="2000/01",
        normalized_target_season_label="2000/2001",
        source_template_id="template-a",
        policy="copy_missing_only",
        request_payload_fingerprint="req_abc",
    )


def test_audit_jsonl_append_works_and_writes_canonical_json(tmp_path: Path) -> None:
    path = tmp_path / "planning_calendar_apply_audit.jsonl"
    service = PlanningCalendarApplyAuditService(audit_log_path=path)

    result = service.append_record(record())

    assert result.audit_persisted is True
    assert path.exists()
    line = path.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert line == canonical_json(parsed)
    assert parsed["audit_schema_version"] == "planning_calendar_apply_audit.v1"
    assert parsed["command_type"] == "planning_calendar_apply_template"
    assert parsed["audit_record_fingerprint"].startswith("aud_")


def test_audit_record_fingerprint_is_deterministic() -> None:
    first = record().with_fingerprint()
    second = record().with_fingerprint()

    assert first.audit_record_fingerprint == second.audit_record_fingerprint


def test_for_planning_registry_path_places_audit_beside_planning_registry(tmp_path: Path) -> None:
    registry_path = tmp_path / "config" / "world" / "planning_season_calendars.json"

    service = PlanningCalendarApplyAuditService.for_planning_registry_path(registry_path)

    assert service.audit_log_path == registry_path.with_name("planning_calendar_apply_audit.jsonl")


def test_append_is_append_only(tmp_path: Path) -> None:
    path = tmp_path / "planning_calendar_apply_audit.jsonl"
    service = PlanningCalendarApplyAuditService(audit_log_path=path)

    service.append_record(record("aud-a"))
    service.append_record(record("aud-b"))

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    assert json.loads(lines[0])["audit_record_id"] == "aud-a"
    assert json.loads(lines[1])["audit_record_id"] == "aud-b"
