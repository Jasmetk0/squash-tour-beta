from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

import uvicorn

from beta_engine.application.planning_season_calendar_service import (
    PLANNING_SEASON_CALENDAR_SCHEMA_VERSION,
    PlanningSeasonCalendar,
    PlanningSeasonCalendarRegistry,
)
from beta_engine.main import create_app


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
        self.planning_path = tmp_path / "planning_season_calendars.json"
        self.season_calendar_path = tmp_path / "season_calendars.json"
        app = create_app(
            database_url=f"sqlite:///{tmp_path / 'api.db'}",
            planning_season_calendar_registry_path=str(self.planning_path),
            season_calendar_registry_path=str(self.season_calendar_path),
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


def planning_calendar_payload() -> dict:
    return {
        "season_label": "2000/01",
        "normalized_season_label": "2000/01",
        "status": "draft",
        "events": [
            {
                "id": "event-a",
                "name": "Event A",
                "category_code": "diamond",
                "weeks": [7, 6],
                "qualification_weeks": [5],
                "locked": True,
                "country_code": "egy",
                "city": "Cairo",
                "venue": "Venue A",
            }
        ],
        "metadata": {"source": "api-test"},
    }


def write_planning_registry(path: Path) -> str:
    calendar = PlanningSeasonCalendar.model_validate(planning_calendar_payload())
    registry = PlanningSeasonCalendarRegistry(calendars_by_season={calendar.normalized_season_label: calendar})
    path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    return path.read_text(encoding="utf-8")


def assert_safety(body: dict) -> None:
    assert body["read_only"] is True
    assert body["status"] == "ok"
    assert body["safety"] == {
        "planning_only": True,
        "viewer_visible": False,
        "simulation_consumed": False,
        "canonical_season_calendar_modified": False,
    }


def test_list_missing_registry_returns_empty_and_does_not_create_files(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/seasons/planning-calendars")
        assert status == 200
        assert body["calendars"] == []
        assert body["source_path"] == str(server.planning_path)
        assert body["schema_version"] == PLANNING_SEASON_CALENDAR_SCHEMA_VERSION
        assert body["registry_fingerprint"].startswith("pl_reg_")
        assert_safety(body)
        assert not server.planning_path.exists()
        assert not server.season_calendar_path.exists()


def test_detail_missing_registry_returns_404_and_does_not_create_files(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        try:
            call("GET", f"{server.base_url}/admin/seasons/planning-calendars/2000%2F01")
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("missing planning calendar should return 404")
        assert not server.planning_path.exists()
        assert not server.season_calendar_path.exists()


def test_existing_planning_calendar_appears_in_list_with_registry_metadata(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        before = write_planning_registry(server.planning_path)
        status, body = call("GET", f"{server.base_url}/admin/seasons/planning-calendars")
        assert status == 200
        assert len(body["calendars"]) == 1
        assert body["calendars"][0]["normalized_season_label"] == "2000/2001"
        assert body["source_path"] == str(server.planning_path)
        assert body["schema_version"] == PLANNING_SEASON_CALENDAR_SCHEMA_VERSION
        assert body["registry_fingerprint"].startswith("pl_reg_")
        assert_safety(body)
        assert server.planning_path.read_text(encoding="utf-8") == before


def test_detail_supports_short_and_long_labels_and_preserves_planning_fields(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        before = write_planning_registry(server.planning_path)
        _, short_body = call("GET", f"{server.base_url}/admin/seasons/planning-calendars/2000%2F01")
        _, long_body = call("GET", f"{server.base_url}/admin/seasons/planning-calendars/2000%2F2001")

        assert short_body == long_body
        assert_safety(short_body)
        assert short_body["source_path"] == str(server.planning_path)
        assert short_body["schema_version"] == PLANNING_SEASON_CALENDAR_SCHEMA_VERSION
        assert short_body["registry_fingerprint"].startswith("pl_reg_")
        calendar = short_body["calendar"]
        event = calendar["events"][0]
        assert event["weeks"] == [6, 7]
        assert event["qualification_weeks"] == [5]
        assert event["locked"] is True
        assert event["event_fingerprint"].startswith("pl_evt_")
        assert calendar["calendar_fingerprint"].startswith("pl_cal_")
        assert server.planning_path.read_text(encoding="utf-8") == before
        assert not server.season_calendar_path.exists()


def test_existing_season_calendars_file_is_not_modified_by_read_only_api(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        write_planning_registry(server.planning_path)
        server.season_calendar_path.write_text('{"sentinel": true}\n', encoding="utf-8")
        before = server.season_calendar_path.read_text(encoding="utf-8")
        call("GET", f"{server.base_url}/admin/seasons/planning-calendars")
        call("GET", f"{server.base_url}/admin/seasons/planning-calendars/2000%2F01")
        assert server.season_calendar_path.read_text(encoding="utf-8") == before


def test_no_write_methods_exist_for_planning_calendar_endpoints(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                call(method, f"{server.base_url}/admin/seasons/planning-calendars")
            except HTTPError as exc:
                assert exc.code in {404, 405}
            else:
                raise AssertionError(f"{method} should not be enabled")
            try:
                call(method, f"{server.base_url}/admin/seasons/planning-calendars/2000%2F01")
            except HTTPError as exc:
                assert exc.code in {404, 405}
            else:
                raise AssertionError(f"{method} detail should not be enabled")


def test_viewer_routes_do_not_expose_planning_calendars(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        try:
            call("GET", f"{server.base_url}/planning-calendars")
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("viewer planning calendar route should not exist")
