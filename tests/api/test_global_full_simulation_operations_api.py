"""Production FastAPI route and SQLite read-only Task Center evidence boundary."""

import json

import pytest
from contextlib import contextmanager
from threading import Thread
import socket
import time
from urllib.error import HTTPError
from urllib.request import urlopen

import uvicorn

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeFullSimulationCommand,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel, FullSimulationExecutionLeaseModel,
    RunBranchModel, RunContainerModel,
)
from beta_engine.main import create_app


class _Response:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


def _get(base_url: str, path: str) -> _Response:
    try:
        with urlopen(base_url + path, timeout=10) as response:
            return _Response(response.status, response.read().decode("utf-8"))
    except HTTPError as exc:
        return _Response(exc.code, exc.read().decode("utf-8"))


@contextmanager
def _server(app):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="error"
    ))
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                _get(base, "/health")
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Task Center HTTP test server did not start")
                time.sleep(0.05)
        yield base
    finally:
        server.should_exit = True
        thread.join(timeout=10)


@pytest.mark.pr_critical
def test_task_center_http_sqlite_inventory_is_read_only_and_conflicts_on_corruption(tmp_path):
    url = f"sqlite:///{tmp_path / 'task-center-route.db'}"
    app = create_app(database_url=url)
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    factory = create_session_factory(engine)
    command = AuthoritativeFullSimulationCommand(
        command_id="parent", run_id="run", branch_id="branch",
        operator_label="Admin", audit_reason="Explicit review",
        expected_start_week=RankingWeek(season_index=49, week=2),
        expected_position_fingerprint="a" * 64,
        expected_revision_id="rev", expected_preview_fingerprint="b" * 64,
    )
    payload = {
        "schema_version": "authoritative_full_simulation_operation.v1",
        "run_id": "run", "branch_id": "branch",
        "initial_saved_revision_id": "rev",
        "resume_command": command.model_dump(mode="json"),
        "review": {
            "schema_version": "authoritative_full_simulation_preview.v1",
            "run_id": "run", "branch_id": "branch",
            "start_week": {"season_index": 49, "week": 2},
            "final_week": {"season_index": 49, "week": 61},
            "preview_fingerprint": "b" * 64,
            "expected_position_fingerprint": "a" * 64,
            "expected_revision_id": "rev",
        },
        "start_week": {"season_index": 49, "week": 2},
        "final_week": {"season_index": 49, "week": 61},
        "completed_seasons": [],
        "final_completed_weeks": [
            {"season_index": 49, "week": 2},
            {"season_index": 49, "week": 3},
        ],
        "control_state": "paused",
    }
    with factory.begin() as session:
        session.add(RunContainerModel(
            run_id="run", display_name="Run", storage_kind="custom_local",
            read_only=0, timeline_start_season=2000, timeline_end_season=2049,
            official_branch_id="branch", status="working",
        ))
        session.add(RunBranchModel(
            run_id="run", branch_id="branch", display_name="Timeline 1",
            status="active", read_only=0,
        ))
        session.add(AuthoritativeSimulationCommandModel(
            run_id="run", branch_id="branch", command_id="parent",
            request_fingerprint=fingerprint({
                "mode": "full_simulation",
                "command": command.model_dump(mode="json"),
            }),
            status="pending", result_json=json.dumps(payload),
        ))
        session.add(FullSimulationExecutionLeaseModel(
            lease_scope="all_runs", owner_token="NEVER-SEND-TO-UI",
            run_id="run", branch_id="branch", command_id="parent",
            expires_at_unix=1,
        ))

    try:
        with _server(app) as base_url:
            first = _get(base_url, "/run-containers/full-simulation/operations")
            assert first.status_code == 200, first.text
            response = first.json()
            operation = response["operations"][0]
            assert response["pending_count"] == 1
            assert operation["control_state"] == "paused"
            assert operation["lease_state"] == "matching_expired"
            assert operation["final_completed_week_count"] == 2
            assert operation["worker_activity"] == "unknown"
            assert "NEVER-SEND-TO-UI" not in first.text
            second = _get(base_url, "/run-containers/full-simulation/operations")
            assert second.json() == response
            with factory() as session:
                parent = session.get(
                    AuthoritativeSimulationCommandModel, ("run", "branch", "parent")
                )
                assert json.loads(parent.result_json) == payload
                lease = session.get(FullSimulationExecutionLeaseModel, "all_runs")
                assert lease.owner_token == "NEVER-SEND-TO-UI"
                assert lease.expires_at_unix == 1
            with factory.begin() as session:
                parent = session.get(
                    AuthoritativeSimulationCommandModel, ("run", "branch", "parent")
                )
                corrupted = json.loads(parent.result_json)
                corrupted["review"]["final_week"] = {"season_index": 99, "week": 999}
                parent.result_json = json.dumps(corrupted)
            failed = _get(base_url, "/run-containers/full-simulation/operations")
            assert failed.status_code == 409
            assert failed.json()["detail"]["code"] == (
                "global_full_simulation_operations_conflict"
            )
    finally:
        engine.dispose()
