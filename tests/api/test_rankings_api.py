from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

from test_admin_season_bootstrap_api import Server as BootstrapServer, call


class Server(BootstrapServer):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.active_path = tmp_path / "season_active_players.json"

    def persist_ranked_players(self) -> None:
        call("POST", f"{self.base_url}/admin/players/initial-pool/generate", {"season": "2000/2001", "seed": 7, "target_pool_size": 4, "dry_run": False})
        call("POST", f"{self.base_url}/admin/seasons/2000%2F2001/bootstrap-from-initial-pool", {"source_season": "2000/2001", "seed": 1, "dry_run": False, "overwrite_existing": False})
        import json

        registry = json.loads(self.active_path.read_text(encoding="utf-8"))
        players = sorted(registry["players_by_season"]["2000/2001"], key=lambda player: player["player_id"])
        updates = [
            {"player_id": "P-A", "name": "Alpha One", "country_code": "AAA", "nationality": "AAA", "ranking_points": 120, "race_points": 40, "current_ability": 70},
            {"player_id": "P-B", "name": "Bravo Two", "country_code": "BBB", "nationality": "BBB", "ranking_points": 90, "race_points": 110, "current_ability": 79, "potential_ability": 90},
            {"player_id": "P-C", "name": "Charlie Three", "country_code": "AAA", "nationality": "AAA", "ranking_points": 0, "race_points": 0, "current_ability": 65},
            {"player_id": "P-D", "name": "Delta Four", "country_code": "BBB", "nationality": "BBB", "ranking_points": 90, "race_points": 100, "current_ability": 68},
        ]
        for player, update in zip(players, updates, strict=True):
            player.update(update)
        registry["players_by_season"]["2000/2001"] = players
        self.active_path.write_text(json.dumps(registry), encoding="utf-8")


def test_get_admin_ranking_table(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        server.persist_ranked_players()
        status, body = call("GET", f"{server.base_url}/admin/rankings/2000%2F2001?table_type=ranking")

        assert status == 200
        assert body["metadata"]["source"] == "season_active_players"
        assert [row["player_id"] for row in body["rows"][:3]] == ["P-A", "P-B", "P-D"]
        assert [row["rank"] for row in body["rows"][:3]] == [1, 2, 2]
        assert body["summary"]["rolling_ranking_implemented"] is False


def test_get_viewer_race_table_with_query_params(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        server.persist_ranked_players()
        status, body = call("GET", f"{server.base_url}/viewer/rankings/2000%2F2001?table_type=race&country_code=BBB&include_zero_points=false&limit=1")

        assert status == 200
        assert body["metadata"]["table_type"] == "race"
        assert [row["player_id"] for row in body["rows"]] == ["P-B"]
        assert body["rows"][0]["rank"] == 1
        assert body["metadata"]["filters"]["country_code"] == "BBB"


def test_admin_ranking_search_and_min_points_params(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        server.persist_ranked_players()
        status, body = call("GET", f"{server.base_url}/admin/rankings/2000%2F2001?table_type=ranking&search=delta&min_points=80")

        assert status == 200
        assert [row["player_id"] for row in body["rows"]] == ["P-D"]
        assert body["rows"][0]["rank"] == 2


def test_missing_active_players_error(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        try:
            call("GET", f"{server.base_url}/admin/rankings/2000%2F2001")
        except HTTPError as exc:
            assert exc.code == 400
            assert "No active season players" in exc.read().decode()
        else:
            raise AssertionError("missing active players should fail")
