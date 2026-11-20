"""Fast production HTTP/SQLite proof of atomic configured Tour Save validation.

Unlike the full two-Edition acceptance this test keeps a tiny 8-player opening
world so every code change gets feedback without 25-minute historical replay.
"""

import pytest
from sqlalchemy import event

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def test_native_tour_save_validates_once_before_commit_and_rolls_back_on_error(
    tmp_path, monkeypatch,
):
    from beta_engine.infrastructure.db import repositories as storage

    database_url = f"sqlite:///{tmp_path / 'tour-atomic-save.db'}"
    with ApiServer(database_url=database_url) as server:
        repo, last_saved = setup(
            server, RunCalendar(52, 35, 2030, 3), initialize=False
        )
        initial_view = inspect(server)
        execute(server, command(initial_view, "initialize", name="quick-initialize"))
        dirty = inspect(server)
        assert not dirty["saved"]
        assert dirty["saved_head_revision_id"] == last_saved["revision_id"]

        # Deliberately break the ONE final snapshot verification, without
        # touching signed history, to prove validation still occurs before
        # the database transaction commits its new head and audit event.
        def reject_final_source(*_args, **_kwargs):
            raise ValueError("controlled Saved sporting validation failure")

        with monkeypatch.context() as patch:
            patch.setattr(storage, "load_saved_calendar_sources", reject_final_source)
            status, response = _request(
                "POST",
                tour_url(server) + "/save",
                {
                    "expected_draft_version": dirty["draft_version"],
                    "expected_calendar_tour_fingerprint": dirty["tour_fingerprint"],
                },
            )
        assert status == 409, response
        assert repo.get_branch_revision_state(branch_id="branch").saved_head_revision_id == dirty["saved_head_revision_id"]
        after_rollback = inspect(server)
        assert after_rollback["tour_fingerprint"] == dirty["tour_fingerprint"]
        assert not after_rollback["saved"]

        # Successful Save performs exactly one complete fold of the final
        # snapshot. A separate public history read still authenticates every
        # immutable sporting component independently after commit.
        called = []
        original = storage.load_saved_calendar_sources

        def count_final_source(*args, **kwargs):
            called.append(True)
            return original(*args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(storage, "load_saved_calendar_sources", count_final_source)
            receipt = save_tour(server)
        assert len(called) == 1
        stored = repo.get_branch_saved_revision(revision_id=receipt["revision_id"])
        assert stored is not None
        assert stored.content_hash == receipt["content_hash"]
        assert stored.payload["content"]["calendar_tour_authority"]["fingerprint"] == dirty["tour_fingerprint"]


def test_native_tour_save_rejects_flushed_bytes_that_differ_from_canonical_payload(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "v1")
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'tour-bytes.db'}") as server:
        repo, initial = setup(server, RunCalendar(52, 35, 2030, 3), initialize=False)
        execute(server, command(inspect(server), "initialize", name="check-exact-save-bytes"))
        dirty = inspect(server)
        touched = []

        def rewrite_equivalent_json(connection, _cursor, statement, _params, _context, _many):
            if statement.startswith("INSERT INTO branch_saved_revisions "):
                changed = connection.exec_driver_sql(
                    "UPDATE branch_saved_revisions SET payload_json = ' ' || payload_json "
                    "WHERE run_id = 'run' AND branch_id = 'branch' AND parent_revision_id = ?",
                    (initial["revision_id"],),
                )
                touched.append(changed.rowcount)

        event.listen(repo._engine, "after_cursor_execute", rewrite_equivalent_json)
        try:
            code, answer = _request("POST", tour_url(server) + "/save", {
                "expected_draft_version": dirty["draft_version"],
                "expected_calendar_tour_fingerprint": dirty["tour_fingerprint"],
            })
        finally:
            event.remove(repo._engine, "after_cursor_execute", rewrite_equivalent_json)
        assert touched == [1]
        assert code == 409 and "inconsistent immutable revision bytes" in str(answer)
        assert inspect(server)["saved_head_revision_id"] == initial["revision_id"]
        assert not inspect(server)["saved"]
        assert save_tour(server)["revision_id"] != initial["revision_id"]


def test_native_tour_save_reuses_the_drafts_physical_history(tmp_path, monkeypatch):
    from beta_engine.infrastructure.db import native_fork_runtime_state as proof

    monkeypatch.setenv("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "saved_v2")
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'tour-save-history.db'}") as server:
        repo, _ = setup(server, RunCalendar(52, 35, 2030, 3))
        view = inspect(server)
        week = view["state"]["week"]
        execute(server, command(view, "create-edition", name="global-edition", data={
            "schema_version": "calendar_tournament_edition.v2",
            "simulation_seed": 891,
            "edition_id": "global-edition",
            "name": "Global Edition",
            "week": {**week, "week": 4},
            "announcement_week": {**week, "week": 3},
            "start_slot": 1,
            "main_entrant_count": 4,
            "ranked": True,
            "validity_weeks": 52,
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
        }))
        save_tour(server)
        execute(server, command(inspect(server), "transition", name="transition-for-save"))
        view = inspect(server)
        draft_checked = False
        installing_head = False
        old_graph_reads = []
        install_rebuilds = []
        original_draft = repo._viewer_branch_working_draft_in_session
        original_signature = proof.actual_dependency_signature
        original_install = proof.install_verified_global_save_head

        def working_draft(**kwargs):
            nonlocal draft_checked
            result = original_draft(**kwargs)
            if kwargs.get("include_revision_state"):
                draft_checked = True
            return result

        def dependency_signature(session, revision, **kwargs):
            if installing_head:
                install_rebuilds.append(revision.revision_id)
            if not draft_checked or revision.revision_id != view["saved_head_revision_id"]:
                return original_signature(session, revision, **kwargs)
            connection = session.connection()
            reads = []

            def count_reads(_conn, _cursor, statement, _params, _context, _many):
                if statement.lstrip().upper().startswith("SELECT"):
                    reads.append(statement)

            event.listen(connection, "before_cursor_execute", count_reads)
            try:
                return original_signature(session, revision, **kwargs)
            finally:
                event.remove(connection, "before_cursor_execute", count_reads)
                old_graph_reads.append(reads)

        def install_head(*args, **kwargs):
            nonlocal installing_head
            installing_head = True
            try:
                return original_install(*args, **kwargs)
            finally:
                installing_head = False

        monkeypatch.setattr(repo, "_viewer_branch_working_draft_in_session", working_draft)
        monkeypatch.setattr(proof, "actual_dependency_signature", dependency_signature)
        monkeypatch.setattr(proof, "install_verified_global_save_head", install_head)
        body = {
            "expected_draft_version": view["draft_version"],
            "expected_calendar_tour_fingerprint": view["tour_fingerprint"],
        }

        # A late database write can still damage the actual draft independently
        # of the stored graph. The receipt gate must detect it before commit.
        def damage_flushed_draft(connection, _cursor, statement, _params, _context, _many):
            if statement.startswith("UPDATE run_branches SET saved_head_revision_id"):
                connection.exec_driver_sql(
                    "UPDATE branch_working_drafts SET change_count=1 WHERE branch_id='branch'"
                )

        event.listen(repo._engine, "after_cursor_execute", damage_flushed_draft)
        try:
            code, rejected = _request("POST", tour_url(server) + "/save", body)
        finally:
            event.remove(repo._engine, "after_cursor_execute", damage_flushed_draft)
        assert code == 409, rejected
        assert len(install_rebuilds) == 1
        after_rollback = inspect(server)
        assert after_rollback["saved_head_revision_id"] == view["saved_head_revision_id"]
        assert after_rollback["tour_fingerprint"] == view["tour_fingerprint"]
        assert not after_rollback["saved"]
        # The successful request must consistently report its own flushed draft.
        draft_checked = False
        old_graph_reads.clear()
        install_rebuilds.clear()
        code, receipt = _request("POST", tour_url(server) + "/save", body)
        assert code == 201, receipt
        assert receipt["working_draft"]["base_saved_revision_id"] == receipt["saved_revision"]["revision_id"]
        assert receipt["working_draft"]["draft_version"] == view["draft_version"] + 1
        assert receipt["working_draft"]["status"] == "clean"
        # The first old-HEAD graph check after draft validation reuses the
        # same actual rows. Later reads can still follow newly written state.
        assert old_graph_reads and old_graph_reads[0] == []
        assert not install_rebuilds
