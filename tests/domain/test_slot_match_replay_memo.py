"""The batched private replay memo keeps the original one-by-one LRU semantics.

``_simulate_slot_matches`` looks up a whole slot first, computes the misses as
one batch and then refreshes/inserts in request order. With a small test cap
this must leave exactly the cache order, entries and byte accounting of the
original per-match implementation (reproduced verbatim below as the oracle)
for mixed hits/misses, eviction of a later item of the same batch, duplicate
keys and over-limit entries, and must always return fresh decoded values.
"""

from __future__ import annotations

import pytest

from beta_engine.domain.matches import slot_batch
from beta_engine.domain.matches.models import MatchResult
from beta_engine.domain.tournaments import calendar_global_slots as slots
from tests.domain.test_slot_match_batch import InProcessExecutor, corpus

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def items():
    return corpus(6)


def _key(item):
    context, seed, anchor, health = item
    return (seed, anchor, context.model_dump_json().encode(), health.model_dump_json().encode())


@pytest.fixture(scope="module")
def sizes(items):
    out = []
    for item in items:
        encoded = slot_batch.simulate_batch([item])[0].model_dump_json().encode()
        key = _key(item)
        out.append(128 + len(item[2]) + len(key[2]) + len(key[3]) + len(encoded))
    return out


def _original_one(scope, item, limit, calls):
    """``buuk`` 29784d5 ``_simulate_slot_match`` with the cap as a parameter."""
    context, seed, anchor, health = item
    cache = scope["match_results"]
    key = (seed, anchor, context.model_dump_json().encode(), health.model_dump_json().encode())
    previous = cache.pop(key, None)
    if previous is not None:
        cache[key] = previous
        return MatchResult.model_validate_json(previous[1])
    calls.append(context.match_id)
    result = slot_batch.simulate_frozen(context, seed=seed, anchor=anchor, health=health)
    encoded = result.model_dump_json().encode()
    size = 128 + len(anchor) + len(key[2]) + len(key[3]) + len(encoded)
    if size <= limit:
        while scope["match_result_bytes"] + size > limit:
            removed_size, _ = cache.pop(next(iter(cache)))
            scope["match_result_bytes"] -= removed_size
        cache[key] = (size, encoded)
        scope["match_result_bytes"] += size
    return result


def _scope(prefill, items, sizes):
    scope = {"match_results": {}, "match_result_bytes": 0}
    for i in prefill:
        encoded = slot_batch.simulate_batch([items[i]])[0].model_dump_json().encode()
        scope["match_results"][_key(items[i])] = (sizes[i], encoded)
        scope["match_result_bytes"] += sizes[i]
    return scope


def _state(scope, items):
    names = {_key(item): i for i, item in enumerate(items)}
    return ([(names[k], v[0], v[1]) for k, v in scope["match_results"].items()],
            scope["match_result_bytes"])


def _batched(scope, batch, limit, monkeypatch, executor=None):
    monkeypatch.setattr(slots, "_MATCH_REPLAY_BYTES", limit)
    token = slots._replay_projections.set({"fingerprints": {}, "tournaments": {}, **scope})
    real = slot_batch.simulate_batch
    calls = []

    def counting(values, **kwargs):
        calls.extend(context.match_id for context, *_ in values)
        return real(values, executor=executor)

    monkeypatch.setattr(slots, "simulate_batch", counting)
    try:
        results = slots._simulate_slot_matches(batch)
        live = slots._replay_projections.get()
        scope["match_results"], scope["match_result_bytes"] = live["match_results"], live["match_result_bytes"]
    finally:
        slots._replay_projections.reset(token)
    return results, calls


SCENARIOS = {
    # name: (prefilled indexes in LRU order, batch indexes, cap as a function of sizes)
    "mixed-hit-miss": ((1, 3), (0, 1, 2, 3), lambda s: sum(s) * 2),
    "later-item-evicted-by-earlier-miss": ((2, 4), (0, 2), lambda s: s[2] + s[4] + s[0] - 1),
    "earlier-hit-refresh-then-eviction": ((0, 1, 2), (1, 3, 0), lambda s: s[0] + s[1] + s[2]),
    "duplicate-keys": ((), (0, 0, 1, 0), lambda s: sum(s) * 2),
    # The deuce match (index 0) alone exceeds the cap; 1 and 2 fit together.
    "over-limit-entry": ((1,), (0, 1, 2), lambda s: s[1] + s[2] if s[0] > s[1] + s[2] else 0),
    "tiny-cap-nothing-fits": ((), (0, 1, 2), lambda s: min(s) - 1),
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
@pytest.mark.parametrize("pooled", [False, True], ids=["sequential", "executor"])
def test_batched_memo_equals_one_by_one_lru(name, pooled, items, sizes, monkeypatch):
    prefill, batch_indexes, cap = SCENARIOS[name]
    limit = cap(sizes)
    if not limit:
        pytest.skip("corpus sizes do not produce an over-limit entry")
    batch = [items[i] for i in batch_indexes]
    reference = _scope(prefill, items, sizes)
    calls = []
    expected = [_original_one(reference, item, limit, calls) for item in batch]
    actual_scope = _scope(prefill, items, sizes)
    executor = InProcessExecutor(seed=3) if pooled else None
    actual, batch_calls = _batched(actual_scope, batch, limit, monkeypatch, executor)
    assert [r.model_dump_json() for r in actual] == [r.model_dump_json() for r in expected]
    assert _state(actual_scope, items) == _state(reference, items)
    assert actual_scope["match_result_bytes"] <= limit
    assert actual_scope["match_result_bytes"] == sum(v[0] for v in actual_scope["match_results"].values())
    # The batch never computes more than the misses of its own lookup.
    # The batch computes each distinct key its lookup missed exactly once, so
    # never more engine calls than the original (fewer if it evicted a hit).
    known = {_key(items[i]) for i in prefill}
    assert len(batch_calls) == len({_key(item) for item in batch} - known)
    assert len(set(batch_calls)) == len(batch_calls) <= len(calls)


def test_every_hit_is_a_fresh_isolated_decoded_value(items, sizes, monkeypatch):
    scope = _scope((0, 1), items, sizes)
    first, _ = _batched(scope, [items[0], items[1]], sum(sizes) * 2, monkeypatch)
    second, calls = _batched(scope, [items[0], items[1]], sum(sizes) * 2, monkeypatch)
    assert calls == []
    for a, b in zip(first, second):
        assert a == b and a is not b
        assert a.rally_log is not b.rally_log and a.rally_log.events[0] is not b.rally_log.events[0]
    cached = [v[1] for v in scope["match_results"].values()]
    # Mutating a returned (private) decoded object never reaches the memo bytes.
    object.__setattr__(second[0].rally_log, "events", ())
    third, _ = _batched(scope, [items[0], items[1]], sum(sizes) * 2, monkeypatch)
    assert [v[1] for v in scope["match_results"].values()] == cached
    assert third == first
