from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

import uvicorn

from beta_engine.main import create_app


def write_templates(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"templates": [
        {"template_id": "wt_a", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True},
        {"template_id": "et_a", "tour_level": "ELITE_TOUR", "category": "ELITE", "event_name": "Elite A", "region": "ASIA", "host_country": "MAS", "main_draw_size": 24, "qualification_draw_size": 8, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "elite", "prize_money": 25000, "prestige": 4, "event_duration_days": 5, "qualification_duration_days": 2, "duration_in_season_weeks": 2, "active": True}
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
            calendar_config_dir=str(tmp_path / "legacy_calendars"),
            season_calendar_registry_path=str(tmp_path / "season_calendars.json"),
            season_category_points_registry_path=str(tmp_path / "season_category_points.json"),
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


def test_get_empty_calendar_state(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/calendar")
        assert status == 200
        assert body["calendar"] is None
        assert body["summary"]["calendar_exists"] is False


def test_get_calendar_accepts_long_and_compact_labels_equivalently(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {"seed": 5, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/calendar/build", payload)
        _, long_body = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/calendar")
        _, compact_body = call("GET", f"{server.base_url}/admin/seasons/2000%2F01/calendar")
        assert compact_body == long_body


def test_get_calendar_invalid_season_label_returns_400(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        for label in ("2000%2F03", "not-a-season"):
            try:
                call("GET", f"{server.base_url}/admin/seasons/{label}/calendar")
            except HTTPError as exc:
                assert exc.code == 400
            else:
                raise AssertionError(f"invalid season label {label} should fail")


def test_post_dry_run_and_persist_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {"seed": 12345, "dry_run": True, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        status, preview = call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/calendar/build", payload)
        assert status == 200
        assert preview["summary"]["event_count"] == 2
        assert preview["calendar"]["events"][0]["season_week"] >= 1
        _, empty = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/calendar")
        assert empty["calendar"] is None

        payload["dry_run"] = False
        status, persisted = call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/calendar/build", payload)
        assert status == 200
        assert persisted["summary"]["persisted"] is True
        _, loaded = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/calendar")
        assert loaded["summary"]["event_count"] == 2
        assert loaded["validation_warnings"]


def test_calendar_overwrite_safety(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {"seed": 1, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/calendar/build", payload)
        try:
            call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/calendar/build", payload)
        except HTTPError as exc:
            assert exc.code == 400
            assert "already exists" in exc.read().decode()
        else:
            raise AssertionError("overwrite safety should reject existing calendar")
