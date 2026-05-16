from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "application"))

from beta_engine.application.season_event_results_service import EventResultExtractRequest
from test_admin_results_api import Server as ResultsServer, call
from test_season_event_results_service import _persist_synthetic_package


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
