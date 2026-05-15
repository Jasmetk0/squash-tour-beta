from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

from test_admin_draws_api import Server as DrawServer, call


class Server(DrawServer):
    def __init__(self, tmp_path: Path, *, active: bool = True) -> None:
        super().__init__(tmp_path, active=active)
        self.server.config.app.state.season_matches_registry_path = str(tmp_path / "matches.json")
        self.match_path = tmp_path / "matches.json"

    def persist_draw_package(self) -> str:
        event_id = self.persist_entry_list()
        call("POST", f"{self.base_url}/admin/draws/{event_id}/generate", {"seed": 222, "dry_run": False, "overwrite_existing": False})
        return event_id


def test_get_empty_match_package_state(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/matches/EVT-missing")
        assert status == 200
        assert body["match_package"] is None
        assert body["match_package_exists"] is False


def test_post_dry_run_and_persist_match_package(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_draw_package()
        status, preview = call("POST", f"{server.base_url}/admin/matches/{event_id}/generate", {"seed": 333, "dry_run": True, "overwrite_existing": False})
        assert status == 200
        assert preview["match_package"]["main_draw_matches"]
        assert preview["match_package"]["qualification_matches"]
        assert not server.match_path.exists()

        status, persisted = call("POST", f"{server.base_url}/admin/matches/{event_id}/generate", {"seed": 333, "dry_run": False, "overwrite_existing": False})
        assert status == 200
        assert persisted["match_package"]["persisted"] is True
        _, loaded = call("GET", f"{server.base_url}/admin/matches/{event_id}")
        assert loaded["match_package_exists"] is True
        assert loaded["metadata"]["build_fingerprint"] == persisted["metadata"]["build_fingerprint"]


def test_match_overwrite_safety_and_missing_prerequisite(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_draw_package()
        payload = {"seed": 333, "dry_run": False, "overwrite_existing": False}
        call("POST", f"{server.base_url}/admin/matches/{event_id}/generate", payload)
        try:
            call("POST", f"{server.base_url}/admin/matches/{event_id}/generate", payload)
        except HTTPError as exc:
            assert exc.code == 400
            assert "already exists" in exc.read().decode()
        else:
            raise AssertionError("overwrite safety should reject existing match package")

    with Server(tmp_path / "missing") as server:
        event_id = server.persist_entry_list()
        try:
            call("POST", f"{server.base_url}/admin/matches/{event_id}/generate", {"seed": 333, "dry_run": True, "overwrite_existing": False})
        except HTTPError as exc:
            assert exc.code == 400
            assert "No persisted draw package" in exc.read().decode()
        else:
            raise AssertionError("missing draw package should fail")


def test_simulate_selected_and_next(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_draw_package()
        _, persisted = call("POST", f"{server.base_url}/admin/matches/{event_id}/generate", {"seed": 333, "dry_run": False, "overwrite_existing": False})
        match = next(item for item in persisted["match_package"]["qualification_matches"] + persisted["match_package"]["main_draw_matches"] if item["status"] == "pending")

        status, selected = call("POST", f"{server.base_url}/admin/matches/{event_id}/simulate/{match['match_id']}", {"seed": 444})
        assert status == 200
        completed = next(item for item in selected["match_package"]["qualification_matches"] + selected["match_package"]["main_draw_matches"] if item["match_id"] == match["match_id"])
        assert completed["status"] == "completed"
        assert completed["winner_player_id"]
        assert completed["loser_player_id"]
        assert completed["scoreline"]
        assert completed["result_fingerprint"]



def test_simulate_next(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_draw_package()
        call("POST", f"{server.base_url}/admin/matches/{event_id}/generate", {"seed": 333, "dry_run": False, "overwrite_existing": False})
        status, after_next = call("POST", f"{server.base_url}/admin/matches/{event_id}/simulate-next", {"seed": 444})
        assert status == 200
        assert after_next["summary"]["completed_matches"] == 1


def test_progression_endpoints_status_process_byes_promote_refresh_and_round(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_draw_package()
        call("POST", f"{server.base_url}/admin/matches/{event_id}/generate", {"seed": 333, "dry_run": False, "overwrite_existing": False})

        status, progression = call("GET", f"{server.base_url}/admin/matches/{event_id}/progression")
        assert status == 200
        assert progression["event_id"] == event_id
        assert progression["main_draw_status"] in {"not_started", "in_progress", "completed"}

        status, byes = call("POST", f"{server.base_url}/admin/matches/{event_id}/process-byes", {"seed": 444})
        assert status == 200
        assert byes["action"] == "process_byes"
        assert byes["progression_status"]["event_id"] == event_id

        status, refreshed = call("POST", f"{server.base_url}/admin/matches/{event_id}/refresh-progression", {"seed": 444})
        assert status == 200
        assert refreshed["action"] == "advance_completed"

        status, promoted = call("POST", f"{server.base_url}/admin/matches/{event_id}/promote-qualifiers", {"seed": 444})
        assert status == 200
        assert promoted["action"] == "promote_qualifiers"

        status, round_result = call("POST", f"{server.base_url}/admin/matches/{event_id}/simulate-round", {"seed": 444, "draw_type": "main", "round_number": 1})
        assert status == 200
        assert round_result["action"] == "simulate_round"
        assert round_result["match_package"]["summary"]["completed_matches"] >= 1


def test_progression_missing_match_package_errors(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        try:
            call("GET", f"{server.base_url}/admin/matches/EVT-missing/progression")
        except HTTPError as exc:
            assert exc.code == 400
            assert "No persisted match package" in exc.read().decode()
        else:
            raise AssertionError("missing match package should fail progression status")
