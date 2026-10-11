from __future__ import annotations

import json
import threading
import time
from uuid import uuid4
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
        app = create_app(database_url=f"sqlite:///{tmp_path / f'api-{uuid4().hex}.db'}", tournament_templates_config_path=str(template_path), season_calendar_registry_path=str(tmp_path / "season_calendars.json"))
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


def _preflight(server: Server):
    return call("POST", f"{server.base_url}/admin/seasons/builder/preflight", {
        "target_season_label": "2035/2036",
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
    })


def assert_preview_matches_endpoint(preview: dict, endpoint_validation: dict) -> None:
    assert preview["template_id"] == endpoint_validation["template_id"]
    assert preview["template_exists"] == endpoint_validation["template_exists"]
    assert preview["status"] == endpoint_validation["summary"]["status"]
    assert preview["error_count"] == endpoint_validation["summary"]["error_count"]
    assert preview["warning_count"] == endpoint_validation["summary"]["warning_count"]
    assert preview["issue_count"] == endpoint_validation["summary"]["issue_count"]
    assert set(preview["issue_codes"]) == {issue["code"] for issue in endpoint_validation["issues"]}
    assert set(preview["error_codes"]) == {
        issue["code"] for issue in endpoint_validation["issues"] if issue["severity"] == "error"
    }
    assert set(preview["warning_codes"]) == {
        issue["code"] for issue in endpoint_validation["issues"] if issue["severity"] == "warning"
    }
    assert preview["read_only"] is True




def assert_conflict_preview_matches_endpoint(preview: dict, endpoint_conflicts: dict) -> None:
    assert preview["template_id"] == endpoint_conflicts["template_id"]
    assert preview["template_exists"] == endpoint_conflicts["template_exists"]
    assert preview["status"] == endpoint_conflicts["summary"]["status"]
    assert preview["warning_count"] == endpoint_conflicts["summary"]["warning_count"]
    assert preview["info_count"] == endpoint_conflicts["summary"]["info_count"]
    assert preview["conflict_count"] == endpoint_conflicts["summary"]["conflict_count"]
    assert set(preview["conflict_codes"]) == {item["code"] for item in endpoint_conflicts["conflicts"]}
    assert set(preview["warning_codes"]) == {item["code"] for item in endpoint_conflicts["conflicts"] if item["severity"] == "warning"}
    assert set(preview["info_codes"]) == {item["code"] for item in endpoint_conflicts["conflicts"] if item["severity"] == "info"}
    assert preview["busiest_week"] == endpoint_conflicts["summary"]["busiest_week"]
    assert preview["busiest_week_slot_count"] == endpoint_conflicts["summary"]["busiest_week_slot_count"]
    assert preview["read_only"] is True


def test_default_template_no_blocking_template_slot_errors(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, body = _preflight(server)
        assert status == 200
        assert not any("[template_slot_" in err for err in body["validation_errors"])
        preview = body["template_slot_validation_preview"]
        assert preview["template_id"] == "default_msa_template_preview"
        assert preview["read_only"] is True
        assert preview["error_count"] == 0
        assert preview["status"] in ("clean", "warnings")
        status, validation = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-validation")
        assert status == 200
        assert validation["template_exists"] is True
        assert validation["read_only"] is True
        assert validation["summary"]["slot_count"] > 0
        assert validation["summary"]["error_count"] == 0
        assert validation["summary"]["status"] in ("clean", "warnings")


def test_duplicate_and_overload_warnings_surface(tmp_path: Path) -> None:
    base = {"tour_level": "WORLD_TOUR", "category": "PLATINUM", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}
    templates = [dict(base, template_id=f"default_msa_template_preview" if i == 0 else f"dup_{i}", event_name=f"Same Event {i}", duration_in_season_weeks=5) for i in range(5)]
    with Server(tmp_path, templates) as server:
        status, body = _preflight(server)
        assert status == 200
        assert any("template_slot_category_tour_level_week_overloaded" in w for w in body["validation_warnings"])
        assert any("template_slot_duration_long" in w for w in body["validation_warnings"])
        preview = body["template_slot_validation_preview"]
        assert preview["template_id"] == "default_msa_template_preview"
        assert preview["read_only"] is True
        assert preview["status"] == "warnings"
        assert preview["warning_count"] > 0
        assert "template_slot_duration_long" in preview["issue_codes"] or "template_slot_category_tour_level_week_overloaded" in preview["issue_codes"]
        assert any("[template_slot_duration_long]" in item for item in body["validation_warnings"])
        status, validation = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-validation")
        assert status == 200
        assert validation["template_exists"] is True
        assert validation["read_only"] is True
        assert validation["summary"]["warning_count"] > 0
        issue_codes = {issue["code"] for issue in validation["issues"]}
        assert "template_slot_duration_long" in issue_codes or "template_slot_category_tour_level_week_overloaded" in issue_codes


def test_dry_run_includes_template_slot_validation_preview(tmp_path: Path) -> None:
    base = {"tour_level": "WORLD_TOUR", "category": "PLATINUM", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}
    templates = [dict(base, template_id=f"default_msa_template_preview" if i == 0 else f"dup_{i}", event_name=f"Same Event {i}", duration_in_season_weeks=5) for i in range(5)]
    with Server(tmp_path, templates) as server:
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "preflight_fingerprint": "pf_test",
            "reviewed_diff_id": "rd_test",
        })
        assert status == 200
        preview = body["template_slot_validation_preview"]
        assert preview["template_id"] == "default_msa_template_preview"
        assert preview["read_only"] is True
        assert preview["status"] == "warnings"
        assert preview["warning_count"] > 0
        assert "template_slot_duration_long" in preview["issue_codes"] or "template_slot_category_tour_level_week_overloaded" in preview["issue_codes"]
        assert any("[template_slot_duration_long]" in item for item in body["validation_warnings"])


def test_slot_validation_missing_template_returns_structured_diagnostic(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, validation = call("GET", f"{server.base_url}/admin/seasons/templates/not_real/slot-validation")
        assert status == 200
        assert validation["template_exists"] is False
        assert validation["read_only"] is True
        assert validation["summary"]["status"] == "errors"
        issue_codes = {issue["code"] for issue in validation["issues"]}
        assert "template_not_found" in issue_codes


def test_slot_validation_issue_code_registry_endpoint(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, body = call("GET", f"{server.base_url}/admin/seasons/templates/slot-validation/issue-codes")
        assert status == 200
        assert body["read_only"] is True
        assert body["code_count"] > 0
        codes = [item["code"] for item in body["codes"]]
        assert "template_not_found" in codes
        assert "template_slot_duration_long" in codes
        assert "template_slot_start_after_end" in codes
        assert len(codes) == len(set(codes))
        for item in body["codes"]:
            assert item["severity"] in ("warning", "error")
            assert item["title"]
            assert item["description"]


def test_slot_validation_issue_codes_route_does_not_conflict_with_template_validation(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, validation = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-validation")
        assert status == 200
        assert validation["template_id"] == "default_msa_template_preview"
        assert validation["template_exists"] is True


def test_slot_conflicts_endpoint_returns_read_only_report(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, body = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-conflicts")
        assert status == 200
        assert body["read_only"] is True
        assert body["template_id"] == "default_msa_template_preview"
        assert body["summary"]["slot_count"] >= 0
        assert isinstance(body["conflicts"], list)
        overview = body["template_conflict_diagnostics_overview"]
        assert overview["selected_report_available"] is True
        assert overview["selected_status"] == body["summary"]["status"]
        assert overview["selected_conflict_count"] == body["summary"]["conflict_count"]
        assert overview["read_only"] is True
        assert overview["non_blocking"] is True


def test_slot_conflicts_route_does_not_conflict_with_slot_validation(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status_validation, validation = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-validation")
        assert status_validation == 200
        assert validation["template_id"] == "default_msa_template_preview"
        status_conflicts, conflicts = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-conflicts")
        assert status_conflicts == 200
        assert conflicts["template_id"] == "default_msa_template_preview"

def test_slot_conflict_code_registry_endpoint(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, body = call("GET", f"{server.base_url}/admin/seasons/templates/slot-conflicts/codes")
        assert status == 200
        assert body["read_only"] is True
        assert body["code_count"] >= 8
        codes = [item["code"] for item in body["codes"]]
        assert "template_conflict_week_overloaded" in codes
        assert "template_conflict_premium_overlap" in codes
        assert "template_conflict_host_country_cluster" in codes
        assert len(codes) == len(set(codes))
        for item in body["codes"]:
            assert item["severity"] in ("warning", "info")
            assert item["title"]
            assert item["description"]


def test_slot_conflict_codes_route_does_not_conflict_with_template_conflicts_route(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status_codes, _codes = call("GET", f"{server.base_url}/admin/seasons/templates/slot-conflicts/codes")
        assert status_codes == 200
        status_conflicts, conflicts = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-conflicts")
        assert status_conflicts == 200
        assert conflicts["template_id"] == "default_msa_template_preview"


def test_slot_conflicts_report_codes_are_covered_by_conflict_code_registry(tmp_path: Path) -> None:
    base = {"tour_level": "WORLD_TOUR", "region": "EUROPE", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 5, "active": True}
    templates = [
        dict(base, template_id="default_msa_template_preview", category="PLATINUM", event_name="World A", host_country="ENG"),
        dict(base, template_id="tmp_b", category="DIAMOND", event_name="World B", host_country="ENG"),
        dict(base, template_id="tmp_c", category="PLATINUM", event_name="World C", host_country="ENG"),
    ]
    with Server(tmp_path, templates) as server:
        status_report, report = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-conflicts")
        assert status_report == 200
        status_registry, registry = call("GET", f"{server.base_url}/admin/seasons/templates/slot-conflicts/codes")
        assert status_registry == 200
        assert registry["read_only"] is True
        registry_by_code = {item["code"]: item for item in registry["codes"]}
        for conflict in report["conflicts"]:
            assert conflict["code"] in registry_by_code
            assert conflict["severity"] == registry_by_code[conflict["code"]]["severity"]


def test_preflight_planned_source_type_has_no_template_slot_preview(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, body = call("POST", f"{server.base_url}/admin/seasons/builder/preflight", {
            "target_season_label": "2035/2036",
            "source_type": "planned",
        })
        assert status == 200
        assert body["template_slot_validation_preview"] is None
        assert body["template_slot_conflict_preview"] is None


def test_template_slot_validation_consistent_between_endpoint_preflight_and_dry_run_warnings(tmp_path: Path) -> None:
    base = {"tour_level": "WORLD_TOUR", "category": "PLATINUM", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}
    templates = [dict(base, template_id="default_msa_template_preview" if i == 0 else f"dup_{i}", event_name=f"Same Event {i}", duration_in_season_weeks=5) for i in range(5)]
    with Server(tmp_path, templates) as server:
        status, endpoint_validation = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-validation")
        assert status == 200
        status, endpoint_conflicts = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-conflicts")
        assert status == 200
        status, preflight = _preflight(server)
        assert status == 200
        status, dry_run = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "preflight_fingerprint": "pf_test",
            "reviewed_diff_id": "rd_test",
        })
        assert status == 200
        assert preflight["template_slot_validation_preview"] is not None
        assert dry_run["template_slot_validation_preview"] is not None
        assert preflight["template_slot_conflict_preview"] is not None
        assert dry_run["template_slot_conflict_preview"] is not None
        assert_preview_matches_endpoint(preflight["template_slot_validation_preview"], endpoint_validation)
        assert_preview_matches_endpoint(dry_run["template_slot_validation_preview"], endpoint_validation)
        assert_conflict_preview_matches_endpoint(preflight["template_slot_conflict_preview"], endpoint_conflicts)
        assert_conflict_preview_matches_endpoint(dry_run["template_slot_conflict_preview"], endpoint_conflicts)
        assert any("[template_slot_" in item for item in preflight["validation_warnings"])
        assert any("[template_slot_" in item for item in dry_run["validation_warnings"])


def test_template_slot_validation_consistent_between_endpoint_preflight_and_dry_run_clean_default(tmp_path: Path) -> None:
    templates = [{"template_id": "default_msa_template_preview", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "ENG", "main_draw_size": 32, "qualification_draw_size": 16, "seeds_count": 8, "qualifier_spots": 4, "wild_cards": 2, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True}]
    with Server(tmp_path, templates) as server:
        status, endpoint_validation = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-validation")
        assert status == 200
        assert endpoint_validation["summary"]["error_count"] == 0
        status, endpoint_conflicts = call("GET", f"{server.base_url}/admin/seasons/templates/default_msa_template_preview/slot-conflicts")
        assert status == 200
        status, preflight = _preflight(server)
        assert status == 200
        status, dry_run = call("POST", f"{server.base_url}/admin/seasons/builder/dry-run-build", {
            "target_season_label": "2035/2036",
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "preflight_fingerprint": "pf_test",
            "reviewed_diff_id": "rd_test",
        })
        assert status == 200
        assert preflight["template_slot_validation_preview"] is not None
        assert dry_run["template_slot_validation_preview"] is not None
        assert preflight["template_slot_conflict_preview"] is not None
        assert dry_run["template_slot_conflict_preview"] is not None
        assert_preview_matches_endpoint(preflight["template_slot_validation_preview"], endpoint_validation)
        assert_preview_matches_endpoint(dry_run["template_slot_validation_preview"], endpoint_validation)
        assert_conflict_preview_matches_endpoint(preflight["template_slot_conflict_preview"], endpoint_conflicts)
        assert_conflict_preview_matches_endpoint(dry_run["template_slot_conflict_preview"], endpoint_conflicts)
