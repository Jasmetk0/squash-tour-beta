from __future__ import annotations

import json
import socket
import threading
import time
from urllib import error, request

import uvicorn

from beta_engine.main import create_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


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
                _request("GET", f"{self.base_url}/health")
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


def test_race_snapshot_contract_is_distinct_from_ranking_snapshot_contract(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-race-contract.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-contract", "seed": 9090, "season": 2027},
        )
        assert status == 201

        ranking_payload: dict[str, object] = {"snapshots": []}
        for _ in range(10):
            status, _ = _request("POST", f"{server.base_url}/runs/run-contract/simulate/next-week")
            assert status == 200
            status, ranking_payload = _request("GET", f"{server.base_url}/runs/run-contract/snapshots/ranking")
            assert status == 200
            if ranking_payload["snapshots"]:
                break
        assert ranking_payload["snapshots"]

        status, race_payload = _request("GET", f"{server.base_url}/runs/run-contract/snapshots/race")
        assert status == 200
        assert race_payload["snapshots"]

        assert [record["snapshot_sequence"] for record in ranking_payload["snapshots"]] == [
            record["snapshot_sequence"] for record in race_payload["snapshots"]
        ]

        ranking_record = ranking_payload["snapshots"][0]
        race_record = race_payload["snapshots"][0]
        assert set(ranking_record.keys()) == {"snapshot_sequence", "snapshot_kind", "source_event_id", "payload"}
        assert set(race_record.keys()) == {"snapshot_sequence", "snapshot_kind", "source_event_id", "payload"}
        assert "target_season" not in ranking_record["payload"]
        assert race_record["payload"]["target_season"] == 2027

        sequence = int(race_record["snapshot_sequence"])
        status, race_detail = _request("GET", f"{server.base_url}/runs/run-contract/snapshots/race/{sequence}")
        assert status == 200
        assert race_detail["snapshot_sequence"] == sequence
        assert race_detail["payload"]["target_season"] == 2027
