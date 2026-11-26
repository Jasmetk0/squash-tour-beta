"""Manual Tour Save: live checkpoint copy prepared before the SQLite writer lock.

Real HTTP/SQLite/MatchEngine, no fabricated results. The prepared value is
used only for byte-identical bytes of the same live row inside the writer
transaction; every other case must take the original strict decode and every
Save gate. Compared databases use deterministic Saved/audit IDs.
"""

import json
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from itertools import count
from uuid import NAMESPACE_URL, uuid5

import pytest

from tests.api.test_calendar_global_slots import copy_database, ready
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


@pytest.fixture(scope="module")
def drawn_slots_v2(tmp_path_factory):
    """The ``ready`` global-slot Run with both Draws Saved, stored as Saved v2."""
    from beta_engine.infrastructure.db.saved_v2_hooks import ENVIRONMENT_VARIABLE

    path = tmp_path_factory.mktemp("prepared-save-v2") / "drawn-v2.db"
    previous = os.environ.get(ENVIRONMENT_VARIABLE)
    os.environ[ENVIRONMENT_VARIABLE] = "saved_v2"
    try:
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            ready(server, 52)
    finally:
        if previous is None:
            os.environ.pop(ENVIRONMENT_VARIABLE, None)
        else:
            os.environ[ENVIRONMENT_VARIABLE] = previous
    return path


class _Ids:
    def __init__(self, label):
        self.label, self.sequence = label, count()

    def __call__(self):
        return uuid5(NAMESPACE_URL, f"{self.label}:{next(self.sequence)}")


def _ids(monkeypatch, label):
    from beta_engine.api import deps

    ids = _Ids(label)
    monkeypatch.setattr(deps, "uuid4", ids)
    return ids


def _differences(left, right, path=""):
    if isinstance(left, dict) and isinstance(right, dict):
        return [d for key in sorted(set(left) | set(right))
                for d in _differences(left.get(key), right.get(key), f"{path}.{key}")]
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)) and len(left) == len(right):
        return [d for index, pair in enumerate(zip(left, right))
                for d in _differences(*pair, f"{path}[{index}]")]
    return [] if left == right else [(path, str(left)[:120], str(right)[:120])]


def _without_times(value):
    if isinstance(value, dict):
        return {k: _without_times(v) for k, v in value.items() if k not in {"created_at", "updated_at"}}
    if isinstance(value, (list, tuple)):
        return [_without_times(v) for v in value]
    return value


def _rows(path):
    """Every persisted sporting/Saved/draft value; timestamps excluded."""
    with sqlite3.connect(path) as db:
        def query(sql):
            return db.execute(sql).fetchall()

        tables = {name for (name,) in query("SELECT name FROM sqlite_master WHERE type='table'")}
        return {
            "revisions": query(
                "SELECT revision_id, run_id, branch_id, sequence, parent_revision_id, kind, "
                "payload_schema_version, content_hash_algorithm, content_hash, payload_json, "
                "change_summary_json FROM branch_saved_revisions ORDER BY sequence, revision_id"),
            "nodes": query("SELECT * FROM saved_revision_nodes ORDER BY 1, 2")
            if "saved_revision_nodes" in tables else [],
            "audit": query("SELECT audit_event_id, run_id, branch_id, saved_revision_id, event_kind, "
                           "payload_json FROM branch_revision_audit_events ORDER BY audit_event_id"),
            "draft": query("SELECT draft_id, branch_id, base_revision_id, status, change_count, "
                           "draft_version, changes_json FROM branch_working_drafts ORDER BY draft_id"),
            "branches": query("SELECT branch_id, saved_head_revision_id, status FROM run_branches "
                              "ORDER BY branch_id"),
            "checkpoint": query("SELECT run_id, branch_id, fingerprint, payload_json "
                                "FROM calendar_player_sporting_checkpoints ORDER BY 1, 2"),
            "tour": query("SELECT run_id, branch_id, fingerprint, payload_json "
                          "FROM calendar_tour_authorities ORDER BY 1, 2"),
        }


def _post_save(server, view):
    return _request("POST", tour_url(server) + "/save", {
        "expected_draft_version": view["draft_version"],
        "expected_calendar_tour_fingerprint": view["tour_fingerprint"],
    })


def _observe(monkeypatch, *, after_prepare=None):
    """Count prepared hits and writer-side strict decodes of the live row."""
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting

    seen = {"prepared": [], "writer_decodes": 0, "used": 0}
    prepare, decode = sporting.prepare_checkpoint_for_save, sporting._decode_checkpoint_row
    take = sporting.PreparedSaveCheckpoint.take

    def observed_prepare(session_factory, **kwargs):
        prepared = prepare(session_factory, **kwargs)
        seen["prepared"].append((kwargs["run_id"], kwargs["branch_id"], prepared))
        if after_prepare is not None and prepared is not None:
            after_prepare(prepared)
        return prepared

    def observed_take(self, **kwargs):
        state = take(self, **kwargs)
        seen["used"] += state is not None
        return state

    def observed_decode(*args, **kwargs):
        seen["writer_decodes"] += 1
        return decode(*args, **kwargs)

    monkeypatch.setattr(sporting, "prepare_checkpoint_for_save", observed_prepare)
    monkeypatch.setattr(sporting.PreparedSaveCheckpoint, "take", observed_take)
    monkeypatch.setattr(sporting, "_decode_checkpoint_row", observed_decode)
    return seen


def _play_and_save(tmp_path, source, name, monkeypatch, *, disable_prepared=False):
    """next-match -> GET -> Save -> GET, then a restarted process GET."""
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting

    path = tmp_path / f"{name}.db"
    copy_database(source, path)
    _ids(monkeypatch, "prepared-save-equivalence")
    with monkeypatch.context() as patch:
        if disable_prepared:
            patch.setattr(sporting, "prepare_checkpoint_for_save", lambda *_a, **_k: None)
        seen = _observe(patch)
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            execute(server, command(inspect(server), "next-match", name="prepared-equivalence-1"))
            view = inspect(server)
            status, receipt = _post_save(server, view)
            assert status == 201, receipt
            saved = inspect(server)
            execute(server, command(saved, "next-match", name="prepared-equivalence-2"))
            status, second = _post_save(server, inspect(server))
            assert status == 201, second
            final = inspect(server)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert inspect(server) == final
    return path, receipt, second, final, seen


@pytest.mark.parametrize("storage", ["saved_v1", "saved_v2"])
def test_prepared_copy_save_equals_original_writer_decode(tmp_path, prepared_slots, drawn_slots_v2,
                                                          monkeypatch, storage):
    source = prepared_slots if storage == "saved_v1" else drawn_slots_v2
    expected = _play_and_save(tmp_path, source, "original", monkeypatch, disable_prepared=True)
    actual = _play_and_save(tmp_path, source, "prepared", monkeypatch)
    # The original path decoded the live row inside the writer transaction;
    # the candidate used its prepared copy for both Saves.
    assert expected[4]["used"] == 0 and expected[4]["writer_decodes"] >= 2
    assert actual[4]["used"] == 2
    assert [entry[:2] for entry in actual[4]["prepared"]] == [("run", "branch")] * 2
    assert _differences(_without_times(actual[1:3]), _without_times(expected[1:3])) == []
    assert _differences(actual[3], expected[3]) == []
    rows = _rows(actual[0])
    assert rows == _rows(expected[0])
    assert bool(rows["nodes"]) is (storage == "saved_v2")


def _rewrite_live_row(path, *, same_value):
    from beta_engine.domain.run_packages import canonical_hash

    with sqlite3.connect(path) as db:
        raw, fingerprint = db.execute(
            "SELECT payload_json, fingerprint FROM calendar_player_sporting_checkpoints "
            "WHERE run_id='run' AND branch_id='branch'").fetchone()
        body = json.loads(raw)
        if same_value:
            # Equivalent JSON, different bytes: only the strict decode may decide.
            replacement, new_fingerprint = json.dumps(body, indent=1), fingerprint
        else:
            body["events"][-1]["scheduled"][-1]["seed"] += 1
            replacement, new_fingerprint = json.dumps(body), canonical_hash(body)
        db.execute("UPDATE calendar_player_sporting_checkpoints SET payload_json=?, fingerprint=? "
                   "WHERE run_id='run' AND branch_id='branch'", (replacement, new_fingerprint))
    return raw, fingerprint


def test_changed_row_bytes_between_phases_take_the_original_decode(tmp_path, prepared_slots, monkeypatch):
    path = tmp_path / "changed-row.db"
    copy_database(prepared_slots, path)
    original = {}

    def change_after_prepare(_prepared):
        original["row"] = _rewrite_live_row(path, same_value=True)

    seen = _observe(monkeypatch, after_prepare=change_after_prepare)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="changed-row"))
        view = inspect(server)
        status, receipt = _post_save(server, view)
        # Same value, other bytes: the prepared copy is discarded and the
        # writer's own strict decode accepts the actual row.
        assert status == 201, receipt
        assert seen["used"] == 0 and seen["writer_decodes"] >= 1
        assert inspect(server)["saved_head_revision_id"] == receipt["saved_revision"]["revision_id"]


def test_changed_live_value_between_phases_rolls_back_the_entire_save(tmp_path, prepared_slots, monkeypatch):
    path = tmp_path / "changed-value.db"
    copy_database(prepared_slots, path)
    seen = _observe(monkeypatch, after_prepare=lambda _prepared: _rewrite_live_row(path, same_value=False))
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="changed-value"))
        view = inspect(server)
        before = _rows(path)
        status, error = _post_save(server, view)
        assert status == 409, error
    after = _rows(path)
    assert seen["used"] == 0 and seen["writer_decodes"] >= 1
    # Only the live row this test rewrote differs; no Saved/draft/audit row.
    assert {key: value for key, value in after.items() if key != "checkpoint"} == {
        key: value for key, value in before.items() if key != "checkpoint"}


def test_working_draft_change_between_phases_is_rejected(tmp_path, prepared_slots, monkeypatch):
    path = tmp_path / "changed-draft.db"
    copy_database(prepared_slots, path)

    bumped = []

    def bump_draft(_prepared):
        if bumped:
            return
        bumped.append(True)
        # One concurrent draft change after this Save prepared its copy.
        with sqlite3.connect(path) as db:
            db.execute("UPDATE branch_working_drafts SET draft_version = draft_version + 1 "
                       "WHERE branch_id='branch'")

    seen = _observe(monkeypatch, after_prepare=bump_draft)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="changed-draft"))
        view = inspect(server)
        before = _rows(path)
        status, error = _post_save(server, view)
        assert status == 409, error
        after = _rows(path)
        # Nothing but the externally bumped version changed; the prepared copy
        # never reached capture.
        assert after["revisions"] == before["revisions"] and after["branches"] == before["branches"]
        assert seen["used"] == 0
        current = inspect(server)
        assert not current["saved"] and current["draft_version"] == view["draft_version"] + 1
        seen["prepared"].clear()
        status, receipt = _post_save(server, current)
        assert status == 201, receipt
        assert seen["used"] == 1


def _first_mutable_result(state):
    for event in reversed(state.events):
        for match in getattr(event, "accepted", ()):
            sets_won = getattr(getattr(match, "result", None), "sets_won", None)
            if isinstance(sets_won, dict) and sets_won:
                return sets_won
    raise AssertionError("No mutable nested match result in the live checkpoint")


def test_nested_mutation_of_the_private_copy_is_never_saved_or_cached(tmp_path, prepared_slots, monkeypatch):
    from sqlalchemy import text

    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint

    path = tmp_path / "mutated-copy.db"
    copy_database(prepared_slots, path)

    def mutate(prepared):
        sets_won = _first_mutable_result(prepared._state)
        key = next(iter(sets_won))
        sets_won[key] += 1

    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="mutated-copy"))
        view = inspect(server)
        before = _rows(path)
        with monkeypatch.context() as patch:
            seen = _observe(patch, after_prepare=mutate)
            status, error = _post_save(server, view)
        assert status == 409, error
        assert seen["used"] == 1
        assert _rows(path) == before
        repository = server.app.state.runtime.repository
        with repository._session_factory() as session:
            live = load_checkpoint(session, run_id="run", branch_id="branch", _repository=repository)
            raw = session.execute(text(
                "SELECT payload_json FROM calendar_player_sporting_checkpoints "
                "WHERE run_id='run' AND branch_id='branch'")).scalar_one()
        # The value cache was never given (or handed back) the mutated copy.
        assert live.model_dump(mode="json") == json.loads(raw)
        receipt = save_tour(server)
        assert inspect(server)["saved_head_revision_id"] == receipt["revision_id"]


def test_foreign_run_or_branch_preparation_is_never_used(tmp_path, prepared_slots, monkeypatch):
    path = tmp_path / "foreign-scope.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="foreign-scope"))
        for index, forge in enumerate((
            lambda prepared: setattr(prepared, "run_id", "other-run"),
            lambda prepared: setattr(prepared, "branch_id", "other-branch"),
            lambda prepared: setattr(prepared, "_state",
                                     prepared._state.model_copy(update={"branch_id": "other-branch"})),
        )):
            view = inspect(server)
            with monkeypatch.context() as patch:
                seen = _observe(patch, after_prepare=forge)
                status, receipt = _post_save(server, view)
            assert status == 201, receipt
            assert seen["used"] == 0 and seen["writer_decodes"] >= 1
            if index < 2:
                execute(server, command(inspect(server), "next-match", name=f"foreign-scope-{index}"))


def test_concurrent_saves_commit_exactly_once(tmp_path, prepared_slots, monkeypatch):
    path = tmp_path / "concurrent-save.db"
    copy_database(prepared_slots, path)
    seen = _observe(monkeypatch)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="concurrent-save"))
        view = inspect(server)
        before = _rows(path)
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = list(pool.map(lambda _: _post_save(server, view), range(2)))
        assert sorted(status for status, _ in attempts) == [201, 409], attempts
        receipt = next(body for status, body in attempts if status == 201)
        after = _rows(path)
        assert len(after["revisions"]) == len(before["revisions"]) + 1
        assert after["revisions"][-1][0] == receipt["saved_revision"]["revision_id"]
        assert len(seen["prepared"]) == 2
        saved = inspect(server)
        assert saved["saved"] and saved["saved_head_revision_id"] == receipt["saved_revision"]["revision_id"]


def test_rollback_after_use_leaves_no_state_and_retry_matches(tmp_path, prepared_slots, monkeypatch):
    from beta_engine.api import deps
    from beta_engine.infrastructure.db import repositories

    reference = _play_and_save(tmp_path, prepared_slots, "rollback-reference", monkeypatch)
    path = tmp_path / "rollback.db"
    copy_database(prepared_slots, path)
    _ids(monkeypatch, "prepared-save-equivalence")
    seen = _observe(monkeypatch)
    capture = repositories.capture_saved_calendar_match

    def fail_after_capture(*args, **kwargs):
        capture(*args, **kwargs)
        raise ValueError("Injected Save rollback after the prepared copy was captured")

    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="prepared-equivalence-1"))
        view = inspect(server)
        before = _rows(path)
        with monkeypatch.context() as patch:
            # The failed attempt draws its IDs from another sequence only so
            # that the retried databases stay directly comparable.
            patch.setattr(deps, "uuid4", _Ids("rolled-back-attempt"))
            patch.setattr(repositories, "capture_saved_calendar_match", fail_after_capture)
            status, error = _post_save(server, view)
        assert status == 409, error
        assert seen["used"] == 1
        assert _rows(path) == before
        # The same request is retried; it prepares again and commits normally.
        status, receipt = _post_save(server, view)
        assert status == 201, receipt
        assert seen["used"] == 2
        assert inspect(server)["saved_head_revision_id"] == receipt["saved_revision"]["revision_id"]
        execute(server, command(inspect(server), "next-match", name="prepared-equivalence-2"))
        status, second = _post_save(server, inspect(server))
        assert status == 201, second
        final = inspect(server)
    assert final == reference[3]
    assert _without_times([receipt, second]) == _without_times(list(reference[1:3]))
    assert _rows(path) == _rows(reference[0])


def test_lost_save_response_retry_is_rejected_without_a_duplicate_revision(tmp_path, prepared_slots, monkeypatch):
    from beta_engine.application import calendar_tour_save_projection

    path = tmp_path / "lost-response.db"
    copy_database(prepared_slots, path)
    seen = _observe(monkeypatch)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="lost-response"))
        view = inspect(server)

        def lose_response(*_args, **_kwargs):
            raise ValueError("Injected lost response after a successful commit")

        with monkeypatch.context() as patch:
            patch.setattr(calendar_tour_save_projection, "saved_inspection_value_fingerprint", lose_response)
            status, error = _post_save(server, view)
        assert status == 409, error
        committed = inspect(server)
        assert committed["saved"] and committed["saved_head_revision_id"] != view["saved_head_revision_id"]
        revisions = _rows(path)["revisions"]
        status, retry = _post_save(server, view)
        assert status == 409, retry
        assert _rows(path)["revisions"] == revisions
        assert seen["used"] == 1


def test_fork_save_and_restore_keep_their_original_paths(tmp_path, prepared_slots, monkeypatch):
    from tests.api.test_calendar_global_slots import sporting
    from tests.api.test_calendar_population_sporting_checkpoint import restore
    from tests.api.test_native_fork_public_continuation import Tour, fork

    path = tmp_path / "fork-restore.db"
    copy_database(prepared_slots, path)
    seen = _observe(monkeypatch)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="fork-source"))
        saved = save_tour(server)
        accepted = sporting(server)
        created = fork(server, saved["revision_id"], name="Prepared Save fork")
        target = Tour(server, created["branch_id"])
        target.execute("next-match", "fork-target-match")
        target.save()
        # The native fork Save keeps its own coordinator: nothing prepared there.
        assert [entry[:2] for entry in seen["prepared"]] == [("run", "branch")]
        execute(server, command(inspect(server), "next-match", name="fork-source-second"))
        save_tour(server)
        restore(server, saved["revision_id"])
        assert sporting(server) == accepted
        assert inspect(server)["next_slot"]["remaining"] == 3
        execute(server, command(inspect(server), "next-match", name="after-restore"))
        save_tour(server)
        assert seen["used"] == 3
        assert target.view()["next_slot"]["remaining"] == 2


def test_taken_live_value_is_uncopied_and_returns_only_after_commit(tmp_path, prepared_slots, monkeypatch):
    from beta_engine.infrastructure.db import native_fork_source_projection as cache
    from beta_engine.infrastructure.db import repositories

    path = tmp_path / "taken-value.db"
    copy_database(prepared_slots, path)
    copies = []
    copy = cache._copy_decoded_value

    def counted(value, *args, **kwargs):
        if getattr(value, "schema_version", None) == "calendar_sporting_checkpoint.v13":
            copies.append(sys._getframe(1).f_code.co_name)
        return copy(value, *args, **kwargs)

    def retained(repository):
        """Values retained for exactly the current live row bytes."""
        import hashlib

        with sqlite3.connect(path) as db:
            (raw,) = db.execute("SELECT payload_json FROM calendar_player_sporting_checkpoints "
                                "WHERE run_id='run' AND branch_id='branch'").fetchone()
        key = ("run", "branch", "calendar_player_sporting_checkpoint",
               hashlib.sha256(raw.encode("utf-8")).digest())
        with repository._revision_validation_lock:
            entry = getattr(repository, "_live_calendar_value_cache", {}).get(key)
        return [] if entry is None else [entry[1]]

    monkeypatch.setattr(cache, "_copy_decoded_value", counted)
    seen = _observe(monkeypatch)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repository = server.app.state.runtime.repository
        execute(server, command(inspect(server), "next-match", name="taken-rollback"))
        view = inspect(server)
        (before,) = retained(repository)
        capture = repositories.capture_saved_calendar_match

        def fail(*args, **kwargs):
            capture(*args, **kwargs)
            raise ValueError("Injected rollback after the taken value was captured")

        with monkeypatch.context() as patch:
            patch.setattr(repositories, "capture_saved_calendar_match", fail)
            copies.clear()
            assert _post_save(server, view)[0] == 409
        # Taken without a copy, then dropped by the rolled-back Save.
        assert seen["used"] == 1 and "decoded_live_calendar_component" not in copies
        assert retained(repository) == [] and before is not None
        inspect(server)  # an ordinary reader decodes the unchanged row again
        (fresh,) = retained(repository)
        copies.clear()
        status, receipt = _post_save(server, view)
        assert status == 201, receipt
        assert seen["used"] == 2 and "decoded_live_calendar_component" not in copies
        # The committed Save returned exactly its own value to the live cache.
        assert [value is fresh for value in retained(repository)] == [True]
        # Every later reader still receives its own defensive copy.
        from sqlalchemy import text

        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint

        with repository._session_factory() as session:
            reader = load_checkpoint(session, run_id="run", branch_id="branch", _repository=repository)
            raw = session.execute(text(
                "SELECT payload_json FROM calendar_player_sporting_checkpoints "
                "WHERE run_id='run' AND branch_id='branch'")).scalar_one()
        assert reader is not fresh and reader.model_dump(mode="json") == json.loads(raw)
        execute(server, command(inspect(server), "next-match", name="taken-after-commit"))
        assert save_tour(server)["revision_id"]
