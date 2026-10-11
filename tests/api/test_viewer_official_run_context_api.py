from __future__ import annotations

from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request
from tests.api.viewer_saved_revision_helpers import canonical_product_run
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    BranchStateModel,
    RunBranchModel,
    RunContainerModel,
)


def _repository(url: str):
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    return SimulationPersistenceRepository(
        engine=engine, session_factory=create_session_factory(engine)
    )


def _url(server, run_id):
    return f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/official-context"


def _snapshot(repository):
    with repository._session_factory() as session:
        return {
            model.__tablename__: [
                tuple(getattr(row, c.name) for c in model.__table__.columns)
                for row in session.query(model).order_by(
                    *model.__table__.primary_key.columns
                )
            ]
            for model in (
                RunContainerModel,
                RunBranchModel,
                BranchSavedRevisionModel,
                BranchStateModel,
            )
        }


@pytest.mark.pr_critical
def test_viewer_context_resolves_canonical_saved_head_without_legacy_and_is_pure(
    tmp_path,
):
    url = f"sqlite:///{tmp_path / 'context.db'}"
    with ApiServer(database_url=url) as server:
        branch_id, run_id = canonical_product_run(server)
        repository = _repository(url)
        before = _snapshot(repository)
        status, context = _request("GET", _url(server, run_id))
        assert status == 200
        assert context["official_branch_id"] == branch_id
        assert context["saved_head_revision_id"]
        assert context["legacy_simulation_run_id"] is None
        assert context["head_checkpoint_id"] is None
        assert context["current_season"] is None
        assert context["current_week"] is None
        assert context["current_event_id"] is None
        assert context["resolution_version"] == "viewer_saved_revision_v2"
        assert _snapshot(repository) == before
        assert _request("GET", _url(server, "missing"))[0] == 404


@pytest.mark.pr_critical
def test_viewer_context_ignores_live_branch_position(tmp_path):
    url = f"sqlite:///{tmp_path / 'position.db'}"
    with ApiServer(database_url=url) as server:
        branch_id, run_id = canonical_product_run(server)
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            state = session.get(BranchStateModel, branch_id)
            state.current_season = 2049
            state.current_week = 61
            state.current_event_id = "future"
            state.current_event_sequence = 99
        status, context = _request("GET", _url(server, run_id))
        assert status == 200
        assert (
            context["current_season"],
            context["current_week"],
            context["current_event_id"],
        ) == (None, None, None)


@pytest.mark.pr_critical
@pytest.mark.parametrize(
    "mutation", ["wrong_branch", "missing_head", "wrong_revision_scope", "bad_hash"]
)
def test_viewer_context_fails_closed_for_saved_boundary_corruption(tmp_path, mutation):
    url = f"sqlite:///{tmp_path / (mutation + '.db')}"
    with ApiServer(database_url=url) as server:
        branch_id, run_id = canonical_product_run(server)
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            run = session.get(RunContainerModel, run_id)
            branch = session.get(RunBranchModel, branch_id)
            revision = session.get(
                BranchSavedRevisionModel, branch.saved_head_revision_id
            )
            if mutation == "wrong_branch":
                run.official_branch_id = "branch-from-another-run"
            elif mutation == "missing_head":
                branch.saved_head_revision_id = None
            elif mutation == "wrong_revision_scope":
                revision.run_id = "other-run"
            else:
                revision.content_hash = "0" * 64
        before = _snapshot(repository)
        assert _request("GET", _url(server, run_id))[0] == 409
        assert _snapshot(repository) == before
