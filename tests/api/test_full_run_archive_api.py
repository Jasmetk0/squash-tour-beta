"""Whole-Run export through HTTP and independent SQLite cold restore."""

import json
import sqlite3
from contextlib import closing
from urllib.request import Request, urlopen

import pytest

from beta_engine.domain.run_branch_archive import (
    FULL_RUN_FORMAT, FULL_RUN_SCOPE, decode, encode,
)
from beta_engine.infrastructure.db import run_branch_archive
from beta_engine.infrastructure.db.saved_v2_hooks import ENVIRONMENT_VARIABLE
from beta_engine.infrastructure.db.saved_v2_store import ENVELOPE_PREFIX
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_run_branch_archive_api import (
    archive_root, confirm, export, manual_match, raw_request, upload_preview,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.run_branch_archive_http import ColdApiServer

pytestmark = pytest.mark.pr_critical


def create_branch(server, rid, branch, revision):
    status, result = _request(
        "POST",
        server.base_url + f"/run-containers/{rid}/branches",
        {"source_branch_id": branch, "source_saved_revision_id": revision},
    )
    assert status == 201, result
    return result["branch_id"]


def full_preview(server, rid, branch):
    selection = {"run_id": rid, "branch_id": branch, "mode": "full_run"}
    status, preview = _request("POST", archive_root(server) + "/export/preview", selection)
    assert status == 200, preview
    return preview, {
        **selection,
        "expected_head_revision_id": preview["selected_head_revision_id"],
        "expected_archive_digest": preview["archive_digest"],
    }


def stage_viewer(server, rid, owner, viewer):
    draft_url = server.base_url + f"/run-containers/{rid}/branches/{owner}/working-draft"
    status, result = _request(
        "PUT", draft_url + "/viewer-branch",
        {"viewer_branch_id": viewer, "expected_draft_version": 0},
    )
    assert status == 200, result
    return draft_url, result["draft_version"]


def test_full_archive_cold_roundtrip_saved_v2_includes_every_branch(tmp_path, monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, "saved_v2")
    source, target = tmp_path / "source.db", tmp_path / "target.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, branch, played, _ = manual_match(server)
        _, selected = export(server, rid, branch)
        initial = selected["history"][0]["revision_id"]
        fork = create_branch(server, rid, branch, initial)
        other = create_branch(server, rid, branch, initial)
        _, branch_preview = export(server, rid, branch)
        assert set(branch_preview["omitted_branch_ids"]) == {fork, other}
        draft, version = stage_viewer(server, rid, fork, fork)
        status, fork_saved = _request(
            "POST", draft + "/save", {"expected_draft_version": version}
        )
        assert status == 201, fork_saved
        before = _dump(source)

        preview, command = full_preview(server, rid, branch)
        assert (preview["format"], preview["scope"]) == (FULL_RUN_FORMAT, FULL_RUN_SCOPE)
        assert preview["omitted_branch_ids"] == []
        assert {b["branch_id"] for b in preview["branches"]} == {branch, fork, other}
        assert preview["viewer_branch_id"] == fork
        assert len(preview["history"]) == 3
        req = Request(
            archive_root(server) + "/export",
            headers={"Content-Type": "application/json"},
            data=encode(command),
        )
        with urlopen(req, timeout=120) as response:
            assert response.headers["Content-Disposition"] == 'attachment; filename="full-run-v1.sqbranch"'
            raw = response.read()
        assert decode(raw)["branch_ids"] == sorted([branch, fork, other])
        history = {
            bid: _request("GET", server.base_url + f"/run-containers/{rid}/branches/{bid}/saved-revisions")
            for bid in (branch, fork, other)
        }
        assert all(status == 200 for status, _ in history.values())
        assert _dump(source) == before
        with closing(sqlite3.connect(source)) as connection:
            (stored,) = connection.execute(
                "SELECT payload_json FROM branch_saved_revisions WHERE revision_id = ?",
                (preview["selected_head_revision_id"],),
            ).fetchone()
        assert stored.startswith(ENVELOPE_PREFIX)
        with monkeypatch.context() as limited:
            limited.setattr(run_branch_archive, "MAX_ARCHIVE_BYTES", len(stored))
            status, result = _request(
                "POST", archive_root(server) + "/export/preview",
                {"run_id": rid, "branch_id": branch, "mode": "full_run"},
            )
            assert status == 409 and result["detail"]["code"] == "archive_request_too_large"
        assert _dump(source) == before
    server.app.state.runtime.repository._engine.dispose()
    source.unlink()
    installation = tmp_path / "independent-installation"
    installation.mkdir()

    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        envelope = decode(raw)
        envelope["branch_ids"].remove(other)
        status, body = raw_request(archive_root(server) + "/import/preview", encode(envelope))
        assert status == 409 and json.loads(body)["detail"]["code"] == "invalid_manifest"
        review = upload_preview(server, raw)
        assert review["can_restore"]
        status, receipt = confirm(server, raw, review)
        assert status == 201, receipt
        assert set(receipt["restored_branch_ids"]) == {branch, fork, other}
    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        assert confirm(server, raw, review) == (201, receipt)
        for bid, expected in history.items():
            assert _request(
                "GET", server.base_url + f"/run-containers/{rid}/branches/{bid}/saved-revisions"
            ) == expected
        root = server.base_url + f"/admin/runs/{rid}/branches/{branch}/authoritative-simulation"
        assert _request("GET", root + "/match-replay?group_id=standalone-match-group-1") == (
            200, played["stored_replay"]
        )


def test_full_export_rejects_new_branch_or_dirty_branch_without_affecting_branch_mode(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'stale.db'}") as server:
        status, run = _request(
            "POST", server.base_url + "/run-containers", {"display_name": "Full archive review"}
        )
        assert status == 201, run
        rid, branch = run["run_id"], run["viewer_branch_id"]
        first, command = full_preview(server, rid, branch)
        fork = create_branch(server, rid, branch, first["selected_head_revision_id"])
        status, body = raw_request(archive_root(server) + "/export", encode(command))
        assert status == 409 and json.loads(body)["detail"]["code"] == "stale_export_preview"

        _, command = full_preview(server, rid, branch)
        draft, version = stage_viewer(server, rid, fork, fork)
        for endpoint, payload in (
            ("/export/preview", {"run_id": rid, "branch_id": branch, "mode": "full_run"}),
            ("/export", command),
        ):
            status, result = _request("POST", archive_root(server) + endpoint, payload)
            assert status == 409 and result["detail"]["code"] == "unsaved_changes", result
        _, branch_preview = export(server, rid, branch)
        assert branch_preview["omitted_branch_ids"] == [fork]
        status, saved = _request("POST", draft + "/save", {"expected_draft_version": version})
        assert status == 201, saved
        status, body = raw_request(archive_root(server) + "/export", encode(command))
        assert status == 409 and json.loads(body)["detail"]["code"] == "stale_export_preview"
