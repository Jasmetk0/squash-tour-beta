"""MatchEngine performance changes must not change a single result byte.

Golden fingerprints were computed on unmodified ``buuk`` (``320e476`` for the
first two, re-confirmed on ``8af660d``; the edge-case corpus on ``8af660d``)
with ``scripts/benchmark_match_engine.py``: complete ``MatchResult`` dumps of
real matches through the production input path, the Tournament Lab path and
the step-wise ``Simulate Next Rally`` path including every persisted working
state.
"""

from __future__ import annotations

import json
import random

import pytest

from beta_engine.core import DeterministicRng
from beta_engine.core.rng import derive_child_seed
from beta_engine.core.types import Seed, SeedScope
from beta_engine.domain.matches import MatchEngine, content_hash
from beta_engine.domain.matches import match_engine as match_engine_module
from beta_engine.domain.matches.rallies import RallyEvent, _json_value
from beta_engine.domain.matches.stamina import (
    MatchStaminaLog,
    StaminaAdvanceMemo,
    StaminaTransition,
    StaminaTransitionCause,
    _exact_scalar,
)
from scripts import benchmark_match_engine as bench

pytestmark = pytest.mark.pr_critical

GOLDEN_SINGLE = "7ef71261c0027218d76b9bc507bb637634871d73138382bbf29e2f424fca29cc"
GOLDEN_FIRST_SIX = "ad84a849b87cb0647d3f3e305e4f1d7100f243bfc9e349058bd1b9ee506faeda"
GOLDEN_EDGE_CASES = "70b082cb3046a6b4d9e46fdb012e266fd1c7001d993a7eb73eaf56fa96e00a69"


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


@pytest.fixture(scope="module")
def edge_outputs():
    return {output["case"]: output for output in bench.edge_case_outputs()}


def test_edge_case_corpus_is_byte_identical_to_the_pre_change_engine(edge_outputs):
    # Includes every persisted working state of the step-wise path.
    assert bench.digest(list(edge_outputs.values())) == GOLDEN_EDGE_CASES


def test_edge_case_corpus_really_contains_the_abnormal_states(edge_outputs):
    def deuce_rallies(result):
        return sum(
            1
            for event in result["rally_log"]["events"]
            if event["score_before"]["points_a"] >= 10
            and event["score_before"]["points_a"] == event["score_before"]["points_b"]
        )

    for label in ("deuce-bo5", "injured-health-input", "step-deuce-bo3"):
        assert deuce_rallies(edge_outputs[label]["result"]) >= 1, label
    retirements = {
        label: (output["result"]["termination_reason"], output["result"]["retired_at_set_start"])
        for label, output in edge_outputs.items()
        if label.startswith(("retire", "lab-retire", "step-retire"))
    }
    assert retirements == {
        "retire-explicit-set1": ("RETIREMENT", 1),
        "retire-explicit-set3": ("RETIREMENT", 3),
        "retire-probabilistic": ("RETIREMENT", 3),
        "lab-retire-explicit": ("RETIREMENT", 2),
        "step-retire-probabilistic": ("RETIREMENT", 2),
    }
    assert edge_outputs["retire-explicit-set1"]["result"]["rally_log"]["events"] == []
    assert len(edge_outputs["step-deuce-bo3"]["steps"]) > 60
    timeline_types = {
        event["event_type"]
        for output in edge_outputs.values()
        for event in output["result"]["timeline_log"]["events"]
    }
    assert timeline_types == {"RALLY", "BETWEEN_RALLY_INTERVAL", "GAME_BREAK", "OBJECTIVE_DELAY"}


def _original_rally_hash(event):
    # The pre-change algorithm: defensive deep conversion of the dump.
    dump = event.model_dump(mode="json", exclude={"event_hash", "event_hash_algorithm"})
    payload = {key: _json_value(value) for key, value in dump.items()}
    return RallyEvent._content_hash(RallyEvent._hash_payload(payload))


def _match(seed=4242, best_of=5):
    a = bench._player("EQ-A", 82, style="front-court")
    b = bench._player("EQ-B", 80, style="counter-punching", archetype="durable grinder")
    context = bench.context_for("eq", a, b, best_of)
    return context, MatchEngine(rng=DeterministicRng(seed)).simulate(context)


def test_every_created_event_hash_equals_the_full_original_computation():
    _, result = _match()
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


@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings:UserWarning")
def test_public_event_factories_keep_historical_pre_validation_hash_checks():
    _, result = _match()
    for event, hash_field in (
        (result.rally_log.events[0], "event_hash"),
        (result.timeline_log.events[0], "event_hash"),
        (result.stamina_log.transitions[0], "transition_hash"),
    ):
        values = dict(event)
        values.pop(hash_field)
        values["elapsed_seconds"] = str(event.elapsed_seconds)
        with pytest.raises(ValueError, match="hash mismatch"):
            type(event).create(**values)


def test_lazy_generator_draws_the_identical_sequence():
    rng = DeterministicRng(123456789)
    child = rng.branch(SeedScope.MATCH, "x", 1)
    reference = random.Random(child.seed.value)
    assert [child.random() for _ in range(5)] == [reference.random() for _ in range(5)]
    grandchild = rng.branch(SeedScope.MATCH, "x", 1).branch(SeedScope.MATCH, "y")
    assert grandchild.uniform(0, 1) == random.Random(grandchild.seed.value).uniform(0, 1)
    assert json.dumps(rng.derive(SeedScope.MATCH, "x", 1).value) == json.dumps(child.seed.value)
    # Mixing draws and derivations on one RNG keeps both streams exact.
    mixed = DeterministicRng(77)
    ref = random.Random(77)
    assert mixed.random() == ref.random()
    assert mixed.derive(SeedScope.WEEK, 3) == derive_child_seed(77, SeedScope.WEEK, 3)
    assert mixed.randint(1, 9) == ref.randint(1, 9)
    assert mixed.choice(["L", "R"]) == ref.choice(["L", "R"])


def test_cached_seed_text_derivation_equals_the_reference_function():
    generator = random.Random(2026)
    parts_pool = (
        "segment", "between-rally", "", "ü-ß", "|", 0, -1, 7, 2**130, 1.5, True, None,
        SeedScope.MATCH, ("tuple", 1),
    )
    for _ in range(400):
        seed = generator.choice((0, 1, 2**127 + generator.randrange(2**64), generator.randrange(2**40)))
        rng = DeterministicRng(Seed(seed) if generator.random() < 0.5 else seed)
        for _ in range(3):  # repeated use of the cached seed text
            scope = generator.choice(tuple(SeedScope))
            parts = tuple(generator.choice(parts_pool) for _ in range(generator.randrange(0, 4)))
            assert rng.derive(scope, *parts) == derive_child_seed(seed, scope, *parts)
            assert rng.branch(scope, *parts).seed == derive_child_seed(seed, scope, *parts)


# --- live restart samples reused by the timeline --------------------------------


def _count_samples(monkeypatch):
    calls = []
    original = MatchEngine._sample_between_rally_interval

    def counting(self, **kwargs):
        calls.append(kwargs["previous_rally"].rally_index)
        return original(self, **kwargs)

    monkeypatch.setattr(MatchEngine, "_sample_between_rally_interval", counting)
    return calls


def test_each_restart_is_sampled_once_and_reused_by_the_timeline(monkeypatch):
    calls = _count_samples(monkeypatch)
    _, result = _match()
    intervals = [
        event.after_rally_index
        for event in result.timeline_log.events
        if event.event_type in {"BETWEEN_RALLY_INTERVAL", "OBJECTIVE_DELAY"}
    ]
    assert intervals and calls == intervals


def test_timeline_ignores_a_stale_sample_and_recomputes_identically(monkeypatch):
    context, result = _match(best_of=3)
    engine = MatchEngine(rng=DeterministicRng(4242))
    match_rng = engine.rng.branch(
        SeedScope.MATCH, context.match_id, "EQ-A", "EQ-B"
    )
    timing = match_engine_module.EffectiveMatchTimingSnapshot.create(
        player_a_id="EQ-A", player_b_id="EQ-B"
    )
    kwargs = dict(
        context=context,
        match_rng=match_rng,
        rally_log=result.rally_log,
        timing=timing,
        termination_reason=result.termination_reason,
        retired_at_set_start=None,
    )
    reference = engine._build_timeline(**kwargs).model_dump(mode="json")
    assert reference == result.timeline_log.model_dump(mode="json")
    events = result.rally_log.events
    timeline_rng = match_rng.branch(SeedScope.MATCH, "timeline-v1")
    good = {
        event.rally_index: engine._sample_between_rally_interval(
            context=context,
            timing=timing,
            previous_rally=event,
            interval_rng=timeline_rng.branch(SeedScope.MATCH, "between-rally", event.rally_index),
        )
        for event in events[:-1]
    }
    # A sample is reused only for the exact rally hash AND derived interval seed.
    wrong_hash = {
        index: match_engine_module._BetweenRallySample(
            previous_rally_hash="e" * 64,
            interval_seed=sample.interval_seed,
            event_type=sample.event_type,
            elapsed_seconds=99.0,
            values={**sample.values, "elapsed_seconds": 99.0},
        )
        for index, sample in good.items()
    }
    wrong_seed = {
        index: match_engine_module._BetweenRallySample(
            previous_rally_hash=sample.previous_rally_hash,
            interval_seed=sample.interval_seed + 1,
            event_type=sample.event_type,
            elapsed_seconds=99.0,
            values={**sample.values, "elapsed_seconds": 99.0},
        )
        for index, sample in good.items()
    }
    calls = _count_samples(monkeypatch)
    assert engine._build_timeline(**kwargs, interval_samples=good).model_dump(mode="json") == reference
    assert calls == []
    for stale in (wrong_hash, wrong_seed):
        assert engine._build_timeline(**kwargs, interval_samples=stale).model_dump(mode="json") == reference
    intervals = sum(
        1
        for event in reference["events"]
        if event["event_type"] in {"BETWEEN_RALLY_INTERVAL", "OBJECTIVE_DELAY"}
    )
    assert intervals and len(calls) == 2 * intervals


# --- exact-input stamina memo -------------------------------------------------------


def test_exact_scalar_never_merges_values_that_serialize_differently():
    assert _exact_scalar(0.0) != _exact_scalar(-0.0)
    assert _exact_scalar(1) != _exact_scalar(1.0)
    assert _exact_scalar(True) != _exact_scalar(1)
    assert _exact_scalar(0.1 + 0.2) != _exact_scalar(0.3)
    assert _exact_scalar(2.5) == _exact_scalar(2.5)


def test_stamina_rebuild_with_live_memo_is_identical_and_misses_recompute():
    context, result = _match(seed=5150, best_of=3)
    effective = match_engine_module.EffectiveMatchStaminaSnapshot.create(context=context)
    timeline = result.timeline_log
    rally_events = result.rally_log.events
    plain = MatchStaminaLog.build(
        context=context, timeline=timeline, rally_events=rally_events, effective=effective
    )
    assert plain.model_dump(mode="json") == result.stamina_log.model_dump(mode="json")

    initial = MatchStaminaLog.create_initial_states(effective=effective, player_ids=("EQ-A", "EQ-B"))
    memo = StaminaAdvanceMemo(effective=effective, initial_states=initial)
    states = initial
    for transition in plain.transitions:
        source = next(e for e in timeline.events if e.event_hash == transition.source_timeline_event_hash)
        workloads = (
            {item.player_id: item.workload_units for item in transition.player_workloads}
            if transition.player_workloads
            else None
        )
        _, states = memo.advance(
            states=states,
            cause=transition.cause,
            elapsed_seconds=source.elapsed_seconds,
            workload_units=transition.workload_units,
            player_workload_units=workloads,
        )
    advance_calls = []
    original = MatchStaminaLog.advance_states.__func__

    def counting(cls, **kwargs):
        advance_calls.append(kwargs["cause"])
        return original(cls, **kwargs)

    try:
        MatchStaminaLog.advance_states = classmethod(counting)
        reused = MatchStaminaLog.build(
            context=context, timeline=timeline, rally_events=rally_events,
            effective=effective, live_memo=memo,
        )
        assert advance_calls == []  # every step came from the exact live result
        assert reused.model_dump(mode="json") == plain.model_dump(mode="json")
        # A memo recorded for another snapshot object is never consulted.
        other = match_engine_module.EffectiveMatchStaminaSnapshot.create(context=context)
        recomputed = MatchStaminaLog.build(
            context=context, timeline=timeline, rally_events=rally_events,
            effective=other, live_memo=memo,
        )
        assert len(advance_calls) == len(plain.transitions)
        assert recomputed.model_dump(mode="json") == plain.model_dump(mode="json")
    finally:
        MatchStaminaLog.advance_states = classmethod(original)

    first = plain.transitions[0]
    source = timeline.events[0]
    lookup = dict(
        effective=effective,
        cause=first.cause,
        workload_units=first.workload_units,
        player_workload_units={i.player_id: i.workload_units for i in first.player_workloads} or None,
    )
    assert memo.recorded(states=initial, elapsed_seconds=source.elapsed_seconds, **lookup) is not None
    # Equal-valued but different state objects, or a perturbed elapsed time, miss.
    copy = tuple(state.model_copy(deep=True) for state in initial)
    assert copy == initial
    assert memo.recorded(states=copy, elapsed_seconds=source.elapsed_seconds, **lookup) is None
    assert memo.recorded(states=initial, elapsed_seconds=source.elapsed_seconds + 1e-9, **lookup) is None
    assert memo.recorded(
        states=initial, elapsed_seconds=source.elapsed_seconds,
        **{**lookup, "cause": StaminaTransitionCause.GAME_BREAK_RECOVERY},
    ) is None

    # Same snapshot object and initial state, but different force/recovery inputs.
    bar = effective.player_profiles[0].bars[0]
    bar.workload_cost_factor *= 2
    updated = MatchStaminaLog.build(
        context=context, timeline=timeline, rally_events=rally_events, effective=effective
    )
    from_memo = MatchStaminaLog.build(
        context=context, timeline=timeline, rally_events=rally_events,
        effective=effective, live_memo=memo,
    )
    assert updated.model_dump(mode="json") != plain.model_dump(mode="json")
    assert from_memo.model_dump(mode="json") == updated.model_dump(mode="json")
