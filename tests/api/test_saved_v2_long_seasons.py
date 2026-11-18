"""Two real closed seasons on an explicitly opted-in Saved v2 Run: Save, restart, Restore.

Runs the unchanged wide two-season acceptance scenario of
``test_native_season_archive_wide.py`` (every week and both Season Transitions over
HTTP/SQLite, real MatchEngine matches, an explicit Save after every operation,
archive and comparison reads, explicit horizon extension, cold restart) with
``BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2``. It then checks that the Run really
is stored as v2, restores an earlier Saved Revision, Saves a further Week
Transition on the restored state, and requires a cold restart to read exactly the
same inspection and history.

W6 is the fast variant; W52/W61/W80 are ``long_season`` (dedicated CI jobs).
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from beta_engine.infrastructure.db.saved_v2_hooks import ENVIRONMENT_VARIABLE
from beta_engine.infrastructure.db.saved_v2_store import ENVELOPE_PREFIX, FORMAT, sha256_hex
from tests.api import test_native_season_archive_wide as wide
from tests.api.test_calendar_population_sporting_checkpoint import restore
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke

def _lineage(path):
    """Branch lineage metadata (oldest first) read directly from SQLite.

    Only selects a Restore target and compares identities; product reads are
    exercised through the HTTP inspection. (A full validated history read of a
    two-season W61 Run costs ~160 s and ~10 GiB for v1 and v2 alike, measured;
    that pre-existing read cost is not part of this storage check.)
    """
    with sqlite3.connect(path) as connection:
        head = connection.execute(
            "SELECT saved_head_revision_id FROM run_branches WHERE branch_id='branch'").fetchone()[0]
        rows = {rid: (rid, seq, parent, digest) for rid, seq, parent, digest in connection.execute(
            "SELECT revision_id, sequence, parent_revision_id, content_hash FROM branch_saved_revisions "
            "WHERE run_id='run'")}
    lineage, current = [], head
    while current is not None:
        lineage.append(rows[current])
        current = rows[current][2]
    return lineage[::-1]


def _assert_v2_storage(path):
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT run_id, storage_format FROM run_saved_storage_formats").fetchall() \
            == [("run", FORMAT)]
        rows = connection.execute("SELECT payload_json FROM branch_saved_revisions WHERE run_id='run'").fetchall()
        assert len(rows) > 20 and all(text.startswith(ENVELOPE_PREFIX) for (text,) in rows)
        nodes = connection.execute("SELECT digest, body FROM saved_revision_nodes WHERE run_id='run'").fetchall()
        assert nodes and all(sha256_hex(body) == digest for digest, body in nodes)
        return len(rows), sum(len(body) for _, body in nodes)


def _in_fresh_process(target, *args):
    """Run one phase in a NEW interpreter (a real restart; also keeps the
    in-process growth of repeated server lifetimes, which v1 shows as well,
    out of the measured phases)."""
    import multiprocessing

    queue = multiprocessing.get_context("spawn").Queue()
    child = multiprocessing.get_context("spawn").Process(target=_phase, args=(queue, target, *args))
    child.start()
    result = queue.get()
    child.join()
    assert child.exitcode == 0 and result[0] == "ok", result
    return result[1]


def _phase(queue, target, *args):
    import os
    import traceback

    os.environ[ENVIRONMENT_VARIABLE] = "saved_v2"
    try:
        queue.put(("ok", globals()[target](*args)))
    except BaseException:  # reported to the parent, which fails the test
        queue.put(("error", traceback.format_exc()))


def _scenario(directory, width):
    from pathlib import Path

    # Unchanged acceptance scenario: all Saves, archive/comparison, extension, restart.
    wide.test_two_closed_seasons_archive_compare_extend_and_restart(Path(directory), width)


def _restore_and_save(path, target):
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repository = server.app.state.runtime.repository
        target_payload = repository.get_branch_saved_revision(revision_id=target).payload
        restored = restore(server, target)
        content = restored["payload"]["content"]
        for key in ("calendar_player_sporting_checkpoint", "calendar_tour_authority"):
            assert content[key] == target_payload["content"][key], key
        view = inspect(server)
        assert view["saved"] and view["saved_head_revision_id"] == restored["revision_id"]
        execute(server, command(view, "transition", name="after-v2-restore"))
        save_tour(server)
        final = inspect(server)
        assert final["saved"]
        return json.dumps(final, sort_keys=True)


def _restarted_inspection(path):
    with ApiServer(database_url=f"sqlite:///{path}") as restarted:
        return json.dumps(inspect(restarted), sort_keys=True)


@pytest.mark.parametrize("width", [
    pytest.param(6, id="w6"),
    pytest.param(52, id="w52", marks=pytest.mark.long_season),
    pytest.param(61, id="w61", marks=pytest.mark.long_season),
    pytest.param(80, id="w80", marks=pytest.mark.long_season),
])
def test_saved_v2_two_closed_seasons_save_restart_restore(tmp_path, width):
    _in_fresh_process("_scenario", str(tmp_path), width)
    path = tmp_path / "wide-archive.sqlite"
    revisions, node_bytes = _assert_v2_storage(path)
    lineage = _lineage(path)
    assert len(lineage) == revisions
    # lineage[-1] is the extension, [-2] the second Season Transition, [-3] the
    # transition to Week W and [-4] the transition to Week W-1 of the second
    # season (its Editions are terminal, so a Week Transition is legal).
    final = _in_fresh_process("_restore_and_save", str(path), lineage[-4][0])
    final_lineage = _lineage(path)
    assert final_lineage[-1][0] == json.loads(final)["saved_head_revision_id"]
    assert [r[0] for r in final_lineage[:-2]] == [r[0] for r in lineage]
    assert _in_fresh_process("_restarted_inspection", str(path)) == final
    assert _lineage(path) == final_lineage
    after, _ = _assert_v2_storage(path)
    assert after == revisions + 2
    print(json.dumps({"width": width, "revisions": after, "node_body_bytes": node_bytes,
                      "sqlite_bytes": path.stat().st_size}))
