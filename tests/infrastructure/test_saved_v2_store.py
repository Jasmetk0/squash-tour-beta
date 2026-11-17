"""Saved v2 rope store: exact reconstruction, incremental writes, fail-closed reads.

Pure component tests of ``saved_v2_store`` (no HTTP). The ORM/SQLite and real
HTTP paths are covered by ``test_saved_v2_sqlite.py`` and
``tests/api/test_saved_v2_http.py``.
"""

import hashlib
import json

import pytest

from beta_engine.infrastructure.db import saved_v2_store as st


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
    with pytest.raises(st.SavedV2IntegrityError, match="size limit"):
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
