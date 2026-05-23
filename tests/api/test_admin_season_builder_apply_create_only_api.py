from __future__ import annotations

import copy
import json
import threading
import time
from uuid import uuid4
from pathlib import Path
from urllib import error, parse, request

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
            database_url=f"sqlite:///{tmp_path / f'api-{uuid4().hex}.db'}",
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
        if self.thread.is_alive():
            raise RuntimeError("server did not shut down")


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
    first_candidate = dr["dry_run_result_preview"]["candidate_events"][0]
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
        "_first_candidate": first_candidate,
    }


def test_apply_create_only_success(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        first_candidate = payload.pop("_first_candidate")
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 200
        assert body["applied"] is True
        assert body["enabled"] is True
        assert body["can_execute"] is True
        assert body["can_mutate"] is True
        assert body["applied_event_count"] > 0
        assert body["created_calendar_summary"]["season"] == "2035/2036"
        assert body["created_calendar_summary"]["event_count"] == body["applied_event_count"]
        assert 0 < len(body["created_event_preview"]) <= 3
        assert body["created_calendar_identity"]["dry_run_result_fingerprint"] == payload["dry_run_result_fingerprint"]
        assert body["created_calendar_identity"]["dry_run_result_id"] == payload["dry_run_result_id"]
        assert "created_calendar_validation_preview" in body
        assert body["created_calendar_validation_preview"]["calendar_exists"] is True
        assert body["created_calendar_validation_preview"]["read_only"] is True
        assert body["created_calendar_validation_preview"]["event_count"] == body["applied_event_count"]
        assert body["created_calendar_validation_preview"]["error_count"] == 0
        assert body["created_calendar_validation_preview"]["validation_status"] in ("clean", "warnings")
        assert "issue_codes_first_10" in body["created_calendar_validation_preview"]
        assert body["apply_gate_summary"]["service_insert_succeeded"] is True
        assert body["audit_preview"]["audit_persisted"] is False
        _, calendar = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert calendar["summary"]["event_count"] == body["applied_event_count"]
        first_event = calendar["calendar"]["events"][0]
        assert body["created_event_preview"][0]["event_id"] == first_event["event_id"]
        assert body["created_event_preview"][0]["event_name"] == first_event["event_name"]
        assert body["created_event_preview"][0]["season_week"] == first_event["season_week"]
        assert body["created_event_preview"][0]["end_season_week"] == first_event["end_season_week"]
        assert body["created_event_preview"][0]["category"] == first_event["category"]
        assert body["created_event_preview"][0]["tour_level"] == first_event["tour_level"]
        assert body["created_event_preview"][0]["host_country"] == first_event["host_country"]
        assert body["created_event_preview"][0]["main_draw_size"] == first_event["main_draw_size"]
        assert first_event["event_name"] == first_candidate["event_name"]
        assert first_event["category"] == first_candidate["category"]
        assert first_event["host_country"] == first_candidate["host_country"]
        assert first_event["region"] == first_candidate["region"]
        assert first_event["season_week"] == first_candidate["season_week_start"]
        assert first_event["end_season_week"] == first_candidate["season_week_end"]
        assert first_event["duration_in_season_weeks"] == first_candidate["duration_in_season_weeks"]
        assert first_event["main_draw_size"] == first_candidate["main_draw_size"]
        assert first_event["qualification_draw_size"] == first_candidate["qualification_draw_size"]
        assert first_event["point_distribution_ref"] == first_candidate["point_distribution_ref"]
        assert first_event["prize_money"] == first_candidate["prize_money"]
        assert first_event["prestige"] == first_candidate["prestige"]
        assert first_event["tour_level"] == first_candidate["tour_level"]


def test_apply_create_only_reject_existing_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        payload.pop("_first_candidate")
        call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        _, before = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 409
        assert body["applied"] is False
        assert body["created_calendar_validation_preview"] == {}
        assert body["apply_gate_summary"]["service_insert_succeeded"] is False
        assert body["audit_preview"]["audit_persisted"] is False
        _, after = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert len(after["calendar"]["events"]) == len(before["calendar"]["events"])


def test_apply_create_only_reject_non_template_source_type(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        payload.pop("_first_candidate")
        payload["source_type"] = "calendar_clone"
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 400
        assert body["applied"] is False
        assert body["created_calendar_validation_preview"] == {}
        _, cal = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert cal["calendar"] is None


def test_apply_create_only_reject_missing_source_template_id(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        payload.pop("_first_candidate")
        payload["source_template_id"] = None
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 400
        assert body["applied"] is False
        assert body["created_calendar_validation_preview"] == {}
        _, cal = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert cal["calendar"] is None


def test_apply_create_only_reject_wrong_mutation_scopes(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        for idx, scope in enumerate(("merge_preview", "overwrite_preview", "repair_preview", "create_only_preview", "merge", "overwrite", "repair"), start=1):
            payload = identity_payload(server, season=f"{2040+idx}/{2041+idx}")
            payload.pop("_first_candidate")
            payload["mutation_scope"] = scope
            status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
            assert status == 400
            assert body["applied"] is False
            assert body["created_calendar_validation_preview"] == {}
            season_path = parse.quote(payload["target_season_label"], safe="")
            _, cal = call("GET", f"{server.base_url}/admin/seasons/{season_path}/calendar")
            assert cal["calendar"] is None


def test_apply_create_only_reject_missing_audit_metadata(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        base = identity_payload(server)
        base.pop("_first_candidate")
        for key in ("audit_reason", "requested_by", "explicit_confirmation", "mutation_scope"):
            payload = copy.deepcopy(base)
            payload[key] = ""
            status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
            assert status == 400
            assert body["applied"] is False
            assert body["created_calendar_validation_preview"] == {}
            season_path = parse.quote(payload["target_season_label"], safe="")
            _, cal = call("GET", f"{server.base_url}/admin/seasons/{season_path}/calendar")
            assert cal["calendar"] is None


def test_apply_create_only_reject_wrong_confirmation(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        payload.pop("_first_candidate")
        payload["explicit_confirmation"] = "wrong"
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 400
        assert body["applied"] is False
        assert body["created_calendar_validation_preview"] == {}
        _, cal = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert cal["calendar"] is None


def test_apply_create_only_reject_stale_identity(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = identity_payload(server)
        payload.pop("_first_candidate")
        payload["dry_run_result_fingerprint"] = "drf_stale"
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", payload)
        assert status == 400
        assert body["applied"] is False
        assert body["created_calendar_validation_preview"] == {}
        _, cal = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert cal["calendar"] is None


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
