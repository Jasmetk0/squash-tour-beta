from __future__ import annotations

import json
import socket
import threading
import time
from typing import Self
from urllib import error, parse, request

import uvicorn
from sqlalchemy import text

from beta_engine.main import create_app


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


def _create_run(server: ApiServer, *, display_name: str) -> tuple[str, str, str]:
    status_code, run = _request(
        "POST",
        f"{server.base_url}/run-containers",
        {"display_name": display_name},
    )
    assert status_code == 201
    run_id = str(run["run_id"])
    branch_id = str(run["viewer_branch_id"])
    status_code, branch_index = _request(
        "GET",
        f"{server.base_url}/run-branches?{parse.urlencode({'run_id': run_id})}",
    )
    assert status_code == 200
    revision_id = str(branch_index["run_branches"][0]["saved_head_revision_id"])
    return run_id, branch_id, revision_id


def test_saved_revision_history_api_supports_historical_branching(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'revision-history-api.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, initial_branch_id, initial_revision_id = _create_run(
            server,
            display_name="API Revision History",
        )
        status_code, fork = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": initial_branch_id,
                "source_saved_revision_id": initial_revision_id,
            },
        )
        assert status_code == 201
        fork_id = str(fork["branch_id"])
        draft_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/"
            f"{fork_id}/working-draft"
        )
        status_code, staged = _request(
            "PUT",
            f"{draft_url}/viewer-branch",
            {"viewer_branch_id": fork_id, "expected_draft_version": 0},
        )
        assert status_code == 200
        status_code, saved = _request(
            "POST",
            f"{draft_url}/save",
            {"expected_draft_version": staged["draft_version"]},
        )
        assert status_code == 201
        saved_revision_id = str(saved["saved_revision"]["revision_id"])

        history_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/"
            f"{fork_id}/saved-revisions"
        )
        status_code, history = _request("GET", history_url)
        assert status_code == 200
        assert history["run_id"] == run_id
        assert history["branch_id"] == fork_id
        assert history["saved_head_revision_id"] == saved_revision_id
        assert [item["revision_id"] for item in history["saved_revisions"]] == [
            initial_revision_id,
            saved_revision_id,
        ]
        assert [item["is_shared_revision"] for item in history["saved_revisions"]] == [
            True,
            False,
        ]
        assert [item["is_branch_head"] for item in history["saved_revisions"]] == [
            False,
            True,
        ]

        status_code, detail = _request(
            "GET",
            f"{history_url}/{initial_revision_id}",
        )
        assert status_code == 200
        assert detail["revision_id"] == initial_revision_id
        assert detail["revision_branch_id"] == initial_branch_id
        assert detail["branch_id"] == fork_id
        assert detail["is_shared_revision"] is True
        assert detail["payload"]["branch"]["branch_id"] == initial_branch_id

        status_code, historical_fork = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": fork_id,
                "source_saved_revision_id": detail["revision_id"],
            },
        )
        assert status_code == 201
        assert historical_fork["saved_head_revision_id"] == initial_revision_id
        assert historical_fork["forked_from_branch_id"] == fork_id


def test_saved_revision_history_api_is_scoped_and_fail_closed(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'revision-history-api-errors.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, revision_id = _create_run(
            server,
            display_name="Scoped History",
        )
        _, _, other_revision_id = _create_run(
            server,
            display_name="Other Scoped History",
        )
        history_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/"
            f"{branch_id}/saved-revisions"
        )

        status_code, missing = _request(
            "GET",
            f"{history_url}/{other_revision_id}",
        )
        assert status_code == 404
        assert missing["detail"]["code"] == "saved_revision_history_not_found"

        status_code, missing_branch = _request(
            "GET",
            f"{server.base_url}/run-containers/{run_id}/branches/"
            "missing-branch/saved-revisions",
        )
        assert status_code == 404
        assert missing_branch["detail"]["code"] == "saved_revision_history_not_found"

        repository = server.app.state.runtime.repository
        with repository._engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE branch_saved_revisions "
                    "SET change_summary_json = :change_summary_json "
                    "WHERE revision_id = :revision_id"
                ),
                {
                    "change_summary_json": '{"tampered":true}',
                    "revision_id": revision_id,
                },
            )

        status_code, corrupt = _request("GET", history_url)
        assert status_code == 409
        assert corrupt["detail"]["code"] == "saved_revision_history_conflict"


def test_saved_revision_restore_api_requires_confirmation_and_returns_checkpoint(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'revision-restore-api.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, initial_revision_id = _create_run(
            server,
            display_name="API Revision Restore",
        )
        status_code, fork = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": branch_id,
                "source_saved_revision_id": initial_revision_id,
            },
        )
        assert status_code == 201
        fork_id = str(fork["branch_id"])
        draft_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/"
            f"{branch_id}/working-draft"
        )
        status_code, staged = _request(
            "PUT",
            f"{draft_url}/viewer-branch",
            {"viewer_branch_id": fork_id, "expected_draft_version": 0},
        )
        assert status_code == 200
        status_code, saved = _request(
            "POST",
            f"{draft_url}/save",
            {"expected_draft_version": staged["draft_version"]},
        )
        assert status_code == 201
        saved_revision_id = str(saved["saved_revision"]["revision_id"])
        restore_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/"
            f"saved-revisions/{initial_revision_id}/restore"
        )
        restore_request = {
            "expected_head_saved_revision_id": saved_revision_id,
            "expected_draft_version": saved["working_draft"]["draft_version"],
            "expected_current_viewer_branch_id": fork_id,
            "explicit_confirmation": False,
        }

        status_code, unconfirmed = _request("POST", restore_url, restore_request)
        assert status_code == 409
        assert (
            unconfirmed["detail"]["code"]
            == "saved_revision_restore_conflict"
        )

        restore_request["explicit_confirmation"] = True
        status_code, restored = _request("POST", restore_url, restore_request)
        assert status_code == 201
        assert restored["previous_saved_head_revision_id"] == saved_revision_id
        assert restored["target_saved_revision_id"] == initial_revision_id
        assert restored["previous_viewer_branch_id"] == fork_id
        assert restored["viewer_branch_id"] == branch_id
        assert restored["saved_revision"]["kind"] == "branch_restore"
        assert restored["saved_revision"]["parent_revision_id"] == saved_revision_id
        assert restored["safety_checkpoint"]["kind"] == (
            "pre_restore_saved_revision"
        )
        assert (
            restored["safety_checkpoint"]["saved_revision_id"]
            == saved_revision_id
        )
        assert (
            restored["safety_checkpoint"]["restore_saved_revision_id"]
            == restored["saved_revision"]["revision_id"]
        )
        assert restored["working_draft"]["status"] == "clean"
        assert (
            restored["working_draft"]["base_saved_revision_id"]
            == restored["saved_revision"]["revision_id"]
        )

        recovery_activity_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/"
            "saved-revision-recovery-activity"
        )
        status_code, recovery_activity = _request("GET", recovery_activity_url)
        assert status_code == 200
        assert recovery_activity["run_id"] == run_id
        assert recovery_activity["branch_id"] == branch_id
        assert (
            recovery_activity["saved_head_revision_id"]
            == restored["saved_revision"]["revision_id"]
        )
        assert len(recovery_activity["safety_checkpoints"]) == 1
        recovery_checkpoint = recovery_activity["safety_checkpoints"][0]
        assert recovery_checkpoint["run_id"] == run_id
        assert recovery_checkpoint["branch_id"] == branch_id
        assert recovery_checkpoint["checkpoint_id"] == (
            restored["safety_checkpoint"]["checkpoint_id"]
        )
        assert recovery_checkpoint["saved_revision_id"] == saved_revision_id
        assert [event["event_kind"] for event in recovery_activity["audit_events"]] == [
            "saved_revision_created",
            "branch_restored",
        ]
        assert recovery_activity["audit_events"][-1]["payload"]["checkpoint_id"] == (
            recovery_checkpoint["checkpoint_id"]
        )

        history_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/"
            f"{branch_id}/saved-revisions"
        )
        status_code, history = _request("GET", history_url)
        assert status_code == 200
        assert [item["revision_id"] for item in history["saved_revisions"]] == [
            initial_revision_id,
            saved_revision_id,
            restored["saved_revision"]["revision_id"],
        ]

        stale_request = dict(restore_request)
        stale_request["explicit_confirmation"] = True
        status_code, stale = _request("POST", restore_url, stale_request)
        assert status_code == 409
        assert (
            stale["detail"]["code"]
            == "saved_revision_restore_version_conflict"
        )


def test_saved_revision_recovery_activity_api_is_scoped_and_fail_closed(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'recovery-activity-api-errors.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="Scoped Recovery Activity",
        )
        activity_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/"
            "saved-revision-recovery-activity"
        )

        status_code, activity = _request("GET", activity_url)
        assert status_code == 200
        assert activity["safety_checkpoints"] == []
        assert activity["audit_events"] == []

        status_code, missing = _request(
            "GET",
            f"{server.base_url}/run-containers/{run_id}/branches/missing-branch/"
            "saved-revision-recovery-activity",
        )
        assert status_code == 404
        assert missing["detail"]["code"] == (
            "saved_revision_recovery_activity_not_found"
        )

        repository = server.app.state.runtime.repository
        with repository._engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE branch_saved_revisions "
                    "SET change_summary_json = :change_summary_json "
                    "WHERE revision_id = :revision_id"
                ),
                {
                    "change_summary_json": '{"tampered":true}',
                    "revision_id": activity["saved_head_revision_id"],
                },
            )

        status_code, corrupt = _request("GET", activity_url)
        assert status_code == 409
        assert corrupt["detail"]["code"] == (
            "saved_revision_recovery_activity_conflict"
        )
