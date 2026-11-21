"""Bounded cold validation of a Saved v2 native global-slot lineage; real SQLite.

A cold Tour read validates every historical Saved Revision. It used to keep the
complete text of every revision alive for the whole request (the snapshot read
cache, the retained ORM rows, the digest memo and the operation's canonical
proofs), so peak memory grew with the square of the revision count. Each
historical text is now released after that revision's own validation and read
again from the same SQLite snapshot whenever a later gate needs it.

Nothing is mocked. Observers only count live strings or disable the release to
obtain the unbounded reference result. Tampering edits stored node bytes
directly in SQLite (after dropping the insert-only trigger, as a tamperer would).
"""

import gc
import json
import sqlite3
import sys

import pytest

from beta_engine.api.deps import build_runtime
from beta_engine.application.calendar_tour_service import CalendarTourService
from beta_engine.infrastructure.db import native_fork_runtime_state as runtime_state
from beta_engine.infrastructure.db import repositories
from beta_engine.infrastructure.db import saved_v2_store as st
from tests.api.test_calendar_global_slots import copy_database

pytestmark = pytest.mark.smoke


def cold(tmp_path, source, name):
    """A copy of the prepared Run opened by a fresh repository and cold digests."""
    path = tmp_path / name
    copy_database(source, path)
    st.TEXT_DIGESTS.clear()
    return path, build_runtime(database_url=f"sqlite:///{path}").repository


def read(repository):
    return CalendarTourService(repository).inspect(run_id="run", branch_id="branch")


def dump(value):
    return json.dumps(value, sort_keys=True, default=str)


def lineage(path):
    """(revision_id, logical chars, root digest) of the Branch lineage, oldest first."""
    with sqlite3.connect(path) as connection:
        head = connection.execute(
            "SELECT saved_head_revision_id FROM run_branches WHERE branch_id='branch'").fetchone()[0]
        rows = {rid: (parent, stored) for rid, parent, stored in connection.execute(
            "SELECT revision_id, parent_revision_id, payload_json FROM branch_saved_revisions "
            "WHERE run_id='run'")}
    result, current = [], head
    while current is not None:
        parent, stored = rows[current]
        root, chars = st.parse_envelope(stored, run_id="run")
        result.append((current, chars, root))
        current = parent
    return result[::-1]


LARGE = 64 * 1024  # smaller strings of an equal length occur by coincidence


def live_strings_of_lengths(lengths):
    """Every live ``str`` whose length is in ``lengths`` (gc referents and frames).

    Excludes only the process-wide canonical proof cache, which by construction
    holds at most ``MAX_REFERENCES`` texts and ``MAX_REFERENCE_CHARACTERS`` in
    total (none of a W9-sized history), independent of the revision count.
    """
    from beta_engine.infrastructure.db import canonical_text

    lengths = {length for length in lengths if length >= LARGE}
    bounded = {id(proof.text) for _scope, proof in canonical_text.PROOFS._entries}
    found = {}
    holders = gc.get_objects()
    for frame in sys._current_frames().values():
        while frame is not None:
            holders.append(frame)
            frame = frame.f_back
    try:
        for holder in holders:
            for value in gc.get_referents(holder):
                if type(value) is str and len(value) in lengths and id(value) not in bounded:
                    found[id(value)] = len(value)
    finally:
        # This frame is in ``holders``: break the cycle explicitly, the read
        # under test pauses the cyclic collector.
        holders.clear()
    return found


def test_saved_v2_fixture_is_a_long_native_lineage(prepared_slots_v2):
    rows = lineage(prepared_slots_v2)
    assert len(rows) >= 12
    assert sum(chars >= LARGE for _rid, chars, _root in rows) >= 8
    with sqlite3.connect(prepared_slots_v2) as connection:
        assert connection.execute("SELECT storage_format FROM run_saved_storage_formats "
                                  "WHERE run_id='run'").fetchone()[0] == st.FORMAT


def test_cold_v2_read_holds_one_historical_text_at_a_time_and_is_unchanged(
        tmp_path, prepared_slots_v2, monkeypatch):
    rows = lineage(prepared_slots_v2)
    head_chars = rows[-1][1]
    released, alive = [], []
    original = runtime_state.release_snapshot_saved_text

    def observed(session, run_id, revision_id):
        count = original(session, run_id, revision_id)
        released.append((revision_id, count))
        # Historical texts other than the most recent two (the proof scope's
        # newest reference and the one-step shared decode) and HEAD.
        recent = {revision_id}
        index = next(i for i, row in enumerate(rows) if row[0] == revision_id)
        recent.update(row[0] for row in rows[max(index - 1, 0):index + 2])
        older = {row[1] for row in rows[:-1] if row[0] not in recent} - {head_chars} - {
            row[1] for row in rows if row[0] in recent}
        alive.append((revision_id, len(live_strings_of_lengths(older)) if older else 0))
        return count

    with monkeypatch.context() as patch:
        patch.setattr(runtime_state, "release_snapshot_saved_text", lambda *args: 0)
        _path, unbounded = cold(tmp_path, prepared_slots_v2, "unbounded.db")
        expected = dump(read(unbounded))
    walked = []
    walk = repositories.SimulationPersistenceRepository._validated_branch_revision_lineage_core_in_session

    def observed_walk(self, **kwargs):
        result = walk(self, **kwargs)
        # Still inside the read snapshot: the complete validated lineage holds
        # no historical text (HEAD's payload is the one the reader returns).
        walked.append(len(live_strings_of_lengths({row[1] for row in rows[:-1]} - {head_chars})))
        return result

    monkeypatch.setattr(runtime_state, "release_snapshot_saved_text", observed)
    monkeypatch.setattr(repositories.SimulationPersistenceRepository,
                        "_validated_branch_revision_lineage_core_in_session", observed_walk)
    _path, repository = cold(tmp_path, prepared_slots_v2, "bounded.db")
    view = read(repository)
    assert dump(view) == expected
    assert walked and max(walked) == 0, walked
    # Every historical revision was released after its validation; a released
    # row really dropped its cached text references.
    historical = {row[0] for row in rows[:-1]}
    assert historical <= {revision_id for revision_id, count in released if count > 0}
    # No other historical text was alive at any release point.
    assert alive and max(count for _rid, count in alive) == 0, alive
    # A warm read in the same process returns exactly the same inspection.
    assert dump(read(repository)) == expected


def test_released_text_is_read_again_from_the_same_snapshot(tmp_path, prepared_slots_v2):
    from sqlalchemy import text

    from beta_engine.infrastructure.db.exact_text_digest import row_text_sha256, unloaded_column
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

    rows = lineage(prepared_slots_v2)
    path, repository = cold(tmp_path, prepared_slots_v2, "reread.db")
    revision_id = rows[-3][0]
    with repository._session_factory() as session, runtime_state.native_read_proof_scope():
        session.execute(text("BEGIN"))
        model = runtime_state.retain_saved_model(session, session.get(BranchSavedRevisionModel, revision_id))
        original_text = model.payload_json
        original_digest = row_text_sha256(model, "payload_json")
        assert runtime_state.release_snapshot_saved_text(session, "run", revision_id) > 0
        assert unloaded_column(model, "payload_json")
        # The digest is bound to the actual envelope and re-hashed nodes, and the
        # characters are the actual stored text again.
        assert row_text_sha256(model, "payload_json") == original_digest
        assert model.payload_json == original_text
        del original_text
    # A v1 Run, an unknown row and a row without a cached text are untouched.
    with repository._session_factory() as session, runtime_state.native_read_proof_scope():
        session.execute(text("BEGIN"))
        assert runtime_state.release_snapshot_saved_text(session, "run", "missing-revision") == 0
        assert runtime_state.release_snapshot_saved_text(session, "run", rows[0][0]) == 0


def _damage_node(path, root):
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER IF EXISTS saved_revision_nodes_no_update")
        changed = connection.execute(
            "UPDATE saved_revision_nodes SET body = body || ' ' WHERE run_id='run' AND digest=?",
            (root,)).rowcount
    assert changed == 1


@pytest.mark.parametrize("when", ["cold", "after_successful_read"])
@pytest.mark.parametrize("which", ["oldest", "middle"])
def test_damaged_v2_ancestor_fails_closed(tmp_path, prepared_slots_v2, when, which):
    rows = lineage(prepared_slots_v2)
    target = rows[1] if which == "oldest" else rows[len(rows) // 2]
    path, repository = cold(tmp_path, prepared_slots_v2, f"{when}-{which}.db")
    if when == "after_successful_read":
        read(repository)
    _damage_node(path, target[2])
    with pytest.raises((ValueError, KeyError, TypeError)):
        read(repository)
    # A fresh process (no proof or digest memo) rejects it as well.
    st.TEXT_DIGESTS.clear()
    with pytest.raises((ValueError, KeyError, TypeError)):
        read(build_runtime(database_url=f"sqlite:///{path}").repository)


def test_cold_v2_restore_save_and_fork_keep_history_and_bounded_reads(tmp_path, prepared_slots_v2):
    from tests.api.test_calendar_population_sporting_checkpoint import restore
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
    from tests.api.test_native_fork_public_continuation import fork
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    rows = lineage(prepared_slots_v2)
    path = tmp_path / "restore-fork.db"
    copy_database(prepared_slots_v2, path)
    with sqlite3.connect(path) as connection:
        before = connection.execute(
            "SELECT revision_id, content_hash, payload_json FROM branch_saved_revisions "
            "ORDER BY sequence").fetchall()
    st.TEXT_DIGESTS.clear()
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        cold_view = inspect(server)
        assert cold_view["saved"]
        # Restore an older Saved Revision (both results confirmed, before the
        # last two Week Transitions), continue on it and Save explicitly.
        target = rows[-3][0]
        restored = restore(server, target)
        execute(server, command(inspect(server), "transition", name="bounded-after-restore"))
        saved = save_tour(server)
        continued = inspect(server)
        assert continued["saved"] and continued["saved_head_revision_id"] == saved["revision_id"]
        # Fork an independent Branch from a historical Saved point.
        created = fork(server, rows[len(rows) - 2][0], name="bounded-fork")
        assert created["branch_id"] != "branch"
        assert _request("GET", server.base_url + "/admin/runs/run/branches/branch/calendar-tour")[1] == continued
    # Immutable history: every earlier row is byte-identical.
    with sqlite3.connect(path) as connection:
        after = {row[0]: row for row in connection.execute(
            "SELECT revision_id, content_hash, payload_json FROM branch_saved_revisions")}
    assert all(after[row[0]] == row for row in before)
    assert restored["revision_id"] in after
    # A real restart reads exactly the same continued state.
    st.TEXT_DIGESTS.clear()
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert inspect(server) == continued
