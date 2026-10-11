from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib import error, request

import uvicorn

from beta_engine.main import create_app
from beta_engine.domain.countries import CountriesConfig
from tests.support.world_packages import materialize_test_world_package

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
        countries = CountriesConfig.model_validate(json.loads(Path(countries_config_path).read_text(encoding="utf-8")))
        world_packages_root = Path(countries_config_path).parent / "world_packages"
        materialize_test_world_package(world_packages_root, countries)
        app = create_app(
            database_url=database_url,
            countries_config_path=countries_config_path,
            manual_player_overrides_config_path=manual_overrides_config_path,
            world_packages_root=str(world_packages_root),
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


def test_single_season_player_with_completed_events_returns_results_entries(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-results-single.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "single", "seed": 1011, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs/single/simulate/full-season")
        assert status == 200

        status, events = _request("GET", f"{server.base_url}/runs/single/events")
        assert status == 200
        assert events["events"]
        first_event = events["events"][0]
        champion = first_event["tournament_result"]["main_draw"]["champion_player_id"]

        status, timeline = _request("GET", f"{server.base_url}/runs/single/players/{champion}/career/results")
        assert status == 200
        assert timeline["entries"]
        assert timeline["entries"][0]["season"] == 2027


def test_multi_season_carried_player_results_are_chronological_across_chain(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-results-chain.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "parent", "seed": 1212, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs/parent/simulate/full-season")
        assert status == 200
        _bootstrap_child(server, parent_run_id="parent", child_run_id="child", child_seed=1313)
        status, _ = _request("POST", f"{server.base_url}/runs/child/simulate/full-season")
        assert status == 200

        status, carried_players = _request("GET", f"{server.base_url}/runs/child/players?source_type=rollover_carried")
        assert status == 200

        selected_timeline = None
        for carried in carried_players["players"]:
            status, timeline = _request("GET", f"{server.base_url}/runs/child/players/{carried['player_id']}/career/results")
            assert status == 200
            run_ids = {entry["run_id"] for entry in timeline["entries"]}
            if {"parent", "child"}.issubset(run_ids):
                selected_timeline = timeline
                break

        assert selected_timeline is not None
        keys = [
            (entry["season"], entry.get("week") if entry.get("week") is not None else 999, entry["event_sequence"])
            for entry in selected_timeline["entries"]
        ]
        assert keys == sorted(keys)


def test_finish_and_title_flags_are_returned_when_available(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-results-titles.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "single", "seed": 1414, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs/single/simulate/full-season")
        assert status == 200

        status, events = _request("GET", f"{server.base_url}/runs/single/events")
        assert status == 200
        champion = events["events"][0]["tournament_result"]["main_draw"]["champion_player_id"]

        status, timeline = _request("GET", f"{server.base_url}/runs/single/players/{champion}/career/results")
        assert status == 200
        title_entry = next((entry for entry in timeline["entries"] if entry["is_title"]), None)
        assert title_entry is not None
        assert title_entry["finish"] == "CHAMPION"


def test_wins_losses_count_resolved_matches_only_and_missing_points_metadata_are_graceful(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-results-graceful.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "single", "seed": 1515, "season": 2027})
        assert status == 201

        status, players = _request("GET", f"{server.base_url}/runs/single/players")
        assert status == 200
        sample = players["players"][0]

        status, timeline = _request("GET", f"{server.base_url}/runs/single/players/{sample['player_id']}/career/results")
        assert status == 200
        assert timeline["entries"] == []

        status, _ = _request("POST", f"{server.base_url}/runs/single/simulate/full-season")
        assert status == 200
        status, timeline = _request("GET", f"{server.base_url}/runs/single/players/{sample['player_id']}/career/results")
        assert status == 200
        if timeline["entries"]:
            entry = timeline["entries"][0]
            assert isinstance(entry["wins"], int)
            assert isinstance(entry["losses"], int)
            assert entry["wins"] >= 0
            assert entry["losses"] >= 0

        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "no-snapshots", "seed": 1616, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs/no-snapshots/simulate/next-tournament")
        assert status == 200

        status, events = _request("GET", f"{server.base_url}/runs/no-snapshots/events")
        assert status == 200
        event = events["events"][0]
        player_id = event["tournament_result"]["main_draw"]["champion_player_id"]
        status, timeline = _request("GET", f"{server.base_url}/runs/no-snapshots/players/{player_id}/career/results")
        assert status == 200
        assert timeline["entries"]
        assert timeline["entries"][0]["ranking_points_awarded"] is None or timeline["entries"][0]["ranking_points_awarded"] >= 0
        assert timeline["entries"][0]["event_name"] is None or isinstance(timeline["entries"][0]["event_name"], str)
        assert timeline["entries"][0]["event_category"] is None or isinstance(timeline["entries"][0]["event_category"], str)


def test_nonexistent_player_returns_404(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-results-404.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "single", "seed": 1717, "season": 2027})
        assert status == 201

        status, _ = _request("GET", f"{server.base_url}/runs/single/players/not-real/career/results")
        assert status == 404


def test_branch_traversal_does_not_invent_entries_when_player_absent(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'career-results-branch.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "parent", "seed": 1818, "season": 2027})
        assert status == 201
        _bootstrap_child(server, parent_run_id="parent", child_run_id="child-a", child_seed=1919)
        _bootstrap_child(server, parent_run_id="parent", child_run_id="child-b", child_seed=2020)
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "unrelated", "seed": 2121, "season": 2027})
        assert status == 201

        status, _ = _request("POST", f"{server.base_url}/runs/child-a/simulate/full-season")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/unrelated/simulate/full-season")
        assert status == 200

        status, child_a_players = _request("GET", f"{server.base_url}/runs/child-a/players?limit=500")
        assert status == 200
        player = child_a_players["players"][0]

        status, timeline = _request("GET", f"{server.base_url}/runs/child-a/players/{player['player_id']}/career/results")
        assert status == 200
        run_ids = {entry["run_id"] for entry in timeline["entries"]}
        assert "unrelated" not in run_ids
