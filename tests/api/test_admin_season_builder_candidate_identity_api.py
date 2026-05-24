from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import request

import uvicorn

from beta_engine.main import create_app


def write_templates(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "template_id": "default_msa_template_preview",
                        "tour_level": "WORLD_TOUR",
                        "category": "PLATINUM",
                        "event_name": "World A",
                        "region": "EUROPE",
                        "host_country": "ENG",
                        "main_draw_size": 32,
                        "qualification_draw_size": 16,
                        "seeds_count": 8,
                        "qualifier_spots": 4,
                        "wild_cards": 2,
                        "byes": 0,
                        "lucky_loser_rules": {
                            "enabled": True,
                            "max_spots": 2,
                            "replacement_window": "pre_main_draw_round_1",
                        },
                        "point_distribution_ref": "world",
                        "prize_money": 100000,
                        "prestige": 9,
                        "event_duration_days": 6,
                        "qualification_duration_days": 2,
                        "duration_in_season_weeks": 1,
                        "active": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


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


def assert_candidate_identity_summary_contract(summary: dict, candidate_events: list[dict]) -> None:
    assert summary is not None
    assert summary["candidate_count"] == len(candidate_events)
    assert summary["candidate_ids"] == [candidate["candidate_id"] for candidate in candidate_events]
    assert summary["candidate_identity_keys"] == [candidate["candidate_identity_key"] for candidate in candidate_events]
    assert isinstance(summary["duplicate_candidate_ids"], list)
    assert isinstance(summary["duplicate_candidate_identity_keys"], list)
    assert summary["read_only"] is True
    assert summary["mutation_permitted"] is False
    assert isinstance(summary["message"], str) and summary["message"]


def assert_candidate_identity_contract(contract: dict, summary: dict) -> None:
    assert contract is not None
    assert contract["identity_source"] == "season_template_slot"
    assert contract["id_strategy"] == "sanitized_template_slot_week"
    assert contract["key_strategy"] == "pipe_joined_sanitized_components"
    assert contract["key_components"] == [
        "target_season",
        "source_type",
        "source_template_id",
        "source_slot_id",
        "season_week_start",
        "event_name",
        "category",
        "source_template_ref",
    ]
    assert contract["candidate_count"] == summary["candidate_count"]
    assert contract["has_duplicate_candidate_ids"] == bool(summary["duplicate_candidate_ids"])
    assert contract["has_duplicate_candidate_identity_keys"] == bool(summary["duplicate_candidate_identity_keys"])
    expected_safe = (
        summary["candidate_count"] > 0
        and not summary["duplicate_candidate_ids"]
        and not summary["duplicate_candidate_identity_keys"]
    )
    assert contract["safe_for_future_reference"] == expected_safe
    assert contract["read_only"] is True
    assert contract["mutation_permitted"] is False
    assert isinstance(contract["message"], str) and contract["message"]




def assert_candidate_identity_overview(overview: dict, summary: dict, contract: dict) -> None:
    assert overview is not None
    assert overview["candidate_count"] == summary["candidate_count"]
    assert overview["safe_for_future_reference"] == contract["safe_for_future_reference"]
    assert overview["has_duplicate_candidate_ids"] == contract["has_duplicate_candidate_ids"]
    assert overview["has_duplicate_candidate_identity_keys"] == contract["has_duplicate_candidate_identity_keys"]
    assert overview["read_only"] is True
    assert overview["mutation_permitted"] is False



def assert_candidate_identity_fingerprint(fingerprint: dict, summary: dict, contract: dict) -> None:
    assert isinstance(fingerprint.get("fingerprint"), str) and fingerprint["fingerprint"]
    assert fingerprint["fingerprint_algorithm"] == "sha256"
    assert fingerprint["fingerprint_payload_version"] == 1
    assert fingerprint["candidate_count"] == summary["candidate_count"]
    assert fingerprint["candidate_ids"] == summary["candidate_ids"]
    assert fingerprint["candidate_identity_keys"] == summary["candidate_identity_keys"]
    assert fingerprint["safe_for_future_reference"] == contract["safe_for_future_reference"]
    assert fingerprint["read_only"] is True
    assert fingerprint["mutation_permitted"] is False


def assert_candidate_identity_review_reference(review_reference: dict, fingerprint: dict) -> None:
    assert review_reference["reference_type"] == "candidate_identity_set"
    assert review_reference["reference_id"] == fingerprint["fingerprint"]
    assert review_reference["candidate_count"] == fingerprint["candidate_count"]
    assert review_reference["safe_for_future_reference"] == fingerprint["safe_for_future_reference"]
    assert review_reference["read_only"] is True
    assert review_reference["mutation_permitted"] is False


def assert_candidate_identity_fingerprint_and_review_reference(
    preview: dict,
    summary: dict,
    contract: dict,
) -> tuple[dict, dict]:
    fingerprint = preview["candidate_identity_fingerprint"]
    review_reference = preview["candidate_identity_review_reference"]
    assert_candidate_identity_fingerprint(fingerprint, summary, contract)
    assert_candidate_identity_review_reference(review_reference, fingerprint)
    return fingerprint, review_reference


def assert_identity_readiness_candidate_reference_contract(preview: dict) -> tuple[dict, dict, dict]:
    identity_readiness = preview["identity_readiness"]
    future_reference = identity_readiness["future_command_reference"]
    assert "candidate_identity_fingerprint" in future_reference
    assert "candidate_identity_reference_id" in future_reference
    assert "can_reference_candidate_identity_set" in future_reference
    assert isinstance(future_reference["can_reference_candidate_identity_set"], bool)
    assert "candidate_identity_reference_type" in future_reference
    assert future_reference["mutation_still_disabled"] is True
    assert isinstance(future_reference["can_reference_future_command"], bool)
    candidate_reference_item = next(
        item for item in identity_readiness["items"] if item["area"] == "candidate_identity_review_reference"
    )
    assert candidate_reference_item["status"] in {"OK", "BLOCKED"}
    assert isinstance(candidate_reference_item["message"], str) and candidate_reference_item["message"]
    overview = identity_readiness["candidate_identity_readiness_overview"]
    assert isinstance(overview["available"], bool)
    assert isinstance(overview["can_reference_candidate_identity_set"], bool)
    assert overview["candidate_reference_status"] in {"OK", "BLOCKED"}
    assert isinstance(overview["main_future_command_reference_ready"], bool)
    assert overview["read_only"] is True
    assert overview["mutation_permitted"] is False
    assert isinstance(overview["message"], str) and overview["message"]
    return future_reference, candidate_reference_item, overview


def assert_candidate_identity_readiness_overview_parity(
    overview: dict,
    future_reference: dict,
    candidate_reference_item: dict,
) -> None:
    assert overview["candidate_identity_fingerprint"] == future_reference["candidate_identity_fingerprint"]
    assert overview["candidate_identity_reference_id"] == future_reference["candidate_identity_reference_id"]
    assert overview["candidate_identity_reference_type"] == future_reference["candidate_identity_reference_type"]
    assert overview["can_reference_candidate_identity_set"] == future_reference["can_reference_candidate_identity_set"]
    assert overview["candidate_reference_status"] == candidate_reference_item["status"]
    assert overview["main_future_command_reference_ready"] == future_reference["can_reference_future_command"]
    assert overview["read_only"] is True
    assert overview["mutation_permitted"] is False
    assert isinstance(overview["message"], str) and overview["message"]


def assert_future_apply_reference_contract(
    preview: dict,
    fingerprint: dict,
    review_reference: dict,
    identity_readiness: dict,
) -> dict:
    contract = preview["future_apply_reference_contract"]
    assert isinstance(contract, dict)
    assert contract["contract_type"] == "future_apply_reference_contract"
    assert contract["candidate_identity_reference_id"] == review_reference["reference_id"]
    assert contract["candidate_identity_reference_type"] == review_reference["reference_type"]
    assert contract["candidate_identity_fingerprint"] == fingerprint["fingerprint"]
    assert contract["candidate_identity_set_referenceable"] == review_reference["can_reference_future_apply"]
    assert contract["main_future_command_reference_ready"] == identity_readiness["future_command_reference"]["can_reference_future_command"]
    assert contract["apply_execution_enabled"] is False
    assert contract["create_only_apply_required"] is True
    assert contract["read_only"] is True
    assert contract["mutation_permitted"] is False
    assert isinstance(contract["message"], str) and contract["message"]
    return contract


def assert_future_apply_validation_preview_disabled_response(body: dict) -> dict:
    assert body["enabled"] is False
    assert body["can_execute"] is False
    assert body["can_mutate"] is False
    audit_preview = body["audit_preview"]
    assert isinstance(audit_preview, dict)
    assert audit_preview["action"] == "season_builder_future_apply_request_validation_preview"
    assert audit_preview["read_only"] is True
    assert audit_preview["mutation_permitted"] is False
    assert audit_preview["execution_enabled"] is False
    assert isinstance(body["future_apply_reference_contract"], dict)
    validation_preview = body["future_apply_request_validation_preview"]
    assert isinstance(validation_preview, dict)
    assert validation_preview["apply_execution_enabled"] is False
    assert validation_preview["read_only"] is True
    assert validation_preview["mutation_permitted"] is False
    assert validation_preview["validation_type"] == "future_apply_request_validation_preview"
    assert isinstance(validation_preview["message"], str) and validation_preview["message"]
    return validation_preview


def test_candidate_identity_api_resolved_parity(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_phase14e_resolved",
            "reviewed_diff_id": "rd_phase14e_resolved",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200
        preview = body["dry_run_result_preview"]
        candidate_events = preview["candidate_events"]
        assert len(candidate_events) > 0

        for candidate in candidate_events:
            assert isinstance(candidate["candidate_id"], str) and candidate["candidate_id"]
            assert isinstance(candidate["candidate_identity_key"], str) and candidate["candidate_identity_key"]
            assert candidate["identity_source"] == "season_template_slot"
            assert candidate["read_only"] is True
            assert candidate["mutation_permitted"] is False

        summary = preview["candidate_identity_summary"]
        contract = preview["candidate_identity_contract"]
        assert_candidate_identity_summary_contract(summary, candidate_events)
        assert_candidate_identity_contract(contract, summary)
        overview = preview["candidate_identity_overview"]
        assert_candidate_identity_overview(overview, summary, contract)
        fingerprint, review_reference = assert_candidate_identity_fingerprint_and_review_reference(preview, summary, contract)
        assert review_reference["can_reference_future_apply"] is True
        future_reference, candidate_reference_item, readiness_overview = assert_identity_readiness_candidate_reference_contract(preview)
        assert future_reference["candidate_identity_fingerprint"] == fingerprint["fingerprint"]
        assert future_reference["candidate_identity_reference_id"] == review_reference["reference_id"]
        assert future_reference["can_reference_candidate_identity_set"] == review_reference["can_reference_future_apply"]
        assert future_reference["candidate_identity_reference_type"] == review_reference["reference_type"]
        assert candidate_reference_item["status"] == "OK"
        future_apply_contract = assert_future_apply_reference_contract(
            preview,
            fingerprint,
            review_reference,
            preview["identity_readiness"],
        )
        assert future_apply_contract["available"] is True
        assert future_apply_contract["candidate_identity_set_referenceable"] is True
        assert_candidate_identity_readiness_overview_parity(
            readiness_overview,
            future_reference,
            candidate_reference_item,
        )
        assert readiness_overview["candidate_reference_status"] == "OK"
        assert readiness_overview["can_reference_candidate_identity_set"] is True
        if not summary["duplicate_candidate_ids"] and not summary["duplicate_candidate_identity_keys"]:
            assert contract["safe_for_future_reference"] is True


def test_candidate_identity_api_is_deterministic_for_repeated_dry_runs(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_phase14e_deterministic",
            "reviewed_diff_id": "rd_phase14e_deterministic",
        }
        status_first, body_first = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        status_second, body_second = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status_first == 200
        assert status_second == 200

        first_preview = body_first["dry_run_result_preview"]
        second_preview = body_second["dry_run_result_preview"]
        first_candidates = first_preview["candidate_events"]
        second_candidates = second_preview["candidate_events"]

        assert [c["candidate_id"] for c in first_candidates] == [c["candidate_id"] for c in second_candidates]
        assert [c["candidate_identity_key"] for c in first_candidates] == [c["candidate_identity_key"] for c in second_candidates]
        assert first_preview["candidate_identity_summary"] == second_preview["candidate_identity_summary"]
        assert first_preview["candidate_identity_contract"] == second_preview["candidate_identity_contract"]
        assert first_preview["candidate_identity_fingerprint"] == second_preview["candidate_identity_fingerprint"]
        assert first_preview["candidate_identity_review_reference"] == second_preview["candidate_identity_review_reference"]


def test_candidate_identity_api_unresolved_source_contract_invariants(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "unknown_template",
            "preflight_fingerprint": "pf_phase14e_unresolved",
            "reviewed_diff_id": "rd_phase14e_unresolved",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200

        preview = body["dry_run_result_preview"]
        assert preview["candidate_events"] == []
        summary = preview["candidate_identity_summary"]
        contract = preview["candidate_identity_contract"]
        assert_candidate_identity_summary_contract(summary, preview["candidate_events"])
        assert_candidate_identity_contract(contract, summary)
        overview = preview["candidate_identity_overview"]
        assert_candidate_identity_overview(overview, summary, contract)
        fingerprint, review_reference = assert_candidate_identity_fingerprint_and_review_reference(
            preview, summary, contract
        )
        assert fingerprint["candidate_count"] == 0
        assert fingerprint["safe_for_future_reference"] is False
        assert review_reference["can_reference_future_apply"] is False
        future_reference, candidate_reference_item, readiness_overview = assert_identity_readiness_candidate_reference_contract(preview)
        assert future_reference["can_reference_candidate_identity_set"] is False
        assert future_reference["candidate_identity_fingerprint"] == fingerprint["fingerprint"]
        assert future_reference["candidate_identity_reference_id"] == review_reference["reference_id"]
        assert candidate_reference_item["status"] == "BLOCKED"
        assert_candidate_identity_readiness_overview_parity(
            readiness_overview,
            future_reference,
            candidate_reference_item,
        )
        assert readiness_overview["candidate_reference_status"] == "BLOCKED"
        assert readiness_overview["can_reference_candidate_identity_set"] is False
        assert future_reference["mutation_still_disabled"] is True
        assert future_reference["can_reference_future_command"] == (preview["identity_readiness"]["status"] == "ready_reference")
        future_apply_contract = assert_future_apply_reference_contract(
            preview,
            fingerprint,
            review_reference,
            preview["identity_readiness"],
        )
        assert future_apply_contract["available"] is False
        assert future_apply_contract["candidate_identity_set_referenceable"] is False
        assert contract["safe_for_future_reference"] is False
        assert "no candidates" in str(contract["message"]).lower()
        assert overview["available"] is False
        assert overview["safe_for_future_reference"] is False
        assert "no candidates" in str(overview["message"]).lower()


def test_candidate_identity_api_unsupported_source_contract_invariants(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "blank_calendar_planned",
            "preflight_fingerprint": "pf_phase14e_unsupported",
            "reviewed_diff_id": "rd_phase14e_unsupported",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert status == 200

        preview = body["dry_run_result_preview"]
        assert preview["status"] == "unsupported_source_type"
        assert preview["candidate_events"] == []
        summary = preview["candidate_identity_summary"]
        contract = preview["candidate_identity_contract"]
        assert_candidate_identity_summary_contract(summary, preview["candidate_events"])
        assert_candidate_identity_contract(contract, summary)
        overview = preview["candidate_identity_overview"]
        assert_candidate_identity_overview(overview, summary, contract)
        fingerprint, review_reference = assert_candidate_identity_fingerprint_and_review_reference(
            preview, summary, contract
        )
        assert fingerprint["candidate_count"] == 0
        assert fingerprint["safe_for_future_reference"] is False
        assert review_reference["can_reference_future_apply"] is False
        future_reference, candidate_reference_item, readiness_overview = assert_identity_readiness_candidate_reference_contract(preview)
        assert future_reference["can_reference_candidate_identity_set"] is False
        assert future_reference["candidate_identity_fingerprint"] == fingerprint["fingerprint"]
        assert future_reference["candidate_identity_reference_id"] == review_reference["reference_id"]
        assert candidate_reference_item["status"] == "BLOCKED"
        assert_candidate_identity_readiness_overview_parity(
            readiness_overview,
            future_reference,
            candidate_reference_item,
        )
        assert readiness_overview["candidate_reference_status"] == "BLOCKED"
        assert readiness_overview["can_reference_candidate_identity_set"] is False
        assert future_reference["mutation_still_disabled"] is True
        assert future_reference["can_reference_future_command"] == (preview["identity_readiness"]["status"] == "ready_reference")
        future_apply_contract = assert_future_apply_reference_contract(
            preview,
            fingerprint,
            review_reference,
            preview["identity_readiness"],
        )
        assert future_apply_contract["available"] is False
        assert future_apply_contract["candidate_identity_set_referenceable"] is False
        assert contract["safe_for_future_reference"] is False
        assert "no candidates" in str(contract["message"]).lower()
        assert overview["available"] is False
        assert overview["safe_for_future_reference"] is False
        assert "no candidates" in str(overview["message"]).lower()


def test_future_apply_request_validation_preview_matching_resolved_request(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        base_payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_phase15c_match",
            "reviewed_diff_id": "rd_phase15c_match",
        }
        _, dry_run_body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", base_payload)
        preview = dry_run_body["dry_run_result_preview"]
        contract = preview["future_apply_reference_contract"]
        review_ref = preview["candidate_identity_review_reference"]
        fingerprint = preview["candidate_identity_fingerprint"]

        payload = {
            **base_payload,
            "requested_candidate_identity_reference_id": review_ref["reference_id"],
            "requested_candidate_identity_fingerprint": fingerprint["fingerprint"],
            "requested_candidate_identity_reference_type": review_ref["reference_type"],
        }
        status, body = call(
            "POST",
            f"{server.base_url}/admin/seasons/builder/future-apply-request-validation-preview",
            payload,
        )
        assert status == 200
        validation_preview = assert_future_apply_validation_preview_disabled_response(body)
        assert body["future_apply_reference_contract"] == contract
        assert validation_preview["available"] is True
        assert body["can_execute"] is False
        assert body["can_mutate"] is False
        assert validation_preview["apply_execution_enabled"] is False
        assert body["audit_preview"]["execution_enabled"] is False
        assert body["audit_preview"]["mutation_permitted"] is False
        assert validation_preview["reference_id_matches"] is True
        assert validation_preview["fingerprint_matches"] is True
        assert validation_preview["reference_type_matches"] is True


def test_future_apply_request_validation_preview_mismatched_resolved_request(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        base_payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_phase15c_mismatch",
            "reviewed_diff_id": "rd_phase15c_mismatch",
        }
        _, dry_run_body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", base_payload)
        dry_run_contract = dry_run_body["dry_run_result_preview"]["future_apply_reference_contract"]
        payload = {
            **base_payload,
            "requested_candidate_identity_reference_id": "wrong_ref",
            "requested_candidate_identity_fingerprint": "wrong_fp",
            "requested_candidate_identity_reference_type": "wrong_type",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/future-apply-request-validation-preview", payload)
        assert status == 200
        assert body["future_apply_reference_contract"] == dry_run_contract
        validation_preview = assert_future_apply_validation_preview_disabled_response(body)
        assert validation_preview["available"] is False
        assert validation_preview["reference_id_matches"] is False
        assert validation_preview["fingerprint_matches"] is False
        assert validation_preview["reference_type_matches"] is False


def test_future_apply_request_validation_preview_missing_requested_values(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        base_payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_phase15c_missing",
            "reviewed_diff_id": "rd_phase15c_missing",
        }
        _, dry_run_body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", base_payload)
        dry_run_contract = dry_run_body["dry_run_result_preview"]["future_apply_reference_contract"]
        payload = {**base_payload}
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/future-apply-request-validation-preview", payload)
        assert status == 200
        assert body["future_apply_reference_contract"] == dry_run_contract
        validation_preview = assert_future_apply_validation_preview_disabled_response(body)
        assert validation_preview["requested_candidate_identity_reference_id"] == ""
        assert validation_preview["requested_candidate_identity_fingerprint"] == ""
        assert validation_preview["requested_candidate_identity_reference_type"] == ""
        assert validation_preview["available"] is False
        assert validation_preview["reference_id_matches"] is False
        assert validation_preview["fingerprint_matches"] is False
        assert validation_preview["reference_type_matches"] is False


def test_future_apply_request_validation_preview_unsupported_source(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        base_payload = {
            "target_season_label": "2035/2036",
            "source_type": "blank_calendar_planned",
            "preflight_fingerprint": "pf_phase15c_unsupported",
            "reviewed_diff_id": "rd_phase15c_unsupported",
        }
        _, dry_run_body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", base_payload)
        dry_run_contract = dry_run_body["dry_run_result_preview"]["future_apply_reference_contract"]
        payload = {**base_payload}
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/future-apply-request-validation-preview", payload)
        assert status == 200
        assert body["future_apply_reference_contract"] == dry_run_contract
        validation_preview = assert_future_apply_validation_preview_disabled_response(body)
        contract = body["future_apply_reference_contract"]
        assert contract["available"] is False
        assert validation_preview["available"] is False
        assert validation_preview["contract_referenceable"] is False


def test_future_apply_request_validation_preview_unresolved_source_template(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "missing_template_phase15d",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_phase15d_unresolved",
            "reviewed_diff_id": "rd_phase15d_unresolved",
        }
        dry_run_status, dry_run_body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", payload)
        assert dry_run_status == 200
        dry_run_preview = dry_run_body["dry_run_result_preview"]
        assert dry_run_preview["candidate_events"] == []
        assert dry_run_preview["candidate_identity_summary"]["candidate_count"] == 0
        dry_run_contract = dry_run_preview["future_apply_reference_contract"]
        assert dry_run_contract["available"] is False
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/future-apply-request-validation-preview", payload)
        assert status == 200
        assert body["future_apply_reference_contract"] == dry_run_contract
        validation_preview = assert_future_apply_validation_preview_disabled_response(body)
        assert validation_preview["available"] is False
        assert validation_preview["contract_referenceable"] is False
