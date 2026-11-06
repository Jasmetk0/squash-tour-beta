"""HTTP/SQLite integration through the actual app and public Run/Saved boundaries."""
from urllib.parse import urlencode

import pytest

from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.support.cross_run_compare import params, snapshot

pytestmark = pytest.mark.pr_critical


@pytest.fixture
def cross_client(tmp_path):
    database = tmp_path / "cross-saved.db"
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        yield server, server.app, database


def create(server, name):
    return _create_run(server, display_name=name)


def compare(server, query):
    return _request("GET", server.base_url + "/admin/cross-run-compare?" + urlencode(query))


def test_cross_sources_same_source_swap_and_read_only(cross_client):
    client, _app, path = cross_client
    a, b = create(client, "Source A"), create(client, "Source B")
    before = snapshot(path)
    code, value = compare(client, params(a, b))
    assert code == 200, value
    assert value["from_source"]["run_id"] == a[0]
    assert value["to_source"]["run_id"] == b[0]
    assert value["from_source"]["revision"]["revision_id"] == a[2]
    assert value["from_source"]["revision"]["is_shared_revision"] is False
    code, reverse = compare(client, params(b, a))
    assert code == 200, reverse
    assert reverse["from_source"] == value["to_source"]
    for key, change in value["run_changes"].items():
        assert reverse["run_changes"][key]["before"] == change["after"]
        assert reverse["run_changes"][key]["after"] == change["before"]
    code, same = compare(client, params(a, a))
    assert code == 200, same
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
    assert compare(client, query)[0] == 404
    query = params(a, b)
    query[f"branch_{side}_id"] = b[1] if side == "a" else a[1]
    assert compare(client, query)[0] == 404
    assert snapshot(path) == before


@pytest.mark.parametrize("side", ["a", "b"])
def test_corruption_rejected_after_warming_real_validation(cross_client, side):
    client, app, path = cross_client
    a, b = create(client, "A"), create(client, "B")
    assert compare(client, params(a, b))[0] == 200
    with app.state.runtime.repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, a[2] if side == "a" else b[2])
        row.change_summary_json = '{"tampered":true}'
    damaged = snapshot(path)
    code, response = compare(client, params(a, b))
    assert code == 409, response
    assert snapshot(path) == damaged


def test_shared_ancestor_requires_reachable_selected_branch(cross_client):
    client, _app, path = cross_client
    a, b = create(client, "A"), create(client, "B")
    code, fork = _request("POST", client.base_url + f"/run-containers/{a[0]}/branches", {
        "source_branch_id": a[1], "source_saved_revision_id": a[2]})
    assert code == 201, fork
    shared = (a[0], fork["branch_id"], a[2])
    before = snapshot(path)
    code, value = compare(client, params(shared, b))
    assert code == 200, value
    assert value["from_source"]["branch_id"] == fork["branch_id"]
    assert value["from_source"]["revision"]["revision_branch_id"] == a[1]
    assert value["from_source"]["revision"]["is_shared_revision"] is True
    assert snapshot(path) == before


def test_query_validation_and_missing_scope(cross_client):
    client, _app, _path = cross_client
    a, b = create(client, "A"), create(client, "B")
    query = params(a, b)
    for field in query:
        assert compare(client, {**query, field: ""})[0] == 422
    assert compare(client, {**query, "run_a_id": "not-found"})[0] == 404
