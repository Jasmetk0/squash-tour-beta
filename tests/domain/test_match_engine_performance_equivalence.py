"""MatchEngine performance changes must not change a single result byte.

Golden fingerprints were computed on ``buuk 320e476`` (before these changes)
with ``scripts/benchmark_match_engine.py``: complete ``MatchResult`` dumps of
real matches through the production input path and the Tournament Lab path.
"""

from __future__ import annotations

import json
import random

import pytest

from beta_engine.core import DeterministicRng
from beta_engine.core.types import SeedScope
from beta_engine.domain.matches import content_hash
from beta_engine.domain.matches.rallies import RallyEvent, _json_value
from beta_engine.domain.matches.stamina import StaminaTransition
from beta_engine.domain.matches.timeline import MatchTimelineEventBase
from scripts import benchmark_match_engine as bench

pytestmark = pytest.mark.pr_critical

GOLDEN_SINGLE = "7ef71261c0027218d76b9bc507bb637634871d73138382bbf29e2f424fca29cc"
GOLDEN_FIRST_SIX = "ad84a849b87cb0647d3f3e305e4f1d7100f243bfc9e349058bd1b9ee506faeda"


def _single():
    a = bench._player("SINGLE-A", 86, style="attacking", archetype="explosive shotmaker")
    b = bench._player("SINGLE-B", 84, style="retrieving", archetype="durable grinder")
    return bench.production_match("bench-single", a, b, 5, 918273)


def test_real_match_is_byte_identical_to_the_pre_change_engine():
    assert bench.digest([_single()]) == GOLDEN_SINGLE


def test_varied_matches_are_byte_identical_to_the_pre_change_engine():
    cases = bench.match_set()[:6]
    outputs = [bench.production_match(*case) for case in cases[:3]]
    outputs += [bench.lab_match(*case) for case in cases[3:]]
    assert bench.digest(outputs) == GOLDEN_FIRST_SIX


def _original_rally_hash(event):
    # The pre-change algorithm: defensive deep conversion of the dump.
    dump = event.model_dump(mode="json", exclude={"event_hash", "event_hash_algorithm"})
    payload = {key: _json_value(value) for key, value in dump.items()}
    return RallyEvent._content_hash(RallyEvent._hash_payload(payload))


def test_every_created_event_hash_equals_the_full_original_computation():
    from beta_engine.domain.matches import MatchEngine

    a = bench._player("EQ-A", 82, style="front-court")
    b = bench._player("EQ-B", 80, style="counter-punching", archetype="durable grinder")
    result = MatchEngine(rng=DeterministicRng(4242)).simulate(bench.context_for("eq", a, b, 5))
    events = result.rally_log.events
    assert events
    for event in events:
        assert event.event_hash == _original_rally_hash(event)
        # A stored event reloads through the COMPLETE validator.
        assert RallyEvent.model_validate(event.model_dump()) == event
    for transition in result.stamina_log.transitions:
        assert StaminaTransition.model_validate(transition.model_dump()) == transition
    for item in result.timeline_log.events:
        assert type(item).model_validate(item.model_dump()) == item


def test_tampered_stored_events_are_still_rejected():
    from beta_engine.domain.matches import MatchEngine

    a = bench._player("TM-A", 84)
    b = bench._player("TM-B", 83, style="retrieving")
    result = MatchEngine(rng=DeterministicRng(99)).simulate(bench.context_for("tm", a, b, 3))
    for model, value in (
        (RallyEvent, result.rally_log.events[0]),
        (StaminaTransition, result.stamina_log.transitions[0]),
        (type(result.timeline_log.events[0]), result.timeline_log.events[0]),
    ):
        hash_field = "transition_hash" if model is StaminaTransition else "event_hash"
        chained = "previous_transition_hash" if model is StaminaTransition else "previous_event_hash"
        payload = value.model_dump()
        payload[chained] = "a" * 64  # valid format, covered only by the hash
        with pytest.raises(ValueError, match="hash mismatch"):
            model.model_validate(payload)
        payload = value.model_dump()
        payload[hash_field] = "f" * 64
        with pytest.raises(ValueError, match="hash mismatch"):
            model.model_validate(payload)
        payload = value.model_dump()
        payload["elapsed_seconds"] = payload["elapsed_seconds"] + 1.0
        with pytest.raises(ValueError):
            model.model_validate(payload)


def test_deferred_check_applies_once_and_only_to_the_created_type():
    class Other:
        pass

    assert content_hash.hash_check_deferred(Other()) is False
    marker_token = content_hash._deferred.set([Other, False])
    try:
        assert content_hash.hash_check_deferred(object()) is False
        assert content_hash.hash_check_deferred(Other()) is True
        assert content_hash.hash_check_deferred(Other()) is False  # consumed
    finally:
        content_hash._deferred.reset(marker_token)
    assert content_hash._deferred.get() is None


def test_lazy_generator_draws_the_identical_sequence():
    rng = DeterministicRng(123456789)
    child = rng.branch(SeedScope.MATCH, "x", 1)
    reference = random.Random(child.seed.value)
    assert [child.random() for _ in range(5)] == [reference.random() for _ in range(5)]
    grandchild = rng.branch(SeedScope.MATCH, "x", 1).branch(SeedScope.MATCH, "y")
    assert grandchild.uniform(0, 1) == random.Random(grandchild.seed.value).uniform(0, 1)
    assert json.dumps(rng.derive(SeedScope.MATCH, "x", 1).value) == json.dumps(child.seed.value)
