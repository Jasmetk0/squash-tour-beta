from __future__ import annotations

import json
from urllib import error, request

import pytest
from sqlalchemy import select

from test_simulation_api import ApiServer, _request
from beta_engine.infrastructure.db import (
    DatabaseSettings, SimulationPersistenceRepository, create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchSimulationCommandModel, BranchStateModel,
    FinalsQualificationModel, FinalsResultModel, RunBranchModel, RunContainerModel,
    SeasonStateModel,
)


_MODELS = (
    SeasonStateModel, FinalsQualificationModel, FinalsResultModel,
    BranchCheckpointModel, RunBranchModel, BranchStateModel,
    BranchSimulationCommandModel, RunContainerModel,
)


def _repository(database_url):
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    return SimulationPersistenceRepository(
        engine=engine, session_factory=create_session_factory(engine)
    )


def _snapshot(repository):
    with repository._session_factory() as session:
        return {
            model.__tablename__: sorted(
                [
                    {column.name: getattr(row, column.name) for column in model.__table__.columns}
                    for row in session.execute(select(model)).scalars()
                ],
                key=lambda row: json.dumps(row, sort_keys=True, default=str),
            )
            for model in _MODELS
        }


def _complete_regular_season(server):
    assert _request("POST", f"{server.base_url}/runs", {"run_id": "source", "seed": 47, "season": 2027})[0] == 201
    _, branches = _request("GET", f"{server.base_url}/run-branches?run_id=source")
    branch_id = branches["run_branches"][0]["branch_id"]
    _, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "source"})
    common = {"audit_reason": "test", "explicit_confirmation": True}
    full_url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-full-season"
    status, regular = _request("POST", full_url, {**common, "expected_head_checkpoint_id": checkpoint["checkpoint_id"], "command_id": "regular"})
    assert status == 200
    url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-world-tour-finals"
    payload = {**common, "expected_head_checkpoint_id": regular["new_head_checkpoint_id"], "command_id": "finals"}
    return branch_id, regular["new_head_checkpoint_id"], url, payload


def test_admin_branch_world_tour_finals_typed_success_and_replay(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'api-finals.db'}"
    with ApiServer(database_url=database_url) as server:
        branch_id, head, url, payload = _complete_regular_season(server)
        status, result = _request("POST", url, payload)
        assert status == 200
        assert result["finals"]["already_simulated"] is False
        assert result["finals"]["event_id"] == "WORLD_TOUR_FINALS"
        assert result["official_branch_changed"] is False
        assert result["previous_season"] == result["current_season"]
        assert _request("POST", url, payload)[1]["idempotent_replay"] is True
        assert _request("POST", url, {**payload, "explicit_confirmation": False})[0] == 400
        assert _request("POST", url, {**payload, "audit_reason": "   "})[0] == 400
        assert _request("POST", url, {**payload, "audit_reason": "changed"})[0] == 409
        assert _request("POST", url, {**payload, "expected_head_checkpoint_id": result["new_head_checkpoint_id"], "command_id": "different"})[0] == 409


def test_admin_branch_world_tour_finals_validation(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'validation.db'}") as server:
        url = f"{server.base_url}/admin/runs/missing/branches/missing/simulate-world-tour-finals"
        payload = {"expected_head_checkpoint_id": "head", "command_id": "finals", "audit_reason": "test", "explicit_confirmation": True}
        assert _request("POST", url, payload)[0] == 404
        assert _request("POST", url, {**payload, "explicit_confirmation": False})[0] == 400


def test_admin_branch_finals_checkpoint_mismatch_is_409(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'coherence.db'}"
    with ApiServer(database_url=database_url) as server:
        _, head, url, payload = _complete_regular_season(server)
        repository = _repository(database_url)
        with repository._session_factory.begin() as session:
            checkpoint = session.get(BranchCheckpointModel, head)
            checkpoint_payload = json.loads(checkpoint.payload_json)
            checkpoint_payload["season_state"]["completed_event_ids"] = []
            checkpoint.payload_json = json.dumps(checkpoint_payload, sort_keys=True, separators=(",", ":"))
        before = _snapshot(repository)
        assert _request("POST", url, payload)[0] == 409
        assert _snapshot(repository) == before


def test_admin_branch_finals_internal_failure_is_500_and_rolls_back(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'rollback.db'}"
    with ApiServer(database_url=database_url) as server:
        _, _, url, payload = _complete_regular_season(server)
        repository = _repository(database_url)
        runtime_repository = server.server.config.app.state.runtime.repository
        original = runtime_repository._upsert_finals_result_in_session

        def fail_after_result_upsert(**kwargs):
            original(**kwargs)
            raise RuntimeError("injected finals persistence failure")

        runtime_repository._upsert_finals_result_in_session = fail_after_result_upsert
        before = _snapshot(repository)
        try:
            http_request = request.Request(
                url, data=json.dumps(payload).encode(), method="POST",
                headers={"content-type": "application/json"},
            )
            with pytest.raises(error.HTTPError) as exc_info:
                request.urlopen(http_request, timeout=60)
            assert exc_info.value.code == 500
            exc_info.value.close()
            assert _snapshot(repository) == before
        finally:
            runtime_repository._upsert_finals_result_in_session = original
