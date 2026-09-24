from __future__ import annotations

from urllib.parse import quote

from test_simulation_api import ApiServer, _request
from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel


def _repo(url: str):
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def test_canonical_viewer_context_uses_verified_saved_revision_without_legacy_binding(tmp_path):
    url = f"sqlite:///{tmp_path / 'viewer-saved-boundary.db'}"
    with ApiServer(database_url=url) as server:
        status, run = _request("POST", f"{server.base_url}/run-containers", {"display_name": "Saved Viewer"})
        assert status == 201
        run_id = run["run_id"]
        branch_id = run["viewer_branch_id"]
        repository = _repo(url)
        with repository._session_factory() as session:
            branch = session.get(RunBranchModel, branch_id)
            assert branch.legacy_simulation_run_id is None
            revision_id = branch.saved_head_revision_id
        status, context = _request("GET", f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/official-context")
        assert status == 200
        assert context["official_branch_id"] == branch_id
        assert context["saved_head_revision_id"] == revision_id
        assert context["legacy_simulation_run_id"] is None
        assert context["head_checkpoint_id"] is None
        assert context["resolution_version"] == "viewer_saved_revision_v2"

        # Empty saved content is unavailable even if future live tables gain data.
        assert _request("GET", f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/rankings/current")[0] == 409
        assert _request("GET", f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/event/draw")[0] == 404

    # Reopen proves the boundary is file-backed rather than process-local.
    with ApiServer(database_url=url) as reopened:
        assert _request("GET", f"{reopened.base_url}/viewer/runs/{quote(run_id, safe='')}/official-context")[1] == context


def test_viewer_saved_revision_integrity_fails_closed(tmp_path):
    url = f"sqlite:///{tmp_path / 'viewer-corrupt.db'}"
    with ApiServer(database_url=url) as server:
        _, run = _request("POST", f"{server.base_url}/run-containers", {"display_name": "Corrupt Viewer"})
        repository = _repo(url)
        with repository._session_factory.begin() as session:
            branch = session.get(RunBranchModel, run["viewer_branch_id"])
            session.get(BranchSavedRevisionModel, branch.saved_head_revision_id).content_hash = "0" * 64
        status, _ = _request("GET", f"{server.base_url}/viewer/runs/{quote(run['run_id'], safe='')}/official-context")
        assert status == 409
