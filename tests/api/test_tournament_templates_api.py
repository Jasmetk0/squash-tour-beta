from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib import error, request

import uvicorn

from beta_engine.main import create_app


TEMPLATE = {
    "template_id": "custom_opener_16",
    "tour_level": "WORLD_TOUR",
    "category": "CUSTOM_OPENER",
    "event_name": "Custom Opener",
    "region": "EUROPE",
    "host_country": "ENG",
    "main_draw_size": 16,
    "qualification_draw_size": 8,
    "seeds_count": 4,
    "qualifier_spots": 2,
    "wild_cards": 2,
    "byes": 0,
    "lucky_loser_rules": {"enabled": True, "max_spots": 1, "replacement_window": "pre_main_draw_round_1"},
    "point_distribution": {
        "winner": 500,
        "finalist": 300,
        "semifinalist": 180,
        "quarterfinalist": 90,
        "round_of_16": 45,
        "round_of_32": 0,
    },
    "event_duration_days": 5,
    "qualification_duration_days": 1,
    "preferred_week_type": "standard",
    "seasonal_grouping": "custom_swing",
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ApiServer:
    def __init__(self, *, tmp_path: Path, tournament_templates_config_path: str, calendar_config_dir: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(
            database_url=f"sqlite:///{tmp_path / 'tournament-templates.db'}",
            tournament_templates_config_path=tournament_templates_config_path,
            calendar_config_dir=calendar_config_dir,
        )
        self.server = uvicorn.Server(uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> "ApiServer":
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                _request("GET", f"{self.base_url}/health")
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def _request(method: str, url: str, payload: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method=method)
    req.add_header("content-type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        return int(exc.code), parsed


def _write_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"templates": [TEMPLATE]}, indent=2) + "\n", encoding="utf-8")


def test_list_tournament_templates_endpoint(tmp_path) -> None:
    templates_path = tmp_path / "templates.json"
    _write_fixture(templates_path)
    with ApiServer(tmp_path=tmp_path, tournament_templates_config_path=str(templates_path), calendar_config_dir=str(tmp_path / "calendars")) as server:
        status, payload = _request("GET", f"{server.base_url}/world/tournament-templates")
        assert status == 200
        assert payload["templates"][0]["template_id"] == "custom_opener_16"
        status, meta = _request("GET", f"{server.base_url}/world/tournament-templates/metadata")
        assert status == 200
        assert meta["template_count"] == 1


def test_create_update_reject_duplicate_and_delete_tournament_template(tmp_path) -> None:
    templates_path = tmp_path / "templates.json"
    _write_fixture(templates_path)
    with ApiServer(tmp_path=tmp_path, tournament_templates_config_path=str(templates_path), calendar_config_dir=str(tmp_path / "calendars")) as server:
        new_template = {**TEMPLATE, "template_id": "user_diamond_32", "category": "USER_DIAMOND", "main_draw_size": 32}
        status, created = _request("POST", f"{server.base_url}/world/tournament-templates", new_template)
        assert status == 201
        assert created["template_id"] == "user_diamond_32"

        status, duplicate = _request("POST", f"{server.base_url}/world/tournament-templates", new_template)
        assert status == 409
        assert "already exists" in duplicate["detail"]

        updated_payload = {**new_template, "event_name": "User Diamond Updated", "lucky_loser_rules": {**new_template["lucky_loser_rules"], "max_spots": 2}}
        status, updated = _request("PUT", f"{server.base_url}/world/tournament-templates/user_diamond_32", updated_payload)
        assert status == 200
        assert updated["event_name"] == "User Diamond Updated"
        assert updated["lucky_loser_rules"]["max_spots"] == 2

        status, _ = _request("DELETE", f"{server.base_url}/world/tournament-templates/user_diamond_32")
        assert status == 204

        status, payload = _request("GET", f"{server.base_url}/world/tournament-templates")
        assert status == 200
        assert [template["template_id"] for template in payload["templates"]] == ["custom_opener_16"]


def test_delete_referenced_template_returns_clear_error(tmp_path) -> None:
    templates_path = tmp_path / "templates.json"
    calendars = tmp_path / "calendars"
    calendars.mkdir()
    _write_fixture(templates_path)
    calendars.joinpath("season_2027.json").write_text(
        json.dumps(
            {
                "season": 2027,
                "events": [
                    {
                        "event_id": "evt_2027_custom",
                        "season": 2027,
                        "week": 1,
                        "template_id": "custom_opener_16",
                        "start_day": "MONDAY",
                        "region": "EUROPE",
                        "host_country": "ENG",
                        "is_world_tour": True,
                        "is_elite_tour": False,
                        "cluster_id": "cluster_1",
                        "travel_group": "europe",
                        "status": "scheduled",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with ApiServer(tmp_path=tmp_path, tournament_templates_config_path=str(templates_path), calendar_config_dir=str(calendars)) as server:
        status, payload = _request("DELETE", f"{server.base_url}/world/tournament-templates/custom_opener_16")
        assert status == 409
        assert "referenced by loaded season calendar events" in payload["detail"]


def test_export_import_preserves_nested_tournament_template_data(tmp_path) -> None:
    templates_path = tmp_path / "templates.json"
    _write_fixture(templates_path)
    with ApiServer(tmp_path=tmp_path, tournament_templates_config_path=str(templates_path), calendar_config_dir=str(tmp_path / "calendars")) as server:
        status, exported = _request("GET", f"{server.base_url}/world/tournament-templates/export")
        assert status == 200
        assert exported["templates"][0]["lucky_loser_rules"]["max_spots"] == 1
        assert exported["templates"][0]["point_distribution"]["winner"] == 500

        imported_template = {**TEMPLATE, "template_id": "imported_future_8", "category": "IMPORTED_FUTURE", "main_draw_size": 8, "seeds_count": 2}
        status, result = _request(
            "POST",
            f"{server.base_url}/world/tournament-templates/import",
            {"dataset": {"templates": [imported_template]}, "dry_run": False},
        )
        assert status == 200
        assert result == {"ok": True, "dry_run": False, "template_count": 1, "errors": []}

    persisted = json.loads(templates_path.read_text(encoding="utf-8"))
    assert persisted["templates"][0]["template_id"] == "imported_future_8"
    assert persisted["templates"][0]["lucky_loser_rules"]["max_spots"] == 1
    assert persisted["templates"][0]["point_distribution"]["winner"] == 500
