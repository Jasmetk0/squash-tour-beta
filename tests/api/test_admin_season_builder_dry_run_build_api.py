from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import request

import uvicorn

from beta_engine.main import create_app


MESSAGE = "Dry-run build command contract exists, but execution is disabled in this phase."


def write_templates(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"templates": [
        {"template_id": "wt_a", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}
    ]}), encoding="utf-8")


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header("content-type", "application/json")
    with request.urlopen(req, timeout=60) as response:
        raw = response.read().decode()
        return response.status, json.loads(raw) if raw else {}


def free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Server:
    def __init__(self, tmp_path: Path) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        template_path = tmp_path / "templates.json"
        write_templates(template_path)
        app = create_app(
            database_url=f"sqlite:///{tmp_path / 'api.db'}",
            tournament_templates_config_path=str(template_path),
            season_calendar_registry_path=str(tmp_path / "season_calendars.json"),
        )
        self.server = uvicorn.Server(uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                call("GET", f"{self.base_url}/health")
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def create_calendar(server: Server, season: str) -> None:
    payload = {"dry_run": False, "overwrite_existing": True}
    status, _ = call("POST", f"{server.base_url}/admin/seasons/{season}/calendar/build", payload)
    assert status == 200


def assert_conflict_preview_is_null(body: dict) -> None:
    assert body["template_slot_conflict_preview"] is None
    dry_run_preview = body.get("dry_run_result_preview")
    if not isinstance(dry_run_preview, dict):
        return
    summary = dry_run_preview["template_conflict_summary"]
    assert summary["available"] is False
    assert summary["read_only"] is True
    assert summary["non_blocking"] is True
    assert summary["status"] is None
    assert summary["warning_count"] == 0
    assert summary["info_count"] == 0
    assert summary["conflict_count"] == 0
    assert summary["conflict_codes"] == []
    assert summary["busiest_week"] is None
    assert summary["busiest_week_slot_count"] is None
    assert summary["source"] == "template_slot_conflict_preview"


def assert_conflict_preview_is_present(body: dict, template_id: str) -> None:
    preview = body["template_slot_conflict_preview"]
    assert preview is not None
    assert preview["read_only"] is True
    assert preview["template_id"] == template_id
    assert preview["template_exists"] is True
    assert isinstance(preview["conflict_count"], int)
    assert preview["conflict_count"] >= 0
    assert isinstance(preview["conflict_codes"], list)
    dry_run_preview = body.get("dry_run_result_preview")
    if not isinstance(dry_run_preview, dict):
        return
    summary = dry_run_preview["template_conflict_summary"]
    assert summary["available"] is True
    assert summary["read_only"] is True
    assert summary["non_blocking"] is True
    assert summary["status"] == preview["status"]
    assert summary["warning_count"] == preview["warning_count"]
    assert summary["info_count"] == preview["info_count"]
    assert summary["conflict_count"] == preview["conflict_count"]
    assert summary["conflict_codes"] == preview["conflict_codes"]
    assert summary["busiest_week"] == preview["busiest_week"]
    assert summary["busiest_week_slot_count"] == preview["busiest_week_slot_count"]
    assert summary["source"] == "template_slot_conflict_preview"


def test_builder_dry_run_build_minimal_contract(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2002/2003",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_123",
            "reviewed_diff_id": "rd_123",
            "requested_by": "qa",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        assert body["enabled"] is False
        assert body["can_execute"] is False
        assert body["can_mutate"] is False
        assert body["message"] == MESSAGE
        assert body["audit_preview"]["read_only"] is True
        assert body["audit_preview"]["mutation_permitted"] is False
        assert body["audit_preview"]["execution_enabled"] is False
        assert body["audit_preview"]["generation_design_preview_available"] is True
        assert body["audit_preview"]["candidate_event_contract_preview_available"] is True
        assert body["audit_preview"]["conflict_contract_preview_available"] is True
        assert body["audit_preview"]["dry_run_result_contract_preview_available"] is True
        assert body["audit_preview"]["dry_run_result_preview_available"] is True
        design = body["generation_design_preview"]
        assert design["status"] == "design_preview_only"
        assert design["execution_enabled"] is False
        assert design["will_generate_events"] is False
        assert design["will_persist_calendar"] is False
        assert design["will_mutate_existing_calendar"] is False
        assert "Validate reviewed preflight identity." in design["planned_steps"]
        assert "Return additions/replacements/conflicts without persistence." in design["planned_steps"]
        assert "preflight_fingerprint" in design["required_future_inputs"]
        assert "reviewed_diff_id" in design["required_future_inputs"]
        assert "audit_reason" in design["required_future_inputs"]
        assert "explicit_confirmation" in design["required_future_inputs"]
        assert "mutation_scope" in design["required_future_inputs"]
        assert "candidate_events" in design["planned_output_sections"]
        assert "conflict_summary" in design["planned_output_sections"]
        assert "audit_preview" in design["planned_output_sections"]
        assert design["blocked_reason"] == "Dry-run generation is not implemented in this phase."
        candidate_preview = body["candidate_event_contract_preview"]
        assert candidate_preview["status"] == "contract_preview_only"
        assert candidate_preview["will_generate_candidates"] is False
        assert candidate_preview["candidate_count"] == 0
        event_shape = candidate_preview["event_shape"]
        assert "candidate_id" in event_shape
        assert "source_slot_id" in event_shape
        assert "season_week_start" in event_shape
        assert "event_name" in event_shape
        assert "candidate_status" in event_shape
        assert "comparison_classification" in event_shape
        assert "comparison_reason" in event_shape
        assert "matched_existing_event_id" in event_shape
        assert "matched_existing_event_name" in event_shape
        assert "matched_existing_event_week" in event_shape
        assert "validation_errors" in event_shape
        assert "validation_warnings" in event_shape
        structural_shape = candidate_preview["structural_summary_shape"]
        assert "candidate_count" in structural_shape
        assert "additions_count" in structural_shape
        assert "conflict_count" in structural_shape
        assert "invalid_count" in structural_shape
        conflict_shape = candidate_preview["conflict_summary_shape"]
        assert "week_conflicts" in conflict_shape
        assert "slot_conflicts" in conflict_shape
        assert "policy_conflicts" in conflict_shape
        assert "validation_conflicts" in conflict_shape
        assert candidate_preview["blocked_reason"] == "Candidate event generation is not implemented in this phase."
        conflict_contract_preview = body["conflict_contract_preview"]
        assert conflict_contract_preview["status"] == "contract_preview_only"
        assert conflict_contract_preview["will_compute_conflicts"] is False
        assert conflict_contract_preview["conflict_count"] == 0
        week_conflict_shape = conflict_contract_preview["week_conflict_shape"]
        assert "conflict_id" in week_conflict_shape
        assert "conflict_type" in week_conflict_shape
        assert "season_week" in week_conflict_shape
        assert "candidate_id" in week_conflict_shape
        assert "existing_event_id" in week_conflict_shape
        assert "severity" in week_conflict_shape
        slot_conflict_shape = conflict_contract_preview["slot_conflict_shape"]
        assert "source_slot_id" in slot_conflict_shape
        assert "candidate_id" in slot_conflict_shape
        assert "severity" in slot_conflict_shape
        policy_conflict_shape = conflict_contract_preview["policy_conflict_shape"]
        assert "policy" in policy_conflict_shape
        assert "message" in policy_conflict_shape
        assert "severity" in policy_conflict_shape
        validation_conflict_shape = conflict_contract_preview["validation_conflict_shape"]
        assert "field" in validation_conflict_shape
        assert "message" in validation_conflict_shape
        assert "severity" in validation_conflict_shape
        assert conflict_contract_preview["blocked_reason"] == "Conflict computation is not implemented in this phase."
        dry_run_result_preview = body["dry_run_result_contract_preview"]
        assert dry_run_result_preview["status"] == "contract_preview_only"
        assert dry_run_result_preview["will_return_real_result"] is False
        assert dry_run_result_preview["candidate_events"] == []
        assert dry_run_result_preview["structural_summary"]["candidate_count"] == 0
        assert dry_run_result_preview["structural_summary"]["additions_count"] == 0
        assert dry_run_result_preview["structural_summary"]["conflict_count"] == 0
        assert dry_run_result_preview["conflict_summary"]["week_conflicts"] == []
        assert dry_run_result_preview["conflict_summary"]["policy_conflicts"] == []
        assert dry_run_result_preview["result_metadata"]["preflight_fingerprint"] == payload["preflight_fingerprint"]
        assert dry_run_result_preview["result_metadata"]["reviewed_diff_id"] == payload["reviewed_diff_id"]
        assert dry_run_result_preview["result_metadata"]["execution_enabled"] is False
        assert dry_run_result_preview["result_metadata"]["read_only"] is True
        assert dry_run_result_preview["result_metadata"]["mutation_permitted"] is False
        assert dry_run_result_preview["blocked_reason"] == "Dry-run result generation is not implemented in this phase."
        assert body["dry_run_result_preview"]["status"] == "read_only_generated"


def test_builder_dry_run_build_missing_fingerprint(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2002/2003",
            "source_type": "season_template",
            "preflight_fingerprint": "",
            "reviewed_diff_id": "rd_123",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        assert "preflight_fingerprint is required for any future dry-run build command." in body["validation_errors"]
        assert body["template_slot_conflict_preview"] is None


def test_builder_dry_run_build_missing_reviewed_diff_id(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2002/2003",
            "source_type": "season_template",
            "preflight_fingerprint": "pf_123",
            "reviewed_diff_id": "",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        assert "reviewed_diff_id is required for any future dry-run build command." in body["validation_errors"]
        assert body["template_slot_conflict_preview"] is None


def test_builder_dry_run_build_full_future_metadata(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2002/2003",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "overwrite_preview",
            "preflight_fingerprint": "pf_123",
            "reviewed_diff_id": "rd_123",
            "requested_by": "qa",
            "audit_reason": "ticket-123",
            "explicit_confirmation": "I understand this is disabled.",
            "mutation_scope": "none",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert body["can_execute"] is False
        assert body["can_mutate"] is False
        assert body["generation_design_preview"]["status"] == "design_preview_only"
        assert body["candidate_event_contract_preview"]["candidate_count"] == 0
        assert "conflict_contract_preview" in body
        assert body["conflict_contract_preview"]["conflict_count"] == 0
        assert "dry_run_result_contract_preview" in body
        assert body["dry_run_result_contract_preview"]["candidate_events"] == []
        assert "audit_reason will be required before execution is enabled in a future phase." not in body["validation_warnings"]
        assert "explicit_confirmation will be required before execution is enabled in a future phase." not in body["validation_warnings"]
        assert "mutation_scope will be required before execution is enabled in a future phase." not in body["validation_warnings"]
        assert body["audit_preview"]["explicit_confirmation_present"] is True
        assert "explicit_confirmation" not in body["audit_preview"]


def test_builder_dry_run_build_does_not_create_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "preflight_fingerprint": "pf_123",
            "reviewed_diff_id": "rd_123",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        assert body["can_mutate"] is False
        assert body["template_slot_conflict_preview"] is None

        _, calendar_body = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert calendar_body["calendar"] is None
        assert calendar_body["summary"]["calendar_exists"] is False


def test_builder_dry_run_build_generates_read_only_candidates_from_template(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_live",
            "reviewed_diff_id": "rd_live",
            "requested_by": "qa",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        assert body["can_mutate"] is False
        assert body["can_execute"] is False
        assert body["dry_run_result_preview"]["status"] == "read_only_generated"
        candidates = body["dry_run_result_preview"]["candidate_events"]
        assert len(candidates) > 0
        assert body["dry_run_result_preview"]["structural_summary"]["candidate_count"] == len(candidates)
        assert body["dry_run_result_preview"]["structural_summary"]["additions_count"] == len(candidates)
        assert body["dry_run_result_preview"]["result_metadata"]["target_calendar_exists"] is False
        assert body["dry_run_result_preview"]["result_metadata"]["target_event_count"] == 0
        assert body["dry_run_result_preview"]["result_metadata"]["comparison_performed"] is True
        assert body["dry_run_result_preview"]["conflict_summary"]["week_conflicts"] == []
        assert body["dry_run_result_preview"]["conflict_summary"]["slot_conflicts"] == []
        assert body["dry_run_result_preview"]["conflict_summary"]["policy_conflicts"] == []
        first = candidates[0]
        assert "candidate_id" in first
        assert "source_slot_id" in first
        assert "season_week_start" in first
        assert "season_week_end" in first
        assert "event_name" in first
        assert first["source_template_id"] == "default_msa_template_preview"
        assert first["source_type"] == "season_template"
        assert first["candidate_status"] == "planned"
        assert first["comparison_classification"] == "addition"
        assert "would be an addition" in first["comparison_reason"]
        assert first["matched_existing_event_id"] is None
        assert first["matched_existing_event_name"] is None
        assert first["matched_existing_event_week"] is None
        assert first["validation_errors"] == []
        assert first["validation_warnings"] == []
        for candidate in candidates:
            assert candidate["comparison_classification"] == "addition"
            assert "would be an addition" in candidate["comparison_reason"]
            assert candidate["matched_existing_event_id"] is None
            assert candidate["matched_existing_event_name"] is None
            assert candidate["matched_existing_event_week"] is None
        assert body["audit_preview"]["dry_run_result_preview_available"] is True
        validation_summary = body["dry_run_result_preview"]["validation_summary"]
        assert validation_summary["status"] == "warnings"
        assert validation_summary["blocking_count"] == 0
        assert len(validation_summary["warning_reasons"]) >= 3
        _, calendar_body = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert calendar_body["calendar"] is None
        assert calendar_body["summary"]["calendar_exists"] is False


def test_builder_dry_run_build_unknown_template_returns_unresolved_source(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "unknown_template",
            "preflight_fingerprint": "pf_live",
            "reviewed_diff_id": "rd_live",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert "source_template_id could not be resolved for read-only dry-run candidate generation." in body["validation_errors"]
        assert body["dry_run_result_preview"]["status"] == "blocked_unresolved_source"
        assert body["template_slot_conflict_preview"] is None
        assert body["dry_run_result_preview"]["validation_summary"]["status"] == "blocking"
        assert "source_template_id could not be resolved for read-only dry-run candidate generation." in body["dry_run_result_preview"]["validation_summary"]["blocking_reasons"]
        assert body["dry_run_result_preview"]["plan_readiness"]["read_only_plan_available"] is False
        assert body["dry_run_result_preview"]["identity_readiness"]["status"] == "blocked_reference"
        assert body["dry_run_result_preview"]["identity_readiness"]["future_command_reference"]["can_reference_future_command"] is False
        assert body["dry_run_result_preview"]["candidate_events"] == []
        assert body["can_mutate"] is False


def test_builder_dry_run_build_non_template_source_is_unsupported_for_generation(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "calendar_snapshot",
            "preflight_fingerprint": "pf_live",
            "reviewed_diff_id": "rd_live",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert "Read-only candidate generation currently supports season_template sources only." in body["validation_warnings"]
        assert body["dry_run_result_preview"]["status"] == "unsupported_source_type"
        assert body["template_slot_conflict_preview"] is None
        assert body["dry_run_result_preview"]["candidate_events"] == []
        assert body["can_mutate"] is False


def test_builder_dry_run_build_existing_target_calendar_comparison(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        create_calendar(server, "2002%2F2003")
        payload = {
            "target_season_label": "2002/2003",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": None,
            "preflight_fingerprint": "pf_existing",
            "reviewed_diff_id": "rd_existing",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        assert body["can_mutate"] is False
        assert body["template_slot_conflict_preview"] is not None
        metadata = body["dry_run_result_preview"]["result_metadata"]
        assert metadata["target_calendar_exists"] is True
        assert metadata["target_event_count"] > 0
        assert metadata["comparison_performed"] is True
        assert body["dry_run_result_preview"]["structural_summary"]["target_event_count"] == metadata["target_event_count"]
        policy_conflicts = body["dry_run_result_preview"]["conflict_summary"]["policy_conflicts"]
        assert any("Existing target calendar requires explicit merge/overwrite policy before future mutation." in item["message"] for item in policy_conflicts)
        validation_summary = body["dry_run_result_preview"]["validation_summary"]
        assert validation_summary["status"] == "blocking"
        assert "Existing target calendar requires explicit merge/overwrite policy before future mutation." in validation_summary["blocking_reasons"]
        assert validation_summary["conflict_type_counts"]["policy_conflicts"] > 0
        assert body["dry_run_result_preview"]["plan_readiness"]["has_blocking_issues"] is True
        assert body["dry_run_result_preview"]["structural_summary"]["conflict_count"] >= len(policy_conflicts)
        statuses = {candidate["candidate_status"] for candidate in body["dry_run_result_preview"]["candidate_events"]}
        assert statuses.issubset({"planned", "conflict", "invalid"})
        classifications = [candidate["comparison_classification"] for candidate in body["dry_run_result_preview"]["candidate_events"]]
        assert set(classifications).issubset({"addition", "replacement", "conflict", "invalid"})
        for candidate in body["dry_run_result_preview"]["candidate_events"]:
            assert isinstance(candidate["comparison_reason"], str)
            assert candidate["comparison_reason"].strip()
            assert "matched_existing_event_id" in candidate
        replacement_candidates = [candidate for candidate in body["dry_run_result_preview"]["candidate_events"] if candidate["comparison_classification"] == "replacement"]
        for candidate in replacement_candidates:
            assert candidate["matched_existing_event_id"] is not None
            assert candidate["matched_existing_event_name"] is not None
            assert candidate["matched_existing_event_week"] is not None


def test_builder_dry_run_build_empty_target_calendar_comparison(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2038/2039",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": None,
            "preflight_fingerprint": "pf_empty_comp",
            "reviewed_diff_id": "rd_empty_comp",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        metadata = body["dry_run_result_preview"]["result_metadata"]
        assert metadata["target_calendar_exists"] is False
        assert metadata["target_event_count"] == 0
        assert metadata["comparison_performed"] is True
        assert body["dry_run_result_preview"]["conflict_summary"]["policy_conflicts"] == []
        summary = body["dry_run_result_preview"]["structural_summary"]
        assert summary["additions_count"] == summary["candidate_count"]
        assert body["can_mutate"] is False
        _, calendar_body = call("GET", f"{server.base_url}/admin/seasons/2038%2F2039/calendar")
        assert calendar_body["calendar"] is None


def test_builder_dry_run_build_validation_summary_clean_when_metadata_is_present(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2038/2039",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_clean",
            "reviewed_diff_id": "rd_clean",
            "requested_by": "qa",
            "audit_reason": "phase-8d-clean-check",
            "explicit_confirmation": "confirmed",
            "mutation_scope": "none",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        summary = body["dry_run_result_preview"]["validation_summary"]
        assert summary["status"] == "clean"
        assert summary["blocking_count"] == 0
        assert summary["warning_count"] == 0
        assert summary["candidate_status_counts"]["planned"] == body["dry_run_result_preview"]["structural_summary"]["candidate_count"]
        readiness = body["dry_run_result_preview"]["plan_readiness"]
        assert readiness["read_only_plan_available"] is True
        assert readiness["mutation_still_disabled"] is True
        identity_readiness = body["dry_run_result_preview"]["identity_readiness"]
        assert identity_readiness["status"] == "ready_reference"
        future_reference = identity_readiness["future_command_reference"]
        assert future_reference["preflight_fingerprint"] == "pf_clean"
        assert future_reference["reviewed_diff_id"] == "rd_clean"
        assert future_reference["dry_run_result_fingerprint"].startswith("drf_")
        assert future_reference["dry_run_result_id"].startswith("drr_")
        assert future_reference["can_reference_future_command"] is True
        assert future_reference["mutation_still_disabled"] is True


def test_builder_dry_run_build_missing_audit_metadata_adds_warning_reasons(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2038/2039",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "preflight_fingerprint": "pf_warn",
            "reviewed_diff_id": "rd_warn",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        summary = body["dry_run_result_preview"]["validation_summary"]
        assert summary["status"] in {"warnings", "blocking"}
        assert any("audit_reason will be required before execution is enabled in a future phase." in reason for reason in summary["warning_reasons"])
        assert any("explicit_confirmation will be required before execution is enabled in a future phase." in reason for reason in summary["warning_reasons"])
        assert any("mutation_scope will be required before execution is enabled in a future phase." in reason for reason in summary["warning_reasons"])


def test_builder_dry_run_build_identity_readiness_blocked_for_existing_target_without_policy(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        create_calendar(server, "2004%2F2005")
        payload = {
            "target_season_label": "2004/2005",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "preflight_fingerprint": "pf_blocked",
            "reviewed_diff_id": "rd_blocked",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        identity_readiness = body["dry_run_result_preview"]["identity_readiness"]
        assert identity_readiness["status"] == "blocked_reference"
        assert identity_readiness["future_command_reference"]["can_reference_future_command"] is False
        validation_item = next(item for item in identity_readiness["items"] if item["area"] == "validation_summary")
        assert validation_item["status"] == "Blocked"
        assert "blocking" in validation_item["message"].lower()


def test_builder_dry_run_build_identity_readiness_missing_identity(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2038/2039",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "",
            "reviewed_diff_id": "",
            "audit_reason": "phase-8f-missing-id",
            "explicit_confirmation": "confirmed",
            "mutation_scope": "none",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        identity_readiness = body["dry_run_result_preview"]["identity_readiness"]
        assert identity_readiness["status"] == "missing_identity"
        assert identity_readiness["future_command_reference"]["can_reference_future_command"] is False
        preflight_item = next(item for item in identity_readiness["items"] if item["area"] == "preflight_fingerprint")
        reviewed_item = next(item for item in identity_readiness["items"] if item["area"] == "reviewed_diff_id")
        assert preflight_item["status"] == "Missing"
        assert reviewed_item["status"] == "Missing"


def test_builder_dry_run_build_existing_target_with_merge_preview_has_no_policy_conflict(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        create_calendar(server, "2004%2F2005")
        payload = {
            "target_season_label": "2004/2005",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_merge",
            "reviewed_diff_id": "rd_merge",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        assert body["can_mutate"] is False
        assert body["template_slot_conflict_preview"] is not None
        assert body["dry_run_result_preview"]["result_metadata"]["target_calendar_exists"] is True
        assert body["dry_run_result_preview"]["conflict_summary"]["policy_conflicts"] == []


def test_builder_dry_run_build_result_identity_is_stable_for_identical_state(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2038/2039",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_stable",
            "reviewed_diff_id": "rd_stable",
            "requested_by": "qa",
            "audit_reason": "ticket-stable",
            "explicit_confirmation": "confirmed-stable",
            "mutation_scope": "merge_preview",
        }
        _, first = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        _, second = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        first_fp = first["dry_run_result_preview"]["dry_run_result_fingerprint"]
        second_fp = second["dry_run_result_preview"]["dry_run_result_fingerprint"]
        first_id = first["dry_run_result_preview"]["dry_run_result_id"]
        second_id = second["dry_run_result_preview"]["dry_run_result_id"]
        assert first_fp == second_fp
        assert first_id == second_id
        assert first_fp.startswith("drf_")
        assert first_id.startswith("drr_")
        assert first["dry_run_result_preview"]["result_metadata"]["dry_run_result_fingerprint"] == first_fp
        assert first["dry_run_result_preview"]["result_metadata"]["dry_run_result_id"] == first_id
        assert second["dry_run_result_preview"]["result_metadata"]["dry_run_result_fingerprint"] == second_fp
        assert second["dry_run_result_preview"]["result_metadata"]["dry_run_result_id"] == second_id
        assert first["audit_preview"]["dry_run_result_identity_available"] is True
        assert second["audit_preview"]["dry_run_result_identity_available"] is True


def test_builder_dry_run_build_result_identity_changes_with_overwrite_policy(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        create_calendar(server, "2006%2F2007")
        base_payload = {
            "target_season_label": "2006/2007",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "preflight_fingerprint": "pf_policy",
            "reviewed_diff_id": "rd_policy",
            "requested_by": "qa",
            "audit_reason": "ticket-policy",
            "explicit_confirmation": "confirmed-policy",
            "mutation_scope": "merge_preview",
        }
        _, no_policy = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {**base_payload, "overwrite_policy": None})
        _, merge_policy = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {**base_payload, "overwrite_policy": "merge_preview"})
        assert no_policy["dry_run_result_preview"]["dry_run_result_fingerprint"] != merge_policy["dry_run_result_preview"]["dry_run_result_fingerprint"]
        assert no_policy["dry_run_result_preview"]["dry_run_result_id"] != merge_policy["dry_run_result_preview"]["dry_run_result_id"]


def test_builder_dry_run_build_result_identity_excludes_audit_metadata(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        base_payload = {
            "target_season_label": "2037/2038",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_audit",
            "reviewed_diff_id": "rd_audit",
        }
        _, first = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {
            **base_payload,
            "requested_by": "qa-a",
            "audit_reason": "ticket-a",
            "explicit_confirmation": "confirmed-a",
            "mutation_scope": "merge_preview",
        })
        _, second = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {
            **base_payload,
            "requested_by": "qa-b",
            "audit_reason": "ticket-b",
            "explicit_confirmation": "confirmed-b",
            "mutation_scope": "merge_preview",
        })
        assert first["dry_run_result_preview"]["validation_summary"]["status"] == "clean"
        assert second["dry_run_result_preview"]["validation_summary"]["status"] == "clean"
        assert first["dry_run_result_preview"]["dry_run_result_fingerprint"] == second["dry_run_result_preview"]["dry_run_result_fingerprint"]
        assert first["dry_run_result_preview"]["dry_run_result_id"] == second["dry_run_result_preview"]["dry_run_result_id"]

def test_builder_preflight_resolved_template_includes_conflict_preview(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2036/2037",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", payload)
        assert status == 200
        assert_conflict_preview_is_present(body, "default_msa_template_preview")


def test_builder_preflight_planned_source_has_null_conflict_preview(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2036/2037",
            "source_type": "blank_calendar_planned",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", payload)
        assert status == 200
        assert_conflict_preview_is_null(body)
        assert "Source type 'blank_calendar_planned' is planned and not executable yet in this phase." in body["validation_warnings"]


def test_builder_dry_run_resolved_template_includes_conflict_preview(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2036/2037",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "preflight_fingerprint": "pf_resolved",
            "reviewed_diff_id": "rd_resolved",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        assert body["can_mutate"] is False
        assert_conflict_preview_is_present(body, "default_msa_template_preview")


def test_builder_dry_run_unavailable_preview_paths_return_null_preview(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        missing_source_payload = {
            "target_season_label": "2036/2037",
            "source_type": "season_template",
            "preflight_fingerprint": "pf_missing",
            "reviewed_diff_id": "rd_missing",
        }
        unknown_source_payload = {
            "target_season_label": "2036/2037",
            "source_type": "season_template",
            "source_template_id": "unknown_template",
            "preflight_fingerprint": "pf_unknown",
            "reviewed_diff_id": "rd_unknown",
        }
        non_template_payload = {
            "target_season_label": "2036/2037",
            "source_type": "calendar_snapshot",
            "preflight_fingerprint": "pf_non_template",
            "reviewed_diff_id": "rd_non_template",
        }

        status_missing, body_missing = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", missing_source_payload)
        status_unknown, body_unknown = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", unknown_source_payload)
        status_non_template, body_non_template = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", non_template_payload)

        assert status_missing == 200
        assert body_missing["can_mutate"] is False
        assert body_missing["dry_run_result_preview"]["status"] == "blocked_unresolved_source"
        assert_conflict_preview_is_null(body_missing)

        assert status_unknown == 200
        assert body_unknown["can_mutate"] is False
        assert body_unknown["dry_run_result_preview"]["status"] == "blocked_unresolved_source"
        assert_conflict_preview_is_null(body_unknown)

        assert status_non_template == 200
        assert body_non_template["can_mutate"] is False
        assert body_non_template["dry_run_result_preview"]["status"] == "unsupported_source_type"
        assert_conflict_preview_is_null(body_non_template)
