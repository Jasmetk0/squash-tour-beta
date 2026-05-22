from __future__ import annotations

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
        {"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}
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


def create_only_apply(server: Server, season: str = "2035/2036") -> None:
    _, pf = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", {
        "target_season_label": season,
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
    })
    _, dr = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {
        "target_season_label": season,
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
        "preflight_fingerprint": pf["preflight_fingerprint"],
        "reviewed_diff_id": pf["reviewed_diff_id"],
        "requested_by": "qa",
        "audit_reason": "phase11a",
        "explicit_confirmation": "I understand this will create a new season calendar.",
        "mutation_scope": "create_only",
    })
    status, body = call("POST", f"{server.base_url}/admin/seasons/builder/apply-create-only-command", {
        "target_season_label": season,
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
        "preflight_fingerprint": pf["preflight_fingerprint"],
        "reviewed_diff_id": pf["reviewed_diff_id"],
        "dry_run_result_fingerprint": dr["dry_run_result_preview"]["dry_run_result_fingerprint"],
        "dry_run_result_id": dr["dry_run_result_preview"]["dry_run_result_id"],
        "requested_by": "qa",
        "audit_reason": "phase11a",
        "explicit_confirmation": "I understand this will create a new season calendar.",
        "mutation_scope": "create_only",
    })
    assert status == 200
    assert body["applied"] is True


def test_validation_endpoint_missing_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar/validation")
        assert status == 200
        assert body["calendar_exists"] is False
        assert body["read_only"] is True
        assert body["validation_summary"]["status"] == "warnings"
        assert any(issue["code"] == "calendar_missing" for issue in body["issues"])


def test_validation_endpoint_for_created_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        create_only_apply(server)
        calendar_status, calendar_body = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar")
        assert calendar_status == 200
        assert calendar_body["calendar"] is not None
        events = calendar_body["calendar"]["events"]
        assert len(events) > 0
        first_event = events[0]
        assert first_event["template_id"] == "default_msa_template_preview"

        status, body = call("GET", f"{server.base_url}/admin/seasons/2035%2F2036/calendar/validation")
        assert status == 200
        assert body["calendar_exists"] is True
        assert body["read_only"] is True
        assert body["validation_summary"]["event_count"] == len(events)
        assert body["validation_summary"]["error_count"] == 0
        assert not any(issue["severity"] == "error" for issue in body["issues"])
        assert body["validation_summary"]["status"] in {"clean", "warnings"}
        assert body["validation_summary"]["categories"]["values"]
        assert body["validation_summary"]["tour_levels"]["values"]


def test_validation_endpoint_invalid_season_label(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, _body = call("GET", f"{server.base_url}/admin/seasons/not-a-season/calendar/validation")
        assert status == 400


def test_validation_endpoint_invalid_persisted_calendar_flags_errors(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        registry_path = tmp_path / "season_calendars.json"
        registry_path.write_text(json.dumps({
            "calendars_by_season": {
                "2038/2039": {
                    "season": "2038/2039",
                    "events": [
                        {
                            "event_id": "EVT-2038-W01-default_msa_template_preview",
                            "season": "2038/2039",
                            "season_week": 20,
                            "calendar_year": 2038,
                            "year_week": 20,
                            "template_id": "default_msa_template_preview",
                            "event_name": "Broken Event",
                            "category": "PLATINUM",
                            "tour_level": "WORLD_TOUR",
                            "host_country": "ENG",
                            "region": "EUROPE",
                            "duration_in_season_weeks": 1,
                            "start_season_week": 20,
                            "end_season_week": 19,
                            "status": "planned",
                            "main_draw_size": 0,
                            "qualification_draw_size": 0,
                            "seeds_count": 0,
                            "qualifier_spots": 0,
                            "wild_cards": 0,
                            "byes": 0,
                            "point_distribution_ref": "world",
                            "prize_money": 0,
                            "prestige": 0,
                        }
                    ]
                }
            }
        }), encoding="utf-8")

        status, body = call("GET", f"{server.base_url}/admin/seasons/2038%2F2039/calendar/validation")
        assert status == 200
        assert body["calendar_exists"] is True
        assert body["validation_summary"]["status"] == "errors"
        issue_codes = {issue["code"] for issue in body["issues"]}
        assert "season_week_after_end_week" in issue_codes
        assert "main_draw_size_invalid" in issue_codes


def test_validation_endpoint_malformed_registry_json_returns_structured_error(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        registry_path = tmp_path / "season_calendars.json"
        registry_path.write_text('{"calendars_by_season": {"2038/2039":', encoding="utf-8")

        status, body = call("GET", f"{server.base_url}/admin/seasons/2038%2F2039/calendar/validation")
        assert status == 200
        assert body["calendar_exists"] is False
        assert body["read_only"] is True
        assert body["validation_summary"]["status"] == "errors"
        assert body["validation_summary"]["error_count"] >= 1
        issue = next(issue for issue in body["issues"] if issue["code"] == "calendar_registry_parse_error")
        assert issue["context"]["exception_type"] == "JSONDecodeError"
        assert "2038/2039" not in issue["message"]
        assert "calendars_by_season" not in issue["message"]
        assert "calendars_by_season" not in json.dumps(issue["context"])


def test_validation_endpoint_model_invalid_registry_returns_structured_error(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        registry_path = tmp_path / "season_calendars.json"
        duplicate_event = {
            "event_id": "EVT-DUPLICATE-1",
            "season": "2038/2039",
            "season_week": 20,
            "calendar_year": 2038,
            "year_week": 20,
            "template_id": "default_msa_template_preview",
            "event_name": "Broken Event",
            "category": "PLATINUM",
            "tour_level": "WORLD_TOUR",
            "host_country": "ENG",
            "region": "EUROPE",
            "duration_in_season_weeks": 1,
            "start_season_week": 20,
            "end_season_week": 20,
            "status": "planned",
            "main_draw_size": 32,
            "qualification_draw_size": 16,
            "seeds_count": 8,
            "qualifier_spots": 4,
            "wild_cards": 2,
            "byes": 0,
            "point_distribution_ref": "world",
            "prize_money": 100000,
            "prestige": 9,
        }
        registry_path.write_text(json.dumps({
            "calendars_by_season": {
                "2038/2039": {
                    "season": "2038/2039",
                    "events": [duplicate_event, dict(duplicate_event)],
                }
            }
        }), encoding="utf-8")

        status, body = call("GET", f"{server.base_url}/admin/seasons/2038%2F2039/calendar/validation")
        assert status == 200
        assert body["read_only"] is True
        assert body["validation_summary"]["status"] == "errors"
        issue = next(issue for issue in body["issues"] if issue["code"] == "calendar_registry_model_error")
        assert issue["context"]["exception_type"] == "ValidationError"
        assert "EVT-DUPLICATE-1" not in issue["message"]
        assert "Duplicate event_id" not in issue["message"]
        assert "EVT-DUPLICATE-1" not in json.dumps(issue["context"])
