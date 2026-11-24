"""Production HTTP/SQLite: a native Tour Save reuses authenticated v2 text digests,
yet a damaged historical node between requests still rejects the Save atomically.

Real ApiServer, real SQLite file and Saved v2 storage; no API result is mocked.
The only test-side change is a direct SQLite edit of one stored node (after
dropping its insert-only triggers, as a tamperer would).
"""

import sqlite3

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db import saved_v2_store as st
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def _stored(database, sql, *args):
    with sqlite3.connect(database) as connection:
        return connection.execute(sql, args).fetchall()


def test_save_reuses_v2_digests_and_rejects_a_damaged_historical_node(tmp_path, monkeypatch):
    monkeypatch.setenv("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "saved_v2")
    st.TEXT_DIGESTS.clear()
    database = tmp_path / "digest-reuse.db"
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        setup(server, RunCalendar(52, 35, 2030, 3))
        view = inspect(server)
        week = view["state"]["week"]
        execute(server, command(view, "create-edition", name="digest-edition", data={
            "schema_version": "calendar_tournament_edition.v2",
            "simulation_seed": 517, "edition_id": "digest-edition", "name": "Digest Edition",
            "week": {**week, "week": 4}, "announcement_week": {**week, "week": 3},
            "start_slot": 1, "main_entrant_count": 4, "ranked": True, "validity_weeks": 52,
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
        }))
        save_tour(server)

        reused = []
        original = st.stored_text_sha256

        def observed(*args, **kwargs):
            digest = original(*args, **kwargs)
            if digest is not None:
                reused.append(digest)
            return digest

        monkeypatch.setattr(st, "stored_text_sha256", observed)
        execute(server, command(inspect(server), "transition", name="digest-transition"))
        receipt = save_tour(server)
        # The real Save authenticated unchanged history without materializing it again.
        assert reused

        execute(server, command(inspect(server), "transition", name="digest-transition-2"))
        dirty = inspect(server)
        assert not dirty["saved"]
        revisions = _stored(database, "SELECT COUNT(*) FROM branch_saved_revisions")[0][0]
        # Damage the root node of the OLDEST Saved revision only.
        oldest = _stored(database, "SELECT payload_json FROM branch_saved_revisions "
                                   "WHERE run_id='run' ORDER BY sequence LIMIT 1")[0][0]
        root, _chars = st.parse_envelope(oldest, run_id="run")
        with sqlite3.connect(database) as connection:
            connection.execute("DROP TRIGGER IF EXISTS saved_revision_nodes_no_update")
            changed = connection.execute(
                "UPDATE saved_revision_nodes SET body = body || ' ' WHERE run_id='run' AND digest=?",
                (root,)).rowcount
        assert changed == 1
        code, answer = _request("POST", tour_url(server) + "/save", {
            "expected_draft_version": dirty["draft_version"],
            "expected_calendar_tour_fingerprint": dirty["tour_fingerprint"],
        })
        assert code == 409, (code, answer)
        # Atomic rollback: no new row, the HEAD and every node of other rows unchanged.
        assert _stored(database, "SELECT COUNT(*) FROM branch_saved_revisions")[0][0] == revisions
        assert _stored(database, "SELECT saved_head_revision_id FROM run_branches "
                                 "WHERE branch_id='branch'")[0][0] == receipt["revision_id"]
        # Independent readers also fail closed on the damaged history.
        code, _ = _request("GET", tour_url(server))
        assert code != 200


def test_warm_tour_reads_do_not_materialize_every_historical_payload(tmp_path, monkeypatch):
    from sqlalchemy import event

    monkeypatch.setenv("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "saved_v2")
    st.TEXT_DIGESTS.clear()
    database = tmp_path / "deferred-lineage.db"
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        setup(server, RunCalendar(52, 35, 2030, 3))
        for name in ("deferred-1", "deferred-2"):
            execute(server, command(inspect(server), "transition", name=name))
            save_tour(server)
        first = inspect(server)
        revisions = _stored(database, "SELECT COUNT(*) FROM branch_saved_revisions")[0][0]
        engine = server.app.state.runtime.repository._engine
        reads = []

        def count(_connection, _cursor, statement, _params, _context, _many):
            if "saved_v2_payload(" in statement and "branch_saved_revisions" in statement:
                reads.append(statement)

        event.listen(engine, "before_cursor_execute", count)
        try:
            assert inspect(server) == first
        finally:
            event.remove(engine, "before_cursor_execute", count)
        # The ordinary lineage gate still authenticated every revision; it no
        # longer loads every historical text into the ORM to do so.
        assert revisions >= 6
        assert len(reads) < revisions - 2, (len(reads), revisions)
