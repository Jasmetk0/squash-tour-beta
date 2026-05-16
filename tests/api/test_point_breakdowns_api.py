from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "application"))

from test_admin_points_api import Server, call


def _persist_awards(server: Server, *, apply: bool = True) -> str:
    event_id = server.persist_complete_result_package()
    call("POST", f"{server.base_url}/admin/points/{event_id}/generate", {"seed": 77, "dry_run": False, "overwrite_existing": False})
    if apply:
        call("POST", f"{server.base_url}/admin/points/{event_id}/apply", {"seed": 88, "allow_reapply": False})
    return event_id


def test_get_admin_point_breakdown(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = _persist_awards(server, apply=True)
        status, body = call("GET", f"{server.base_url}/admin/point-breakdowns/2000%2F2001?player_id=P1")
        assert status == 200
        assert body["metadata"]["source"] == "season_point_awards"
        assert body["breakdown"]["player_id"] == "P1"
        assert body["breakdown"]["entries"][0]["event_id"] == event_id
        assert body["breakdown"]["entries"][0]["applied"] is True


def test_get_viewer_point_breakdown_summary_rows(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        _persist_awards(server, apply=True)
        status, body = call("GET", f"{server.base_url}/viewer/point-breakdowns/2000%2F2001?country_code=EGY&limit=10")
        assert status == 200
        assert body["breakdown"] is None
        assert {row["country_code"] for row in body["summary_rows"]} == {"EGY"}


def test_player_id_param_works(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        _persist_awards(server, apply=True)
        status, body = call("GET", f"{server.base_url}/viewer/point-breakdowns/2000%2F2001?player_id=P2")
        assert status == 200
        assert body["breakdown"]["player_id"] == "P2"


def test_applied_only_false_includes_unapplied(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        _persist_awards(server, apply=False)
        status, body = call("GET", f"{server.base_url}/admin/point-breakdowns/2000%2F2001?player_id=P1&applied_only=false")
        assert status == 200
        assert body["breakdown"]["entries"]
        assert body["breakdown"]["entries"][0]["applied"] is False
        assert body["breakdown"]["unapplied_ranking_points_total"] > 0


def test_missing_active_players_error(tmp_path: Path) -> None:
    with Server(tmp_path, active=False) as server:
        try:
            call("GET", f"{server.base_url}/admin/point-breakdowns/2000%2F2001")
        except HTTPError as exc:
            assert exc.code == 400
            assert "No active season players" in exc.read().decode()
        else:
            raise AssertionError("missing active players should fail")
