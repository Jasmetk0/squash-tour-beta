"""Manual Tour Save: the live checkpoint decode is transferred, never shared.

Real HTTP/SQLite/MatchEngine, no fabricated results. Inside its writer
transaction the Save hashes the complete actual live row and may take the
retained private decode of exactly those bytes instead of copying it, but only
if no reader is copying it (pinned) and no other cache references it (shared).
Every other case is the original strict decode and every Save gate. Compared
databases use deterministic Saved/audit IDs.
"""

import json
import os
import sqlite3
import sys
import threading
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


def _observe(monkeypatch, *, on_take=None):
    """Count transfers, writer reads and strict decodes of the live row."""
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting
    from beta_engine.infrastructure.db import native_fork_source_projection as cache

    seen = {"offered": 0, "refused": 0, "used": 0, "reads": 0, "decodes": 0, "writer_reads": []}
    take, read, decode = (cache.take_live_calendar_component, sporting.read_checkpoint_for_save,
                          sporting._decode_checkpoint_row)

    def observed_take(repository, **kwargs):
        taken = take(repository, **kwargs)
        seen["offered" if taken is not None else "refused"] += 1
        if taken is not None and on_take is not None:
            taken = on_take(taken)
        return taken

    def observed_read(session, **kwargs):
        result = read(session, **kwargs)
        seen["writer_reads"].append((kwargs["run_id"], kwargs["branch_id"], kwargs.get("take_live", False)))
        seen["used"] += result is not None and result.taken is not None
        return result

    def observed_decode(*args, **kwargs):
        seen["decodes"] += 1
        return decode(*args, **kwargs)

    monkeypatch.setattr(cache, "take_live_calendar_component", observed_take)
    monkeypatch.setattr(sporting, "read_checkpoint_for_save", observed_read)
    monkeypatch.setattr(sporting, "_decode_checkpoint_row", observed_decode)
    return seen


def _play_and_save(tmp_path, source, name, monkeypatch, *, disable_take=False):
    """next-match -> GET -> Save -> GET, then a restarted process GET."""
    from beta_engine.infrastructure.db import native_fork_source_projection as cache

    path = tmp_path / f"{name}.db"
    copy_database(source, path)
    _ids(monkeypatch, "prepared-save-equivalence")
    with monkeypatch.context() as patch:
        if disable_take:
            patch.setattr(cache, "take_live_calendar_component", lambda *_a, **_k: None)
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
def test_transferred_value_save_equals_original_copying_decode(tmp_path, prepared_slots, drawn_slots_v2,
                                                              monkeypatch, storage):
    source = prepared_slots if storage == "saved_v1" else drawn_slots_v2
    expected = _play_and_save(tmp_path, source, "original", monkeypatch, disable_take=True)
    actual = _play_and_save(tmp_path, source, "taken", monkeypatch)
    assert expected[4]["used"] == 0 and actual[4]["used"] == 2
    assert [r for r in actual[4]["writer_reads"] if r[2]] == [("run", "branch", True)] * 2
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


def test_changed_row_bytes_before_the_writer_read_take_the_original_decode(
    tmp_path, prepared_slots, monkeypatch,
):
    path = tmp_path / "changed-row.db"
    copy_database(prepared_slots, path)
    seen = _observe(monkeypatch)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="changed-row"))
        view = inspect(server)          # retains the decode of the current bytes
        _rewrite_live_row(path, same_value=True)
        decodes = seen["decodes"]
        status, receipt = _post_save(server, view)
        # Same value, other bytes: nothing retained matches the actual digest,
        # so the writer's own strict decode accepts the actual row.
        assert status == 201, receipt
        assert seen["used"] == 0 and seen["decodes"] > decodes
        assert inspect(server)["saved_head_revision_id"] == receipt["saved_revision"]["revision_id"]


def test_changed_live_value_before_the_writer_read_rolls_back_the_entire_save(
    tmp_path, prepared_slots, monkeypatch,
):
    path = tmp_path / "changed-value.db"
    copy_database(prepared_slots, path)
    seen = _observe(monkeypatch)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="changed-value"))
        view = inspect(server)
        _rewrite_live_row(path, same_value=False)
        before = _rows(path)
        status, error = _post_save(server, view)
        assert status == 409, error
    after = _rows(path)
    assert seen["used"] == 0
    assert after == before


def _first_mutable_result(state):
    for event in reversed(state.events):
        for match in getattr(event, "accepted", ()):
            sets_won = getattr(getattr(match, "result", None), "sets_won", None)
            if isinstance(sets_won, dict) and sets_won:
                return sets_won
    raise AssertionError("No mutable nested match result in the live checkpoint")


def test_nested_mutation_of_the_taken_value_is_never_saved_or_cached(tmp_path, prepared_slots, monkeypatch):
    from sqlalchemy import text

    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint

    path = tmp_path / "mutated-copy.db"
    copy_database(prepared_slots, path)

    def mutate(taken):
        sets_won = _first_mutable_result(taken[1][1])
        key = next(iter(sets_won))
        sets_won[key] += 1
        return taken

    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="mutated-copy"))
        view = inspect(server)
        before = _rows(path)
        with monkeypatch.context() as patch:
            seen = _observe(patch, on_take=mutate)
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
        # The value cache was never handed back the mutated value.
        assert live.model_dump(mode="json") == json.loads(raw)
        receipt = save_tour(server)
        assert inspect(server)["saved_head_revision_id"] == receipt["revision_id"]


def test_a_foreign_or_mismatched_retained_value_is_never_used(tmp_path, prepared_slots, monkeypatch):
    path = tmp_path / "foreign-scope.db"
    copy_database(prepared_slots, path)
    forgeries = (
        lambda t: (t[0], (t[1][0], t[1][1].model_copy(update={"run_id": "other-run"}), *t[1][2:])),
        lambda t: (t[0], (t[1][0], t[1][1].model_copy(update={"branch_id": "other-branch"}), *t[1][2:])),
        lambda t: (t[0], (*t[1][:2], "0" * 64, *t[1][3:])),  # retained for another fingerprint
    )
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="foreign-scope"))
        for index, forge in enumerate(forgeries):
            view = inspect(server)
            with monkeypatch.context() as patch:
                seen = _observe(patch, on_take=forge)
                status, receipt = _post_save(server, view)
            assert status == 201, receipt
            assert seen["offered"] == 1 and seen["used"] == 0 and seen["decodes"] >= 1
            execute(server, command(inspect(server), "next-match", name=f"foreign-scope-{index}"))


def _slow_reader_copy(monkeypatch):
    """Hold the first reader's copy of the retained checkpoint until released."""
    from beta_engine.infrastructure.db import native_fork_source_projection as cache

    copying, release = threading.Event(), threading.Event()
    copy = cache._copy_decoded_value

    def gated(value, *args, **kwargs):
        if (getattr(value, "schema_version", None) == "calendar_sporting_checkpoint.v13"
                and sys._getframe(1).f_code.co_name == "decoded_live_calendar_component"
                and not copying.is_set()):
            copying.set()
            assert release.wait(120)
        return copy(value, *args, **kwargs)

    monkeypatch.setattr(cache, "_copy_decoded_value", gated)
    return copying, release


def _retained(repository, path):
    import hashlib

    with sqlite3.connect(path) as db:
        (raw,) = db.execute("SELECT payload_json FROM calendar_player_sporting_checkpoints "
                            "WHERE run_id='run' AND branch_id='branch'").fetchone()
    key = ("run", "branch", "calendar_player_sporting_checkpoint", hashlib.sha256(raw.encode("utf-8")).digest())
    with repository._revision_validation_lock:
        return getattr(repository, "_live_calendar_value_cache", {}).get(key)


def test_a_save_never_takes_a_value_a_rate_limited_reader_is_copying(tmp_path, prepared_slots, monkeypatch):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint

    path = tmp_path / "pinned.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repository = server.app.state.runtime.repository
        execute(server, command(inspect(server), "next-match", name="pinned"))
        view = inspect(server)
        retained = _retained(repository, path)
        assert retained is not None
        copying, release = _slow_reader_copy(monkeypatch)
        seen = _observe(monkeypatch)
        read = {}

        def reader():
            with repository._session_factory() as session:
                read["value"] = load_checkpoint(session, run_id="run", branch_id="branch", _repository=repository)

        thread = threading.Thread(target=reader)
        thread.start()
        try:
            assert copying.wait(120)     # the reader holds the retained model now
            status, receipt = _post_save(server, view)
            assert status == 201, receipt
            # The pinned value stayed in the cache, untransferred; the Save
            # used its own copy (the original path).
            assert seen["refused"] >= 1 and seen["used"] == 0
            assert _retained(repository, path)[1] is retained[1]
        finally:
            release.set()
            thread.join(120)
        assert read["value"] is not retained[1]
        assert read["value"].model_dump(mode="json") == retained[1].model_dump(mode="json")
        with repository._revision_validation_lock:
            assert not getattr(repository, "_live_calendar_value_pins", {})


def test_a_reader_after_the_transfer_never_reaches_the_taken_value(tmp_path, prepared_slots, monkeypatch):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
    from beta_engine.infrastructure.db import repositories

    path = tmp_path / "taken-then-read.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repository = server.app.state.runtime.repository
        execute(server, command(inspect(server), "next-match", name="taken-then-read"))
        view = inspect(server)
        retained = _retained(repository, path)[1]
        captured, resume, read = threading.Event(), threading.Event(), {}
        capture = repositories.capture_saved_calendar_match

        def paused(*args, **kwargs):
            captured.set()          # inside the writer transaction, value taken
            assert resume.wait(120)
            return capture(*args, **kwargs)

        monkeypatch.setattr(repositories, "capture_saved_calendar_match", paused)
        seen = _observe(monkeypatch)
        out = {}
        saver = threading.Thread(target=lambda: out.setdefault("save", _post_save(server, view)))
        saver.start()
        try:
            assert captured.wait(120)
            assert _retained(repository, path) is None   # left the cache under its lock
            with repository._session_factory() as session:
                read["value"] = load_checkpoint(session, run_id="run", branch_id="branch",
                                                _repository=repository)
        finally:
            resume.set()
            saver.join(120)
        assert out["save"][0] == 201, out["save"]
        assert seen["used"] == 1
        assert read["value"] is not retained
        assert read["value"].model_dump(mode="json") == retained.model_dump(mode="json")


def test_a_committed_value_is_shared_by_both_caches_and_never_transferred_again(
    tmp_path, prepared_slots, monkeypatch,
):
    from beta_engine.infrastructure.db import native_fork_source_projection as cache
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint

    path = tmp_path / "shared.db"
    copy_database(prepared_slots, path)
    seen = _observe(monkeypatch)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repository = server.app.state.runtime.repository
        execute(server, command(inspect(server), "next-match", name="shared-1"))
        view = inspect(server)
        taken = _retained(repository, path)[1]
        status, receipt = _post_save(server, view)
        assert status == 201, receipt and seen["used"] == 1
        entry = _retained(repository, path)
        assert entry[1] is taken and entry[4] is True        # reinstalled, marked shared
        with repository._revision_validation_lock:
            global_values = [e[1] for e in getattr(repository, "_global_tour_projection_cache", {}).values()]
        assert any(value is taken for value in global_values)  # the alias the flag protects
        import hashlib

        with sqlite3.connect(path) as db:
            (raw,) = db.execute("SELECT payload_json FROM calendar_player_sporting_checkpoints "
                                "WHERE run_id='run' AND branch_id='branch'").fetchone()
        actual = raw.encode("utf-8")
        assert cache.take_live_calendar_component(
            repository, run_id="run", branch_id="branch", kind="calendar_player_sporting_checkpoint",
            size=len(actual), digest=hashlib.sha256(actual).digest()) is None
        assert _retained(repository, path)[1] is taken
        with repository._session_factory() as session:
            reader = load_checkpoint(session, run_id="run", branch_id="branch", _repository=repository)
        assert reader is not taken and reader.model_dump(mode="json") == json.loads(raw)
        # The next draft has new bytes: a new private decode, transferred again.
        execute(server, command(inspect(server), "next-match", name="shared-2"))
        status, second = _post_save(server, inspect(server))
        assert status == 201, second
        assert seen["used"] == 2


def test_cold_miss_and_oversize_keep_the_original_reads_hashes_and_copies(tmp_path, prepared_slots, monkeypatch):
    """A miss costs exactly what the original path costs: no extra row read,
    full-payload hash or copy (counted against the forced original path)."""
    import hashlib

    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting
    from beta_engine.infrastructure.db import native_fork_source_projection as cache

    def counts(label, *, disable, oversize=False):
        path = tmp_path / f"{label}.db"
        copy_database(prepared_slots, path)
        tally = {"row_reads": 0, "copies": 0, "hashes": 0}
        with monkeypatch.context() as patch:
            columns, copy, sha = sporting._read_checkpoint_columns, cache._copy_decoded_value, hashlib.sha256

            def read(*a, **k):
                tally["row_reads"] += 1
                return columns(*a, **k)

            def copied(value, *a, **k):
                tally["copies"] += getattr(value, "schema_version", None) == "calendar_sporting_checkpoint.v13"
                return copy(value, *a, **k)

            def hashed(data=b"", *a, **k):
                tally["hashes"] += len(data) > 1_000_000
                return sha(data, *a, **k)

            if disable:
                patch.setattr(cache, "take_live_calendar_component", lambda *_a, **_k: None)
            if oversize:
                patch.setattr(cache, "MAX_LIVE_COMPONENT_BYTES", 1024)
            with ApiServer(database_url=f"sqlite:///{path}") as server:
                repository = server.app.state.runtime.repository
                execute(server, command(inspect(server), "next-match", name="cold"))
                view = inspect(server)
                with repository._revision_validation_lock:   # exactly what eviction leaves
                    for name in ("_live_calendar_value_cache", "_global_tour_projection_cache"):
                        getattr(repository, name, {}).clear()
                patch.setattr(sporting, "_read_checkpoint_columns", read)
                patch.setattr(cache, "_copy_decoded_value", copied)
                patch.setattr(cache.hashlib, "sha256", hashed)
                status, receipt = _post_save(server, view)
                patch.setattr(cache.hashlib, "sha256", sha)
                assert status == 201, receipt
        return tally, _rows(path)

    original, original_rows = counts("cold-original", disable=True)
    candidate, candidate_rows = counts("cold-candidate", disable=False)
    assert candidate == original and candidate_rows["checkpoint"] == original_rows["checkpoint"]
    oversize, _ = counts("oversize", disable=False, oversize=True)
    oversize_original, _ = counts("oversize-original", disable=True, oversize=True)
    assert oversize == oversize_original


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
        # The loser may be rejected before or after its own writer read.
        assert [r for r in seen["writer_reads"] if r[2]] in ([("run", "branch", True)] * 1,
                                                             [("run", "branch", True)] * 2)
        assert seen["used"] == 1
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
        raise ValueError("Injected Save rollback after the taken value was captured")

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
        # The rolled-back Save dropped the taken value; the retry is a miss
        # that takes the original copying decode and commits normally.
        status, receipt = _post_save(server, view)
        assert status == 201, receipt
        assert seen["used"] == 1
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
        # The native fork Save keeps its own coordinator: nothing is taken there.
        assert [r for r in seen["writer_reads"] if r[2]] == [("run", "branch", True)]
        execute(server, command(inspect(server), "next-match", name="fork-source-second"))
        save_tour(server)
        restore(server, saved["revision_id"])
        assert sporting(server) == accepted
        assert inspect(server)["next_slot"]["remaining"] == 3
        execute(server, command(inspect(server), "next-match", name="after-restore"))
        refused = seen["refused"]
        save_tour(server)
        # After Restore the same match yields byte-identical live checkpoint
        # bytes: their retained value is the one the previous Save committed,
        # shared with the global cache, so it is copied, never transferred.
        assert seen["used"] == 2 and seen["refused"] == refused + 1
        assert target.view()["next_slot"]["remaining"] == 2


