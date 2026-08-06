from __future__ import annotations

import json
from urllib import error, request

import pytest
from sqlalchemy import select

from test_simulation_api import ApiServer, _request
from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchSimulationCommandModel, BranchStateModel, CompletedEventMetadataModel,
    CompletedEventModel, CompletedTournamentInputModel, RaceSnapshotModel, RankingSnapshotModel,
    RunBranchModel, RunContainerModel, SeasonStateModel, SimulationRunModel,
)

MODELS = (SeasonStateModel, CompletedEventModel, CompletedTournamentInputModel,
          CompletedEventMetadataModel, RankingSnapshotModel, RaceSnapshotModel,
          BranchCheckpointModel, RunBranchModel, BranchStateModel, BranchSimulationCommandModel)


def _repo(database_url):
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def _setup(server):
    assert _request("POST", f"{server.base_url}/runs", {"run_id": "source", "seed": 47, "season": 2027})[0] == 201
    _, branches = _request("GET", f"{server.base_url}/run-branches?run_id=source")
    branch_id = branches["run_branches"][0]["branch_id"]
    _, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "source"})
    payload = {"expected_head_checkpoint_id": checkpoint["checkpoint_id"], "command_id": "api-tournament", "audit_reason": "test", "explicit_confirmation": True}
    url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-full-season"
    return branch_id, checkpoint["checkpoint_id"], url, payload


def _snapshot(repository):
    with repository._session_factory() as session:
        result = {}
        for model in MODELS:
            rows = [{c.name: getattr(row, c.name) for c in model.__table__.columns}
                    for row in session.execute(select(model)).scalars()]
            result[model.__tablename__] = sorted(rows, key=lambda x: json.dumps(x, sort_keys=True, default=str))
        return result


def test_admin_branch_full_season_success_replay_and_conflicts(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'success.db'}"
    with ApiServer(database_url=database_url) as server:
        branch_id, head, url, payload = _setup(server)
        status, result = _request("POST", url, payload)
        assert status == 200 and result["official_branch_changed"] is False
        assert set(result) == {"product_run_id", "branch_id", "legacy_simulation_run_id", "command_id", "request_fingerprint", "idempotent_replay", "previous_head_checkpoint_id", "new_head_checkpoint_id", "previous_season", "previous_week", "previous_event_id", "previous_event_sequence", "current_season", "current_week", "current_event_id", "current_event_sequence", "official_branch_changed", "simulation_result"}
        repo = _repo(database_url); after = _snapshot(repo)
        status, replay = _request("POST", url, payload)
        assert status == 200 and replay["idempotent_replay"] is True
        assert replay["new_head_checkpoint_id"] == result["new_head_checkpoint_id"]
        assert _snapshot(repo) == after
        assert _request("POST", url, {**payload, "audit_reason": "different"})[0] == 409
        assert _request("POST", url, {**payload, "command_id": "same-head"})[0] == 409
        with repo._session_factory() as session:
            journals = session.execute(select(BranchSimulationCommandModel).where(BranchSimulationCommandModel.previous_head_checkpoint_id == head)).scalars().all()
            assert len(journals) == 1 and journals[0].branch_id == branch_id


def test_admin_branch_full_season_validation(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'validation.db'}"
    with ApiServer(database_url=database_url) as server:
        _, _, url, payload = _setup(server)
        assert _request("POST", url, {**payload, "explicit_confirmation": False})[0] == 400
        assert _request("POST", url, {**payload, "command_id": "blank", "audit_reason": "   "})[0] == 400
