from __future__ import annotations

import copy
import json
import threading
import time
from pathlib import Path
from urllib import error, request

import uvicorn

from beta_engine.main import create_app


def write_templates(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"templates": [
        {"template_id": "wt_a", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}
    ]}), encoding="utf-8")


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header("content-type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        body = json.loads(exc.read().decode())
        if isinstance(body.get("detail"), dict):
            return exc.code, body["detail"]
        return exc.code, body


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


def identity_payload(server: Server, season: str = "2035/2036") -> dict:
    preflight = {
        "target_season_label": season,
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
    }
    _, pf = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", preflight)
    _, dr = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {
        "target_season_label": season,
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
        "preflight_fingerprint": pf["preflight_fingerprint"],
        "reviewed_diff_id": pf["reviewed_diff_id"],
        "requested_by": "qa",
        "audit_reason": "phase9a",
        "explicit_confirmation": "I understand this will create a new season calendar.",
        "mutation_scope": "create_only",
    })
    return {
        "target_season_label": season,
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
        "preflight_fingerprint": pf["preflight_fingerprint"],
        "reviewed_diff_id": pf["reviewed_diff_id"],
        "dry_run_result_fingerprint": dr["dry_run_result_preview"]["dry_run_result_fingerprint"],
        "dry_run_result_id": dr["dry_run_result_preview"]["dry_run_result_id"],
        "requested_by": "qa",
        "audit_reason": "phase9a",
        "explicit_confirmation": "I understand this will create a new season calendar.",
        "mutation_scope": "create_only",
    }


def test_apply_create_only_success(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 200
        assert body["applied"] is True
        assert body["enabled"] is True
        assert body["can_execute"] is True
        assert body["can_mutate"] is True
        assert body["applied_event_count"] > 0
        assert body["created_calendar_summary"]["event_count"] == body["applied_event_count"]


def test_apply_create_only_reject_existing_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 409
        assert body["applied"] is False


def test_apply_create_only_reject_wrong_mutation_scopes(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        for scope in ("merge_preview", "overwrite_preview", "repair_preview", "create_only_preview", "merge", "overwrite", "repair"):
            payload = identity_payload(server, season=f"2035/{2036+len(scope)}")
            payload["mutation_scope"] = scope
            status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
            assert status == 400
            assert body["applied"] is False


def test_apply_create_only_reject_missing_audit_metadata(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        base = identity_payload(server)
        for key in ("audit_reason", "requested_by", "explicit_confirmation", "mutation_scope"):
            payload = copy.deepcopy(base)
            payload[key] = ""
            status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
            assert status == 400
            assert body["applied"] is False


def test_apply_create_only_reject_wrong_confirmation(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        payload["explicit_confirmation"] = "wrong"
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 400
        assert body["applied"] is False


def test_apply_create_only_reject_stale_identity(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        payload["dry_run_result_fingerprint"] = "drf_stale"
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 400
        assert body["applied"] is False


def test_contract_endpoint_stays_disabled(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-command-contract", {
            "target_season_label": "2035/2036", "source_type": "season_template", "preflight_fingerprint": "pf", "reviewed_diff_id": "rd", "dry_run_result_fingerprint": "drf", "dry_run_result_id": "drr"
        })
        assert status == 200
        assert body["enabled"] is False and body["can_execute"] is False and body["can_mutate"] is False


def test_dry_run_remains_read_only(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        _status, _body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {
            "target_season_label": "2039/2040", "source_type": "season_template", "source_template_id": "default_msa_template_preview", "preflight_fingerprint": "pf", "reviewed_diff_id": "rd"
        })
        _, cal = call("GET", f"{server.base_url}/admin/seasons/2039%2F2040/calendar")
        assert cal["calendar"] is None
