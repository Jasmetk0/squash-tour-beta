"""Saved v2 rope store: exact reconstruction, incremental writes, fail-closed reads.

Pure component tests of ``saved_v2_store`` (no HTTP). The ORM/SQLite and real
HTTP paths are covered by ``test_saved_v2_sqlite.py`` and
``tests/api/test_saved_v2_http.py``.
"""

import hashlib
import json

import pytest

from beta_engine.infrastructure.db import saved_v2_store as st

pytestmark = pytest.mark.pr_critical


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def player(index, **extra):
    return {"player_id": f"p-{index:05d}", "name": f"Hráč {index} ✓", "attributes": {
        "speed": index % 97, "stamina": [index % 7, index % 11, index % 13],
        "absent": None, "flag": index % 2 == 0, "ratio": index / 7}, **extra}


def payload(events=2, players=120, edit=None):
    roster = [player(i) for i in range(players)]
    if edit is not None:
        roster[edit] = player(edit, corrected=True)
    return {"content": {
        "events": [{"week": w, "completed_players": roster, "target_players": roster[::-1],
                    "rallies": [[w, i, i * 3] for i in range(400)]} for w in range(events)],
        "empty": {}, "nothing": [], "note": "ünïcødé   \"quoted\" \\ back", "n": None,
    }, "schema_version": "run_saved_revision_v1"}


class Store:
    def __init__(self):
        self.rows = {}   # (run_id, digest) -> body

    def fetch(self, run_id, digests):
        return {d: self.rows[(run_id, d)] for d in digests if (run_id, d) in self.rows}

    def write(self, run_id, text, index=None):
        encoder = st.Encoder(run_id, index=index)
        root = encoder.encode(text)
        new = {d: b for d, b in encoder.nodes.items() if (run_id, d) not in self.rows}
        for digest, body in new.items():
            self.rows[(run_id, digest)] = body
        if index is not None:
            for digest, start, end in encoder.value_nodes:
                index.add(run_id, digest, text, start, end)
        return root, new, encoder

    def read(self, run_id, root, chars):
        return st.materialize(self.fetch, run_id=run_id, root=root, expected_chars=chars)


@pytest.mark.parametrize("text", [
    canonical(payload()),
    canonical(payload(events=1, players=3)),
    json.dumps(payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    json.dumps(payload(), indent=2),             # not compact: exact raw fallback
    canonical({"a": float("nan"), "b": [float("inf"), -float("inf")] * 2000}),
    canonical([]), canonical({}), "null", "",
    canonical({"looks_like_a_ref": {"c": ["0" * 64], "k": "v", "n": [0, 0]}, "x": "\n" * 5000}),
])
def test_exact_round_trip(text):
    store = Store()
    root, _, _ = store.write("run-a", text)
    assert store.read("run-a", root, len(text)) == text


def test_deterministic_and_identical_with_or_without_hints():
    texts = [canonical(payload(events=n)) for n in (1, 2, 3)]
    plain, hinted = Store(), Store()
    index = st.KnownValueIndex()
    for text in texts:
        root_plain, _, _ = plain.write("run", text)
        root_hinted, _, encoder = hinted.write("run", text, index=index)
        assert root_plain == root_hinted
    assert encoder.reused > 0
    assert plain.rows == hinted.rows


def test_append_writes_only_new_nodes_and_edit_uses_copy_on_write():
    store, index = Store(), st.KnownValueIndex()
    first = canonical(payload(events=4))
    _, new_first, _ = store.write("run", first, index=index)
    appended = canonical(payload(events=5))
    root, new, _ = store.write("run", appended, index=index)
    assert store.read("run", root, len(appended)) == appended
    added = sum(len(b) for b in new.values())
    # One more event of ~len(first)/4 text; unchanged history is not rewritten.
    assert added < 0.5 * len(first) / 4
    # A legitimate change of historical content (not an append) is stored exactly.
    corrected = canonical(payload(events=5, edit=17))
    root, new, _ = store.write("run", corrected, index=index)
    assert store.read("run", root, len(corrected)) == corrected
    assert 0 < sum(len(b) for b in new.values()) < len(corrected) / 4
    # Truncation / deletion of history: also exact.
    shorter = canonical(payload(events=2))
    root, _, _ = store.write("run", shorter, index=index)
    assert store.read("run", root, len(shorter)) == shorter


def test_stale_or_foreign_hint_never_changes_the_result():
    store, index = Store(), st.KnownValueIndex()
    text = canonical(payload(events=2))
    store.write("other-run", text, index=index)    # hints belong to another Run
    root, new, encoder = store.write("run", text, index=index)
    assert encoder.reused == 0 and new
    assert store.read("run", root, len(text)) == text


def _written():
    store = Store()
    text = canonical(payload(events=3))
    root, _, _ = store.write("run", text)
    return store, text, root


def test_rejects_tampered_child_even_after_successful_read():
    store, text, root = _written()
    assert store.read("run", root, len(text)) == text      # warm read succeeds
    key = next(k for k, body in store.rows.items() if k[1] != root and "p-00007" in body)
    store.rows[key] = store.rows[key].replace("p-00007", "p-00008")
    with pytest.raises(st.SavedV2IntegrityError, match="does not match"):
        store.read("run", root, len(text))


def test_rejects_rehashed_child_because_parent_commits_to_old_digest():
    store, text, root = _written()
    key = next(k for k, body in store.rows.items() if k[1] != root and "p-00007" in body)
    forged = store.rows.pop(key).replace("p-00007", "p-00008")
    store.rows[("run", st.sha256_hex(forged))] = forged       # self-consistent row
    with pytest.raises(st.SavedV2IntegrityError, match="missing"):
        store.read("run", root, len(text))


def test_rejects_missing_and_foreign_run_nodes():
    store, text, root = _written()
    with pytest.raises(st.SavedV2IntegrityError, match="missing"):
        store.read("another-run", root, len(text))
    child = next(k for k in store.rows if k[1] != root)
    body = store.rows.pop(child)
    store.rows[("another-run", child[1])] = body              # same digest, other Run
    with pytest.raises(st.SavedV2IntegrityError, match="missing"):
        store.read("run", root, len(text))


def test_rejects_forged_size():
    store, text, root = _written()
    for forged in (len(text) - 1, len(text) + 1, 0):
        with pytest.raises(st.SavedV2IntegrityError, match="size"):
            store.read("run", root, forged)


@pytest.mark.parametrize("header", [
    '{"c":[],"k":"v","n":[3]}x',                 # trailing garbage in header line
    '{"c":[],"k":"x","n":[3]}',                  # unknown kind
    '{"c":[],"k":"v","n":[2]}',                  # pieces do not cover data
    '{"c":[],"k":"v","n":[-1,4]}',               # negative / count mismatch
    '{"k":"v","c":[],"n":[3]}',                  # non-canonical key order
    '{"c":["XYZ"],"k":"v","n":[1,2]}',           # malformed digest
    '{"c":[],"k":"v","n":[true]}',               # boolean length
])
def test_rejects_malformed_nodes(header):
    body = header + "\nabc"
    store = Store()
    store.rows[("run", st.sha256_hex(body))] = body
    with pytest.raises(st.SavedV2IntegrityError):
        store.read("run", st.sha256_hex(body), 3)


def test_rejects_cycles_and_expansion(monkeypatch):
    # A genuine digest cycle would need a SHA-256 fixpoint; disable the hash
    # check to prove the graph walk itself fails closed.
    monkeypatch.setattr(st, "sha256_hex", lambda body: body.split("|", 1)[0])
    a, b = "a" * 64, "b" * 64
    store = Store()
    store.rows[("run", a)] = a + "|"
    store.rows[("run", b)] = b + "|"
    monkeypatch.setattr(st, "parse_node", lambda body: ("v", (b,), ("[", "]")) if body.startswith(a)
                        else ("v", (a,), ("[", "]")))
    with pytest.raises(st.SavedV2IntegrityError, match="cycle"):
        store.read("run", a, 10)
    # Exponential expansion: each level references its child twice.
    levels = ["%064x" % i for i in range(40)]
    store.rows = {("run", d): d + "|" for d in levels}
    shape = {d: ("v", (levels[i + 1], levels[i + 1]), ("[", ",", "]")) if i + 1 < len(levels)
             else ("v", (), ("[]",)) for i, d in enumerate(levels)}
    monkeypatch.setattr(st, "parse_node", lambda body: shape[body.split("|", 1)[0]])
    with pytest.raises(st.SavedV2IntegrityError, match="size limit|piece limit"):
        store.read("run", levels[0], 10)


def test_envelope_binds_run_and_format():
    envelope = st.envelope_text(run_id="run", root="a" * 64, chars=10)
    assert st.parse_envelope(envelope, run_id="run") == ("a" * 64, 10)
    with pytest.raises(st.SavedV2IntegrityError, match="different Run"):
        st.parse_envelope(envelope, run_id="other")
    for forged in (envelope.replace(st.FORMAT, "saved_v2.rope.9"), envelope.replace(":10", ":-1"),
                   envelope + " ", envelope.replace('"a', '"A', 1)):
        with pytest.raises(st.SavedV2IntegrityError):
            st.parse_envelope(forged, run_id="run")


def test_node_digest_is_sha256_of_actual_body():
    store, _, root = _written()
    for (run_id, digest), body in store.rows.items():
        assert digest == hashlib.sha256(body.encode()).hexdigest()


def _sqlite_store(tmp_path, text, *, guards=True, name="nodes.db"):
    """Real SQLite file with the two v2 tables but WITHOUT the persistent insert-only
    triggers (as after a tamperer dropped them), the read functions and, unless
    ``guards`` is False, this connection's TEMP guard triggers."""
    import sqlite3

    path = tmp_path / name
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE run_saved_storage_formats(run_id TEXT PRIMARY KEY, storage_format TEXT)")
    connection.execute("CREATE TABLE saved_revision_nodes(run_id TEXT, digest TEXT, body TEXT, PRIMARY KEY(run_id, digest))")
    connection.execute("CREATE TABLE branch_saved_revisions(revision_id TEXT PRIMARY KEY, run_id TEXT, payload_json TEXT)")
    connection.execute("INSERT INTO run_saved_storage_formats VALUES ('run', ?)", (st.FORMAT,))
    state = st.ConnectionState()
    st.register_sqlite_functions(connection, state)
    if guards:
        assert st.install_guards(connection)
    encoder = st.Encoder("run", index=None)
    root = encoder.encode(text)
    connection.executemany("INSERT INTO saved_revision_nodes VALUES ('run', ?, ?)", list(encoder.nodes.items()))
    envelope = st.envelope_text(run_id="run", root=root, chars=len(text))
    connection.execute("INSERT INTO branch_saved_revisions VALUES ('r1', 'run', ?)", (envelope,))
    return path, connection, envelope, state


def _child_digest(connection, envelope):
    return next(d for (d,) in connection.execute("SELECT digest FROM saved_revision_nodes") if d not in envelope)


def test_snapshot_reuse_is_bounded_by_the_transaction(tmp_path):
    import sqlite3

    text = canonical(payload(events=3))
    path, connection, envelope, state = _sqlite_store(tmp_path, text)
    connection.execute("BEGIN")
    first = st.read_payload(connection, "run", envelope, state=state)
    assert first == text
    assert st.read_payload(connection, "run", envelope, state=state) is first   # same snapshot
    # Another connection changes a node and commits; this snapshot is isolated.
    other = sqlite3.connect(path)
    other.execute("UPDATE saved_revision_nodes SET body = body || ' ' WHERE digest = ?",
                  (_child_digest(other, envelope),))
    other.commit()
    assert st.read_payload(connection, "run", envelope, state=state) == text
    connection.execute("COMMIT")
    st.bump_snapshot(state)                       # transaction boundary
    connection.execute("BEGIN")
    with pytest.raises(st.SavedV2IntegrityError, match="does not match"):
        st.read_payload(connection, "run", envelope, state=state)
    connection.execute("ROLLBACK")
    # Outside an explicit transaction nothing is cached at all.
    st.bump_snapshot(state)
    assert st.snapshot_cache(connection, state) is None


@pytest.mark.parametrize("change", [
    "UPDATE saved_revision_nodes SET body = body || ' ' WHERE digest = ?",
    "DELETE FROM saved_revision_nodes WHERE digest = ?",
    "INSERT OR REPLACE INTO saved_revision_nodes SELECT run_id, digest, body || ' ' FROM saved_revision_nodes WHERE digest = ?",
])
def test_same_transaction_node_change_cannot_reuse_old_authentication(tmp_path, change):
    """Work blocker 2: a change on the SAME connection inside the SAME transaction,
    issued as raw driver SQL (no SQLAlchemy event) with the persistent triggers
    absent, must invalidate earlier authentication."""
    text = canonical(payload(events=3))
    _path, connection, envelope, state = _sqlite_store(tmp_path, text)
    connection.execute("BEGIN")
    assert st.read_payload(connection, "run", envelope, state=state) == text   # authenticated + cached
    assert state.cache is not None and state.cache.texts
    connection.execute(change, (_child_digest(connection, envelope),))
    assert state.cache is None                     # guard trigger fired
    with pytest.raises(st.SavedV2IntegrityError):
        st.read_payload(connection, "run", envelope, state=state)
    connection.execute("ROLLBACK")


def test_format_change_in_same_transaction_is_seen(tmp_path):
    text = canonical(payload(events=1))
    _path, connection, envelope, state = _sqlite_store(tmp_path, text)
    connection.execute("BEGIN")
    assert st.read_payload(connection, "run", envelope, state=state) == text
    connection.execute("DELETE FROM run_saved_storage_formats")
    with pytest.raises(st.SavedV2IntegrityError, match="v1 Run contains a v2"):
        st.read_payload(connection, "run", envelope, state=state)
    connection.execute("ROLLBACK")


def test_no_reuse_without_this_connections_guards(tmp_path):
    text = canonical(payload(events=2))
    _path, connection, envelope, state = _sqlite_store(tmp_path, text, guards=False)
    connection.execute("BEGIN")
    assert st.read_payload(connection, "run", envelope, state=state) == text
    assert st.snapshot_cache(connection, state) is None and state.cache is None
    connection.execute("UPDATE saved_revision_nodes SET body = body || ' ' WHERE digest = ?",
                       (_child_digest(connection, envelope),))
    with pytest.raises(st.SavedV2IntegrityError):
        st.read_payload(connection, "run", envelope, state=state)
    connection.execute("ROLLBACK")


def test_retained_text_is_bounded_by_data_volume(tmp_path, monkeypatch):
    """Work blocker 1: retention is bounded by characters, not entry counts."""
    texts = [canonical(payload(events=n)) for n in (1, 2, 3, 4)]
    _path, connection, envelope, state = _sqlite_store(tmp_path, texts[0])
    envelopes = [envelope]
    for text in texts[1:]:
        encoder = st.Encoder("run", index=None)
        root = encoder.encode(text)
        connection.executemany("INSERT OR IGNORE INTO saved_revision_nodes VALUES ('run', ?, ?)",
                               list(encoder.nodes.items()))
        envelopes.append(st.envelope_text(run_id="run", root=root, chars=len(text)))
    budget = len(texts[-1]) + len(texts[-2])
    monkeypatch.setattr(st, "SNAPSHOT_TEXT_CHARS", budget)
    monkeypatch.setattr(st, "SNAPSHOT_NODE_CHARS", len(texts[1]))
    connection.execute("BEGIN")
    for _ in range(3):
        for envelope, text in zip(envelopes, texts):
            assert st.read_payload(connection, "run", envelope, state=state) == text
            assert state.cache.chars <= budget
            assert state.cache.node_chars <= len(texts[1])
    connection.execute("ROLLBACK")


def test_unconsumed_or_failing_sql_result_retains_nothing(tmp_path):
    """Work blocker 1: verified text goes back to SQLite as an ordinary value; an
    abandoned or failing statement leaves no per-row registry and drops the cache."""
    import gc

    text = canonical(payload(events=3))
    _path, connection, envelope, state = _sqlite_store(tmp_path, text)
    for index in range(2, 6):
        connection.execute("INSERT INTO branch_saved_revisions VALUES (?, 'run', ?)", (f"r{index}", envelope))
    assert not hasattr(st, "_handoff") and not hasattr(st, "take_handed_off")
    connection.execute("BEGIN")
    cursor = connection.execute("SELECT saved_v2_payload(run_id, payload_json) FROM branch_saved_revisions")
    assert cursor.fetchone()[0] == text       # first row only, then abandon
    cursor.close()
    del cursor
    gc.collect()
    assert set(state.cache.texts) == {("run", st.parse_envelope(envelope, run_id="run")[0], len(text))}
    connection.execute("UPDATE branch_saved_revisions SET payload_json = ? WHERE revision_id = 'r3'",
                       (envelope.replace('"chars":', '"chars":9', 1),))
    with pytest.raises(Exception):
        connection.execute("SELECT saved_v2_payload(run_id, payload_json) FROM branch_saved_revisions").fetchall()
    assert state.cache is None                 # failed statement: nothing reusable kept
    connection.execute("ROLLBACK")


def test_writer_bounds_references_for_repeated_large_items():
    """Work blocker 3: identical large members (same digest, same CRC) must still be
    chunked; every written node respects the reader's limit."""
    big = {"blob": "x" * 5000}
    for value in ([big] * 9000, {f"k{i:05d}": big for i in range(9000)},
                  [[big] * 3] * 3000, {"a": [big] * 9000, "b": [{"c": big}] * 5000}):
        text = canonical(value)
        store = Store()
        root, _new, encoder = store.write("run", text)
        for body in encoder.nodes.values():
            _kind, children, _pieces = st.parse_node(body)
            assert len(children) <= st.WRITE_MAX_CHILDREN <= st.MAX_CHILDREN
        assert store.read("run", root, len(text)) == text


def test_writer_refuses_a_node_beyond_the_reference_limit():
    parts = [("ref", "a" * 64)] * (st.WRITE_MAX_CHILDREN + 1)
    with pytest.raises(st.SavedV2IntegrityError, match="references"):
        st.node_body("s", parts)


def test_process_body_cache_reuses_only_byte_identical_bodies(tmp_path):
    """A changed body with the same digest key is hashed again and rejected, even
    right after the unchanged body was verified and remembered."""
    text = canonical(payload(events=2))
    store, root = Store(), None
    root, _, _ = store.write("run", text)
    st.BODIES.clear()
    assert store.read("run", root, len(text)) == text
    key = next(k for k in store.rows if k[1] != root)
    store.rows[key] = store.rows[key][:-1] + ("0" if store.rows[key][-1] != "0" else "1")
    with pytest.raises(st.SavedV2IntegrityError, match="does not match"):
        store.read("run", root, len(text))


def test_native_snapshot_trace_ignores_only_nested_selects():
    """The v2 reader's own SELECTs inside its SQL function are traced as "-- SELECT";
    they must not reset the native physical read cache, while writes, savepoint
    operations and trigger bodies still do."""
    import sqlite3

    from beta_engine.infrastructure.db.native_fork_runtime_state import _statement_may_change_snapshot

    for statement in ("SELECT 1", "  select x from t", "-- SELECT digest, body FROM saved_revision_nodes"):
        assert not _statement_may_change_snapshot(statement)
    for statement in ("BEGIN", "ROLLBACK TO s", "UPDATE t SET x=1", "-- UPDATE t SET x=1",
                      "-- TRIGGER guard", "--SELECT 1", "WITH x AS (SELECT 1) DELETE FROM t"):
        assert _statement_may_change_snapshot(statement)
    # SQLite really reports function-nested statements with the "-- " prefix.
    connection = sqlite3.connect(":memory:")
    seen = []
    connection.create_function("nested", 0, lambda: connection.execute("SELECT 2").fetchone()[0])
    connection.set_trace_callback(seen.append)
    connection.execute("SELECT nested()").fetchone()
    assert "-- SELECT 2" in seen
