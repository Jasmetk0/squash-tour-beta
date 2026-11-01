"""ASGI/SQLite integration through the actual app and public Run/Saved boundaries."""
import pytest
from fastapi.testclient import TestClient

from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.main import create_app
from tests.support.cross_run_compare import create, params, snapshot

pytestmark = pytest.mark.pr_critical


@pytest.fixture
def cross_client(tmp_path):
    database = tmp_path / "cross-saved.db"
    app = create_app(database_url=f"sqlite:///{database}")
    with TestClient(app) as client:
        yield client, app, database


def test_cross_sources_same_source_swap_and_read_only(cross_client):
    client, _app, path = cross_client
    a, b = create(client, "Source A"), create(client, "Source B")
    before = snapshot(path)
    result = client.get("/admin/cross-run-compare", params=params(a, b))
    assert result.status_code == 200, result.text
    value = result.json()
    assert value["from_source"]["run_id"] == a[0]
    assert value["to_source"]["run_id"] == b[0]
    assert value["from_source"]["revision"]["revision_id"] == a[2]
    assert value["from_source"]["revision"]["is_shared_revision"] is False
    reverse = client.get("/admin/cross-run-compare", params=params(b, a)).json()
    assert reverse["from_source"] == value["to_source"]
    for key, change in value["run_changes"].items():
        assert reverse["run_changes"][key]["before"] == change["after"]
        assert reverse["run_changes"][key]["after"] == change["before"]
    same = client.get("/admin/cross-run-compare", params=params(a, a)).json()
    assert same["run_changes"] == same["branch_changes"] == {}
    assert all(c["status"] == "unchanged" for c in same["components"])
    assert snapshot(path) == before


@pytest.mark.parametrize("side", ["a", "b"])
def test_foreign_revision_and_wrong_branch_are_404_without_mutation(cross_client, side):
    client, _app, path = cross_client
    a, b = create(client, "A"), create(client, "B")
    query = params(a, b)
    before = snapshot(path)
    query[f"revision_{side}_id"] = b[2] if side == "a" else a[2]
    assert client.get("/admin/cross-run-compare", params=query).status_code == 404
    query = params(a, b)
    query[f"branch_{side}_id"] = b[1] if side == "a" else a[1]
    assert client.get("/admin/cross-run-compare", params=query).status_code == 404
    assert snapshot(path) == before


@pytest.mark.parametrize("side", ["a", "b"])
def test_corruption_rejected_after_warming_real_validation(cross_client, side):
    client, app, path = cross_client
    a, b = create(client, "A"), create(client, "B")
    assert client.get("/admin/cross-run-compare", params=params(a, b)).status_code == 200
    with app.state.runtime.repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, a[2] if side == "a" else b[2])
        row.change_summary_json = '{"tampered":true}'
    damaged = snapshot(path)
    response = client.get("/admin/cross-run-compare", params=params(a, b))
    assert response.status_code == 409, response.text
    assert snapshot(path) == damaged


def test_shared_ancestor_requires_reachable_selected_branch(cross_client):
    client, _app, path = cross_client
    a, b = create(client, "A"), create(client, "B")
    response = client.post(f"/run-containers/{a[0]}/branches", json={
        "source_branch_id": a[1], "source_saved_revision_id": a[2]})
    assert response.status_code == 201, response.text
    fork = response.json()
    shared = (a[0], fork["branch_id"], a[2])
    before = snapshot(path)
    value = client.get("/admin/cross-run-compare", params=params(shared, b)).json()
    assert value["from_source"]["branch_id"] == fork["branch_id"]
    assert value["from_source"]["revision"]["revision_branch_id"] == a[1]
    assert value["from_source"]["revision"]["is_shared_revision"] is True
    assert snapshot(path) == before


def test_query_validation_and_missing_scope(cross_client):
    client, _app, _path = cross_client
    a, b = create(client, "A"), create(client, "B")
    query = params(a, b)
    for field in query:
        assert client.get("/admin/cross-run-compare", params={**query, field: ""}).status_code == 422
    assert client.get("/admin/cross-run-compare", params={**query, "run_a_id": "not-found"}).status_code == 404
