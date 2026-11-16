"""A/B original vs reduced append copy through actual native v2 SQLite services.

One real HTTP-generated fork is snapshotted before its dirty Save. All variants
start with identical validated database bytes. No Saved rows are hand-authored.
The timing is intentionally exploratory: a tiny fork is not a long-season Run.
"""

import json
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from statistics import median
from time import perf_counter

import pytest
from sqlalchemy import event

from beta_engine.application import native_fork_runtime_service as writer
from beta_engine.application.native_fork_runtime_service import NativeForkRuntimeService
from beta_engine.application.native_fork_runtime_reducer import source_inputs
from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_native_fork_public_continuation import Tour, fork
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.pr_critical


def _backup(source, destination):
    """Use a consistent SQLite backup, never a potentially live file copy."""
    with sqlite3.connect(source) as original, sqlite3.connect(destination) as copy:
        original.backup(copy)


def _stored(path, revision_id):
    with sqlite3.connect(path) as db:
        row = db.execute(
            """SELECT revision_id, run_id, branch_id, sequence,
                      parent_revision_id, kind, payload_schema_version,
                      payload_json, content_hash, change_summary_json
                 FROM branch_saved_revisions WHERE revision_id = ?""",
            (revision_id,),
        ).fetchone()
    assert row is not None
    return row


@contextmanager
def _late_audit_failure(engine):
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO branch_revision_audit_events"):
            raise RuntimeError("controlled append audit rollback")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        yield
    finally:
        event.remove(engine, "before_cursor_execute", fail)


def _history(repository, branch_id):
    history = repository.get_branch_saved_revision_history(
        run_id="run", branch_id=branch_id
    )
    return (
        history.saved_head_revision_id,
        tuple(
            (
                item.revision_id,
                item.parent_revision_id,
                item.sequence,
                item.run_id,
                item.branch_id,
                item.content_hash,
            )
            for item in history.saved_revisions
        ),
    )


def _exercise_database(path, branch_id, root_id, original_id, *, baseline, rollback):
    """Real production Save -> signed read -> Restore -> replay, with copy timed."""
    original_copy = writer._copy_append_payload_without_replaced_runtime
    action = deepcopy if baseline else original_copy
    copy_durations = []

    def measured_copy(source):
        start = perf_counter()
        value = action(source)
        copy_durations.append(perf_counter() - start)
        return value

    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repository = server.app.state.runtime.repository
        tour = Tour(server, branch_id)
        view = tour.view()
        assert not view["saved"]
        service = NativeForkRuntimeService(repository)
        original_before = _stored(path, original_id)
        root_before = _stored(path, root_id)
        before_save = _dump(path)

        with pytest.MonkeyPatch.context() as patch:
            # Patch only the copy strategy, not the SQLite writer, validation,
            # hash implementation, runtime serializer or sporting algorithm.
            patch.setattr(writer, "_copy_append_payload_without_replaced_runtime", measured_copy)
            params = dict(
                run_id="run",
                branch_id=branch_id,
                expected_draft_version=view["draft_version"],
                expected_calendar_tour_fingerprint=view["tour_fingerprint"],
                revision_id="ab-native-save",
                audit_event_id="ab-native-save-audit",
            )
            if rollback:
                with _late_audit_failure(repository._engine):
                    with pytest.raises(RuntimeError, match="controlled append audit rollback"):
                        repository.save_viewer_branch_selection_atomically(**params)
                assert _dump(path) == before_save
                assert _stored(path, original_id) == original_before
                assert _stored(path, root_id) == root_before

            began = perf_counter()
            saved = repository.save_viewer_branch_selection_atomically(**params)
            save_seconds = perf_counter() - began
            assert len(copy_durations) == (2 if rollback else 1)
            save_copy_seconds = copy_durations[-1]
            assert saved.saved_revision.revision_id == "ab-native-save"
            assert saved.saved_revision.run_id == "run"
            assert saved.saved_revision.branch_id == branch_id
            assert repository.verify_branch_saved_revision_hash(revision_id="ab-native-save")
            saved_row = _stored(path, "ab-native-save")
            saved_history = _history(repository, branch_id)
            assert saved_row[3] == root_before[3] + 1
            assert saved_row[4] == root_id
            assert saved_row[1:3] == ("run", branch_id)
            assert json.loads(saved_row[7])["content"][writer.KEY]
            assert tour.view()["saved"]

            preflight = service.preview_restore(
                run_id="run", branch_id=branch_id,
                target_saved_revision_id=root_id,
            )
            assert preflight.can_restore, preflight.blockers
            restore_params = dict(
                run_id="run",
                branch_id=branch_id,
                target_saved_revision_id=root_id,
                expected_head_saved_revision_id=preflight.saved_head_revision_id,
                expected_draft_version=preflight.draft_version,
                expected_current_viewer_branch_id=preflight.current_viewer_branch_id,
                checkpoint_id="ab-native-checkpoint",
                restore_saved_revision_id="ab-native-restore",
                audit_event_id="ab-native-restore-audit",
            )
            if rollback:
                before_restore = _dump(path)
                with _late_audit_failure(repository._engine):
                    with pytest.raises(RuntimeError, match="controlled append audit rollback"):
                        service.restore(**restore_params)
                assert _dump(path) == before_restore
                assert _stored(path, "ab-native-save") == saved_row

            began = perf_counter()
            restored = service.restore(**restore_params)
            restore_seconds = perf_counter() - began
            assert len(copy_durations) == (4 if rollback else 2)
            restore_copy_seconds = copy_durations[-1]
            assert restored.saved_revision.revision_id == "ab-native-restore"
            assert repository.verify_branch_saved_revision_hash(revision_id="ab-native-restore")
            restored_row = _stored(path, "ab-native-restore")
            restored_history = _history(repository, branch_id)
            assert restored_row[4] == "ab-native-save"
            assert restored_row[3] == saved_row[3] + 1
            assert restored_row[1:3] == ("run", branch_id)
            assert tour.view()["saved"]
            assert tour.view()["state"]["week"]["week"] == 2

            # Replay from the genuine signed opening, not a stub MatchEngine.
            original = repository.get_branch_saved_revision(revision_id=original_id)
            inputs = source_inputs(original)
            assert inputs.opening.matches
            match_id = inputs.opening.matches[0].input_context.match_id
            replay = service.replay(run_id="run", branch_id=branch_id, match_id=match_id)
            assert replay["exact_replay"] and replay["match_id"] == match_id

        # The original and root's physical SQLite rows must never be rewritten.
        assert _stored(path, original_id) == original_before
        assert _stored(path, root_id) == root_before
        assert saved_history[0] == "ab-native-save"
        assert restored_history[0] == "ab-native-restore"
        return {
            "save_row": saved_row,
            "restore_row": restored_row,
            "save_history": saved_history,
            "restore_history": restored_history,
            "save_seconds": save_seconds,
            "save_copy_seconds": save_copy_seconds,
            "restore_seconds": restore_seconds,
            "restore_copy_seconds": restore_copy_seconds,
            "input_payload_bytes": len(root_before[7].encode("utf-8")),
        }


def test_real_native_v2_sqlite_save_restore_rollback_replay_ab_equivalence(tmp_path, capsys):
    clock = RunCalendar(7, 1, 2030, 3)
    seed = tmp_path / "native-fork-before-save.db"
    with ApiServer(database_url=f"sqlite:///{seed}") as server:
        repo, _ = setup(server, clock, 4)
        original = sign_prospects(server, repo, clock)
        created = fork(server, original["revision_id"], name="ab-native-fork")
        branch_id = created["branch_id"]
        root_id = created["saved_head_revision_id"]
        # Exercise a real dirty native-fork v2 runtime (born 15-year-old at W3).
        target = Tour(server, branch_id)
        target.execute("transition", "ab-native-birth")
        assert not target.view()["saved"]
        assert repo.get_branch_saved_revision(revision_id=root_id).payload_schema_version == writer.SAVED_SCHEMA

    variants = []
    # One paired A/B/B/A run controls ordering somewhat. This is still a
    # small input and is not a whole-season performance claim.
    for index, baseline in enumerate((True, False, False, True)):
        path = tmp_path / f"native-fork-variant-{index}.db"
        _backup(seed, path)
        variants.append(_exercise_database(
            path, branch_id, root_id, original["revision_id"],
            baseline=baseline, rollback=(index == 1),
        ))

    for variant in variants[1:]:
        assert variant["save_row"] == variants[0]["save_row"]
        assert variant["restore_row"] == variants[0]["restore_row"]
        assert variant["save_history"] == variants[0]["save_history"]
        assert variant["restore_history"] == variants[0]["restore_history"]

    old = [variants[i] for i in (0, 3)]
    new = [variants[i] for i in (1, 2)]
    stats = {
        "scope": "paired_real_native_v2_SQLite_save_and_restore_small_4_player_fixture",
        "not": "full_season_or_1000_player_measurement",
        "input_payload_bytes": variants[0]["input_payload_bytes"],
        "baseline_save_median_ms": round(1000 * median(x["save_seconds"] for x in old), 2),
        "candidate_save_median_ms": round(1000 * median(x["save_seconds"] for x in new), 2),
        "baseline_copy_median_ms": round(1000 * median(x["save_copy_seconds"] for x in old), 2),
        "candidate_copy_median_ms": round(1000 * median(x["save_copy_seconds"] for x in new), 2),
        "baseline_copy_fraction_of_save": round(median(x["save_copy_seconds"] / x["save_seconds"] for x in old), 4),
        "candidate_copy_fraction_of_save": round(median(x["save_copy_seconds"] / x["save_seconds"] for x in new), 4),
        "stored_json_hashes_and_history_identical": True,
        "rollback_tested": True,
        "source_replay_tested": True,
    }
    with capsys.disabled():
        print("NATIVE_FORK_REAL_SQLITE_AB " + json.dumps(stats, sort_keys=True), flush=True)
