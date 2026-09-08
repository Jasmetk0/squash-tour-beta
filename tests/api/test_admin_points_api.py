from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "application"))

from test_admin_results_api import Server as ResultsServer
from test_admin_results_api import call
from test_season_event_results_service import _persist_synthetic_package

from beta_engine.application.season_event_results_service import (
    EventResultExtractRequest,
)


class Server(ResultsServer):
    def __init__(self, tmp_path: Path, *, active: bool = True) -> None:
        super().__init__(tmp_path, active=active)
        self.server.config.app.state.season_point_awards_registry_path = str(tmp_path / "points.json")
        self.points_path = tmp_path / "points.json"
        self.tmp_path = tmp_path

    def persist_complete_result_package(self) -> str:
        result_service, event_id = _persist_synthetic_package(self.tmp_path)
        result_service.results_path = self.tmp_path / "results.json"
        result_service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=555, dry_run=False, overwrite_existing=True))
        active_registry = result_service.match_service.active_players_service._load_registry()
        players = active_registry.players_by_season["2000/2001"]
        names = ["Alpha One", "Bravo Two", "Charlie Three", "Delta Four", "Echo Five", "Foxtrot Six", "Q Seven", "Q Eight"]
        for index in range(min(8, len(players))):
            players[index] = players[index].model_copy(update={"player_id": f"P{index + 1}", "name": names[index], "country_code": "EGY" if index in {0, 6} else "ENG"})
        active_registry.players_by_season["2000/2001"] = players
        result_service.match_service.active_players_service._save_registry(active_registry)
        return event_id


def test_get_empty_awards_state(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/points/EVT-missing")
        assert status == 200
        assert body["award_package"] is None
        assert body["award_package_exists"] is False
        assert body["applied"] is False


def test_real_tournament_completion_persists_awards_without_publishing_points(tmp_path: Path) -> None:
    """Exercise the real engine; award storage is not an Official Ranking publication."""
    server = Server(tmp_path)
    templates_path = tmp_path / "templates.json"
    templates = json.loads(templates_path.read_text(encoding="utf-8"))
    templates["templates"][0].update(
        main_draw_size=4, qualification_draw_size=0, qualifier_spots=0,
        wild_cards=0, seeds_count=2, qualification_duration_days=0,
    )
    templates_path.write_text(json.dumps(templates), encoding="utf-8")
    with server:
        active_path = tmp_path / "active.json"
        original_players = active_path.read_bytes()
        event_id = server.persist_match_package()
        match_url = f"{server.base_url}/admin/matches/{event_id}"
        call("POST", f"{match_url}/process-byes", {"seed": 444})
        for _ in range(20):
            _, progression = call("GET", f"{match_url}/progression")
            if progression["event_status"] == "completed":
                break
            call("POST", f"{match_url}/simulate-next", {"seed": 444})
            call("POST", f"{match_url}/promote-qualifiers", {"seed": 444})
        else:
            raise AssertionError("reference tournament did not complete")
        assert progression["champion_player_id"]
        call("POST", f"{server.base_url}/admin/results/{event_id}/extract",
             {"seed": 555, "dry_run": False, "overwrite_existing": False})
        points_url = f"{server.base_url}/admin/points/{event_id}"
        payload = {"seed": 777, "dry_run": False, "overwrite_existing": False}
        _, persisted = call("POST", f"{points_url}/generate", payload)
        assert persisted["summary"]["champion_points"] == 100
        assert persisted["summary"]["finalist_points"] == 60
        _, loaded = call("GET", points_url)
        assert loaded["award_package"] == persisted["award_package"]
        assert loaded["applied"] is False
        with pytest.raises(HTTPError) as error:
            call("POST", f"{points_url}/generate", payload)
        assert error.value.code == 400
        assert "already exists" in error.value.read().decode()
        assert active_path.read_bytes() == original_players


def test_generate_persist_apply_and_duplicate_prevention(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_complete_result_package()
        status, preview = call("POST", f"{server.base_url}/admin/points/{event_id}/generate", {"seed": 777, "dry_run": True, "overwrite_existing": False})
        assert status == 200
        assert preview["award_package"]["persisted"] is False
        assert preview["summary"]["total_ranking_points"] > 0
        assert not server.points_path.exists()

        status, persisted = call("POST", f"{server.base_url}/admin/points/{event_id}/generate", {"seed": 777, "dry_run": False, "overwrite_existing": False})
        assert status == 200
        assert persisted["award_package_exists"] is True
        assert server.points_path.exists()
        _, loaded = call("GET", f"{server.base_url}/admin/points/{event_id}")
        assert loaded["metadata"]["build_fingerprint"] == persisted["metadata"]["build_fingerprint"]

        status, applied = call("POST", f"{server.base_url}/admin/points/{event_id}/apply", {"seed": 888, "allow_reapply": False})
        assert status == 200
        assert applied["applied"] is True
        assert applied["updated_players"]
        assert applied["award_package"]["applied"] is True

        try:
            call("POST", f"{server.base_url}/admin/points/{event_id}/apply", {"seed": 888, "allow_reapply": False})
        except HTTPError as exc:
            assert exc.code == 400
            assert "already been applied" in exc.read().decode()
        else:
            raise AssertionError("duplicate apply should reject")


def test_missing_result_package_errors(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        try:
            call("POST", f"{server.base_url}/admin/points/EVT-missing/generate", {"seed": 777, "dry_run": True, "overwrite_existing": False})
        except HTTPError as exc:
            assert exc.code == 400
            assert "Persist event results first" in exc.read().decode()
        else:
            raise AssertionError("missing result package should fail")


def test_apply_requires_persisted_awards(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_complete_result_package()
        try:
            call("POST", f"{server.base_url}/admin/points/{event_id}/apply", {"seed": 888, "allow_reapply": False})
        except HTTPError as exc:
            assert exc.code == 400
            assert "Persist awards before applying" in exc.read().decode()
        else:
            raise AssertionError("apply without persisted package should fail")
