from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

from test_admin_entries_api import Server as EntryServer, call


class Server(EntryServer):
    def __init__(self, tmp_path: Path, *, active: bool = True) -> None:
        super().__init__(tmp_path, active=active)
        # Rebuild app setup is inherited except draws path support is needed, so patch state before server starts.
        self.server.config.app.state.season_draws_registry_path = str(tmp_path / "draws.json")
        self.draw_path = tmp_path / "draws.json"

    def persist_entry_list(self) -> str:
        event_id = self.persist_calendar()
        call("POST", f"{self.base_url}/admin/entries/{event_id}/generate", {"seed": 123, "dry_run": False, "overwrite_existing": False, "max_alternates": 4, "include_not_entered": False})
        return event_id


def test_get_empty_draw_state(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/draws/EVT-missing")
        assert status == 200
        assert body["draw_package"] is None
        assert body["draw_package_exists"] is False


def test_post_dry_run_and_persist_draw(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_entry_list()
        status, preview = call("POST", f"{server.base_url}/admin/draws/{event_id}/generate", {"seed": 222, "dry_run": True, "overwrite_existing": False})
        assert status == 200
        assert preview["draw_package"]["main_draw"]["slots"]
        assert preview["draw_package"]["qualification_draw"]["slots"]
        assert not server.draw_path.exists()

        status, persisted = call("POST", f"{server.base_url}/admin/draws/{event_id}/generate", {"seed": 222, "dry_run": False, "overwrite_existing": False})
        assert status == 200
        assert persisted["draw_package"]["persisted"] is True
        _, loaded = call("GET", f"{server.base_url}/admin/draws/{event_id}")
        assert loaded["draw_package_exists"] is True
        assert loaded["metadata"]["build_fingerprint"] == persisted["metadata"]["build_fingerprint"]


def test_draw_overwrite_safety_and_missing_prerequisite(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_entry_list()
        payload = {"seed": 222, "dry_run": False, "overwrite_existing": False}
        call("POST", f"{server.base_url}/admin/draws/{event_id}/generate", payload)
        try:
            call("POST", f"{server.base_url}/admin/draws/{event_id}/generate", payload)
        except HTTPError as exc:
            assert exc.code == 400
            assert "already exists" in exc.read().decode()
        else:
            raise AssertionError("overwrite safety should reject existing draw")

    with Server(tmp_path / "missing") as server:
        event_id = server.persist_calendar()
        try:
            call("POST", f"{server.base_url}/admin/draws/{event_id}/generate", {"seed": 222, "dry_run": True, "overwrite_existing": False})
        except HTTPError as exc:
            assert exc.code == 400
            assert "No persisted entry list" in exc.read().decode()
        else:
            raise AssertionError("missing entry list should fail")
