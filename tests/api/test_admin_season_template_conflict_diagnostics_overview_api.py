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
        self.server = uvicorn.Server(
            uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error")
        )
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


def assert_overview_common_contract(overview: dict) -> None:
    assert overview is not None
    assert overview["read_only"] is True
    assert overview["non_blocking"] is True
    assert overview["mutation_behavior"] == "unavailable"
    assert overview["blocking_behavior"] == "non_blocking"
    assert isinstance(overview["selected_report_available"], bool)
    assert isinstance(overview["preflight_preview_available"], bool)
    assert isinstance(overview["preflight_summary_available"], bool)
    assert isinstance(overview["dry_run_preview_available"], bool)
    assert isinstance(overview["dry_run_summary_available"], bool)
    assert isinstance(overview["selected_conflict_count"], int)
    assert isinstance(overview["preflight_conflict_count"], int)
    assert isinstance(overview["dry_run_conflict_count"], int)
    assert overview["selected_conflict_count"] >= 0
    assert overview["preflight_conflict_count"] >= 0
    assert overview["dry_run_conflict_count"] >= 0


def test_selected_template_slot_conflicts_overview_contract(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call(
            "GET",
            f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-conflicts",
        )
        assert status == 200
        overview = body["template_conflict_diagnostics_overview"]
        assert_overview_common_contract(overview)
        assert overview["selected_report_available"] is True
        assert overview["selected_status"] == body["summary"]["status"]
        assert overview["selected_conflict_count"] == body["summary"]["conflict_count"]
        assert overview["preflight_preview_available"] is False
        assert overview["dry_run_preview_available"] is False




def test_selected_template_slot_conflicts_overview_normalized_summary_parity(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call(
            "GET",
            f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-conflicts",
        )
        assert status == 200
        overview = body["template_conflict_diagnostics_overview"]
        assert_overview_common_contract(overview)
        assert overview["selected_report_available"] is True
        assert overview["selected_status"] in ("clean", "warnings", "info")
        assert overview["selected_status"] == body["summary"]["status"]
        assert isinstance(overview["selected_conflict_count"], int)
        assert overview["selected_conflict_count"] == body["summary"]["conflict_count"]
        assert overview["selected_conflict_count"] >= 0


def test_selected_template_slot_conflicts_unknown_template_overview_contract(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call(
            "GET",
            f"{server.base_url}/admin/seasons/templates/unknown_template/slot-conflicts",
        )
        assert status == 200
        overview = body["template_conflict_diagnostics_overview"]
        assert_overview_common_contract(overview)
        assert overview["selected_report_available"] is False
        assert overview["selected_status"] is None
        assert overview["selected_conflict_count"] == 0
        assert body["template_exists"] is False

def test_builder_preflight_overview_contract(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call(
            "POST",
            f"{server.base_url}/admin/seasons/builder/preflight",
            {
                "target_season_label": "2035/2036",
                "source_type": "season_template",
                "source_template_id": "default_msa_template_preview",
            },
        )
        assert status == 200
        overview = body["template_conflict_diagnostics_overview"]
        assert_overview_common_contract(overview)
        assert overview["preflight_preview_available"] is True
        assert overview["preflight_summary_available"] is True
        assert overview["preflight_status"] == body["template_slot_conflict_preview"]["status"]
        assert overview["preflight_conflict_count"] == body["template_slot_conflict_preview"]["conflict_count"]
        assert overview["selected_report_available"] is False
        assert overview["dry_run_preview_available"] is False


def test_builder_dry_run_build_overview_contract(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call(
            "POST",
            f"{server.base_url}/admin/seasons/builder/dry-run-build",
            {
                "target_season_label": "2035/2036",
                "source_type": "season_template",
                "source_template_id": "default_msa_template_preview",
                "preflight_fingerprint": "pf_test",
                "reviewed_diff_id": "rd_test",
            },
        )
        assert status == 200
        overview = body["template_conflict_diagnostics_overview"]
        assert_overview_common_contract(overview)
        assert overview["dry_run_preview_available"] is True
        assert overview["dry_run_summary_available"] is True
        assert overview["dry_run_status"] == body["template_slot_conflict_preview"]["status"]
        assert overview["dry_run_conflict_count"] == body["template_slot_conflict_preview"]["conflict_count"]
        assert overview["selected_report_available"] is False
        assert overview["preflight_preview_available"] is False


def test_builder_dry_run_build_unknown_template_overview_contract(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call(
            "POST",
            f"{server.base_url}/admin/seasons/builder/dry-run-build",
            {
                "target_season_label": "2035/2036",
                "source_type": "season_template",
                "source_template_id": "unknown_template",
                "preflight_fingerprint": "pf_test",
                "reviewed_diff_id": "rd_test",
            },
        )
        assert status == 200
        overview = body["template_conflict_diagnostics_overview"]
        assert_overview_common_contract(overview)
        assert overview["dry_run_preview_available"] is False
        assert overview["dry_run_summary_available"] is True
        assert overview["dry_run_conflict_count"] == 0
        assert overview["selected_report_available"] is False
