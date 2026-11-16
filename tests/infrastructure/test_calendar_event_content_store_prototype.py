"""Experimental scoped sporting-event blob storage: never a Saved writer.

Every test exercises real in-memory SQLite rows. The v1 source Saved envelope
and independent production source verification remain out of scope.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from beta_engine.infrastructure.db import calendar_event_content_store_prototype as ev


pytestmark = pytest.mark.pr_critical
RUN, BRANCH = "run", "branch"


def hashed(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def rows(count=1):
    return [
        {
            "schema_version": (
                "calendar_global_slot.v1"
                if index % 2 else "calendar_native_sporting_week.v1"
            ),
            "index": index, "rallies": "R" * (3000 + 60 * index),
            "world": {"a": "Žluťoučký", "b": "🏆", "i": index},
        }
        for index in range(count)
    ]


def db():
    result = sqlite3.connect(":memory:")
    ev.create_schema(result)
    return result


def add(connection, num, history, previous=None, run=RUN, branch=BRANCH):
    return ev.append(
        connection, run_id=run, branch_id=branch, revision_id=f"rev-{num}",
        independently_verified_source_hash=hashed(f"source {run}/{branch}/{num}"),
        events=history,
        preceding_manifest_revision_id=previous,
    )


def read(connection, num, run=RUN, branch=BRANCH):
    return ev.restore(
        connection, run_id=run, branch_id=branch, revision_id=f"rev-{num}",
        independently_verified_source_hash=hashed(f"source {run}/{branch}/{num}"),
    )


def test_exact_3_revision_reconstruction_and_unique_node_storage():
    conn = db()
    for number in range(1, 4):
        add(conn, number, rows(number), f"rev-{number - 1}" if number > 1 else None)
        assert read(conn, number) == rows(number)
    info = ev.stats(conn)
    assert info["nodes"] == 3 and info["manifests"] == 3
    original = sum(len(ev._canonical(rows(n)).encode()) for n in range(1, 4))
    assert info["total_payload_bytes"] < original
    assert json.loads(ev._canonical(read(conn, 3))) == rows(3)


def test_idempotent_unchanged_event_list_adds_no_new_nodes():
    conn = db()
    add(conn, 1, rows(2))
    add(conn, 2, rows(2), "rev-1")
    assert ev.stats(conn)["nodes"] == 2
    assert read(conn, 2) == rows(2)


@pytest.mark.parametrize("tamper", ["rewrite", "delete", "noncanonical"])
def test_actual_event_node_physical_corruption_fails_closed(tamper):
    conn = db()
    add(conn, 1, rows())
    digest = hashed(ev._canonical(rows()[0]))
    if tamper == "rewrite":
        conn.execute(
            "UPDATE experimental_sporting_event_nodes SET canonical_event_json=? "
            "WHERE event_sha256=?", (ev._canonical({**rows()[0], "index": -9}), digest)
        )
    elif tamper == "delete":
        conn.execute("DELETE FROM experimental_sporting_event_nodes WHERE event_sha256=?", (digest,))
    else:
        conn.execute(
            "UPDATE experimental_sporting_event_nodes SET canonical_event_json=? "
            "WHERE event_sha256=?", (ev._canonical(rows()[0]) + " ", digest)
        )
    with pytest.raises(ev.SportingEventStoreError):
        read(conn, 1)


def test_physical_manifest_rewrite_is_not_accepted():
    conn = db()
    add(conn, 1, rows(2))
    conn.execute(
        "UPDATE experimental_sporting_event_manifests SET manifest_json=? "
        "WHERE revision_id='rev-1'", ('{"forged":"manifest"}',)
    )
    with pytest.raises(ev.SportingEventStoreError):
        read(conn, 1)


def test_refuses_changes_to_preexisting_events_in_a_later_snapshot():
    conn = db()
    add(conn, 1, rows(3))
    changed = rows(4)
    changed[0]["rallies"] = "forged revision"
    with pytest.raises(ev.SportingEventStoreError, match="Non-append-only"):
        add(conn, 2, changed, "rev-1")
    assert ev.stats(conn)["manifests"] == 1
    assert ev.stats(conn)["nodes"] == 3


def test_refuses_deletion_and_reordering_of_historical_events():
    conn = db()
    add(conn, 1, rows(3))
    for forged in (rows(2), list(reversed(rows(3))), rows(3)[1:] + rows(3)[:1]):
        with pytest.raises(ev.SportingEventStoreError, match="Non-append-only"):
            add(conn, 2, forged, "rev-1")
    assert ev.stats(conn)["manifests"] == 1


def test_owner_isolation_and_cross_branch_replay_are_rejected():
    conn = db()
    add(conn, 1, rows(1))
    with pytest.raises(ev.SportingEventStoreError):
        read(conn, 1, run="foreign")
    with pytest.raises(ev.SportingEventStoreError):
        read(conn, 1, branch="foreign")
    with pytest.raises(ev.SportingEventStoreError):
        add(conn, 2, rows(2), "rev-1", run="foreign")
    add(conn, 1, rows(1), run="foreign")
    assert ev.stats(conn)["nodes"] == 2  # no cross-Run node sharing


def test_independently_verified_source_hash_must_bind_manifest():
    conn = db()
    add(conn, 1, rows(2))
    with pytest.raises(ev.SportingEventStoreError, match="source binding"):
        ev.restore(
            conn, run_id=RUN, branch_id=BRANCH, revision_id="rev-1",
            independently_verified_source_hash=hashed("different actual signed Saved"),
        )


def test_ancestor_manifest_is_reattested_after_later_save():
    conn = db()
    add(conn, 1, rows(1))
    add(conn, 2, rows(2), "rev-1")
    assert read(conn, 2) == rows(2)
    conn.execute(
        "UPDATE experimental_sporting_event_manifests SET manifest_json='{}' "
        "WHERE revision_id='rev-1'"
    )
    with pytest.raises(ev.SportingEventStoreError):
        read(conn, 2)


def test_savepoint_within_outer_transaction_is_rollback_safe():
    conn = db()
    conn.execute("BEGIN")
    add(conn, 1, rows(2))
    assert ev.stats(conn)["nodes"] == 2
    conn.rollback()
    assert ev.stats(conn) == {
        "nodes": 0, "node_bytes": 0, "manifests": 0,
        "manifest_bytes": 0, "total_payload_bytes": 0,
    }


def test_internal_sqlite_insert_failure_rollback_keeps_no_orphan_nodes():
    conn = db()
    conn.execute("""
        CREATE TRIGGER deny_manifest BEFORE INSERT
        ON experimental_sporting_event_manifests
        BEGIN SELECT RAISE(ABORT,'injected manifest failure'); END
    """)
    with pytest.raises(sqlite3.DatabaseError):
        add(conn, 1, rows(2))
    assert ev.stats(conn)["nodes"] == ev.stats(conn)["manifests"] == 0


def test_duplicate_revision_cannot_be_overwritten_or_resigned():
    conn = db()
    add(conn, 1, rows(2))
    baseline = ev.stats(conn)
    with pytest.raises(ev.SportingEventStoreError, match="Duplicate"):
        add(conn, 1, rows(2))
    assert ev.stats(conn) == baseline
    assert read(conn, 1) == rows(2)
