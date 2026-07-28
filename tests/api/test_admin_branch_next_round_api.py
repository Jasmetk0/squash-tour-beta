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
    payload = {"expected_head_checkpoint_id": checkpoint["checkpoint_id"], "command_id": "api-round", "audit_reason": "test", "explicit_confirmation": True}
    url = f"{server.base_url}/admin/runs/source/branches/{branch_id}/simulate-next-round"
    return branch_id, checkpoint["checkpoint_id"], url, payload


def _snapshot(repository):
    with repository._session_factory() as session:
        result = {}
        for model in MODELS:
            rows = [{c.name: getattr(row, c.name) for c in model.__table__.columns}
                    for row in session.execute(select(model)).scalars()]
            result[model.__tablename__] = sorted(rows, key=lambda x: json.dumps(x, sort_keys=True, default=str))
        return result


def test_admin_branch_next_round_success_replay_and_conflicts(tmp_path):
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


@pytest.mark.parametrize("case", ["product", "branch", "legacy", "checkpoint"])
def test_admin_branch_next_round_not_found_cases(tmp_path, case):
    database_url = f"sqlite:///{tmp_path / f'404-{case}.db'}"
    with ApiServer(database_url=database_url) as server:
        branch_id, head, url, payload = _setup(server); repo = _repo(database_url)
        if case == "product": url = f"{server.base_url}/admin/runs/missing/branches/{branch_id}/simulate-next-round"
        elif case == "branch": url = f"{server.base_url}/admin/runs/source/branches/missing/simulate-next-round"
        elif case == "legacy":
            with repo._session_factory.begin() as session: session.get(RunBranchModel, branch_id).legacy_simulation_run_id = "missing"
        else:
            payload = {**payload, "expected_head_checkpoint_id": "missing"}
            with repo._session_factory.begin() as session:
                session.get(RunBranchModel, branch_id).head_checkpoint_id = "missing"
                session.get(BranchStateModel, branch_id).head_checkpoint_id = "missing"
        assert _request("POST", url, payload)[0] == 404


@pytest.mark.parametrize("case", ["run-inactive", "run-read-only", "run-built-in", "branch-inactive", "branch-read-only", "binding", "wrong-run", "head-mismatch", "stale", "checkpoint-owner"])
def test_admin_branch_next_round_conflict_cases(tmp_path, case):
    database_url = f"sqlite:///{tmp_path / f'409-{case}.db'}"
    with ApiServer(database_url=database_url) as server:
        branch_id, head, url, payload = _setup(server); repo = _repo(database_url)
        if case == "wrong-run":
            assert _request("POST", f"{server.base_url}/runs", {"run_id": "other", "seed": 47, "season": 2027})[0] == 201
        with repo._session_factory.begin() as session:
            container = session.get(RunContainerModel, "source"); branch = session.get(RunBranchModel, branch_id)
            if case == "run-inactive": container.status = "inactive"
            elif case == "run-read-only": container.read_only = 1
            elif case == "run-built-in": container.storage_kind = "built_in"
            elif case == "branch-inactive": branch.status = "inactive"
            elif case == "branch-read-only": branch.read_only = 1
            elif case == "binding": branch.legacy_simulation_run_id = None
            elif case == "wrong-run":
                url = f"{server.base_url}/admin/runs/other/branches/{branch_id}/simulate-next-round"
            elif case == "head-mismatch": session.get(BranchStateModel, branch_id).head_checkpoint_id = "other"
            elif case == "stale": payload = {**payload, "expected_head_checkpoint_id": "stale"}
            else: session.get(BranchCheckpointModel, head).branch_id = "other"
        assert _request("POST", url, payload)[0] == 409


def test_admin_branch_next_round_validation_and_no_executable_round(tmp_path):
    database_url = f"sqlite:///{tmp_path / '400.db'}"
    with ApiServer(database_url=database_url) as server:
        branch_id, head, url, payload = _setup(server)
        assert _request("POST", url, {**payload, "explicit_confirmation": False})[0] == 400
        assert _request("POST", url, {**payload, "command_id": "blank", "audit_reason": "   "})[0] == 400
        repo = _repo(database_url)
        with repo._session_factory.begin() as session:
            state = session.get(SeasonStateModel, "source")
            state.ordered_events_json = "[]"; state.next_event_index = 0; state.active_tournament_json = None
            checkpoint = session.get(BranchCheckpointModel, head)
            body = json.loads(checkpoint.payload_json); body["season_state"] = repo._season_state_payload_in_session(session=session, model=state)
            checkpoint.payload_json = repo.canonical_json(body)
            checkpoint.content_hash = repo.checkpoint_envelope_content_hash(repo._to_branch_checkpoint(checkpoint))
        assert _request("POST", url, {**payload, "command_id": "no-round"})[0] == 400


def test_admin_branch_next_round_internal_failure_rolls_back(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'rollback.db'}"
    with ApiServer(database_url=database_url) as server:
        _, _, url, payload = _setup(server)
        repository = server.server.config.app.state.runtime.repository
        before = _snapshot(repository)
        def fail(**kwargs): raise RuntimeError("injected persistence failure")
        monkeypatch.setattr(repository, "_persist_branch_simulation_step_in_session", fail)
        req = request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={"content-type": "application/json"})
        try:
            request.urlopen(req)
        except error.HTTPError as exc:
            assert exc.code == 500
            exc.read()
            exc.close()
        else:
            pytest.fail("injected persistence failure unexpectedly succeeded")
        assert _snapshot(repository) == before
