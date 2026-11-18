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
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

HISTORY = "/run-containers/run/branches/branch/saved-revisions"


def _history(server):
    code, body = _request("GET", server.base_url + HISTORY)
    assert code == 200, body

    def strip(value):
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k != "created_at"}
        if isinstance(value, list):
            return [strip(v) for v in value]
        return value
    return strip(body)


def _assert_v2_storage(path):
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT run_id, storage_format FROM run_saved_storage_formats").fetchall() \
            == [("run", FORMAT)]
        rows = connection.execute("SELECT payload_json FROM branch_saved_revisions WHERE run_id='run'").fetchall()
        assert len(rows) > 20 and all(text.startswith(ENVELOPE_PREFIX) for (text,) in rows)
        nodes = connection.execute("SELECT digest, body FROM saved_revision_nodes WHERE run_id='run'").fetchall()
        assert nodes and all(sha256_hex(body) == digest for digest, body in nodes)
        return len(rows), sum(len(body) for _, body in nodes)


@pytest.mark.parametrize("width", [
    pytest.param(6, id="w6"),
    pytest.param(52, id="w52", marks=pytest.mark.long_season),
    pytest.param(61, id="w61", marks=pytest.mark.long_season),
    pytest.param(80, id="w80", marks=pytest.mark.long_season),
])
def test_saved_v2_two_closed_seasons_save_restart_restore(tmp_path, width, monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, "saved_v2")
    # Unchanged acceptance scenario: all Saves, archive/comparison, extension, restart.
    wide.test_two_closed_seasons_archive_compare_extend_and_restart(tmp_path, width)
    path = tmp_path / "wide-archive.sqlite"
    revisions, node_bytes = _assert_v2_storage(path)
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        lineage = _history(server)["saved_revisions"]
        assert len(lineage) == revisions
        # A Week Transition revision of the second season, well before its end.
        target = lineage[-8]
        repository = server.app.state.runtime.repository
        target_payload = repository.get_branch_saved_revision(revision_id=target["revision_id"]).payload
        restored = restore(server, target["revision_id"])
        content = restored["payload"]["content"]
        for key in ("calendar_player_sporting_checkpoint", "calendar_tour_authority"):
            assert content[key] == target_payload["content"][key], key
        view = inspect(server)
        assert view["saved"] and view["saved_head_revision_id"] == restored["revision_id"]
        execute(server, command(view, "transition", name="after-v2-restore"))
        save_tour(server)
        final = inspect(server)
        assert final["saved"]
        final_history = _history(server)
    with ApiServer(database_url=db) as restarted:
        assert inspect(restarted) == final
        assert _history(restarted) == final_history
    after, _ = _assert_v2_storage(path)
    assert after == revisions + 2
    print(json.dumps({"width": width, "revisions": after, "node_body_bytes": node_bytes,
                      "sqlite_bytes": path.stat().st_size}))
