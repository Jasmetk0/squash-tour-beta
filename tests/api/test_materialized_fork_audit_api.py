"""#1939: a fork from a played Saved revision audits its own root atomically.

Real HTTP/SQLite: play a standalone match, Save explicitly, create a reviewed
materialized fork from that Saved revision, export it in every Saved scope and
cold-restore the complete archive into a fresh SQLite installation.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from beta_engine.domain.run_branch_archive import Archive, decode
from beta_engine.domain.run_revisions import (
    BRANCH_FORK_MATERIALIZED_AUDIT_EVENT_KIND,
    BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND,
    branch_fork_materialized_audit_event_id,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_run_branch_archive_api import (
    archive_root, confirm, manual_match, raw_request, upload_preview,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.run_branch_archive_http import ColdApiServer

pytestmark = pytest.mark.pr_critical

REPLAY = "/authoritative-simulation/match-replay?group_id=standalone-match-group-1"


def reviewed_fork(server, rid, owner, revision, command_id):
    request = {"source_branch_id": owner, "source_saved_revision_id": revision}
    status, preview = _request(
        "POST", server.base_url + f"/run-containers/{rid}/branches/preview", request
    )
    assert status == 200 and preview["can_create"], preview
    body = {
        **request,
        "review": {
            "command_id": command_id,
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "explicit_confirmation": True,
        },
    }
    return body, _request("POST", server.base_url + f"/run-containers/{rid}/branches", body)


def rows(path, sql, *args):
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(sql, args).fetchall()


def export_scope(server, selection):
    status, preview = _request("POST", archive_root(server) + "/export/preview", selection)
    assert status == 200, preview
    command = {
        **selection,
        "expected_head_revision_id": preview["selected_head_revision_id"],
        "expected_archive_digest": preview["archive_digest"],
    }
    status, raw = raw_request(archive_root(server) + "/export", json.dumps(command).encode())
    assert status == 200, raw[:2000]
    assert Archive(raw).raw_digest == preview["archive_digest"]
    return raw, preview


def scopes(rid, owner, fork):
    return {
        "branch": {"run_id": rid, "branch_id": fork},
        "custom": {
            "run_id": rid, "branch_id": owner, "mode": "custom",
            "selected_branch_ids": [owner, fork],
        },
        "full_run": {"run_id": rid, "branch_id": owner, "mode": "full_run"},
    }


def test_played_revision_fork_audits_root_exports_and_cold_restores(tmp_path):
    source, target = tmp_path / "fork-source.db", tmp_path / "fork-target.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, owner, played, saved = manual_match(server)
        played_revision = saved["saved_revision"]["revision_id"]
        request, (status, branch) = reviewed_fork(
            server, rid, owner, played_revision, "fork-played-1"
        )
        assert status == 201, branch
        fork, root = branch["branch_id"], branch["saved_head_revision_id"]
        ((kind, parent, owner_id, content_hash),) = rows(
            source,
            "SELECT kind, parent_revision_id, branch_id, content_hash "
            "FROM branch_saved_revisions WHERE revision_id = ?", root,
        )
        assert (kind, parent, owner_id) == (
            BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND, played_revision, fork,
        )
        audits = rows(
            source,
            "SELECT audit_event_id, run_id, branch_id, event_kind, payload_json "
            "FROM branch_revision_audit_events WHERE saved_revision_id = ?", root,
        )
        assert len(audits) == 1
        audit_id, audit_run, audit_branch, audit_kind, audit_payload = audits[0]
        assert (audit_id, audit_run, audit_branch, audit_kind) == (
            branch_fork_materialized_audit_event_id(root), rid, fork,
            BRANCH_FORK_MATERIALIZED_AUDIT_EVENT_KIND,
        )
        payload = json.loads(audit_payload)
        assert payload["source_branch_id"] == owner
        assert payload["source_saved_revision_id"] == played_revision
        assert payload["saved_revision_content_hash"] == content_hash
        assert payload["viewer_branch_id"] == owner
        assert payload["command_id"] == "fork-played-1"
        assert payload["working_draft_id"] == rows(
            source, "SELECT draft_id FROM branch_working_drafts WHERE branch_id = ?", fork
        )[0][0]

        # Exact retry: same receipt, no second Branch/root/audit.
        before_retry = _dump(source)
        assert _request(
            "POST", server.base_url + f"/run-containers/{rid}/branches", request
        ) == (201, branch)
        assert _dump(source) == before_retry

        before = _dump(source)
        exported = {
            name: export_scope(server, selection)
            for name, selection in scopes(rid, owner, fork).items()
        }
        assert _dump(source) == before  # export is read-only for the source Run
        for name, (raw, preview) in exported.items():
            ids = {a["audit_event_id"] for a in decode(
                next(p for p in decode(raw)["parts"] if p["name"] == "audits")["data_json"]
            )}
            assert audit_id in ids, name
            assert "original_audit_absent_fork_roots" not in preview
        histories = {
            bid: _request(
                "GET", server.base_url + f"/run-containers/{rid}/branches/{bid}/saved-revisions"
            )
            for bid in (owner, fork)
        }
        assert all(status == 200 for status, _ in histories.values())
        replays = {
            bid: _request("GET", server.base_url + f"/admin/runs/{rid}/branches/{bid}" + REPLAY)
            for bid in (owner, fork)
        }
        assert replays[owner] == (200, played["stored_replay"])
        audit_rows = rows(
            source, "SELECT * FROM branch_revision_audit_events ORDER BY audit_event_id"
        )
    server.app.state.runtime.repository._engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(str(source) + suffix).unlink(missing_ok=True)

    raw = exported["full_run"][0]
    installation = tmp_path / "fork-installation"
    installation.mkdir()
    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        review = upload_preview(server, raw)
        assert review["can_restore"], review
        status, receipt = confirm(server, raw, review, command_id="restore-fork")
        assert status == 201, receipt
        assert set(receipt["restored_branch_ids"]) == {owner, fork}
    # Physical restart of a separate process on the restored SQLite file.
    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        assert confirm(server, raw, review, command_id="restore-fork") == (201, receipt)
        for bid, expected in histories.items():
            assert _request(
                "GET", server.base_url + f"/run-containers/{rid}/branches/{bid}/saved-revisions"
            ) == expected
        for bid, expected in replays.items():
            assert _request(
                "GET", server.base_url + f"/admin/runs/{rid}/branches/{bid}" + REPLAY
            ) == expected
        assert rows(
            target, "SELECT * FROM branch_revision_audit_events ORDER BY audit_event_id"
        ) == audit_rows
        # The restored Run re-exports byte-identically.
        assert export_scope(server, scopes(rid, owner, fork)["full_run"])[0] == raw


def test_failed_fork_audit_rolls_back_every_row_and_exact_retry_succeeds(tmp_path):
    path = tmp_path / "fork-rollback.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        rid, owner, _, saved = manual_match(server)
        played_revision = saved["saved_revision"]["revision_id"]
        before = _dump(path)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute(
                "CREATE TRIGGER fail_fork_audit BEFORE INSERT ON branch_revision_audit_events "
                f"WHEN NEW.event_kind = '{BRANCH_FORK_MATERIALIZED_AUDIT_EVENT_KIND}' "
                "BEGIN SELECT RAISE(ABORT, 'injected fork audit failure'); END"
            )
            connection.commit()
        request, (status, error) = reviewed_fork(
            server, rid, owner, played_revision, "fork-rollback-1"
        )
        assert status == 409, error
        assert error["detail"]["code"] == "branch_identity_conflict"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("DROP TRIGGER fail_fork_audit")
            connection.commit()
        # Nothing of the Branch, draft, components, root or receipt survived.
        assert _dump(path) == before

        status, branch = _request(
            "POST", server.base_url + f"/run-containers/{rid}/branches", request
        )
        assert status == 201, branch
        root = branch["saved_head_revision_id"]
        assert rows(
            path,
            "SELECT event_kind FROM branch_revision_audit_events WHERE saved_revision_id = ?",
            root,
        ) == [(BRANCH_FORK_MATERIALIZED_AUDIT_EVENT_KIND,)]
        assert _request(
            "POST", server.base_url + f"/run-containers/{rid}/branches", request
        ) == (201, branch)
        assert rows(
            path, "SELECT count(*) FROM run_branches WHERE run_id = ?", rid
        ) == [(2,)]
        export_scope(server, {"run_id": rid, "branch_id": branch["branch_id"]})
