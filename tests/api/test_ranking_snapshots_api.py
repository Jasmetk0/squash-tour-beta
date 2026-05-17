from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

from test_rankings_api import Server, call


def test_admin_get_empty_snapshot_state(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/ranking-snapshots/2000%2F2001?season_week=1")
        assert status == 200
        assert body["snapshot_exists"] is False
        assert body["snapshot"] is None


def test_generate_dry_run_persist_get_and_viewer(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        server.persist_ranked_players()
        status, preview = call("POST", f"{server.base_url}/admin/ranking-snapshots/2000%2F2001/generate?season_week=1", {"seed": 12345, "dry_run": True, "include_zero_points": True, "limit": 10})
        assert status == 200
        assert preview["snapshot"]["persisted"] is False
        assert preview["snapshot_exists"] is False

        status, persisted = call("POST", f"{server.base_url}/admin/ranking-snapshots/2000%2F2001/generate?season_week=1", {"seed": 12345, "dry_run": False, "include_zero_points": True, "limit": 10})
        assert status == 200
        assert persisted["snapshot_exists"] is True
        assert persisted["snapshot"]["ranking_table"]["rows"][0]["player_id"] == "P-A"

        _, admin_loaded = call("GET", f"{server.base_url}/admin/ranking-snapshots/2000%2F2001?season_week=1")
        _, viewer_loaded = call("GET", f"{server.base_url}/viewer/ranking-snapshots/2000%2F2001?season_week=1")
        assert admin_loaded["snapshot"]["metadata"]["snapshot_fingerprint"] == persisted["snapshot"]["metadata"]["snapshot_fingerprint"]
        assert viewer_loaded["snapshot"]["metadata"]["snapshot_fingerprint"] == persisted["snapshot"]["metadata"]["snapshot_fingerprint"]


def test_overwrite_safety_and_invalid_missing_errors(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        server.persist_ranked_players()
        payload = {"seed": 1, "dry_run": False, "overwrite_existing": False}
        call("POST", f"{server.base_url}/admin/ranking-snapshots/2000%2F2001/generate?season_week=1", payload)
        try:
            call("POST", f"{server.base_url}/admin/ranking-snapshots/2000%2F2001/generate?season_week=1", payload)
        except HTTPError as exc:
            assert exc.code == 400
            assert "Snapshot already exists" in exc.read().decode()
        else:
            raise AssertionError("overwrite safety should reject")
        status, overwritten = call("POST", f"{server.base_url}/admin/ranking-snapshots/2000%2F2001/generate?season_week=1", {**payload, "overwrite_existing": True})
        assert status == 200
        assert overwritten["snapshot_exists"] is True

    empty_path = tmp_path / "empty"
    empty_path.mkdir()
    with Server(empty_path) as server:
        try:
            call("POST", f"{server.base_url}/admin/ranking-snapshots/2000%2F2001/generate?season_week=1", {"dry_run": True})
        except HTTPError as exc:
            assert exc.code == 400
            assert "No active season players" in exc.read().decode()
        else:
            raise AssertionError("missing active players should fail")
