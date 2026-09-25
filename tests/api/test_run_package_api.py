from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)


def _repo(url):
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    return SimulationPersistenceRepository(
        engine=engine, session_factory=create_session_factory(engine)
    )


@pytest.mark.pr_critical
def test_run_package_http_preview_confirm_conflict_save_and_reopen(tmp_path):
    url = f"sqlite:///{tmp_path / 'package-api.db'}"
    document = {
        "schema_version": 1,
        "package_type": "World",
        "package_id": "world",
        "source_version": 1,
        "provenance": {"source": "fixture"},
        "explicit_scope": ["world"],
        "entities": [
            {
                "source_entity_id": "country",
                "entity_kind": "country",
                "entity_schema_version": 1,
                "scope": "world",
                "payload": {"name": "A"},
                "references": [],
                "valid": True,
            }
        ],
        "children": [],
        "parent_source_fingerprint": None,
    }
    with ApiServer(database_url=url) as server:
        _, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "HTTP Packages"},
        )
        run_id, branch_id = run["run_id"], run["viewer_branch_id"]
        base = f"{server.base_url}/admin/runs/{quote(run_id, safe='')}/branches/{quote(branch_id, safe='')}/packages"
        status, preview = _request("POST", base + "/preview", {"document": document})
        assert status == 200 and preview["additions"] == ["world/country"]
        assert _request("GET", base)[1]["state"] is None
        confirm = {
            "document": document,
            "command_id": "apply",
            "expected_head_revision_id": preview["saved_head_revision_id"],
            "expected_draft_version": 0,
            "expected_state_fingerprint": None,
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "conflict_resolutions": {},
        }
        status, applied = _request("POST", base + "/confirm", confirm)
        assert status == 200 and applied["draft_version"] == 1
        assert (
            _request(
                "POST",
                base + "/confirm",
                {**confirm, "document": {**document, "package_id": "other"}},
            )[0]
            == 409
        )
        assert _request("GET", base)[1]["fingerprint"] == applied["state_fingerprint"]
        save_url = f"{server.base_url}/run-containers/{quote(run_id, safe='')}/branches/{quote(branch_id, safe='')}/working-draft/save"
        assert _request("POST", save_url, {"expected_draft_version": 1})[0] == 201
    with ApiServer(database_url=url) as reopened:
        base = f"{reopened.base_url}/admin/runs/{quote(run_id, safe='')}/branches/{quote(branch_id, safe='')}/packages"
        assert _request("GET", base)[1]["fingerprint"] == applied["state_fingerprint"]
        revision = _repo(url).get_run_branch(branch_id=branch_id).saved_head_revision_id
        assert (
            _repo(url)
            .get_branch_saved_revision(revision_id=revision)
            .payload["content"]["run_package_state"]["fingerprint"]
            == applied["state_fingerprint"]
        )
