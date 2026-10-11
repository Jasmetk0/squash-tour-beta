from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

from test_admin_matches_api import Server as MatchServer, call


class Server(MatchServer):
    def __init__(self, tmp_path: Path, *, active: bool = True) -> None:
        super().__init__(tmp_path, active=active)
        self.server.config.app.state.season_event_results_registry_path = str(tmp_path / "results.json")
        self.results_path = tmp_path / "results.json"

    def persist_match_package(self) -> str:
        event_id = self.persist_draw_package()
        call("POST", f"{self.base_url}/admin/matches/{event_id}/generate", {"seed": 333, "dry_run": False, "overwrite_existing": False})
        return event_id


def test_get_empty_result_state(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/results/EVT-missing")
        assert status == 200
        assert body["result_package"] is None
        assert body["result_package_exists"] is False


def test_post_dry_run_and_persist_result_package(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_match_package()
        status, preview = call("POST", f"{server.base_url}/admin/results/{event_id}/extract", {"seed": 333, "dry_run": True, "overwrite_existing": False})
        assert status == 200
        assert preview["result_package"]["event_id"] == event_id
        assert preview["result_package"]["persisted"] is False
        assert preview["summary"]["ranking_points_awarded_total"] == 0
        assert not server.results_path.exists()

        status, persisted = call("POST", f"{server.base_url}/admin/results/{event_id}/extract", {"seed": 333, "dry_run": False, "overwrite_existing": False})
        assert status == 200
        assert persisted["result_package"]["persisted"] is True
        assert server.results_path.exists()
        _, loaded = call("GET", f"{server.base_url}/admin/results/{event_id}")
        assert loaded["result_package_exists"] is True
        assert loaded["metadata"]["build_fingerprint"] == persisted["metadata"]["build_fingerprint"]


def test_result_overwrite_safety_and_missing_match_package(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_match_package()
        payload = {"seed": 333, "dry_run": False, "overwrite_existing": False}
        call("POST", f"{server.base_url}/admin/results/{event_id}/extract", payload)
        try:
            call("POST", f"{server.base_url}/admin/results/{event_id}/extract", payload)
        except HTTPError as exc:
            assert exc.code == 400
            assert "already exists" in exc.read().decode()
        else:
            raise AssertionError("overwrite safety should reject existing result package")
        status, overwritten = call("POST", f"{server.base_url}/admin/results/{event_id}/extract", {"seed": 334, "dry_run": False, "overwrite_existing": True})
        assert status == 200
        assert overwritten["metadata"]["seed"] == 334

    with Server(tmp_path / "missing") as server:
        try:
            call("POST", f"{server.base_url}/admin/results/EVT-missing/extract", {"seed": 333, "dry_run": True, "overwrite_existing": False})
        except HTTPError as exc:
            assert exc.code == 400
            assert "No persisted match package" in exc.read().decode()
        else:
            raise AssertionError("missing match package should fail")
