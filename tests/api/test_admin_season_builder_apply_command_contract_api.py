from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import request

import uvicorn

from beta_engine.main import create_app


MESSAGE = "Apply command contract exists, but execution is disabled in this phase."


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


def test_apply_command_contract_minimal_identity_request(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2002/2003",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "merge_preview",
            "preflight_fingerprint": "pf_123",
            "reviewed_diff_id": "rd_123",
            "dry_run_result_fingerprint": "drf_123",
            "dry_run_result_id": "drr_123",
            "requested_by": "qa",
        }
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-command-contract", payload)
        assert status == 200
        assert body["enabled"] is False
        assert body["can_execute"] is False
        assert body["can_mutate"] is False
        assert body["required_identity"]["all_identity_fields_present"] is True
        assert body["required_audit_metadata"]["all_audit_metadata_present"] is False
        assert "audit_reason will be required before apply execution is enabled in a future phase." in body["validation_warnings"]
        assert "explicit_confirmation will be required before apply execution is enabled in a future phase." in body["validation_warnings"]
        assert "mutation_scope will be required before apply execution is enabled in a future phase." in body["validation_warnings"]
        assert body["audit_preview"]["mutation_permitted"] is False
        assert body["message"] == MESSAGE


def test_apply_command_contract_missing_identity_fields(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2002/2003",
            "source_type": "season_template",
            "preflight_fingerprint": "",
            "reviewed_diff_id": "",
            "dry_run_result_fingerprint": "",
            "dry_run_result_id": "",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-command-contract", payload)
        assert "preflight_fingerprint is required before any future apply command." in body["validation_errors"]
        assert "reviewed_diff_id is required before any future apply command." in body["validation_errors"]
        assert "dry_run_result_fingerprint is required before any future apply command." in body["validation_errors"]
        assert "dry_run_result_id is required before any future apply command." in body["validation_errors"]
        assert body["required_identity"]["all_identity_fields_present"] is False
        assert body["can_execute"] is False
        assert body["can_mutate"] is False


def test_apply_command_contract_full_metadata_present(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2002/2003",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "overwrite_policy": "overwrite_preview",
            "preflight_fingerprint": "pf_123",
            "reviewed_diff_id": "rd_123",
            "dry_run_result_fingerprint": "drf_123",
            "dry_run_result_id": "drr_123",
            "requested_by": "qa",
            "audit_reason": "ticket-123",
            "explicit_confirmation": "Acknowledged",
            "mutation_scope": "none",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-command-contract", payload)
        assert "audit_reason will be required before apply execution is enabled in a future phase." not in body["validation_warnings"]
        assert "explicit_confirmation will be required before apply execution is enabled in a future phase." not in body["validation_warnings"]
        assert "mutation_scope will be required before apply execution is enabled in a future phase." not in body["validation_warnings"]
        assert body["required_audit_metadata"]["all_audit_metadata_present"] is True
        assert body["audit_preview"]["explicit_confirmation_present"] is True
        assert body["can_execute"] is False
        assert body["can_mutate"] is False


def test_apply_command_contract_does_not_create_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "preflight_fingerprint": "pf_123",
            "reviewed_diff_id": "rd_123",
            "dry_run_result_fingerprint": "drf_123",
            "dry_run_result_id": "drr_123",
        }
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-command-contract", payload)
        assert body["can_mutate"] is False

        _, calendar_body = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert calendar_body["calendar"] is None
        assert calendar_body["summary"]["calendar_exists"] is False
