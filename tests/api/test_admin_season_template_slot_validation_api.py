from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import error, request

import uvicorn

from beta_engine.main import create_app


def write_templates(path: Path, templates: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"templates": templates}), encoding="utf-8")


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header("content-type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        body = json.loads(exc.read().decode())
        return exc.code, body.get("detail", body)


def free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Server:
    def __init__(self, tmp_path: Path, templates: list[dict]) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        template_path = tmp_path / "templates.json"
        write_templates(template_path, templates)
        app = create_app(database_url=f"sqlite:///{tmp_path / 'api.db'}", tournament_templates_config_path=str(template_path), season_calendar_registry_path=str(tmp_path / "season_calendars.json"))
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


def _preflight(server: Server):
    return call("POST", f"{server.base_url}/admin/seasons/builder/preflight", {
        "target_season_label": "2035/2036",
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
    })


def test_default_template_no_blocking_template_slot_errors(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, body = _preflight(server)
        assert status == 200
        assert not any("[template_slot_" in err for err in body["validation_errors"])


def test_duplicate_and_overload_warnings_surface(tmp_path: Path) -> None:
    base = {"tour_level": "WORLD_TOUR", "category": "PLATINUM", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}
    templates = [dict(base, template_id=f"default_msa_template_preview" if i == 0 else f"dup_{i}", event_name=f"Same Event {i}", duration_in_season_weeks=5) for i in range(5)]
    with Server(tmp_path, templates) as server:
        status, body = _preflight(server)
        assert status == 200
        assert any("template_slot_category_tour_level_week_overloaded" in w for w in body["validation_warnings"])
        assert any("template_slot_duration_long" in w for w in body["validation_warnings"])
