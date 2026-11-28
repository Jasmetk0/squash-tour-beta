"""Manual Tour Save: an oversize committed value is not re-encoded after commit.

Real HTTP/SQLite/MatchEngine on the genuinely produced global-slot Run, Saved v1
and Saved v2. The candidate passes the Save's own canonical payload text to the
post-commit retention. It is compared with the forced original re-encoding path
on identical database copies with deterministic Saved/audit IDs: every persisted
row, the retained decode cache, a retry after an uncertain response and a fresh
restart followed by another command and Save must be identical.
"""

import sqlite3
from itertools import count
from uuid import NAMESPACE_URL, uuid5

import pytest

from tests.api.test_calendar_global_slots import copy_database
from tests.api.test_calendar_tour_flow import command, execute, inspect, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def _rows(path):
    with sqlite3.connect(path) as db:
        tables = {name for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {
            "revisions": db.execute(
                "SELECT revision_id, run_id, branch_id, sequence, parent_revision_id, kind, "
                "payload_schema_version, content_hash_algorithm, content_hash, payload_json, "
                "change_summary_json FROM branch_saved_revisions ORDER BY sequence, revision_id").fetchall(),
            "nodes": db.execute("SELECT * FROM saved_revision_nodes ORDER BY 1, 2").fetchall()
            if "saved_revision_nodes" in tables else [],
            "audit": db.execute("SELECT audit_event_id, saved_revision_id, event_kind, payload_json "
                                "FROM branch_revision_audit_events ORDER BY audit_event_id").fetchall(),
            "draft": db.execute("SELECT draft_id, base_revision_id, status, change_count, draft_version, "
                                "changes_json FROM branch_working_drafts ORDER BY draft_id").fetchall(),
            "heads": db.execute("SELECT branch_id, saved_head_revision_id FROM run_branches").fetchall(),
            "checkpoint": db.execute("SELECT fingerprint, payload_json FROM "
                                     "calendar_player_sporting_checkpoints").fetchall(),
            "tour": db.execute("SELECT fingerprint, payload_json FROM calendar_tour_authorities").fetchall(),
        }


def _post_save(server, view):
    return _request("POST", tour_url(server) + "/save", {
        "expected_draft_version": view["draft_version"],
        "expected_calendar_tour_fingerprint": view["tour_fingerprint"],
    })


def _arm(tmp_path, source, monkeypatch, *, label, original, limit):
    from beta_engine.api import deps
    from beta_engine.infrastructure.db import native_fork_source_projection as cache

    path = tmp_path / f"{label}.db"
    copy_database(source, path)
    sequence = count()
    observed = {"calls": [], "identities": 0}
    with monkeypatch.context() as patch:
        patch.setattr(deps, "uuid4", lambda: uuid5(NAMESPACE_URL, f"oversize-text:{next(sequence)}"))
        if limit is not None:
            patch.setattr(cache, "MAX_GLOBAL_TOUR_BYTES", limit)
        remember, identity = cache.remember_committed_global_sources, cache._value_identity

        def remembered(repository, src, captured, **kwargs):
            observed["calls"].append(type(kwargs.get("_payload_text")).__name__)
            if original:
                kwargs.pop("_payload_text", None)
            before = observed["identities"]
            remember(repository, src, captured, **kwargs)
            observed["calls"][-1] += f":identities={observed['identities'] - before}"

        def counted(*args):
            observed["identities"] += 1
            return identity(*args)

        patch.setattr(cache, "remember_committed_global_sources", remembered)
        patch.setattr(cache, "_value_identity", counted)
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            repository = server.app.state.runtime.repository
            execute(server, command(inspect(server), "next-match", name="oversize-text"))
            view = inspect(server)
            status, receipt = _post_save(server, view)
            assert status == 201, receipt
            retained = {key: (entry[0], type(entry[1]).__name__)
                        for key, entry in getattr(repository, "_global_tour_projection_cache", {}).items()}
            # Uncertain response: the same request again never adds a revision.
            committed = _rows(path)
            status, retry = _post_save(server, view)
            assert status == 409, retry
            assert _rows(path) == committed
            after = inspect(server)
            assert after["saved"] and after["saved_head_revision_id"] == receipt["saved_revision"]["revision_id"]
        # Physical restart: a fresh process-equivalent server continues and Saves.
        with ApiServer(database_url=f"sqlite:///{path}") as restarted:
            reopened = inspect(restarted)
            assert reopened["saved"] and reopened["saved_head_revision_id"] == after["saved_head_revision_id"]
            execute(restarted, command(reopened, "next-match", name="oversize-text-after-restart"))
            status, second = _post_save(restarted, inspect(restarted))
            assert status == 201, second
    return receipt, retained, observed, _rows(path)


@pytest.mark.parametrize("storage", ["prepared_slots", "prepared_slots_v2"])
@pytest.mark.parametrize("limit", [1024, None])
def test_oversize_decision_from_the_committed_text_keeps_every_byte_and_cache_entry(
    tmp_path, monkeypatch, request, storage, limit,
):
    source = request.getfixturevalue(storage)
    original = _arm(tmp_path, source, monkeypatch, label=f"original-{limit}", original=True, limit=limit)
    candidate = _arm(tmp_path, source, monkeypatch, label=f"candidate-{limit}", original=False, limit=limit)
    assert candidate[0]["saved_revision"] == original[0]["saved_revision"]
    assert candidate[1] == original[1]          # identical retained decode cache
    assert candidate[3] == original[3]          # identical rows after retry, restart and 2nd Save
    assert original[2]["calls"][0] == "NoneType:identities=1"
    if limit is None:
        # A value that fits keeps the original identity, key and retention.
        assert candidate[2]["calls"][0] == "str:identities=1" and candidate[1]
    else:
        # Oversize: neither the payload nor the checkpoint is re-encoded and
        # nothing is retained, exactly as the original path decided.
        assert candidate[2]["calls"][0] == "str:identities=0"
