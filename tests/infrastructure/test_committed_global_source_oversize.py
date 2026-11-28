"""Post-commit retention after a manual Tour Save: oversize is decided from the
Save's own canonical payload text, never by re-encoding the complete value.

Skipping a retention is always safe (a later reader misses and strictly
decodes); these tests prove the cache ends in EXACTLY the state the original
re-encoding path produces, including at the byte boundaries.
"""

from copy import deepcopy
from threading import Lock
from types import SimpleNamespace

import pytest

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.run_revisions import canonical_json
from beta_engine.infrastructure.db import native_fork_source_projection as cache

pytestmark = pytest.mark.pr_critical

ENVELOPE = len('{"calendar_player_sporting_checkpoint":}')


def _source(checkpoint_filler, other_filler="o", *, name="saved"):
    body = {"schema_version": "calendar_sporting_checkpoint.v13", "filler": checkpoint_filler}
    component = {"state": body, "fingerprint": canonical_hash(body)}
    payload = {
        "branch": {"branch_id": "branch"},
        "content": {
            "calendar_player_sporting_checkpoint": component,
            "calendar_tour_authority": {"state": {"schema_version": "calendar_tour_authority.v5"}},
            "zzz_other": other_filler,
        },
        "run": {"name": name},
    }
    source = SimpleNamespace(run_id="run", branch_id="branch", payload=payload)
    checkpoint = SimpleNamespace(schema_version="calendar_sporting_checkpoint.v13", run_id="run",
                                 branch_id="branch", fingerprint=component["fingerprint"])
    captured = (SimpleNamespace(evidence=[1]), checkpoint, SimpleNamespace(tour=[2]))
    return source, captured, component


def _retained(source, captured, *, text, take=True):
    repository = SimpleNamespace(_revision_validation_lock=Lock())
    cache.remember_committed_global_sources(repository, deepcopy(source), deepcopy(captured),
                                            _take_ownership=take, _payload_text=text)
    retained = getattr(repository, "_global_tour_projection_cache", {})
    return {key: (entry[0], type(entry[1]).__name__) for key, entry in retained.items()}


def _sizes(source, component):
    return (len(canonical_json(source.payload)),
            len(canonical_json({"calendar_player_sporting_checkpoint": component})))


@pytest.mark.parametrize("limit_from", ["payload-1", "payload", "component-1", "component"])
@pytest.mark.parametrize("take", [False, True])
def test_same_retention_as_the_original_re_encoding_at_every_boundary(monkeypatch, limit_from, take):
    source, captured, component = _source("x" * 600, "y" * 300)
    payload_size, component_size = _sizes(source, component)
    limit = {"payload-1": payload_size - 1, "payload": payload_size,
             "component-1": component_size - 1, "component": component_size}[limit_from]
    monkeypatch.setattr(cache, "MAX_GLOBAL_TOUR_BYTES", limit)
    original = _retained(source, captured, text=None, take=take)
    candidate = _retained(source, captured, text=canonical_json(source.payload), take=take)
    assert candidate == original
    expected_entries = 2 if limit >= payload_size else 1 if limit >= component_size else 0
    assert len(original) == expected_entries


def test_derived_checkpoint_length_is_exact_for_escapes_and_key_order():
    for filler in ("", "a", "é☃\"\\\n\t", "x" * 1000, ["nested", {"b": 1, "a": None}]):
        source, _, component = _source(filler, {"ü": "\u0000"})
        text = canonical_json(source.payload)
        assert text.isascii()
        assert (cache._committed_checkpoint_text_length(source, text) + ENVELOPE
                == len(canonical_json({"calendar_player_sporting_checkpoint": component})))


def test_oversize_never_re_encodes_or_rechecks_the_complete_value(monkeypatch):
    source, captured, component = _source("x" * 5000)
    text = canonical_json(source.payload)
    monkeypatch.setattr(cache, "MAX_GLOBAL_TOUR_BYTES", 1000)
    encoded = []
    original_json = cache.canonical_json

    def observed(value):
        result = original_json(value)
        encoded.append(len(result))
        return result

    monkeypatch.setattr(cache, "canonical_json", observed)
    monkeypatch.setattr(cache, "_value_identity",
                        lambda *a: pytest.fail("complete payload re-encoded for an oversize Save"))
    monkeypatch.setattr(cache, "_checked_checkpoint",
                        lambda *a: pytest.fail("nothing is retained, so nothing needs re-checking"))
    repository = SimpleNamespace(_revision_validation_lock=Lock())
    cache.remember_committed_global_sources(repository, source, captured,
                                            _take_ownership=True, _payload_text=text)
    assert not getattr(repository, "_global_tour_projection_cache", {})
    # Only the payload WITHOUT the checkpoint was encoded, once.
    assert encoded == [len(text) - len(canonical_json(component)) + len("null")]


@pytest.mark.parametrize("text", [None, 123, b"bytes", "short", "é" * 5000])
def test_absent_short_or_non_ascii_text_keeps_the_original_path(monkeypatch, text):
    source, captured, _ = _source("x" * 5000)
    monkeypatch.setattr(cache, "MAX_GLOBAL_TOUR_BYTES", 1000)
    calls = []
    original_identity = cache._value_identity

    def identity(*args):
        calls.append(args)
        return original_identity(*args)

    monkeypatch.setattr(cache, "_value_identity", identity)
    _retained(source, captured, text=text)
    assert len(calls) == 1


def test_a_component_that_fits_is_still_retained_and_rechecked(monkeypatch):
    source, captured, component = _source("x" * 10, "y" * 5000)
    payload_size, component_size = _sizes(source, component)
    monkeypatch.setattr(cache, "MAX_GLOBAL_TOUR_BYTES", component_size)
    checked = []
    original_check = cache._checked_checkpoint

    def check(*args):
        checked.append(args[0])
        return original_check(*args)

    monkeypatch.setattr(cache, "_checked_checkpoint", check)
    repository = SimpleNamespace(_revision_validation_lock=Lock())
    cache.remember_committed_global_sources(repository, source, captured,
                                            _payload_text=canonical_json(source.payload))
    assert checked == [captured[1]]
    assert [entry[0] for entry in repository._global_tour_projection_cache.values()] == [component_size]
    # A mismatched captured value for a FITTING component is still rejected.
    bad = (captured[0], SimpleNamespace(**{**vars(captured[1]), "fingerprint": "0" * 64}), captured[2])
    with pytest.raises(ValueError, match="scope/hash"):
        cache.remember_committed_global_sources(SimpleNamespace(_revision_validation_lock=Lock()),
                                                source, bad, _payload_text=canonical_json(source.payload))
