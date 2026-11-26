"""The real archive API round-trips a selected graph on independent SQLite."""

import json
from pathlib import Path

import pytest

from beta_engine.domain.run_branch_archive import Archive, CUSTOM_FORMAT, decode, encode
from beta_engine.infrastructure.db.saved_v2_hooks import ENVIRONMENT_VARIABLE
from tests.api.test_full_run_archive_api import create_branch, stage_viewer
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_run_branch_archive_api import (
    archive_root, confirm, export, manual_match, raw_request, upload_preview,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.run_branch_archive_http import ColdApiServer

pytestmark = pytest.mark.pr_critical


def selection(run_id, primary, additional):
    return {
        "run_id": run_id, "branch_id": primary, "mode": "custom",
        "selected_branch_ids": [primary, *additional],
    }


def preview_command(server, scope):
    status, preview = _request("POST", archive_root(server) + "/export/preview", scope)
    assert status == 200, preview
    return preview, {
        **scope,
        "expected_head_revision_id": preview["selected_head_revision_id"],
        "expected_archive_digest": preview["archive_digest"],
    }


def test_custom_archive_deduplicates_shared_history_and_cold_restores(tmp_path, monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, "saved_v2")
    source, target = tmp_path / "custom-source.db", tmp_path / "custom-target.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, owner, played, _ = manual_match(server)
        _, original = export(server, rid, owner)
        initial = original["history"][0]["revision_id"]
        primary, second, omitted = [create_branch(server, rid, owner, initial) for _ in range(3)]
        before = _dump(source)
        scope = selection(rid, primary, [second])
        preview, command = preview_command(server, scope)
        assert preview["format"] == CUSTOM_FORMAT
        assert preview["selected_branch_ids"] == sorted([primary, second])
        assert preview["omitted_branch_ids"] == [omitted]
        assert {b["branch_id"]: b["role"] for b in preview["branches"]} == {
            primary: "selected", second: "selected", owner: "dependency",
        }
        assert preview["history"] == original["history"]
        scope["selected_branch_ids"].reverse()
        assert preview_command(server, scope)[0] == preview
        status, raw = raw_request(archive_root(server) + "/export", encode(command))
        assert status == 200, raw[:2000]
        assert len(raw) == preview["archive_size_bytes"]
        assert Archive(raw).raw_digest == preview["archive_digest"]
        assert _dump(source) == before
        paths = [
            f"/run-containers/{rid}/branches/{bid}/saved-revisions"
            for bid in (owner, primary, second)
        ]
        histories = [_request("GET", server.base_url + path) for path in paths]
        assert all(status == 200 for status, _ in histories)
        replay = (
            f"/admin/runs/{rid}/branches/{owner}/authoritative-simulation"
            "/match-replay?group_id=standalone-match-group-1"
        )
    server.app.state.runtime.repository._engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(str(source) + suffix).unlink(missing_ok=True)

    installation = tmp_path / "custom-installation"
    installation.mkdir()
    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        broken = decode(raw)
        broken["selected_branch_ids"] = [primary, omitted]
        status, error = raw_request(archive_root(server) + "/import/preview", encode(broken))
        assert status == 409, error
        reviewed = upload_preview(server, raw)
        assert reviewed["can_restore"]
        status, receipt = confirm(server, raw, reviewed)
        assert status == 201, receipt
        assert set(receipt["restored_branch_ids"]) == {owner, primary, second}
    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        assert confirm(server, raw, reviewed) == (201, receipt)
        assert [_request("GET", server.base_url + path) for path in paths] == histories
        assert _request("GET", server.base_url + replay) == (200, played["stored_replay"])
        assert _request("GET", server.base_url + f"/run-containers/{rid}/branches/{omitted}")[0] == 404


def test_custom_export_binds_other_selected_head_and_rejects_foreign_ids(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'custom-scope.db'}") as server:
        status, run = _request("POST", server.base_url + "/run-containers", {"display_name": "Custom export"})
        assert status == 201, run
        rid, primary = run["run_id"], run["viewer_branch_id"]
        _, branch = export(server, rid, primary)
        extra = create_branch(server, rid, primary, branch["selected_head_revision_id"])
        status, foreign = _request("POST", server.base_url + "/run-containers", {"display_name": "Unrelated Run"})
        assert status == 201, foreign
        for invalid, expected in (([primary], 422), ([foreign["viewer_branch_id"]], 409)):
            status, _ = _request(
                "POST", archive_root(server) + "/export/preview", selection(rid, primary, invalid)
            )
            assert status == expected
        scope = selection(rid, primary, [extra])
        _, command = preview_command(server, scope)
        draft, version = stage_viewer(server, rid, extra, extra)
        status, error = _request("POST", archive_root(server) + "/export/preview", scope)
        assert status == 409 and error["detail"]["code"] == "unsaved_changes"
        status, saved = _request("POST", draft + "/save", {"expected_draft_version": version})
        assert status == 201, saved
        status, body = raw_request(archive_root(server) + "/export", encode(command))
        assert status == 409 and json.loads(body)["detail"]["code"] == "stale_export_preview"
        refreshed, _ = preview_command(server, scope)
        assert refreshed["selected_head_revision_id"] == command["expected_head_revision_id"]
        assert refreshed["archive_digest"] != command["expected_archive_digest"]
