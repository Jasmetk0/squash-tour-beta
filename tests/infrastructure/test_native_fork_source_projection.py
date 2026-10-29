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


def test_whole_dto_adapter_retains_one_checkpoint_and_preserves_complete_reuse(monkeypatch):
    from copy import deepcopy
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db import native_fork_source_projection as cache

    body = {'schema_version': 'calendar_sporting_checkpoint.v13', 'nested': {'values': [1]}}
    component = {'state': body, 'fingerprint': canonical_hash(body)}
    cp = SimpleNamespace(schema_version='calendar_sporting_checkpoint.v13', run_id='run',
        branch_id='branch', fingerprint=component['fingerprint'], body=deepcopy(body))
    src = source()
    src.payload = {'run': {'name': 'saved'}, 'content': {
        'calendar_player_sporting_checkpoint': component,
        'calendar_tour_authority': {'state': {'schema_version': 'calendar_tour_authority.v5'}},
    }}
    captured = (SimpleNamespace(nested=[{'evidence': 1}]), cp,
                SimpleNamespace(schema_version='legacy-test-value', nested=[{'tour': 2}]))
    repo = repository()
    copies = []
    original_copy = cache._copy_decoded_value

    def observe(value, *args):
        copies.append(value)
        return original_copy(value, *args)

    monkeypatch.setattr(cache, '_copy_decoded_value', observe)
    cache.remember_committed_global_sources(repo, src, captured)
    assert copies == [cp, (captured[0], captured[2])]
    retained = repo._global_tour_projection_cache
    assert len(retained) == 2
    assert sum(v[0] for v in retained.values()) == len(cache.canonical_json(src.payload).encode())

    def forbidden(_):
        pytest.fail('complete DTO or component was needlessly decoded again')

    expected = deepcopy(captured)
    cp.body['nested']['values'].append('capturing caller')
    captured[0].nested[0]['evidence'] = 'capturing caller'
    first = cache.decoded_global_tour_source(repo, deepcopy(src), forbidden)
    assert first == expected
    first[1].body['nested']['values'].clear()
    first[0].nested.clear()
    first[2].nested[0]['tour'] = 'reading caller'
    assert cache.decoded_global_tour_source(repo, src, forbidden) == expected
    assert cache.decoded_global_checkpoint_component(repo, component,
        run_id='run', branch_id='branch', decode=forbidden) == expected[1]

    # A declared component fingerprint cannot substitute for the model guard
    # on a new complete key. This also leaves the previous entries intact.
    mismatched = deepcopy(src)
    mismatched.payload['run']['name'] = 'another Saved'
    bad = deepcopy(expected)
    bad[1].fingerprint = '0' * 64
    before = dict(retained)
    with pytest.raises(ValueError, match='scope/hash'):
        cache.remember_committed_global_sources(repo, mismatched, bad)
    assert retained == before

    # Same component, different COMPLETE Saved content: no whole-tuple reuse.
    changed = deepcopy(src)
    changed.payload['run']['name'] = 'rehashed changed source'
    with pytest.raises(LookupError):
        cache.decoded_global_tour_source(repo, changed, lambda _: (_ for _ in ()).throw(LookupError()))
    foreign = deepcopy(src)
    foreign.branch_id = 'foreign'
    with pytest.raises(LookupError):
        cache.decoded_global_tour_source(repo, foreign, lambda _: (_ for _ in ()).throw(LookupError()))

    # Evict the component via the ordinary shared budget. Its adapter must not
    # keep that model alive, and a later whole read must use the strict fallback.
    monkeypatch.setattr(cache, 'MAX_GLOBAL_TOUR_BYTES', 300)
    for i in range(4):
        state = {'i': i}
        raw = {'state': state, 'fingerprint': canonical_hash(state)}
        cache.decoded_global_checkpoint_component(repo, raw, run_id='run', branch_id='branch',
            decode=lambda r: SimpleNamespace(schema_version='calendar_sporting_checkpoint.v13',
                run_id='run', branch_id='branch', fingerprint=r['fingerprint']))
    assert not any(isinstance(v[1], cache._GlobalTourValue) for v in retained.values())
    assert sum(v[0] for v in retained.values()) <= 300
    with pytest.raises(LookupError):
        cache.decoded_global_tour_source(repo, src, lambda _: (_ for _ in ()).throw(LookupError()))
