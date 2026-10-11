from __future__ import annotations

import json
import socket
import threading
import time
from typing import Self
from urllib import error, parse, request

import uvicorn

from beta_engine.main import create_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return int(server_socket.getsockname()[1])


class ApiServer:
    def __init__(self, *, database_url: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(database_url=database_url)
        self.server = uvicorn.Server(
            uvicorn.Config(
                app=app,
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
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    body = None if payload is None else json.dumps(payload).encode()
    http_request = request.Request(url, data=body, method=method)
    http_request.add_header("content-type", "application/json")
    try:
        with request.urlopen(http_request, timeout=60) as response:
            raw = response.read().decode()
            return response.status, (json.loads(raw) if raw else {})
    except error.HTTPError as exc:
        raw = exc.read().decode()
        return int(exc.code), (json.loads(raw) if raw else {})


def test_viewer_branch_draft_and_save_api_boundary(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-draft-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status_code, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "API History"},
        )
        assert status_code == 201
        run_id = run["run_id"]
        initial_branch_id = run["viewer_branch_id"]

        status_code, branch_index = _request(
            "GET",
            f"{server.base_url}/run-branches?{parse.urlencode({'run_id': run_id})}",
        )
        assert status_code == 200
        initial_revision_id = branch_index["run_branches"][0]["saved_head_revision_id"]
        status_code, created_branch = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": initial_branch_id,
                "source_saved_revision_id": initial_revision_id,
            },
        )
        assert status_code == 201
        target_branch_id = created_branch["branch_id"]
        draft_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/"
            f"{initial_branch_id}/working-draft"
        )

        status_code, clean = _request("GET", draft_url)
        assert status_code == 200
        assert clean == {
            "run_id": run_id,
            "branch_id": initial_branch_id,
            "draft_id": clean["draft_id"],
            "base_saved_revision_id": initial_revision_id,
            "saved_viewer_branch_id": initial_branch_id,
            "proposed_viewer_branch_id": initial_branch_id,
            "current_viewer_branch_id": initial_branch_id,
            "status": "clean",
            "change_count": 0,
            "draft_version": 0,
            "can_save": False,
        }

        status_code, staged = _request(
            "PUT",
            f"{draft_url}/viewer-branch",
            {
                "viewer_branch_id": target_branch_id,
                "expected_draft_version": 0,
            },
        )
        assert status_code == 200
        assert staged["status"] == "dirty"
        assert staged["saved_viewer_branch_id"] == initial_branch_id
        assert staged["proposed_viewer_branch_id"] == target_branch_id
        assert staged["current_viewer_branch_id"] == initial_branch_id
        assert staged["draft_version"] == 1
        assert staged["can_save"] is True
        status_code, unchanged_run = _request(
            "GET", f"{server.base_url}/run-containers/{run_id}"
        )
        assert status_code == 200
        assert unchanged_run["viewer_branch_id"] == initial_branch_id

        status_code, stale = _request(
            "PUT",
            f"{draft_url}/viewer-branch",
            {
                "viewer_branch_id": initial_branch_id,
                "expected_draft_version": 0,
            },
        )
        assert status_code == 409
        assert stale["detail"]["code"] == "working_draft_version_conflict"

        status_code, saved = _request(
            "POST", f"{draft_url}/save", {"expected_draft_version": 1}
        )
        assert status_code == 201
        assert saved["previous_viewer_branch_id"] == initial_branch_id
        assert saved["viewer_branch_id"] == target_branch_id
        assert saved["audit_event_id"]
        assert saved["saved_revision"]["sequence"] == 2
        assert saved["saved_revision"]["parent_revision_id"] == initial_revision_id
        assert saved["saved_revision"]["kind"] == "viewer_branch_selection"
        assert saved["saved_revision"]["content_hash_algorithm"] == "sha256"
        assert saved["working_draft"]["status"] == "clean"
        assert saved["working_draft"]["draft_version"] == 2
        assert saved["working_draft"]["can_save"] is False
        status_code, switched_run = _request(
            "GET", f"{server.base_url}/run-containers/{run_id}"
        )
        assert status_code == 200
        assert switched_run["viewer_branch_id"] == target_branch_id

        status_code, reloaded = _request("GET", draft_url)
        assert status_code == 200
        assert reloaded["saved_viewer_branch_id"] == target_branch_id
        assert reloaded["current_viewer_branch_id"] == target_branch_id

        status_code, clean_save = _request(
            "POST", f"{draft_url}/save", {"expected_draft_version": 2}
        )
        assert status_code == 409
        assert clean_save["detail"]["code"] == "working_draft_conflict"


def test_viewer_branch_draft_api_reports_missing_target_and_validation(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-draft-api-errors.db'}"
    with ApiServer(database_url=database_url) as server:
        status_code, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "API Errors"},
        )
        assert status_code == 201
        run_id = run["run_id"]
        branch_id = run["viewer_branch_id"]
        draft_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/"
            f"{branch_id}/working-draft"
        )

        status_code, missing = _request(
            "PUT",
            f"{draft_url}/viewer-branch",
            {
                "viewer_branch_id": "missing-branch",
                "expected_draft_version": 0,
            },
        )
        assert status_code == 404
        assert missing["detail"]["code"] == "working_draft_not_found"

        status_code, _ = _request(
            "POST", f"{draft_url}/save", {"expected_draft_version": -1}
        )
        assert status_code == 422
        status_code, draft = _request("GET", draft_url)
        assert status_code == 200
        assert draft["draft_version"] == 0
