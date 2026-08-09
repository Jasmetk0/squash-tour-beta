from __future__ import annotations

import json
import pytest

from test_simulation_api import ApiServer, _request
from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import BranchCheckpointModel, RunBranchModel


def _repository(url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def test_historical_season_state_is_typed_read_only_and_identity_scoped(tmp_path):
    url = f"sqlite:///{tmp_path / 'history.db'}"
    with ApiServer(database_url=url) as server:
        assert _request("POST", f"{server.base_url}/runs", {"run_id": "run-a", "seed": 47, "season": 2005})[0] == 201
        branch = _request("GET", f"{server.base_url}/run-branches?run_id=run-a")[1]["run_branches"][0]
        checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "run-a"})[1]
        repository = _repository(url)
        before = (repository.get_run_branch(branch_id=branch["branch_id"]), repository.get_branch_state(branch_id=branch["branch_id"]), repository.get_branch_checkpoint(checkpoint_id=checkpoint["checkpoint_id"]), repository.get_run_container(run_id="run-a"))
        endpoint = f"{server.base_url}/admin/runs/run-a/branches/{branch['branch_id']}/checkpoints/{checkpoint['checkpoint_id']}/season-state"
        status, result = _request("GET", endpoint)
        assert status == 200
        assert set(result) == {"product_run_id", "branch_id", "checkpoint_id", "checkpoint_sequence", "checkpoint_kind", "checkpoint_content_hash", "payload_schema_version", "checkpoint_season", "checkpoint_week", "checkpoint_event_id", "checkpoint_event_sequence", "season_state"}
        assert result["product_run_id"] == "run-a" and result["branch_id"] == branch["branch_id"]
        assert result["season_state"]["season"] == 2005
        assert before == (repository.get_run_branch(branch_id=branch["branch_id"]), repository.get_branch_state(branch_id=branch["branch_id"]), repository.get_branch_checkpoint(checkpoint_id=checkpoint["checkpoint_id"]), repository.get_run_container(run_id="run-a"))
        assert _request("GET", endpoint.replace(f"branches/{branch['branch_id']}", "branches/wrong"))[0] == 404
        assert _request("GET", endpoint.replace("admin/runs/run-a", "admin/runs/wrong"))[0] == 404


def test_historical_season_state_fails_closed_without_canonical_state(tmp_path):
    url = f"sqlite:///{tmp_path / 'unsupported.db'}"
    with ApiServer(database_url=url) as server:
        _request("POST", f"{server.base_url}/runs", {"run_id": "run-a", "seed": 47, "season": 2005})
        branch = _request("GET", f"{server.base_url}/run-branches?run_id=run-a")[1]["run_branches"][0]
        checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "run-a"})[1]
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            model = session.get(BranchCheckpointModel, checkpoint["checkpoint_id"])
            payload = json.loads(model.payload_json); payload.pop("season_state")
            model.payload_json = repository.canonical_json(payload)
            model.content_hash = repository.checkpoint_envelope_content_hash(repository._to_branch_checkpoint(model))
            session.get(RunBranchModel, branch["branch_id"]).read_only = True
        endpoint = f"{server.base_url}/admin/runs/run-a/branches/{branch['branch_id']}/checkpoints/{checkpoint['checkpoint_id']}/season-state"
        status, result = _request("GET", endpoint)
        assert status == 409 and result["detail"]["code"] == "historical_season_state_unavailable"


@pytest.mark.parametrize("case", ["malformed-state", "hash-tamper", "run-identity", "branch-identity"])
def test_historical_season_state_fails_closed_for_invalid_checkpoint_content(tmp_path, case):
    url = f"sqlite:///{tmp_path / f'{case}.db'}"
    with ApiServer(database_url=url) as server:
        _request("POST", f"{server.base_url}/runs", {"run_id": "run-a", "seed": 47, "season": 2005})
        branch = _request("GET", f"{server.base_url}/run-branches?run_id=run-a")[1]["run_branches"][0]
        checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "run-a"})[1]
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            model = session.get(BranchCheckpointModel, checkpoint["checkpoint_id"])
            payload = json.loads(model.payload_json)
            if case == "malformed-state": payload["season_state"] = {"season": "not-a-season"}
            elif case == "run-identity": payload["run_id"] = "other-run"
            elif case == "branch-identity": payload["branch_id"] = "other-branch"
            else: payload["season_state"]["season"] = 2006
            model.payload_json = repository.canonical_json(payload)
            if case != "hash-tamper":
                model.content_hash = repository.checkpoint_envelope_content_hash(repository._to_branch_checkpoint(model))
        endpoint = f"{server.base_url}/admin/runs/run-a/branches/{branch['branch_id']}/checkpoints/{checkpoint['checkpoint_id']}/season-state"
        status, result = _request("GET", endpoint)
        assert status == 409 and result["detail"]["code"] == "historical_season_state_unavailable"
        if case == "hash-tamper": assert "integrity validation failed" in result["detail"]["message"]


def test_valid_historical_season_state_reads_on_read_only_branch_and_is_exactly_scoped(tmp_path):
    url = f"sqlite:///{tmp_path / 'readonly.db'}"
    with ApiServer(database_url=url) as server:
        for run_id in ("run-a", "run-b"):
            _request("POST", f"{server.base_url}/runs", {"run_id": run_id, "seed": 47, "season": 2005})
        branch_a = _request("GET", f"{server.base_url}/run-branches?run_id=run-a")[1]["run_branches"][0]
        branch_b = _request("GET", f"{server.base_url}/run-branches?run_id=run-b")[1]["run_branches"][0]
        checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "run-a"})[1]
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            session.get(RunBranchModel, branch_a["branch_id"]).read_only = True
        base = f"{server.base_url}/admin/runs/run-a/branches/{branch_a['branch_id']}/checkpoints/{checkpoint['checkpoint_id']}/season-state"
        assert _request("GET", base)[0] == 200
        assert _request("GET", base.replace(f"branches/{branch_a['branch_id']}", f"branches/{branch_b['branch_id']}"))[0] == 404
        assert _request("GET", base.replace("admin/runs/run-a", "admin/runs/run-b"))[0] == 404
