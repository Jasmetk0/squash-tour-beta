from __future__ import annotations

from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunBranchModel,
)


def _repo(url: str):
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    return SimulationPersistenceRepository(
        engine=engine, session_factory=create_session_factory(engine)
    )


@pytest.mark.pr_critical
def test_canonical_viewer_context_uses_verified_saved_revision_without_legacy_binding(
    tmp_path,
):
    url = f"sqlite:///{tmp_path / 'viewer-saved-boundary.db'}"
    with ApiServer(database_url=url) as server:
        status, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "Saved Viewer"},
        )
        assert status == 201
        run_id = run["run_id"]
        branch_id = run["viewer_branch_id"]
        repository = _repo(url)
        with repository._session_factory() as session:
            branch = session.get(RunBranchModel, branch_id)
            assert branch.legacy_simulation_run_id is None
            revision_id = branch.saved_head_revision_id
        status, context = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/official-context",
        )
        assert status == 200
        assert context["official_branch_id"] == branch_id
        assert context["saved_head_revision_id"] == revision_id
        assert context["legacy_simulation_run_id"] is None
        assert context["head_checkpoint_id"] is None
        assert context["resolution_version"] == "viewer_saved_revision_v2"

        # Empty saved content is unavailable even if future live tables gain data.
        assert (
            _request(
                "GET",
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/rankings/current",
            )[0]
            == 409
        )
        assert (
            _request(
                "GET",
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/event/draw",
            )[0]
            == 404
        )

    # Reopen proves the boundary is file-backed rather than process-local.
    with ApiServer(database_url=url) as reopened:
        assert (
            _request(
                "GET",
                f"{reopened.base_url}/viewer/runs/{quote(run_id, safe='')}/official-context",
            )[1]
            == context
        )


@pytest.mark.pr_critical
def test_viewer_saved_revision_integrity_fails_closed(tmp_path):
    url = f"sqlite:///{tmp_path / 'viewer-corrupt.db'}"
    with ApiServer(database_url=url) as server:
        _, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "Corrupt Viewer"},
        )
        repository = _repo(url)
        with repository._session_factory.begin() as session:
            branch = session.get(RunBranchModel, run["viewer_branch_id"])
            session.get(
                BranchSavedRevisionModel, branch.saved_head_revision_id
            ).content_hash = "0" * 64
        status, _ = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run['run_id'], safe='')}/official-context",
        )
        assert status == 409


@pytest.mark.pr_critical
def test_viewer_branch_switch_publishes_target_branch_saved_head_not_editor_revision(
    tmp_path,
):
    from tests.api.viewer_saved_revision_helpers import (
        canonical_product_run,
        save_simulation,
    )
    from tests.api.test_viewer_tournament_entry_field_api import (
        _install_viewer_entry_field,
    )

    url = f"sqlite:///{tmp_path / 'viewer-branch-switch.db'}"
    event_id = "switch-event"
    with ApiServer(database_url=url) as server:
        branch_a, run_id = canonical_product_run(server, "switch")
        repository = _repo(url)
        with repository._session_factory() as session:
            initial_a = session.get(RunBranchModel, branch_a).saved_head_revision_id
        status, branch_b_payload = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {"source_branch_id": branch_a, "source_saved_revision_id": initial_a},
        )
        assert status == 201, branch_b_payload
        branch_b = branch_b_payload["branch_id"]
        saved_b = branch_b_payload["saved_head_revision_id"]
        _install_viewer_entry_field(
            database_url=url, run_id=run_id, branch_id=branch_a, event_id=event_id
        )
        save_simulation(server, run_id, branch_a)
        field_url = f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/{event_id}/entry-field"
        assert _request("GET", field_url)[0] == 200

        draft_url = f"{server.base_url}/run-containers/{run_id}/branches/{branch_a}/working-draft"
        status, draft = _request("GET", draft_url)
        assert status == 200
        status, staged = _request(
            "PUT",
            draft_url + "/viewer-branch",
            {
                "viewer_branch_id": branch_b,
                "expected_draft_version": draft["draft_version"],
            },
        )
        assert status == 200
        assert _request("GET", field_url)[0] == 200
        status, selection = _request(
            "POST",
            draft_url + "/save",
            {
                "expected_draft_version": staged["draft_version"],
            },
        )
        assert status == 201
        assert selection["saved_revision"]["revision_id"] != saved_b
        assert _request("GET", field_url)[0] in (404, 409)
        status, context = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/official-context",
        )
        assert status == 200
        assert context["official_branch_id"] == branch_b
        assert context["saved_head_revision_id"] == saved_b
        assert (
            context["saved_head_revision_id"]
            != selection["saved_revision"]["revision_id"]
        )


@pytest.mark.pr_critical
@pytest.mark.parametrize("component", ["ranking", "simulation", "wild_cards"])
def test_viewer_component_corruption_fails_closed_without_live_fallback(
    tmp_path, component
):
    import json
    from beta_engine.domain.run_revisions import saved_revision_content_hash

    url = f"sqlite:///{tmp_path / (component + '-component.db')}"
    with ApiServer(database_url=url) as server:
        _, run = _request(
            "POST", f"{server.base_url}/run-containers", {"display_name": component}
        )
        repository = _repo(url)
        with repository._session_factory.begin() as session:
            branch = session.get(RunBranchModel, run["viewer_branch_id"])
            row = session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
            payload = json.loads(row.payload_json)
            if component == "ranking":
                payload["content"]["ranking_preparation"] = {
                    "fingerprint": "0" * 64,
                    "state": {},
                }
            elif component == "simulation":
                payload["content"]["simulation_slot_match_state"] = {
                    "fingerprint": "0" * 64,
                    "slots": [],
                    "groups": [],
                }
            else:
                payload["content"]["definitive_wild_card_assignments"] = {
                    "fingerprint": "0" * 64,
                    "assignments": [],
                }
            row.payload_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id,
                run_id=row.run_id,
                branch_id=row.branch_id,
                sequence=row.sequence,
                parent_revision_id=row.parent_revision_id,
                kind=row.kind,
                payload_schema_version=row.payload_schema_version,
                payload=payload,
                change_summary=json.loads(row.change_summary_json),
            )
        status, _ = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run['run_id'], safe='')}/official-context",
        )
        assert status == 409


@pytest.mark.pr_critical
def test_saved_sporting_projection_survives_api_process_reopen(tmp_path):
    from tests.api.viewer_saved_revision_helpers import (
        canonical_product_run,
        save_simulation,
    )
    from tests.api.test_viewer_tournament_entry_field_api import (
        _install_viewer_entry_field,
    )

    url = f"sqlite:///{tmp_path / 'viewer-sporting-reopen.db'}"
    with ApiServer(database_url=url) as server:
        branch_id, run_id = canonical_product_run(server, "reopen")
        _install_viewer_entry_field(
            database_url=url, run_id=run_id, branch_id=branch_id, event_id="event"
        )
        save_simulation(server, run_id, branch_id)
        endpoint = f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/event/entry-field"
        status, before = _request("GET", endpoint)
        assert status == 200
    with ApiServer(database_url=url) as reopened:
        status, after = _request(
            "GET",
            f"{reopened.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/event/entry-field",
        )
        assert status == 200
        assert after == before
