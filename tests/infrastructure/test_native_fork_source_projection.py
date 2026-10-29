"""The projection cache is a bounded value cache, never a physical-row proof."""

from threading import Lock
from types import SimpleNamespace

import pytest

from beta_engine.infrastructure.db.native_fork_source_projection import (
    decoded_original_source,
)

pytestmark = pytest.mark.pr_critical


def repository():
    return SimpleNamespace(_revision_validation_lock=Lock())


def source(value=1, **fields):
    return SimpleNamespace(
        run_id="run",
        branch_id="branch",
        content_hash="same-declared-hash",
        payload={"content": {"value": value}},
        **fields,
    )


def test_exact_current_value_and_defensive_copies():
    repo = repository()
    calls = []

    def decode(src):
        calls.append(src.payload["content"]["value"])
        return SimpleNamespace(items=[{"value": calls[-1]}])

    first = decoded_original_source(repo, source(), decode)
    first.items[0]["value"] = "caller mutation"
    second = decoded_original_source(repo, source(), decode)
    second.items.clear()
    assert decoded_original_source(repo, source(), decode).items == [{"value": 1}]
    assert calls == [1]
    assert decoded_original_source(repo, source(2), decode).items == [{"value": 2}]
    assert calls == [1, 2]  # Same declared hash cannot hide different actual data.


def test_scope_repository_restart_and_failed_decode_are_independent():
    repo = repository()
    calls = []

    def decode(src):
        calls.append((src.run_id, src.branch_id))
        if src.payload["content"]["value"] == "bad":
            raise ValueError("invalid current input")
        return []

    decoded_original_source(repo, source(), decode)
    for _ in range(2):
        with pytest.raises(ValueError, match="invalid current input"):
            decoded_original_source(repo, source("bad"), decode)
    changed_owner = source()
    changed_owner.branch_id = "another"
    decoded_original_source(repo, changed_owner, decode)
    decoded_original_source(repository(), source(), decode)
    assert len(calls) == 5


def test_entry_and_byte_budgets_and_oversize_bypass(monkeypatch):
    from beta_engine.infrastructure.db import native_fork_source_projection as cache

    repo = repository()
    monkeypatch.setattr(cache, "MAX_SOURCE_BYTES", 100)
    for value in range(5):
        decoded_original_source(
            repo, source(value), lambda src: [src.payload["content"]["value"]]
        )
    assert len(repo._native_source_projection_cache) == cache.MAX_SOURCES
    assert sum(v[0] for v in repo._native_source_projection_cache.values()) <= 100
    before = dict(repo._native_source_projection_cache)
    decoded_original_source(repo, source("x" * 101), lambda src: [])
    assert repo._native_source_projection_cache == before
    decoded_original_source(repo, source("x" * 45), lambda src: [])
    assert sum(v[0] for v in repo._native_source_projection_cache.values()) <= 100


def test_global_checkpoint_decode_binds_complete_values_and_isolates_nested_copies():
    from copy import deepcopy
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.native_fork_source_projection import decoded_global_checkpoint_component

    class Value:
        schema_version = 'calendar_sporting_checkpoint.v13'
        run_id = 'run'
        branch_id = 'branch'

        def __init__(self, body):
            self.body = deepcopy(body)

        @property
        def fingerprint(self):
            return canonical_hash(self.body)

    body = {'nested': {'actual': [1, 2]}}
    component = {'state': body, 'fingerprint': canonical_hash(body)}
    repo, calls = repository(), []

    def decode(raw):
        calls.append(deepcopy(raw))
        return Value(raw['state'])

    def read(current=component, **scope):
        return decoded_global_checkpoint_component(repo, current,
            **({'run_id': 'run', 'branch_id': 'branch'} | scope), decode=decode)

    first = read()
    first.body['nested']['actual'].append('caller mutation')
    assert read(deepcopy(component)).body == body
    assert len(calls) == 1
    with pytest.raises(ValueError, match='scope/hash'):
        read(branch_id='foreign')
    changed = deepcopy(component)
    changed['state']['nested']['actual'].append(3)
    for _ in range(2):
        with pytest.raises(ValueError, match='scope/hash'):
            read(changed)  # An unchanged declared hash cannot hide changed data.
    changed['fingerprint'] = canonical_hash(changed['state'])
    assert read(changed).body == changed['state']
    assert read().body == body


def test_global_checkpoint_decode_shares_existing_budget_and_bypasses_oversize(monkeypatch):
    from beta_engine.infrastructure.db import native_fork_source_projection as cache
    from beta_engine.domain.run_packages import canonical_hash

    repo = repository()
    monkeypatch.setattr(cache, 'MAX_GLOBAL_TOUR_BYTES', 200)
    def decode(raw):
        return SimpleNamespace(schema_version='calendar_sporting_checkpoint.v13',
            run_id='run', branch_id='branch', fingerprint=canonical_hash(raw['state']))
    for index in range(8):
        body = {'index': index}
        component = {'state': body, 'fingerprint': canonical_hash(body)}
        cache.decoded_global_checkpoint_component(repo, component,
            run_id='run', branch_id='branch', decode=decode)
    retained = repo._global_tour_projection_cache
    assert len(retained) <= 4
    assert sum(item[0] for item in retained.values()) <= 200
    before = dict(retained)
    body = {'oversize': 'x' * 201}
    component = {'state': body, 'fingerprint': canonical_hash(body)}
    cache.decoded_global_checkpoint_component(repo, component,
        run_id='run', branch_id='branch', decode=decode)
    assert retained == before
