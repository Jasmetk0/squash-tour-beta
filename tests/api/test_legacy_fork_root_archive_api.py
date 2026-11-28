"""#1939: archives of materialized fork roots written before their audit existed.

The pre-#1939 ordinary fork writer produced exactly the current root and summary
bytes but no audit row. The legacy state is reproduced on real SQLite by
creating a fork through the production HTTP route and removing only that
root's audit row; the Saved row is untouched. (PR evidence additionally
replays a database written by the unmodified ``buuk`` writer.)
"""

from __future__ import annotations

import copy
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from beta_engine.domain.run_branch_archive import (
    Archive,
    ArchiveError,
    decode,
    digest,
    encode,
)
from beta_engine.domain.run_revisions import (
    BRANCH_FORK_MATERIALIZED_AUDIT_EVENT_KIND,
    saved_revision_content_hash,
)
from tests.api.test_full_run_archive_api import create_branch
from tests.api.test_materialized_fork_audit_api import (
    REPLAY,
    export_scope,
    rows,
    scopes,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_run_branch_archive_api import confirm, manual_match, upload_preview
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.run_branch_archive_http import ColdApiServer

pytestmark = pytest.mark.pr_critical


def _remove_audit(path, revision_id):
    with closing(sqlite3.connect(path)) as connection:
        removed = connection.execute(
            "DELETE FROM branch_revision_audit_events WHERE saved_revision_id = ?",
            (revision_id,),
        ).rowcount
        connection.commit()
    assert removed == 1


@pytest.fixture(scope="module")
def legacy_run(tmp_path_factory):
    """One played Run with an audited new fork and a legacy-state fork."""
    root = tmp_path_factory.mktemp("legacy-fork")
    source = root / "source.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, owner, played, saved = manual_match(server)
        played_revision = saved["saved_revision"]["revision_id"]
        audited = create_branch(server, rid, owner, played_revision)
        legacy = create_branch(server, rid, owner, played_revision)
        heads = {
            bid: rows(
                source, "SELECT saved_head_revision_id FROM run_branches WHERE branch_id = ?", bid
            )[0][0]
            for bid in (audited, legacy)
        }
        _remove_audit(source, heads[legacy])
        before = _dump(source)
        exported = {}
        for fork in (audited, legacy):
            for name, selection in scopes(rid, owner, fork).items():
                exported[fork, name] = export_scope(server, selection)
        assert _dump(source) == before  # every export is read-only
        histories = {
            bid: _request(
                "GET", server.base_url + f"/run-containers/{rid}/branches/{bid}/saved-revisions"
            )
            for bid in (owner, audited, legacy)
        }
        replays = {
            bid: _request("GET", server.base_url + f"/admin/runs/{rid}/branches/{bid}" + REPLAY)
            for bid in (owner, audited, legacy)
        }
        saved_rows = rows(
            source,
            "SELECT revision_id, payload_json, change_summary_json, content_hash "
            "FROM branch_saved_revisions ORDER BY revision_id",
        )
    server.app.state.runtime.repository._engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(str(source) + suffix).unlink(missing_ok=True)
    return {
        "root": root, "run_id": rid, "owner": owner, "played": played_revision,
        "audited": audited, "legacy": legacy, "heads": heads, "exported": exported,
        "histories": histories, "replays": replays, "saved_rows": saved_rows,
        "stored_replay": played["stored_replay"],
    }


def _part(raw, name):
    return decode(next(p for p in decode(raw)["parts"] if p["name"] == name)["data_json"])


def test_legacy_root_is_disclosed_and_never_given_an_audit(legacy_run):
    legacy_root = legacy_run["heads"][legacy_run["legacy"]]
    audited_root = legacy_run["heads"][legacy_run["audited"]]
    for (fork, name), (raw, preview) in legacy_run["exported"].items():
        audits = {a["saved_revision_id"]: a for a in _part(raw, "audits")}
        disclosed = [r["revision_id"] for r in preview.get("original_audit_absent_fork_roots", [])]
        includes_legacy = legacy_root in {r["revision_id"] for r in _part(raw, "revisions")}
        assert legacy_root not in audits, (fork, name)
        assert disclosed == ([legacy_root] if includes_legacy else []), (fork, name)
        if includes_legacy:
            (entry,) = preview["original_audit_absent_fork_roots"]
            assert entry == {
                "revision_id": legacy_root,
                "branch_id": legacy_run["legacy"],
                "source_saved_revision_id": legacy_run["played"],
                "original_audit": "absent",
                "evidence": "derived_from_saved_fork_lineage",
                "reason": (
                    "Materialized fork root written before its original audit "
                    "existed; no audit is created or transferred"
                ),
            }
        if audited_root in {r["revision_id"] for r in _part(raw, "revisions")}:
            assert audits[audited_root]["event_kind"] == BRANCH_FORK_MATERIALIZED_AUDIT_EVENT_KIND
    # Full and Custom carry the legacy root; the audited-fork Branch export does not.
    assert legacy_root not in {
        r["revision_id"]
        for r in _part(legacy_run["exported"][legacy_run["audited"], "branch"][0], "revisions")
    }


@pytest.mark.parametrize("scope", ["branch", "custom", "full_run"])
def test_legacy_root_archive_cold_restores_restarts_and_reexports_identically(
    legacy_run, scope
):
    rid, legacy = legacy_run["run_id"], legacy_run["legacy"]
    raw, preview = legacy_run["exported"][legacy, scope]
    branch_ids = {b["branch_id"] for b in preview["branches"]}
    target = legacy_run["root"] / f"target-{scope}.db"
    installation = legacy_run["root"] / f"installation-{scope}"
    installation.mkdir()
    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        review = upload_preview(server, raw)
        assert review["can_restore"], review
        assert review["original_audit_absent_fork_roots"] == preview["original_audit_absent_fork_roots"]
        status, receipt = confirm(server, raw, review, command_id=f"restore-{scope}")
        assert status == 201, receipt
        assert set(receipt["restored_branch_ids"]) == branch_ids
    with ColdApiServer(database_url=f"sqlite:///{target}", directory=installation) as server:
        assert confirm(server, raw, review, command_id=f"restore-{scope}") == (201, receipt)
        for bid in branch_ids:
            assert _request(
                "GET", server.base_url + f"/run-containers/{rid}/branches/{bid}/saved-revisions"
            ) == legacy_run["histories"][bid]
            assert _request(
                "GET", server.base_url + f"/admin/runs/{rid}/branches/{bid}" + REPLAY
            ) == legacy_run["replays"][bid]
        assert legacy_run["replays"][legacy_run["owner"]] == (200, legacy_run["stored_replay"])
        # Original Saved bytes/hashes survive; no audit was invented on restore.
        restored = {r[0]: r for r in rows(
            target,
            "SELECT revision_id, payload_json, change_summary_json, content_hash "
            "FROM branch_saved_revisions ORDER BY revision_id",
        )}
        assert all(restored[r[0]] == r for r in legacy_run["saved_rows"] if r[0] in restored)
        assert rows(
            target,
            "SELECT count(*) FROM branch_revision_audit_events WHERE saved_revision_id = ?",
            legacy_run["heads"][legacy],
        ) == [(0,)]
        selection = scopes(rid, legacy_run["owner"], legacy)[scope]
        again = export_scope(server, selection)[0]
        if scope == "full_run":
            assert again == raw
        else:
            # The restored subset re-exports identically; only the source's
            # unselected Branch is no longer there to be declared omitted.
            original, restored_envelope = decode(raw), decode(again)
            assert original["omitted_branch_ids"] == [legacy_run["audited"]]
            assert restored_envelope["omitted_branch_ids"] == []
            original["omitted_branch_ids"] = []
            assert restored_envelope == original


def _repack(raw, mutate):
    envelope = decode(raw)
    parts = {p["name"]: decode(p["data_json"]) for p in envelope["parts"]}
    mutate(parts)
    for revision in parts["revisions"]:
        values = {
            k: revision[k] for k in (
                "revision_id", "run_id", "branch_id", "sequence", "parent_revision_id",
                "kind", "payload_schema_version",
            )
        }
        revision["content_hash"] = saved_revision_content_hash(
            **values,
            payload=decode(revision["payload_json"]),
            change_summary=decode(revision["change_summary_json"]),
        )
    for part in envelope["parts"]:
        data = encode(parts[part["name"]])
        part.update(data_json=data.decode(), size=len(data), sha256=digest(data))
    return encode(envelope)


def _code(raw):
    with pytest.raises(ArchiveError) as error:
        Archive(raw)
    return error.value.code


def _revision(parts, revision_id):
    return next(r for r in parts["revisions"] if r["revision_id"] == revision_id)


def _edit(revision, field, change):
    value = decode(revision[field])
    change(value)
    revision[field] = json.dumps(value, sort_keys=True, separators=(",", ":"))


def test_rejections_keep_audit_and_provenance_strict(legacy_run):
    raw = legacy_run["exported"][legacy_run["legacy"], "full_run"][0]
    Archive(raw)  # the unmodified mixed archive is valid
    legacy_root = legacy_run["heads"][legacy_run["legacy"]]
    audited_root = legacy_run["heads"][legacy_run["audited"]]
    initial = next(r for r in _part(raw, "revisions") if r["sequence"] == 1)["revision_id"]
    assert _repack(raw, lambda parts: None) == raw  # helper is byte-faithful

    def drop_audit(revision_id):
        return lambda parts: parts.update(audits=[
            a for a in parts["audits"] if a["saved_revision_id"] != revision_id
        ])

    # An ordinary Saved revision without its audit is still rejected.
    assert _code(_repack(raw, drop_audit(legacy_run["played"]))) == "missing_audit"

    # Foreign parent binding: a re-hashed root claiming another source revision.
    def foreign_source(parts):
        _edit(_revision(parts, legacy_root), "change_summary_json", lambda s: s.update(
            source_saved_revision_id=initial,
            summary=f"Forked Branch from {initial} with remapped Branch-owned world identity",
        ))
    assert _code(_repack(raw, foreign_source)) == "missing_audit"

    # Signed Branch provenance that disagrees with the actual parent.
    def foreign_signed_branch(parts):
        _edit(_revision(parts, legacy_root), "payload_json", lambda p: p["branch"].update(
            forked_from_saved_revision_id=initial,
        ))
    assert _code(_repack(raw, foreign_signed_branch)) == "missing_audit"

    # A Branch declaring a different fork origin than the root's parent.
    def foreign_branch_origin(parts):
        for branch in parts["branches"]:
            if branch["branch_id"] == legacy_run["legacy"]:
                branch["forked_from_saved_revision_id"] = initial
    assert _code(_repack(raw, foreign_branch_origin)) == "missing_audit"

    # Any other summary shape is not the known legacy writer.
    def extra_summary_field(parts):
        _edit(_revision(parts, legacy_root), "change_summary_json", lambda s: s.update(note="x"))
    assert _code(_repack(raw, extra_summary_field)) == "missing_audit"

    def wrong_fingerprint(parts):
        _edit(_revision(parts, legacy_root), "change_summary_json", lambda s: s.update(
            initial_world_fingerprint="0" * 64,
        ))
    assert _code(_repack(raw, wrong_fingerprint)) == "missing_audit"

    audit = next(a for a in _part(raw, "audits") if a["saved_revision_id"] == audited_root)

    # Duplicate audit for one root.
    def duplicate(parts):
        clone = copy.deepcopy(audit)
        clone["audit_event_id"] = audit["audit_event_id"] + "-copy"
        parts["audits"] = sorted(
            [*parts["audits"], clone], key=lambda a: a["audit_event_id"]
        )
    assert _code(_repack(raw, duplicate)) == "duplicate_audit"

    def edit_audit(change):
        def mutate(parts):
            row = next(a for a in parts["audits"] if a["audit_event_id"] == audit["audit_event_id"])
            change(row)
        return mutate

    # Wrongly owned or mismatched original fork audit.
    assert _code(_repack(raw, edit_audit(
        lambda a: a.update(branch_id=legacy_run["owner"])
    ))) == "invalid_fork_audit"
    assert _code(_repack(raw, edit_audit(
        lambda a: a.update(event_kind="saved_revision_created")
    ))) == "invalid_fork_audit"
    for field, value in (
        ("saved_revision_content_hash", "0" * 64),
        ("source_saved_revision_id", initial),
        ("source_branch_id", legacy_run["legacy"]),
    ):
        def tamper(a, field=field, value=value):
            payload = decode(a["payload_json"])
            payload[field] = value
            a["payload_json"] = encode(payload).decode()
        assert _code(_repack(raw, edit_audit(tamper))) == "invalid_fork_audit", field

    # A fork-root audit kind attached to a non-fork revision.
    def misplaced(parts):
        row = next(a for a in parts["audits"] if a["saved_revision_id"] == legacy_run["played"])
        row["event_kind"] = BRANCH_FORK_MATERIALIZED_AUDIT_EVENT_KIND
    assert _code(_repack(raw, misplaced)) == "invalid_fork_audit"
