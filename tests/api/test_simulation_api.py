from __future__ import annotations

import json
import socket
import threading
import time
from urllib import error, request

import uvicorn

from beta_engine.main import create_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ApiServer:
    def __init__(self, *, database_url: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(database_url=database_url)
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


def test_run_initialization_and_state_fetch_work(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-init.db'}"
    with ApiServer(database_url=database_url) as server:
        status, run_payload = _request(
            "POST",
            f"{server.base_url}/runs",
            {
                "run_id": "run-init",
                "seed": 1001,
                "season": 2027,
                "config_version": "mvp",
                "config_fingerprint": "cfg-a",
            },
        )
        assert status == 201
        assert run_payload["run_id"] == "run-init"
        assert run_payload["next_event_index"] == 0

        status, state_payload = _request("GET", f"{server.base_url}/runs/run-init")
        assert status == 200
        assert state_payload["season_state"]["next_event_index"] == 0
        assert len(state_payload["season_state"]["ordered_events"]) > 0


def test_simulation_endpoints_and_snapshot_queries_work(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-sim.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-sim", "seed": 2002, "season": 2027},
        )
        assert status == 201

        status, run_state = _request("GET", f"{server.base_url}/runs/run-sim")
        assert status == 200
        first_week = run_state["season_state"]["ordered_events"][0]["week"]
        expected_week_event_ids = [
            event["event_id"] for event in run_state["season_state"]["ordered_events"] if event["week"] == first_week
        ]

        status, next_tournament = _request("POST", f"{server.base_url}/runs/run-sim/simulate/next-tournament")
        assert status == 200
        assert next_tournament["step"]["mode"] == "simulate_next_tournament"
        assert next_tournament["run"]["next_event_index"] == 1

        status, next_week = _request("POST", f"{server.base_url}/runs/run-sim/simulate/next-week")
        assert status == 200
        assert next_week["step"]["mode"] == "simulate_next_week"

        status, events_payload = _request("GET", f"{server.base_url}/runs/run-sim/events")
        assert status == 200
        observed_event_ids = [event["event_id"] for event in events_payload["events"]]
        assert observed_event_ids == expected_week_event_ids

        status, full_season = _request("POST", f"{server.base_url}/runs/run-sim/simulate/full-season")
        assert status == 200
        assert full_season["step"]["mode"] == "simulate_full_season"
        assert full_season["run"]["next_event_index"] == full_season["run"]["total_events"]

        status, ranking_payload = _request("GET", f"{server.base_url}/runs/run-sim/snapshots/ranking")
        assert status == 200
        status, race_payload = _request("GET", f"{server.base_url}/runs/run-sim/snapshots/race")
        assert status == 200

        ranking_sequences = [record["snapshot_sequence"] for record in ranking_payload["snapshots"]]
        race_sequences = [record["snapshot_sequence"] for record in race_payload["snapshots"]]
        assert ranking_sequences == sorted(ranking_sequences)
        assert race_sequences == sorted(race_sequences)

        first_event_id = events_payload["events"][0]["event_id"]
        status, event_detail = _request("GET", f"{server.base_url}/runs/run-sim/events/{first_event_id}")
        assert status == 200
        assert event_detail["event_id"] == first_event_id
        assert event_detail["tournament_result"] is not None
