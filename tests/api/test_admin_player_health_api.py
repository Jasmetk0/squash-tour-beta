from __future__ import annotations

import json
import socket
import threading
import time
from typing import Self
from urllib import error, request

import pytest
import uvicorn

from beta_engine.domain.players.health import bootstrap_health_state
from beta_engine.infrastructure.db.player_health_state import put_health
from beta_engine.main import create_app

pytestmark = pytest.mark.pr_critical


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return int(server_socket.getsockname()[1])


class ApiServer:
    def __init__(self, *, database_url: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.app = create_app(database_url=database_url)
        self.server = uvicorn.Server(
            uvicorn.Config(
                app=self.app,
                host="127.0.0.1",
                port=self.port,
                log_level="error",
            )
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> Self:
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                _request("GET", f"{self.base_url}/health")
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def _request(
    method: str,
    url: str,
    payload: dict | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode()
    http_request = request.Request(url, data=body, method=method)
    http_request.add_header("content-type", "application/json")
    for key, value in (headers or {}).items():
        http_request.add_header(key, value)
    try:
        with request.urlopen(http_request, timeout=30) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode()
        return int(exc.code), json.loads(raw) if raw else {}


def test_admin_health_http_preview_commit_retry_and_save(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'admin-health-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "Health API"},
        )
        assert status == 201
        run_id = run["run_id"]
        branch_id = run["viewer_branch_id"]

        runtime = server.app.state.runtime
        with runtime.repository._session_factory.begin() as session:
            put_health(
                session,
                bootstrap_health_state(
                    run_id=run_id,
                    branch_id=branch_id,
                    source_initial_world_fingerprint="world",
                    player_ids=("p1",),
                ),
            )

        root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/players/p1/health"
        )
        status, current = _request("GET", root)
        assert status == 200
        assert current["player"]["records"] == []
        assert current["draft_version"] == 0

        payload = {
            "schema_version": "admin_health_edit_request.v1",
            "command_id": "http-health-edit",
            "player_id": "p1",
            "mode": "pre_start_input",
            "expected_draft_version": 0,
            "records": [
                {
                    "record_id": "prestart-ankle",
                    "kind": "Injury",
                    "condition_key": "ankle-history",
                    "lifecycle": "Active",
                    "severity": 22,
                    "affected_domains": ["movement"],
                    "onset_week": None,
                    "recovered_week": None,
                    "started_before_run": True,
                    "recurrence_of_record_id": None,
                    "recovery_window_min_weeks": 1,
                    "recovery_window_max_weeks": 4,
                    "provenance": "reviewed API pre-start input",
                }
            ],
            "permanent_consequences": [],
            "audit_label": "API Admin",
            "audit_reason": "Reviewed pre-start ankle history",
        }
        status, preview = _request("POST", root + "/preview", payload)
        assert status == 200
        assert len(preview["preview_fingerprint"]) == 64

        status, committed = _request(
            "POST",
            root,
            payload,
            headers={
                "X-Player-Health-Preview-Fingerprint": preview["preview_fingerprint"]
            },
        )
        assert status == 200
        assert committed["already_applied"] is False
        assert committed["draft_version"] == 1

        status, retried = _request(
            "POST",
            root,
            payload,
            headers={
                "X-Player-Health-Preview-Fingerprint": preview["preview_fingerprint"]
            },
        )
        assert status == 200
        assert retried["already_applied"] is True

        save_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/player-health/save"
        )
        status, save_preview = _request("GET", save_root + "/preview")
        assert status == 200
        assert save_preview["can_save"] is True
        assert save_preview["draft_version"] == 1

        status, saved = _request(
            "POST",
            save_root,
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_player_health_fingerprint": save_preview[
                    "health_component_fingerprint"
                ],
            },
        )
        assert status == 201
        assert saved["saved_revision"]["kind"] == "player_health_state"
        assert saved["working_draft"]["status"] == "clean"
