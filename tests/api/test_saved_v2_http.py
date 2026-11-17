"""Saved v2 storage through the real production HTTP/SQLite stack.

The same authentic native scenario (population, health, real MatchEngine opening
match and Tour matches, overlapping Editions, explicit Saves, nested fork, Restore)
is executed once on a v1 Run and once on an explicitly opted-in Saved v2 Run with
the same deterministic entity IDs. Logical history must be byte-identical; the v2
database stores envelopes plus Run-scoped nodes. Then: restart, warm-then-tamper,
foreign-Run, downgrade and missing-format corruption must fail closed.
"""

from __future__ import annotations

import itertools
import json
import sqlite3
from types import SimpleNamespace

import pytest

from beta_engine.infrastructure.db.saved_v2_hooks import ENVIRONMENT_VARIABLE
from beta_engine.infrastructure.db.saved_v2_store import ENVELOPE_PREFIX, FORMAT, sha256_hex
from tests.api.test_calendar_global_slots import copy_database, ready
from tests.api.test_calendar_population_sporting_checkpoint import restore
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, tour_url
from tests.api.test_native_fork_public_continuation import Tour, fork
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

HISTORY = "/run-containers/run/branches/{branch}/saved-revisions"


def _deterministic_ids(monkeypatch):
    import beta_engine.api.deps as deps

    counter = itertools.count(1)
    monkeypatch.setattr(deps, "uuid4", lambda: SimpleNamespace(hex=f"{next(counter):032x}"))


def _history(server, branch):
    code, body = _request("GET", server.base_url + HISTORY.format(branch=branch))
    assert code == 200, body
    return body


def _scenario(server):
    """One authentic flow; returns every public read used for equality."""
    ready(server, 6)
    execute(server, command(inspect(server), "next-match", name="source-first-match"))
    saved = save_tour(server)
    created = fork(server, saved["revision_id"], name="v2 fork")
    target = Tour(server, created["branch_id"])
    target.execute("next-match", "target-second-match")
    target_saved = target.save()
    nested = fork(server, target_saved["revision_id"], branch=created["branch_id"], name="v2 nested")
    nested_tour = Tour(server, nested["branch_id"])
    nested_tour.execute("next-slot", "nested-rest-of-slot")
    nested_tour.save()
    execute(server, command(inspect(server), "next-match", name="source-second-match"))
    save_tour(server)
    # Restore the original Branch to its pre-match revision (copy-on-write path).
    restored = restore(server, saved["revision_id"])
    branches = ["branch", created["branch_id"], nested["branch_id"]]
    return {
        "source": inspect(server),
        "target": target.view(),
        "nested": nested_tour.view(),
        "histories": {b: _history(server, b) for b in branches},
        "restored": restored["revision_id"],
    }


def _rows(server):
    from sqlalchemy import select

    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

    repository = server.app.state.runtime.repository
    with repository._session_factory() as session:
        return [tuple(row) for row in session.execute(select(
            BranchSavedRevisionModel.revision_id, BranchSavedRevisionModel.branch_id,
            BranchSavedRevisionModel.sequence, BranchSavedRevisionModel.parent_revision_id,
            BranchSavedRevisionModel.content_hash, BranchSavedRevisionModel.payload_json,
            BranchSavedRevisionModel.change_summary_json,
        ).order_by(BranchSavedRevisionModel.revision_id))]


def _raw(path, sql, *args):
    with sqlite3.connect(path) as connection:
        return connection.execute(sql, args).fetchall()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    patch = pytest.MonkeyPatch()
    root = tmp_path_factory.mktemp("saved-v2-http")
    result = {}
    try:
        for storage in ("v1", "saved_v2"):
            _deterministic_ids(patch)
            patch.setenv(ENVIRONMENT_VARIABLE, storage)
            path = root / f"{storage}.db"
            with ApiServer(database_url=f"sqlite:///{path}") as server:
                reads = _scenario(server)
                rows = _rows(server)
                repository = server.app.state.runtime.repository
                verified = all(repository.verify_branch_saved_revision_hash(revision_id=r[0]) for r in rows)
            result[storage] = SimpleNamespace(path=path, reads=reads, rows=rows, verified=verified)
    finally:
        patch.undo()
    return result


def test_v2_run_has_identical_logical_history_and_responses(built):
    v1, v2 = built["v1"], built["saved_v2"]
    assert v1.verified and v2.verified
    assert len(v1.rows) == len(v2.rows) > 20
    assert v1.rows == v2.rows                      # IDs, hashes, exact payload text
    assert v1.reads == v2.reads                    # complete public DTOs/histories
    assert _raw(v1.path, "SELECT COUNT(*) FROM run_saved_storage_formats") == [(0,)]
    assert _raw(v1.path, "SELECT COUNT(*) FROM saved_revision_nodes") == [(0,)]
    assert _raw(v2.path, "SELECT run_id, storage_format FROM run_saved_storage_formats") == [("run", FORMAT)]
    stored = _raw(v2.path, "SELECT payload_json FROM branch_saved_revisions")
    assert stored and all(text.startswith(ENVELOPE_PREFIX) and len(text) < 300 for (text,) in stored)
    for digest, body in _raw(v2.path, "SELECT digest, body FROM saved_revision_nodes"):
        assert sha256_hex(body) == digest
    v1_bytes = _raw(v1.path, "SELECT SUM(LENGTH(payload_json)) FROM branch_saved_revisions")[0][0]
    v2_bytes = _raw(v2.path, "SELECT SUM(LENGTH(body)) FROM saved_revision_nodes")[0][0]
    assert v2_bytes < v1_bytes / 3


def test_v2_restart_reads_the_same_history(built, tmp_path):
    path = tmp_path / "restart.db"
    copy_database(built["saved_v2"].path, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert inspect(server) == built["saved_v2"].reads["source"]
        for branch, history in built["saved_v2"].reads["histories"].items():
            assert _history(server, branch) == history
        assert _rows(server) == built["v1"].rows


def _ancestor_node(path):
    """A node used only by early history (not the HEAD's own new nodes)."""
    (first_env,) = _raw(path, "SELECT payload_json FROM branch_saved_revisions "
                        "WHERE branch_id='branch' ORDER BY sequence LIMIT 1 OFFSET 3")[0]
    root = json.loads(first_env)["saved_v2"]["root"]
    return root


def _tamper(path, statements):
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER IF EXISTS saved_revision_nodes_no_update")
        connection.execute("DROP TRIGGER IF EXISTS saved_revision_nodes_no_delete")
        connection.execute("DROP TRIGGER IF EXISTS run_saved_storage_formats_no_delete")
        for sql, args in statements:
            connection.execute(sql, args)


def _corruptions(path):
    root = _ancestor_node(path)
    (body,) = _raw(path, "SELECT body FROM saved_revision_nodes WHERE digest=?", root)[0]
    changed = body[:-1] + ("0" if body[-1] != "0" else "1")
    yield "changed node bytes", [("UPDATE saved_revision_nodes SET body=? WHERE digest=?", (changed, root))]
    yield "missing node", [("DELETE FROM saved_revision_nodes WHERE digest=?", (root,))]
    yield "node moved to a foreign Run", [
        ("UPDATE saved_revision_nodes SET run_id='foreign-run' WHERE digest=?", (root,))]
    yield "no recorded v2 format", [("DELETE FROM run_saved_storage_formats", ())]
    (envelope,) = _raw(path, "SELECT payload_json FROM branch_saved_revisions "
                       "WHERE branch_id='branch' ORDER BY sequence LIMIT 1 OFFSET 3")[0]
    forged = envelope.replace('"chars":', '"chars":1', 1)
    yield "forged envelope size", [("UPDATE branch_saved_revisions SET payload_json=? WHERE payload_json=?",
                                    (forged, envelope))]


@pytest.mark.parametrize("case", range(5))
def test_corruption_after_successful_warm_read_fails_closed(built, tmp_path, case):
    path = tmp_path / "tamper.db"
    copy_database(built["saved_v2"].path, path)
    label, statements = list(_corruptions(path))[case]
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert inspect(server) == built["saved_v2"].reads["source"]       # warm
        assert _history(server, "branch") == built["saved_v2"].reads["histories"]["branch"]
        _tamper(path, statements)
        code, body = _request("GET", tour_url(server))
        assert code != 200, label
        code, body = _request("GET", server.base_url + HISTORY.format(branch="branch"))
        assert code != 200, label


def test_downgraded_inline_row_in_v2_run_fails_closed(built, tmp_path):
    path = tmp_path / "downgrade.db"
    copy_database(built["saved_v2"].path, path)
    logical = {row[0]: row[5] for row in built["v1"].rows}
    (revision_id,) = _raw(path, "SELECT revision_id FROM branch_saved_revisions "
                          "WHERE branch_id='branch' ORDER BY sequence LIMIT 1 OFFSET 2")[0]
    _tamper(path, [("UPDATE branch_saved_revisions SET payload_json=? WHERE revision_id=?",
                    (logical[revision_id], revision_id))])
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        code, _ = _request("GET", server.base_url + HISTORY.format(branch="branch"))
        assert code != 200


def test_v2_envelope_in_v1_run_fails_closed(built, tmp_path):
    path = tmp_path / "upgrade.db"
    copy_database(built["v1"].path, path)
    (envelope,) = _raw(built["saved_v2"].path, "SELECT payload_json FROM branch_saved_revisions "
                       "WHERE branch_id='branch' ORDER BY sequence LIMIT 1 OFFSET 2")[0]
    (revision_id,) = _raw(path, "SELECT revision_id FROM branch_saved_revisions "
                          "WHERE branch_id='branch' ORDER BY sequence LIMIT 1 OFFSET 2")[0]
    _tamper(path, [("UPDATE branch_saved_revisions SET payload_json=? WHERE revision_id=?",
                    (envelope, revision_id))])
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        code, _ = _request("GET", server.base_url + HISTORY.format(branch="branch"))
        assert code != 200


def test_existing_v1_run_stays_v1_when_new_runs_opt_in(built, tmp_path, monkeypatch):
    path = tmp_path / "mixed.db"
    copy_database(built["v1"].path, path)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, "saved_v2")
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="mixed-next-match"))
        save_tour(server)
        code, created = _request("POST", server.base_url + "/run-containers", {"display_name": "New v2 Run"})
        assert code == 201, created
    formats = _raw(path, "SELECT run_id FROM run_saved_storage_formats")
    assert formats == [(created["run_id"],)]
    old = _raw(path, "SELECT payload_json FROM branch_saved_revisions WHERE run_id='run'")
    assert old and not any(text.startswith(ENVELOPE_PREFIX) for (text,) in old)
    new = _raw(path, "SELECT payload_json FROM branch_saved_revisions WHERE run_id=?", created["run_id"])
    assert new and all(text.startswith(ENVELOPE_PREFIX) for (text,) in new)


def test_rehashed_forged_ancestor_is_rejected_like_v1(built, tmp_path):
    """A self-consistent forgery: new nodes, new envelope and a recomputed hash."""
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.domain.run_revisions import saved_revision_content_hash
    from beta_engine.infrastructure.db.saved_v2_store import Encoder, canonical, envelope_text

    path = tmp_path / "rehashed.db"
    copy_database(built["saved_v2"].path, path)
    logical = {row[0]: row for row in built["v1"].rows}
    candidates = [row for row in built["v1"].rows if row[1] == "branch" and json.loads(row[5]).get(
        "content", {}).get("calendar_tour_authority", {}).get("state", {}).get("rankings")]
    revision_id, _branch, sequence, parent, _hash, text, summary = sorted(candidates, key=lambda r: r[2])[0]
    body = json.loads(text)
    component = body["content"]["calendar_tour_authority"]
    component["state"]["rankings"] = component["state"]["rankings"][:-1] or [{"forged": True}]
    component["fingerprint"] = canonical_hash(component["state"])
    forged = canonical(body)
    (kind, schema) = _raw(path, "SELECT kind, payload_schema_version FROM branch_saved_revisions "
                          "WHERE revision_id=?", revision_id)[0]
    forged_hash = saved_revision_content_hash(
        revision_id=revision_id, run_id="run", branch_id="branch", sequence=sequence,
        parent_revision_id=parent, kind=kind, payload_schema_version=schema, payload=body,
        change_summary=json.loads(summary))
    encoder = Encoder("run", index=None)
    root = encoder.encode(forged)
    statements = [("INSERT OR IGNORE INTO saved_revision_nodes(run_id,digest,body) VALUES ('run',?,?)", (d, b))
                  for d, b in encoder.nodes.items()]
    statements.append(("UPDATE branch_saved_revisions SET payload_json=?, content_hash=? WHERE revision_id=?",
                       (envelope_text(run_id="run", root=root, chars=len(forged)), forged_hash, revision_id)))
    _tamper(path, statements)
    assert logical[revision_id][5] != forged
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        code, _ = _request("GET", tour_url(server))
        assert code != 200


def test_stale_concurrent_save_is_rejected_and_writes_no_nodes(built, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "concurrent.db"
    copy_database(built["saved_v2"].path, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="concurrent-match"))
        view = inspect(server)
        request = {"expected_draft_version": view["draft_version"],
                   "expected_calendar_tour_fingerprint": view["tour_fingerprint"]}
        before = _raw(path, "SELECT COUNT(*) FROM saved_revision_nodes")[0][0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = sorted(code for code, _ in pool.map(
                lambda _: _request("POST", tour_url(server) + "/save", request), range(2)))
        assert codes[0] == 201 and codes[1] in (201, 409), codes
        heads = _raw(path, "SELECT COUNT(*) FROM branch_saved_revisions WHERE branch_id='branch'")[0][0]
        after_first = _raw(path, "SELECT COUNT(*) FROM saved_revision_nodes")[0][0]
        assert after_first > before
        # Exactly one new Saved Revision; a retry/second writer added no revision.
        assert heads == 1 + _raw(built["saved_v2"].path,
                                 "SELECT COUNT(*) FROM branch_saved_revisions WHERE branch_id='branch'")[0][0]
        # Stale expected version: rejected, nothing written.
        code, _ = _request("POST", tour_url(server) + "/save", request)
        assert code != 201
        assert _raw(path, "SELECT COUNT(*) FROM saved_revision_nodes")[0][0] == after_first
        assert inspect(server)["saved"]


def test_failed_postwrite_verification_rolls_back_nodes_and_row(built, tmp_path, monkeypatch):
    from beta_engine.infrastructure.db import saved_v2_hooks

    path = tmp_path / "rollback.db"
    copy_database(built["saved_v2"].path, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="rollback-match"))
        view = inspect(server)
        nodes = _raw(path, "SELECT COUNT(*) FROM saved_revision_nodes")[0][0]
        rows = _raw(path, "SELECT COUNT(*) FROM branch_saved_revisions")[0][0]
        original_text = saved_v2_hooks.text
        hits = []

        def verification_reads_other_bytes(sql):
            if sql.startswith("SELECT saved_v2_payload(run_id, payload_json)"):
                hits.append(sql)
                return original_text("SELECT 'different' FROM branch_saved_revisions WHERE revision_id = :id")
            return original_text(sql)

        monkeypatch.setattr(saved_v2_hooks, "text", verification_reads_other_bytes)
        code, _ = _request("POST", tour_url(server) + "/save", {
            "expected_draft_version": view["draft_version"],
            "expected_calendar_tour_fingerprint": view["tour_fingerprint"]})
        monkeypatch.setattr(saved_v2_hooks, "text", original_text)
        assert code != 201 and hits
        assert _raw(path, "SELECT COUNT(*) FROM saved_revision_nodes")[0][0] == nodes
        assert _raw(path, "SELECT COUNT(*) FROM branch_saved_revisions")[0][0] == rows
        assert not inspect(server)["saved"]
        save_tour(server)                       # the same Save then succeeds exactly
        assert _raw(path, "SELECT COUNT(*) FROM branch_saved_revisions")[0][0] == rows + 1
