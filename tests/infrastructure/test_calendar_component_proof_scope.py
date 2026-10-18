"""Expensive component proof reuse is exact and confined to one lineage walk."""

from copy import deepcopy

import pytest

from beta_engine.infrastructure.db import calendar_standalone_match_state as storage

pytestmark = pytest.mark.pr_critical


def test_proof_reuse_requires_exact_component_and_owner(monkeypatch):
    original = storage._parse_saved_calendar_match_evidence
    calls = []

    def counted(payload, **scope):
        calls.append(scope)
        return original(payload, **scope)

    monkeypatch.setattr(storage, "_parse_saved_calendar_match_evidence", counted)
    payload = {"run": {}, "content": {}}
    proofs = {}
    for _ in range(3):
        assert (
            storage.load_saved_calendar_match(
                payload, run_id="r", branch_id="b", _sporting_component_proofs=proofs
            )
            is None
        )
    assert len(calls) == 1
    storage.load_saved_calendar_match(
        payload, run_id="r", branch_id="other", _sporting_component_proofs=proofs
    )
    assert len(calls) == 2
    # A new caller/lineage walk always authenticates anew.
    storage.load_saved_calendar_match(
        payload, run_id="r", branch_id="b", _sporting_component_proofs={}
    )
    assert len(calls) == 3
    corrupt = deepcopy(payload)
    corrupt["content"]["calendar_standalone_match"] = {
        "fingerprint": "a" * 64,
        "state": {},
    }
    with pytest.raises(ValueError):
        storage.load_saved_calendar_match(
            corrupt, run_id="r", branch_id="b", _sporting_component_proofs=proofs
        )
    assert len(calls) == 4


def test_live_source_reuse_requires_exact_saved_bytes_and_owner():
    import json
    from types import SimpleNamespace

    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        load_checkpoint,
    )
    from tests.domain.test_calendar_native_checkpoint_compatibility import initial

    checkpoint = initial()
    row = SimpleNamespace(
        payload_json=checkpoint.model_dump_json(), fingerprint=checkpoint.fingerprint
    )
    session = SimpleNamespace(get=lambda *_args: row)
    scope = {
        "run_id": checkpoint.run_id,
        "branch_id": checkpoint.branch_id,
        "_verified_source": checkpoint,
    }
    assert load_checkpoint(session, **scope) is checkpoint
    raw = json.loads(row.payload_json)
    raw["players"][0]["current_form"] += 1
    row.payload_json = json.dumps(raw)
    with pytest.raises(ValueError, match="identity/hash"):
        load_checkpoint(session, **scope)
    row.payload_json = checkpoint.model_dump_json()
    with pytest.raises(ValueError, match="identity/hash"):
        load_checkpoint(session, **{**scope, "branch_id": "foreign"})


def test_prevalidated_decoder_rechecks_source_identity_and_fingerprint():
    # The production service may only call this *after* its full Saved HEAD
    # validator. This local check ensures its lightweight decoder still detects
    # a different Run/Branch or altered signed component bytes.
    from tests.domain.test_calendar_native_checkpoint_compatibility import initial

    checkpoint = initial()
    payload = {
        "content": {
            "calendar_player_sporting_checkpoint": {
                "fingerprint": checkpoint.fingerprint,
                "state": checkpoint.model_dump(mode="json"),
            }
        }
    }
    evidence, saved, tour = storage.decode_prevalidated_calendar_sources(
        payload, run_id=checkpoint.run_id, branch_id=checkpoint.branch_id
    )
    assert evidence is None and tour is None and saved == checkpoint
    with pytest.raises(ValueError, match="scope/hash"):
        storage.decode_prevalidated_calendar_sources(
            payload, run_id=checkpoint.run_id, branch_id="foreign"
        )
    corrupt = deepcopy(payload)
    corrupt["content"]["calendar_player_sporting_checkpoint"]["fingerprint"] = "f" * 64
    with pytest.raises(ValueError, match="scope/hash"):
        storage.decode_prevalidated_calendar_sources(
            corrupt, run_id=checkpoint.run_id, branch_id=checkpoint.branch_id
        )


def test_prevalidated_lifecycle_decodes_verified_scope_without_replaying_history():
    from tests.infrastructure.test_player_lifecycle_fork_remap import _source_payload
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        decode_prevalidated_lifecycle,
    )

    payload, expected = _source_payload()
    assert decode_prevalidated_lifecycle(
        payload, run_id="run", branch_id="source"
    ) == expected
    assert decode_prevalidated_lifecycle(
        {"content": {}}, run_id="run", branch_id="source"
    ) is None
    with pytest.raises(ValueError, match="identity/hash"):
        decode_prevalidated_lifecycle(
            payload, run_id="run", branch_id="other"
        )
    damaged = deepcopy(payload)
    damaged["content"]["player_lifecycle"]["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="identity/hash"):
        decode_prevalidated_lifecycle(
            damaged, run_id="run", branch_id="source"
        )
    damaged = deepcopy(payload)
    damaged["content"]["player_lifecycle"]["states"][1]["predecessor_fingerprint"] = "wrong"
    with pytest.raises(ValueError, match="identity/hash"):
        decode_prevalidated_lifecycle(
            damaged, run_id="run", branch_id="source"
        )


def test_verified_restore_skips_repeating_signed_checkpoint_fold(monkeypatch):
    # Only the repository coordinator may provide already authenticated Saved
    # sources. The adapter must still match its independent live SQLite owner.
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting
    from tests.domain.test_calendar_native_checkpoint_compatibility import initial

    source = initial()
    deleted = []
    installed = []
    row = object()

    class Session:
        def get(self, _model, _key):
            return row

        def delete(self, item):
            deleted.append(item)

        def flush(self):
            pass

    def must_not_revalidate(*_args, **_kwargs):
        raise AssertionError("Saved sporting replay repeated after source validation")

    monkeypatch.setattr(sporting, "saved_checkpoint", must_not_revalidate)
    monkeypatch.setattr(sporting, "load_checkpoint", lambda *_a, **_k: source)
    monkeypatch.setattr(sporting, "put_checkpoint", lambda _s, state: installed.append(state))
    sporting.restore_checkpoint(
        Session(), current_payload={}, target_payload={},
        current=None, target=None, run_id=source.run_id, branch_id=source.branch_id,
        _validated_states=(source, source),
    )
    assert deleted == [row]
    assert installed == [source]


def test_verified_restore_skips_duplicate_saved_tour_replay(monkeypatch):
    from beta_engine.infrastructure.db import calendar_tour as tour

    class Session:
        def get(self, _model, _key):
            return None

        def flush(self):
            pass

    def must_not_revalidate(*_args, **_kwargs):
        raise AssertionError("Signed Tour validation was repeated after lineage gate")

    monkeypatch.setattr(tour, "saved_tour", must_not_revalidate)
    monkeypatch.setattr(tour, "load_tour", lambda *_a, **_k: None)
    tour.restore_tour(
        Session(), current_payload={}, target_payload={},
        run_id="run", branch_id="branch", _validated_states=(None, None),
    )


def test_verified_restore_dispatch_preserves_strict_default(monkeypatch):
    from beta_engine.infrastructure.db import calendar_standalone_match_state as match

    decoded = []
    restored = []

    class Session:
        def flush(self):
            pass

    def decode(_payload, **_scope):
        decoded.append("original")
        return None

    monkeypatch.setattr(match, "_parse_saved_calendar_match_evidence", decode)
    monkeypatch.setattr(match, "load_match_rows", lambda *_a, **_k: ())
    monkeypatch.setattr(
        "beta_engine.infrastructure.db.calendar_tour.restore_tour",
        lambda *_a, **kw: restored.append(("tour", kw.get("_validated_states"))),
    )
    monkeypatch.setattr(
        "beta_engine.infrastructure.db.calendar_sporting_checkpoint.restore_checkpoint",
        lambda *_a, **kw: restored.append(("checkpoint", kw.get("_validated_states"))),
    )
    match.restore_saved_calendar_match(
        Session(), current_payload={}, target_payload={},
        run_id="r", branch_id="b",
        _validated_saved_sources=((None, None, None), (None, None, None)),
    )
    assert decoded == []
    assert restored == [("tour", (None, None)), ("checkpoint", (None, None))]
    restored.clear()
    match.restore_saved_calendar_match(
        Session(), current_payload={}, target_payload={}, run_id="r", branch_id="b",
    )
    assert decoded == ["original", "original"]
    assert restored == [("tour", None), ("checkpoint", None)]


def test_tour_restore_lifecycle_reuses_signed_inputs_but_checks_live(monkeypatch):
    from tests.infrastructure.test_player_lifecycle_fork_remap import _source_payload
    from beta_engine.infrastructure.db import player_lifecycle_state as module

    payload, original = _source_payload()

    class Rows:
        def order_by(self, *_args):
            return self

    class Session:
        def scalars(self, _query):
            return Rows()

        def execute(self, _query):
            pass

    # The validated inputs must NOT fold Saved life again, but SQLite must
    # still be independently read and compared before any restoration write.
    loaded = []
    def fail_validation(*_a, **_k):
        raise AssertionError("Redundant full Signed lifecycle replay")
    monkeypatch.setattr(module, "load_saved_lifecycle", fail_validation)
    monkeypatch.setattr(module, "_load", fail_validation)

    class GoodSession:
        def scalars(self, _query):
            class Result:
                def order_by(self, *_args):
                    return self
                def all(self):
                    return []
            return Result()

    # A missing live historical row must block the optimized restore rather
    # than quietly accepting the supplied signed component.
    with pytest.raises(ValueError, match="Live player lifecycle differs"):
        module.restore_saved_lifecycle(
            GoodSession(), current_payload=payload, target_payload=payload,
            run_id="run", branch_id="source",
            _validated_states=(original, original),
        )
