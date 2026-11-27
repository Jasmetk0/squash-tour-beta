"""Compact snapshot (Master §24.1 scope 3) on a real HTTP/SQLite Saved v2 Run.

Fixture: one Run, three Branches, the selected Branch has three own Saved
revisions with a really played match and is NOT the Viewer Branch, whose
current choice was Saved by yet another Branch.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from beta_engine.domain.run_branch_archive import (
    COMPACT_FORMAT,
    COMPACT_OMITTED_AREAS,
    CUSTOM_FORMAT,
    FULL_RUN_FORMAT,
    Archive,
    CompactSnapshot,
    decode,
    encode,
)
from beta_engine.infrastructure.db.saved_v2_hooks import ENVIRONMENT_VARIABLE
from tests.api.test_full_run_archive_api import create_branch
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_run_branch_archive_api import (
    archive_root,
    export,
    manual_match,
    raw_request,
)
from tests.api.test_run_branch_archive_boundaries import resign, rewrite
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.run_branch_archive_http import ColdApiServer

pytestmark = pytest.mark.pr_critical

# Standalone reader: a fresh isolated interpreter in an empty directory in
# which opening ANY SQLite connection fails. Only the snapshot bytes are input.
STANDALONE = """
import json, sqlite3, sys
def no_database(*args, **kwargs):
    raise AssertionError("standalone snapshot validation opened a database")
sqlite3.connect = no_database
from pathlib import Path
from beta_engine.application.run_branch_archive_service import validate_compact_snapshot
try:
    print(json.dumps(validate_compact_snapshot(Path(sys.argv[1]).read_bytes())))
except ValueError as exc:
    print(json.dumps({"error": getattr(exc, "code", None), "message": str(exc)}))
"""


def compact_scope(run_id, branch_id):
    return {"run_id": run_id, "branch_id": branch_id, "mode": "compact"}


def compact_preview(server, run_id, branch_id):
    scope = compact_scope(run_id, branch_id)
    status, preview = _request("POST", archive_root(server) + "/export/preview", scope)
    assert status == 200, preview
    return preview, {
        **scope,
        "expected_head_revision_id": preview["selected_head_revision_id"],
        "expected_archive_digest": preview["archive_digest"],
    }


def stage(server, rid, owner, viewer):
    draft = server.base_url + f"/run-containers/{rid}/branches/{owner}/working-draft"
    status, current = _request("GET", draft)
    assert status == 200, current
    status, result = _request("PUT", draft + "/viewer-branch", {
        "viewer_branch_id": viewer, "expected_draft_version": current["draft_version"],
    })
    assert status == 200, result
    return draft, result["draft_version"]


def save_viewer(server, rid, owner, viewer):
    draft, version = stage(server, rid, owner, viewer)
    status, saved = _request("POST", draft + "/save", {"expected_draft_version": version})
    assert status == 201, saved
    return saved


def multi_branch_run(server):
    """T1: create + played match + Viewer choice (3 revisions); T2/T3 forks.

    T2/T3 fork from the empty creation revision. A fork of the PLAYED revision
    materializes a revision without an audit event, which archive v1 rejects
    (``missing_audit``); see the played-fork test below.
    """
    rid, t1, played, match_save = manual_match(server)
    match_head = match_save["saved_revision"]["revision_id"]
    initial = match_save["saved_revision"]["parent_revision_id"]
    t2 = create_branch(server, rid, t1, initial)
    t3 = create_branch(server, rid, t1, initial)
    save_viewer(server, rid, t1, t2)  # T1 HEAD #3 signs Viewer=T2
    save_viewer(server, rid, t2, t3)  # current Viewer=T3, witnessed only by T2
    return rid, t1, t2, t3, played, initial, match_head


def standalone(path, cwd):
    result = subprocess.run(
        [sys.executable, "-I", "-c", STANDALONE, str(path)],
        cwd=cwd, capture_output=True, text=True, timeout=120, check=True,
    )
    return json.loads(result.stdout)


def test_compact_snapshot_of_non_viewer_branch_exports_only_current_saved_state(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, "saved_v2")
    source = tmp_path / "compact-source.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, t1, t2, t3, played, initial, match_head = multi_branch_run(server)
        status, listed = _request("GET", server.base_url + f"/run-branches?run_id={rid}")
        assert status == 200, listed
        head = next(
            b for b in listed["run_branches"] if b["branch_id"] == t1
        )["saved_head_revision_id"]
        status, history = _request(
            "GET", server.base_url + f"/run-containers/{rid}/branches/{t1}/saved-revisions"
        )
        assert status == 200
        assert [r["revision_id"] for r in history["saved_revisions"]][-1] == head
        before = _dump(source)

        preview, command = compact_preview(server, rid, t1)
        assert _dump(source) == before, "Compact preview wrote to the source SQLite"
        assert (preview["format"], preview["scope"]) == (
            COMPACT_FORMAT, "compact_saved_branch_snapshot"
        )
        assert preview["selected_branch_id"] == t1
        assert preview["selected_head_revision_id"] == head
        assert preview["selected_head_sequence"] == 3
        assert preview["omitted_older_revision_count"] == 2
        assert preview["source_context"] == {
            "viewer_branch_id": t3,
            "selected_is_viewer_branch": False,
            "omitted_branch_count": 2,
            "omitted_older_revision_count": 2,
        }
        assert preview["kept_references"] == {
            "parent_revision_id": match_head,
            "forked_from_branch_id": None,
            "forked_from_saved_revision_id": None,
            "viewer_branch_id_signed_at_save": t2,
        }
        assert {"initial_world", "simulation_slot_match_state", "player_sporting_state"} <= set(
            preview["included_components"]
        ), preview["included_components"]
        assert preview["run_calendar"]["weeks_per_year"] > 0
        assert preview["omitted_areas"] == list(COMPACT_OMITTED_AREAS)
        assert preview["verified_uses"] == ["read_and_validate_from_file_bytes"]
        assert "cold_restore" in preview["unsupported_uses"]

        status, raw = raw_request(archive_root(server) + "/export", encode(command))
        assert status == 200, raw[:2000]
        assert _dump(source) == before, "Compact export wrote to the source SQLite"
        assert len(raw) == preview["archive_size_bytes"]
        snapshot = CompactSnapshot(raw)
        assert snapshot.raw_digest == preview["archive_digest"]
        assert snapshot.head.revision_id == head
        assert snapshot.head.content_hash == preview["content_hash"]
        # No older Saved revision, other Branch state or audit travels. The
        # parent id is retained only as a reference bound by the Saved hash.
        assert initial.encode() not in raw
        assert t3.encode() not in raw
        assert b"audit_event_id" not in raw and b"checkpoint_id" not in raw
        assert [p.name for p in snapshot.envelope.parts] == ["run", "branch", "head"]
        played_match = decode(snapshot.head.payload_json)["content"]["simulation_slot_match_state"]
        assert played_match, "Played match is part of the exported Saved state"

        # Same Saved state through the existing Branch archive: identical HEAD
        # row, but it also packs the lineage and the Viewer witness Branches.
        branch_raw, _ = export(server, rid, t1)
        branch_archive = Archive(branch_raw)
        same = next(r for r in branch_archive.revisions if r.revision_id == head)
        assert same.model_dump() == snapshot.head.model_dump()
        assert {b.branch_id for b in branch_archive.branches} == {t1, t2, t3}
        assert len(branch_archive.revisions) == 4
        assert len(raw) < len(branch_raw)
        sizes = {"compact": len(raw), "branch_archive": len(branch_raw)}

        # Full and custom archives keep working on the same Run.
        status, full = _request(
            "POST", archive_root(server) + "/export/preview",
            {"run_id": rid, "branch_id": t1, "mode": "full_run"},
        )
        assert status == 200 and full["format"] == FULL_RUN_FORMAT, full
        status, full_raw = raw_request(archive_root(server) + "/export", encode({
            "run_id": rid, "branch_id": t1, "mode": "full_run",
            "expected_head_revision_id": head,
            "expected_archive_digest": full["archive_digest"],
        }))
        assert status == 200 and len(full_raw) == full["archive_size_bytes"]
        status, custom = _request(
            "POST", archive_root(server) + "/export/preview",
            {"run_id": rid, "branch_id": t1, "mode": "custom", "selected_branch_ids": [t1, t2]},
        )
        assert status == 200 and custom["format"] == CUSTOM_FORMAT, custom
        sizes["full_archive"] = len(full_raw)
        assert _dump(source) == before
        (tmp_path / "sizes.json").write_text(json.dumps(sizes))
    server.app.state.runtime.repository._engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(str(source) + suffix).unlink(missing_ok=True)

    snapshot_file = tmp_path / "compact-snapshot-v1.sqsnap"
    snapshot_file.write_bytes(raw)
    reader = tmp_path / "standalone-reader"
    reader.mkdir()
    validated = standalone(snapshot_file, reader)
    assert list(reader.iterdir()) == [], "Standalone validation created files"
    assert validated == {k: v for k, v in preview.items() if k != "source_context"}
    assert validated["selected_head_revision_id"] == head

    # A fresh installation with an empty, unrelated database: validation works
    # from the bytes; import/restore reports the unsupported scope explicitly.
    installation = tmp_path / "independent-installation"
    installation.mkdir()
    target = installation / "target.db"
    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        before = _dump(target)
        status, body = raw_request(archive_root(server) + "/compact/validate", raw)
        assert status == 200, body
        assert json.loads(body) == validated
        status, body = raw_request(archive_root(server) + "/import/preview", raw)
        assert status == 409
        assert json.loads(body)["detail"]["code"] == "compact_snapshot_not_restorable"
        assert _dump(target) == before
    assert played["result"]


def test_compact_snapshot_guards_and_corruption(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'compact-guards.db'}") as server:
        rid, t1, t2, t3, *_ = multi_branch_run(server)
        root = archive_root(server)
        preview, command = compact_preview(server, rid, t1)
        status, raw = raw_request(root + "/export", encode(command))
        assert status == 200

        # Wrong scope: custom-only field, foreign Branch, shared (never Saved) HEAD.
        status, _ = _request("POST", root + "/export/preview", {
            **compact_scope(rid, t1), "selected_branch_ids": [t1, t2],
        })
        assert status == 422
        status, other = _request("POST", server.base_url + "/run-containers", {"display_name": "Other"})
        assert status == 201
        status, error = _request(
            "POST", root + "/export/preview", compact_scope(rid, other["viewer_branch_id"])
        )
        assert status == 409 and error["detail"]["code"] == "missing_owner"
        status, error = _request("POST", root + "/export/preview", compact_scope(rid, t3))
        assert status == 409 and error["detail"]["code"] == "compact_shared_head", error

        # Unsaved changes block both preview and download; nothing is Saved.
        draft, version = stage(server, rid, t1, t1)
        status, error = _request("POST", root + "/export/preview", compact_scope(rid, t1))
        assert status == 409 and error["detail"]["code"] == "unsaved_changes", error
        status, body = raw_request(root + "/export", encode(command))
        assert status == 409 and json.loads(body)["detail"]["code"] == "unsaved_changes"

        # HEAD changes between Preview and Download: a fresh review is required.
        status, saved = _request("POST", draft + "/save", {"expected_draft_version": version})
        assert status == 201, saved
        status, body = raw_request(root + "/export", encode(command))
        assert status == 409 and json.loads(body)["detail"]["code"] == "stale_export_preview"
        refreshed, _ = compact_preview(server, rid, t1)
        assert refreshed["selected_head_revision_id"] != preview["selected_head_revision_id"]

        def rejected(data, code):
            status, body = raw_request(root + "/compact/validate", data)
            assert status == 409, body
            assert json.loads(body)["detail"]["code"] == code, body

        # Corrupted / forged files fail closed from their own bytes.
        broken = bytearray(raw)
        broken[raw.index(b'"data_json":"') + 20] ^= 1
        rejected(bytes(broken), "invalid_part_integrity")
        rejected(raw[:-7], "invalid_json")
        rejected(encode({**decode(raw), "format": "run_compact_snapshot.v2"}),
                 "unsupported_snapshot_version")
        rejected(encode({**decode(raw), "selected_head_revision_id": "other"}), "invalid_selection")

        def alter_result(row):
            payload = decode(row["payload_json"])
            payload["run"]["display_name"] = "Forged"
            row["payload_json"] = encode(payload).decode()
        rejected(rewrite(raw, "head", alter_result), "invalid_saved_hash")

        def resigned(mutate):
            def change(row):
                payload = decode(row["payload_json"])
                mutate(payload)
                row["payload_json"] = encode(payload).decode()
                resign(row)
            forged = decode(rewrite(raw, "head", change))
            head = decode(next(p for p in forged["parts"] if p["name"] == "head")["data_json"])
            forged["content_hash"] = head["content_hash"]
            return encode(forged)

        # Missing dependency: played sporting authority without its InitialWorld.
        rejected(resigned(lambda p: p["content"].pop("initial_world")), "missing_runtime_dependency")
        # A Run-level value that the HEAD does not sign is never accepted.
        rejected(resigned(lambda p: p["run"].update(display_name="Elsewhere")),
                 "compact_foreign_run_witness")
        # A native-fork dependency is a foreign source, not compact content.
        rejected(resigned(lambda p: p["content"].update(native_fork_baseline={})),
                 "compact_foreign_source_dependency")


def test_compact_snapshot_of_materialized_played_fork_is_self_contained(tmp_path):
    """A fork of played Saved state owns a remapped InitialWorld: no foreign source."""
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'compact-fork.db'}") as server:
        rid, t1, _, match_save = manual_match(server)
        match_head = match_save["saved_revision"]["revision_id"]
        fork = create_branch(server, rid, t1, match_head)
        preview, command = compact_preview(server, rid, fork)
        assert preview["selected_head_kind"] == "branch_fork_materialized"
        assert preview["kept_references"]["parent_revision_id"] == match_head
        assert preview["kept_references"]["forked_from_branch_id"] == t1
        assert preview["source_context"]["selected_is_viewer_branch"] is False
        assert "initial_world" in preview["included_components"]
        status, raw = raw_request(archive_root(server) + "/export", encode(command))
        assert status == 200
        snapshot = CompactSnapshot(raw)
        assert snapshot.head.branch_id == fork
        assert match_head.encode() in raw  # reference only, bound by the Saved hash
        assert snapshot.head.parent_revision_id == match_head
        status, body = raw_request(archive_root(server) + "/compact/validate", raw)
        assert status == 200, body
