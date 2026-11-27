"""Strict-decode reuse of v13 checkpoint parts is exact-text keyed and never shared.

Component tests of ``checkpoint_part_decode``. A real played v13 checkpoint
(global slots with full MatchResults) is checked through HTTP/SQLite in
``tests/api/test_checkpoint_part_decode_real.py``.
"""

from __future__ import annotations

import threading

import pytest

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.infrastructure.db import checkpoint_part_decode as parts

pytestmark = pytest.mark.pr_critical


class Part(FrozenInput):
    values: dict[str, int]


class Other(FrozenInput):
    values: dict[str, int]


@pytest.fixture(autouse=True)
def empty_cache():
    parts.clear()
    yield
    parts.clear()


def _counting(model):
    calls = []

    def parse(text):
        calls.append(text)
        return model.model_validate_json(text)
    parse.__qualname__ = f"{model.__qualname__}.parse"
    return parse, calls


def test_identical_text_is_parsed_once_and_every_use_gets_a_fresh_private_value():
    parse, calls = _counting(Part)
    first, key = parts.decode('{"values": {"a": 1}}', parse)
    second, again = parts.decode('{"values": {"a": 1}}', parse)
    assert calls == ['{"values": {"a": 1}}'] and key == again
    assert first == second and first is not second and first.values is not second.values
    second.values['a'] = 999          # a caller mutating its own copy ...
    third, _ = parts.decode('{"values": {"a": 1}}', parse)
    assert third.values == {'a': 1}   # ... never reaches the cache or other callers
    assert parts.stats()['hits'] == 2 and parts.stats()['misses'] == 1


@pytest.mark.parametrize("changed", [
    '{"values": {"a": 2}}',            # other value
    '{"values":{"a": 1}}',             # same value, other bytes: its own strict parse
    '{"values": {"a": 1}} ',
])
def test_any_other_text_takes_its_own_strict_parse(changed):
    parse, calls = _counting(Part)
    parts.decode('{"values": {"a": 1}}', parse)
    value, _ = parts.decode(changed, parse)
    assert calls == ['{"values": {"a": 1}}', changed]
    assert value == Part.model_validate_json(changed)


def test_the_parser_is_part_of_the_identity():
    part, part_calls = _counting(Part)
    other, other_calls = _counting(Other)
    a, key_a = parts.decode('{"values": {"a": 1}}', part)
    b, key_b = parts.decode('{"values": {"a": 1}}', other)
    assert key_a != key_b and type(a) is Part and type(b) is Other
    assert len(part_calls) == len(other_calls) == 1


def test_invalid_text_raises_the_original_error_and_is_never_retained():
    parse, calls = _counting(Part)
    for _ in range(2):
        with pytest.raises(ValueError):
            parts.decode('{"values": {"a": "x"}}', parse)
    assert len(calls) == 2 and parts.stats()['entries'] == 0


def test_byte_budget_eviction_and_oversized_parts(monkeypatch):
    parse, calls = _counting(Part)
    first, _ = parts.decode('{"values": {"a": 1}}', parse)
    blob = parts.stats()['bytes']
    monkeypatch.setattr(parts, 'MAX_CACHE_BYTES', blob * 2)
    parts.decode('{"values": {"b": 2}}', parse)
    parts.decode('{"values": {"c": 3}}', parse)     # evicts the least recently used
    assert parts.stats()['bytes'] <= blob * 2 and parts.stats()['evictions'] >= 1
    parts.decode('{"values": {"a": 1}}', parse)
    assert calls.count('{"values": {"a": 1}}') == 2
    monkeypatch.setattr(parts, 'MAX_PART_BYTES', 4)
    value, key = parts.decode('{"values": {"z": 9}}', parse)
    assert key is None and value.values == {'z': 9} and parts.stats()['uncached'] == 1


def test_a_damaged_entry_is_dropped_and_parsed_again():
    parse, calls = _counting(Part)
    _, key = parts.decode('{"values": {"a": 1}}', parse)
    with parts._lock:
        parts._entries[key] = b'not a pickle'
    value, _ = parts.decode('{"values": {"a": 1}}', parse)
    assert value.values == {'a': 1} and len(calls) == 2 and parts.stats()['pickle_errors'] == 1


def test_concurrent_decoders_get_equal_independent_values():
    parse, _ = _counting(Part)
    parts.decode('{"values": {"a": 1}}', parse)
    barrier, out = threading.Barrier(4), []

    def run():
        barrier.wait()
        out.append(parts.decode('{"values": {"a": 1}}', parse)[0])

    threads = [threading.Thread(target=run) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(out) == 4 and all(value == out[0] for value in out)
    assert len({id(value) for value in out}) == 4


def test_a_context_dependent_validation_never_uses_or_fills_the_cache():
    from beta_engine.domain.matches import content_hash

    parse, calls = _counting(Part)
    parts.decode('{"values": {"a": 1}}', parse)
    token = content_hash._deferred.set([Part, False])
    try:
        value, key = parts.decode('{"values": {"a": 1}}', parse)
        parts.decode('{"values": {"b": 1}}', parse)
    finally:
        content_hash._deferred.reset(token)
    assert key is None and value.values == {'a': 1} and len(calls) == 3
    assert parts.stats()['entries'] == 1


def test_a_known_oversize_declared_value_skips_only_the_cache_key(monkeypatch):
    from types import SimpleNamespace

    from beta_engine.infrastructure.db import native_fork_source_projection as projection

    repository = SimpleNamespace(_revision_validation_lock=threading.Lock())
    encoded, decoded = [], []
    real = projection.canonical_json
    monkeypatch.setattr(projection, 'canonical_json', lambda value: encoded.append(1) or real(value))
    monkeypatch.setattr(projection, 'MAX_GLOBAL_TOUR_BYTES', 8)

    def component(fingerprint):
        return {'fingerprint': fingerprint, 'state': {'schema_version': 'calendar_sporting_checkpoint.v13'}}

    def decode(raw):
        decoded.append(raw)
        return SimpleNamespace(schema_version='calendar_sporting_checkpoint.v13', run_id='run',
                               branch_id='branch', fingerprint=raw['fingerprint'])

    for _ in range(3):
        value = projection.decoded_global_checkpoint_component(
            repository, component('f' * 64), run_id='run', branch_id='branch', decode=decode)
        assert value.fingerprint == 'f' * 64
    assert len(encoded) == 1 and len(decoded) == 3       # strict decode every time, key once
    # Another declared value, Run or Branch is measured again.
    projection.decoded_global_checkpoint_component(
        repository, component('e' * 64), run_id='run', branch_id='branch', decode=decode)
    assert len(encoded) == 2
    # A lying hint cannot authorize anything: the decoded value is still checked.
    with pytest.raises(ValueError):
        projection.decoded_global_checkpoint_component(
            repository, component('f' * 64), run_id='run', branch_id='branch',
            decode=lambda raw: SimpleNamespace(schema_version='calendar_sporting_checkpoint.v13',
                                               run_id='run', branch_id='branch', fingerprint='0' * 64))
