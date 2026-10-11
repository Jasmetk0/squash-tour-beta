"""Real HTTP/SQLite acceptance for selection-bound World Package staging."""

from urllib.parse import quote
import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _request
from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID
from tests.support.world_packages import copy_builtin_world_packages


@pytest.mark.pr_critical
def test_selected_world_items_exact_diff_no_implicit_changes_and_saved_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'selective-world.db'}"
    server = ApiServer(database_url=url)
    server.app.state.world_packages_root = copy_builtin_world_packages(tmp_path / "worlds")
    with server:
        status, run = _request("POST", f"{server.base_url}/run-containers", {"display_name": "Selective World"})
        assert status == 201, run
        run_id, branch_id = run["run_id"], run["viewer_branch_id"]
        base = (
            f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        source = base + f"/source-world/{OFFICIAL_FAX_WORLD_ID}"
        status, options = _request("POST", source + "/selection-preview", {"selected_entities": []})
        assert status == 200, options
        assert options["selected_entities"] == []
        assert options["can_confirm"] is False
        assert _request("GET", base)[1]["state"] is None
        country_labels = [o["label"] for o in options["available"] if o["scope"] == "countries"]
        assert len(country_labels) > 2
        metadata_labels = [o["label"] for o in options["available"] if o["scope"] == "world_metadata"]
        assert len(metadata_labels) == 1
        chosen = sorted([metadata_labels[0], country_labels[0]])
        status, preview = _request("POST", source + "/selection-preview", {"selected_entities": chosen})
        assert status == 200, preview
        assert preview["can_confirm"] is True
        assert {row["label"] for row in preview["changes"]} == set(chosen)
        assert all(row["status"] == "add" and row["before"] is None and row["fields"] for row in preview["changes"])
        assert country_labels[1] in preview["excluded_entities"]
        confirm = {
            "command_id": "selective-first",
            "selected_entities": chosen,
            "conflict_resolutions": {},
            "expected_head_revision_id": preview["saved_head_revision_id"],
            "expected_draft_version": preview["draft_version"],
            "expected_state_fingerprint": preview["current_state_fingerprint"],
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "expected_selection_fingerprint": preview["selection_fingerprint"],
        }
        bad = {**confirm, "selected_entities": [country_labels[1]]}
        assert _request("POST", source + "/selection-confirm", bad)[0] == 409
        assert _request("GET", base)[1]["state"] is None
        status, applied = _request("POST", source + "/selection-confirm", confirm)
        assert status == 200, applied
        assert applied["draft_version"] == 1
        assert {e["source_package_id"] + "/" + e["source_entity_id"] for e in applied["state"]["entities"]} == set(chosen)
        assert _request("POST", source + "/selection-confirm", {
            **confirm, "command_id": "stale-first",
        })[0] == 409
        assert _request("POST", base + "/source-world/" + OFFICIAL_FAX_WORLD_ID + "/selection-preview", {
            "selected_entities": [country_labels[1]],
        })[1]["can_confirm"] is True

        status, second_preview = _request("POST", source + "/selection-preview", {"selected_entities": [country_labels[1]]})
        assert status == 200, second_preview
        assert second_preview["changes"][0]["before"] is None
        second_confirm = {
            **confirm,
            "command_id": "selective-second",
            "selected_entities": [country_labels[1]],
            "expected_draft_version": second_preview["draft_version"],
            "expected_state_fingerprint": second_preview["current_state_fingerprint"],
            "expected_preview_fingerprint": second_preview["preview_fingerprint"],
            "expected_selection_fingerprint": second_preview["selection_fingerprint"],
        }
        status, second = _request("POST", source + "/selection-confirm", second_confirm)
        assert status == 200, second
        ids = {e["source_package_id"] + "/" + e["source_entity_id"] for e in second["state"]["entities"]}
        assert ids == set(chosen) | {country_labels[1]}
        assert second["draft_version"] == 2
        save_url = (
            f"{server.base_url}/run-containers/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/working-draft/save"
        )
        assert _request("POST", save_url, {"expected_draft_version": 2})[0] == 201
        committed_fingerprint = second["state_fingerprint"]

    reopened = ApiServer(database_url=url)
    reopened.app.state.world_packages_root = server.app.state.world_packages_root
    with reopened:
        read = f"{reopened.base_url}/admin/runs/{quote(run_id, safe='')}/branches/{quote(branch_id, safe='')}/packages"
        status, saved = _request("GET", read)
        assert status == 200
        assert saved["fingerprint"] == committed_fingerprint
        assert len(saved["state"]["entities"]) == 3


@pytest.mark.pr_critical
def test_selection_preview_rejects_unknown_labels_and_unreviewed_conflict_resolutions(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'invalid-selection.db'}")
    server.app.state.world_packages_root = copy_builtin_world_packages(tmp_path / "worlds")
    with server:
        status, run = _request("POST", f"{server.base_url}/run-containers", {"display_name": "Invalid selection"})
        assert status == 201
        base = (f"{server.base_url}/admin/runs/{quote(run['run_id'],safe='')}"
                f"/branches/{quote(run['viewer_branch_id'],safe='')}/packages")
        source = base + f"/source-world/{OFFICIAL_FAX_WORLD_ID}/selection-preview"
        assert _request("POST", source, {"selected_entities": ["fake/country"]})[0] == 409
        assert _request("POST", source, {"selected_entities": ["x", "x"]})[0] == 409
        assert _request("POST", source, {
            "selected_entities": [],
            "conflict_resolutions": {"other/identity": "use_source"},
        })[0] == 409
        assert _request("GET", base)[1]["state"] is None
