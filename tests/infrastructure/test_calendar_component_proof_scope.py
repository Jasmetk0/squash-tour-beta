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
