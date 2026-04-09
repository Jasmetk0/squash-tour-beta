from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib import error, request

import uvicorn

from beta_engine.main import create_app

COUNTRIES_FIXTURE = {
    "dataset_status": "temporary_seed_demo",
    "countries": [
        {
            "code": "AAA",
            "name": "Alpha",
            "flag_asset": None,
            "region": "EUROPE",
            "population": 1_000_000,
            "wealth_support": 3,
            "squash_popularity": 4,
            "squash_tradition": 2,
            "system_quality": 5,
        }
    ],
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ApiServer:
    def __init__(self, *, database_url: str, countries_config_path: str, manual_overrides_config_path: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(
            database_url=database_url,
            countries_config_path=countries_config_path,
            manual_player_overrides_config_path=manual_overrides_config_path,
        )
        self.server = uvicorn.Server(uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> "ApiServer":
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                _ = _request("GET", f"{self.base_url}/health")
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def _request(method: str, url: str, payload: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method=method)
    req.add_header("content-type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        return int(exc.code), parsed


def _write_fixture(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _bootstrap_child(server: ApiServer, *, parent_run_id: str, child_run_id: str, child_seed: int) -> None:
    status, _ = _request(
        "POST",
        f"{server.base_url}/runs/{parent_run_id}/bootstrap-next-season",
        {"child_run_id": child_run_id, "child_seed": child_seed},
    )
    if status == 200:
        return
    status, _ = _request("POST", f"{server.base_url}/runs/{parent_run_id}/simulate/full-season")
    assert status == 200
    status, _ = _request("POST", f"{server.base_url}/runs/{parent_run_id}/rollover/next-season")
    assert status == 200
    status, _ = _request(
        "POST",
        f"{server.base_url}/runs/{parent_run_id}/bootstrap-next-season",
        {"child_run_id": child_run_id, "child_seed": child_seed},
    )
    assert status == 200


def test_single_season_player_returns_one_performance_entry(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-performance-single.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "single", "seed": 111, "season": 2027})
        assert status == 201

        status, players = _request("GET", f"{server.base_url}/runs/single/players")
        assert status == 200
        sample = players["players"][0]

        status, performance = _request(
            "GET", f"{server.base_url}/runs/single/players/{sample['player_id']}/career/performance"
        )
        assert status == 200
        assert performance["requested_run_id"] == "single"
        assert performance["player_id"] == sample["player_id"]
        assert len(performance["entries"]) == 1
        assert performance["entries"][0]["run_id"] == "single"
        assert performance["entries"][0]["season"] == 2027


def test_multi_season_carried_player_returns_chronological_performance(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-performance-chain.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "parent", "seed": 222, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs/parent/simulate/full-season")
        assert status == 200
        _bootstrap_child(server, parent_run_id="parent", child_run_id="child", child_seed=333)

        status, carried_players = _request("GET", f"{server.base_url}/runs/child/players?source_type=rollover_carried")
        assert status == 200
        carried = carried_players["players"][0]

        status, performance = _request(
            "GET", f"{server.base_url}/runs/child/players/{carried['player_id']}/career/performance"
        )
        assert status == 200
        seasons = [entry["season"] for entry in performance["entries"]]
        assert seasons == sorted(seasons)
        run_ids = {entry["run_id"] for entry in performance["entries"]}
        assert {"parent", "child"}.issubset(run_ids)


def test_ranking_and_race_positions_are_returned_when_available(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-performance-snapshots.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "single", "seed": 444, "season": 2027})
        assert status == 201

        status, players = _request("GET", f"{server.base_url}/runs/single/players")
        assert status == 200
        sample = players["players"][0]

        status, _ = _request("POST", f"{server.base_url}/runs/single/simulate/full-season")
        assert status == 200

        status, performance = _request(
            "GET", f"{server.base_url}/runs/single/players/{sample['player_id']}/career/performance"
        )
        assert status == 200
        assert performance["entries"][0]["ranking_position"] is not None
        assert performance["entries"][0]["race_position"] is not None


def test_missing_data_returns_graceful_null_or_zero_values(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-performance-missing.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "single", "seed": 555, "season": 2027})
        assert status == 201

        status, players = _request("GET", f"{server.base_url}/runs/single/players")
        assert status == 200
        sample = players["players"][0]

        status, performance = _request(
            "GET", f"{server.base_url}/runs/single/players/{sample['player_id']}/career/performance"
        )
        assert status == 200
        entry = performance["entries"][0]
        assert entry["ranking_position"] is None
        assert entry["race_position"] is None
        assert entry["tournaments_played"] == 0
        assert entry["titles"] == 0
        assert entry["wins"] == 0
        assert entry["losses"] == 0


def test_nonexistent_player_returns_404(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-performance-404.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "single", "seed": 666, "season": 2027})
        assert status == 201

        status, _ = _request("GET", f"{server.base_url}/runs/single/players/not-real/career/performance")
        assert status == 404


def test_branch_traversal_does_not_invent_entries_when_player_absent(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-performance-branch.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "parent", "seed": 777, "season": 2027})
        assert status == 201
        _bootstrap_child(server, parent_run_id="parent", child_run_id="child-a", child_seed=888)
        _bootstrap_child(server, parent_run_id="parent", child_run_id="child-b", child_seed=999)

        status, child_a_players = _request(
            "GET", f"{server.base_url}/runs/child-a/players?source_type=planner_generated&limit=500"
        )
        assert status == 200
        status, child_b_players = _request("GET", f"{server.base_url}/runs/child-b/players?limit=500")
        assert status == 200

        child_b_ids = {player["player_id"] for player in child_b_players["players"]}
        planner_only = next(
            (player for player in child_a_players["players"] if player["player_id"] not in child_b_ids),
            None,
        )
        assert planner_only is not None

        status, performance = _request(
            "GET", f"{server.base_url}/runs/child-a/players/{planner_only['player_id']}/career/performance"
        )
        assert status == 200
        run_ids = {entry["run_id"] for entry in performance["entries"]}
        assert "child-a" in run_ids
        assert "child-b" not in run_ids
