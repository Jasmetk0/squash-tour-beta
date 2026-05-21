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


def test_builder_preflight_valid_template_read_only(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        payload = {"target_season_label": "2000/2001", "source_type": "season_template", "source_template_id": "default_msa_template_preview", "overwrite_policy": "merge", "requested_by": "qa"}
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", payload)
        assert status == 200
        assert body["can_build"] is False
        assert body["source_resolved"] is True
        diff = body["authoritative_diff_summary"]
        assert diff["status"] == "read_only_preflight"
        assert diff["can_build"] is False
        assert diff["source_resolved"] is True
        assert diff["source_slot_count"] is not None
        assert diff["source_week_count"] is not None
        assert "structural_comparison" in diff
        assert "blocking_reasons" in diff
        assert "advisory_notes" in diff
        assert "Event-level additions/replacements/conflicts remain planned for a future phase." in diff["placeholder"]


def test_builder_preflight_existing_calendar_requires_policy(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        build_payload = {"seed": 1, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/calendar/build", build_payload)
        payload = {"target_season_label": "2000/2001", "source_type": "season_template", "source_template_id": "default_msa_template_preview"}
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", payload)
        assert any("overwrite/merge policy" in message for message in body["validation_errors"])
        diff = body["authoritative_diff_summary"]
        assert diff["structural_comparison"]["requires_overwrite_or_merge_policy"] is True
        assert any("overwrite/merge policy" in message for message in diff["blocking_reasons"])


def test_builder_preflight_planned_source_type(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", {"target_season_label": "2000/2001", "source_type": "blank_calendar_planned"})
        assert body["source_resolved"] is False
        diff = body["authoritative_diff_summary"]
        assert diff["source_resolved"] is False
        assert any("planned" in note.lower() for note in diff["advisory_notes"])


def test_builder_preflight_missing_template_reference(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", {"target_season_label": "2000/2001", "source_type": "season_template", "source_template_id": "does_not_exist"})
        assert any("was not found" in message for message in body["validation_errors"])
        assert any("was not found" in message for message in body["authoritative_diff_summary"]["blocking_reasons"])


def test_builder_preflight_invalid_target_label(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        _, body = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", {"target_season_label": "invalid", "source_type": "season_template", "source_template_id": "default_msa_template_preview"})
        assert any("Invalid target season label" in message for message in body["validation_errors"])
        assert any("Invalid target season label" in message for message in body["authoritative_diff_summary"]["blocking_reasons"])
