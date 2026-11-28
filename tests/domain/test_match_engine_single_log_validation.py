"""Engine-fresh events enter their logs without a second identical hash.

Pydantic re-runs every event's ``after`` validator when the engine assembles
the rally, timeline and stamina logs. Inside one ``MatchEngine`` call that
second run keeps every structural check but skips the hash comparison for the
exact, unchanged instance the engine factory has just hashed. Stored data,
copies, public factories and anything outside an engine call keep the full
check. Byte equality with ``buuk`` is pinned by the golden fingerprints in
``test_match_engine_performance_equivalence.py``.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import json
from pathlib import Path

import pytest

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import MatchEngine, content_hash
from beta_engine.domain.matches import rallies as rallies_module
from beta_engine.domain.matches.rallies import MatchRallyLog, RallyEvent
from beta_engine.domain.matches.stamina import StaminaTransition
from beta_engine.domain.matches.timeline import MatchTimelineEventBase
from scripts import benchmark_match_engine as bench

pytestmark = pytest.mark.pr_critical

MATCHES = Path(__file__).resolve().parents[2] / "src" / "beta_engine" / "domain" / "matches"


def _context(best_of=3):
    a = bench._player("SV-A", 83, style="front-court")
    b = bench._player("SV-B", 81, style="counter-punching", archetype="durable grinder")
    return bench.context_for("single-validation", a, b, best_of)


def _counting(monkeypatch, cls, name):
    calls = []
    original = getattr(cls, name)

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(cls, name, staticmethod(counted))
    return calls


def test_each_engine_event_is_hashed_once_and_still_checked_twice(monkeypatch):
    rally_hashes = _counting(monkeypatch, RallyEvent, "_content_hash")
    timeline_hashes = _counting(monkeypatch, MatchTimelineEventBase, "_content_hash")
    stamina_hashes = _counting(monkeypatch, StaminaTransition, "_content_hash")
    # Each run of the rally validator reaches its hash step only after every
    # structural check passed, and asks ``hash_check_deferred`` exactly once.
    checks = []

    def counted_deferred(instance):
        if isinstance(instance, RallyEvent):
            checks.append(instance.rally_index)
        return content_hash.hash_check_deferred(instance)

    monkeypatch.setattr(rallies_module, "hash_check_deferred", counted_deferred)
    result = MatchEngine(rng=DeterministicRng(31)).simulate(_context())
    rallies = len(result.rally_log.events)
    assert rallies and len(rally_hashes) == rallies  # was 2 per event (create + log)
    assert len(timeline_hashes) == len(result.timeline_log.events)
    assert len(stamina_hashes) == len(result.stamina_log.transitions)
    # Every structural rally check still runs at creation AND at log entry.
    assert sorted(checks) == sorted([*range(1, rallies + 1)] * 2)
    assert content_hash._hashed_in_scope.get() is None


def _fresh_values(event):
    return {name: getattr(event, name) for name in type(event).model_fields if name != "event_hash"}


@pytest.fixture(scope="module")
def engine_result():
    return MatchEngine(rng=DeterministicRng(47)).simulate(_context())


def test_reassigned_field_after_creation_is_still_rejected(engine_result, monkeypatch):
    stored = engine_result.rally_log.events[3]
    with content_hash.engine_event_scope():
        fresh = RallyEvent._create_from_engine(**_fresh_values(stored))
        assert fresh == stored
        fresh.rally_seed = "12345"  # covered only by the event hash
        with pytest.raises(ValueError, match="rally event hash mismatch"):
            RallyEvent.model_validate(fresh)
        untouched = RallyEvent._create_from_engine(**_fresh_values(stored))
        hashes = _counting(monkeypatch, RallyEvent, "_content_hash")
        assert RallyEvent.model_validate(untouched) is untouched
        assert hashes == []  # the identical rehash is skipped exactly once
        RallyEvent.model_validate(untouched)
        assert len(hashes) == 1  # consumed: every later validation recomputes


def test_copies_reloads_and_events_outside_an_engine_call_keep_the_full_check(
    engine_result, monkeypatch
):
    stored = engine_result.rally_log.events[0]
    hashes = _counting(monkeypatch, RallyEvent, "_content_hash")
    outside = RallyEvent._create_from_engine(**_fresh_values(stored))
    assert len(hashes) == 1
    RallyEvent.model_validate(outside)
    assert len(hashes) == 2  # no scope: nothing is remembered
    with content_hash.engine_event_scope():
        fresh = RallyEvent._create_from_engine(**_fresh_values(stored))
        copy = fresh.model_copy()
        RallyEvent.model_validate(copy)  # equal value, other object
        RallyEvent.model_validate_json(fresh.model_dump_json())
        RallyEvent.model_validate(fresh.model_dump())
    assert len(hashes) == 6
    payload = stored.model_dump()
    payload["previous_event_hash"] = "a" * 64
    with content_hash.engine_event_scope(), pytest.raises(ValueError, match="hash mismatch"):
        RallyEvent.model_validate(payload)


def test_scope_is_cleared_after_a_failed_engine_call(monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("log assembly failed")

    monkeypatch.setattr(MatchRallyLog, "create", broken)
    with pytest.raises(RuntimeError, match="log assembly failed"):
        MatchEngine(rng=DeterministicRng(5)).simulate(_context())
    assert content_hash._hashed_in_scope.get() is None


def test_step_path_skips_only_the_new_events_rehash(monkeypatch):
    engine = MatchEngine(rng=DeterministicRng(61))
    working_input, state = engine.start_working_match(_context())
    for _ in range(3):
        state = engine.simulate_next_rally(working_input, state).state
    hashes = _counting(monkeypatch, RallyEvent, "_content_hash")
    outcome = engine.simulate_next_rally(working_input, state)
    # create (1) + the three already-stored events re-validated in the new
    # working state (3) + the step outcome's own copy of the new event (1).
    assert len(hashes) == 5
    assert content_hash._hashed_in_scope.get() is None
    assert outcome.state.rally_events[-1] == outcome.rally


def test_match_package_never_mutates_model_attributes():
    """The skipped rehash relies on engine code never mutating created events."""
    offenders = []
    for path in sorted(MATCHES.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            elif isinstance(node, ast.Delete):
                targets = node.targets
            for target in targets:
                for item in ast.walk(target):
                    if (
                        isinstance(item, ast.Attribute)
                        and isinstance(item.ctx, (ast.Store, ast.Del))
                        and not (isinstance(item.value, ast.Name) and item.value.id == "self")
                    ):
                        offenders.append(f"{path.name}:{node.lineno}")
                    if (
                        isinstance(item, ast.Subscript)
                        and isinstance(item.ctx, (ast.Store, ast.Del))
                        and isinstance(item.value, ast.Attribute)
                        and item.value.attr == "__dict__"
                    ):
                        offenders.append(f"{path.name}:{node.lineno}")
            if isinstance(node, ast.Call):
                func = node.func
                name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(
                    func, ast.Attribute
                ) else None
                if name in {"setattr", "__setattr__", "delattr", "__delattr__"}:
                    offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


# --- canonical event-hash JSON ----------------------------------------------------


def _reference_sha256(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def test_canonical_json_is_byte_identical_to_the_historical_json_dumps():
    awkward = {
        "z": [1, 1.0, -0.0, 0.0, 1e-05, 5e-324, 1e16, 2**130, -(2**70), True, False, None],
        "a": {"ü-ß": "\n\t \u0000\"\\", "emoji": "🎾", "": [], "x": {}},
        "nan": [float("nan"), float("inf"), float("-inf")],
        "Ä": [{"b": 1, "a": [{"d": 0.1 + 0.2, "c": 1 / 3}]}],
        "1": "numeric-looking key", "10": 10, "2": 2,
    }
    for payload in (awkward, [], {}, "text", 0.1, [awkward, awkward]):
        reference = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert content_hash._CANONICAL_JSON.encode(payload) == reference
        assert content_hash.canonical_sha256(payload) == _reference_sha256(payload)


def test_every_stored_event_hash_equals_the_historical_json_dumps_hash():
    result = MatchEngine(rng=DeterministicRng(73)).simulate(_context(best_of=5))
    for event in result.rally_log.events:
        payload = RallyEvent._hash_payload(
            event.model_dump(mode="json", exclude={"event_hash", "event_hash_algorithm"})
        )
        assert event.event_hash == _reference_sha256(payload)
    for event in result.timeline_log.events:
        payload = event.model_dump(mode="json", exclude={"event_hash", "event_hash_algorithm"})
        assert event.event_hash == _reference_sha256(payload)
    for transition in result.stamina_log.transitions:
        assert transition.transition_hash == _reference_sha256(
            StaminaTransition._hash_payload(transition)
        )


# --- stamina and control validators with prebuilt member tables ---------------------


def test_stamina_lookups_keep_their_results_and_missing_dimension_behaviour(engine_result):
    from beta_engine.domain.matches.stamina import (
        PlayerStaminaDelta,
        PlayerStaminaState,
        StaminaDimension,
    )

    state = engine_result.stamina_log.transitions[4].states_after[0]
    for bar in state.bars:
        assert state.current(bar.dimension) == bar.current
        assert state.capacity(bar.dimension) == bar.capacity
        assert state.current(bar.dimension.value) == bar.current  # str-valued enum
    partial = PlayerStaminaState.model_construct(player_id="X", bars=state.bars[:2])
    with pytest.raises(StopIteration):
        partial.current(StaminaDimension.MATCH)
    with pytest.raises(StopIteration):
        partial.capacity(StaminaDimension.MATCH)
    delta = PlayerStaminaDelta(player_id="X", explosive=-0.1, rally=-0.2, match=-0.3)
    assert [delta.for_dimension(d) for d in StaminaDimension] == [-0.1, -0.2, -0.3]
    assert delta.for_dimension("RALLY") == -0.2
    with pytest.raises(KeyError):
        delta.for_dimension("BALANCE")
    payload = state.model_dump()
    with pytest.raises(ValueError, match="every physical dimension once"):
        PlayerStaminaState.model_validate({**payload, "bars": payload["bars"][:2]})
    with pytest.raises(ValueError, match="every physical dimension once"):
        PlayerStaminaState.model_validate(
            {**payload, "bars": [payload["bars"][0]] * 2 + list(payload["bars"][2:])}
        )
    profile = engine_result_profile()
    with pytest.raises(StopIteration):
        type(profile).model_construct(player_id="X", initial_readiness_factor=1.0,
                                      bars=profile.bars[:1]).bar(StaminaDimension.MATCH)
    duplicate = profile.model_dump()
    duplicate["bars"] = [duplicate["bars"][0]] * 3
    with pytest.raises(ValueError, match="every physical dimension once"):
        type(profile).model_validate(duplicate)


def engine_result_profile():
    from beta_engine.domain.matches.stamina import EffectiveMatchStaminaSnapshot

    return EffectiveMatchStaminaSnapshot.create(context=_context()).player_profiles[0]


def test_tampered_stamina_after_state_and_control_segments_are_rejected(engine_result):
    from beta_engine.domain.matches.rallies import (
        RallyControlSegment,
        RallyEffortChange,
        RallyEffortChangeReason,
    )

    transition = engine_result.stamina_log.transitions[2]
    payload = transition.model_dump()
    payload["states_after"][1]["bars"][2]["current"] -= 0.0001
    with pytest.raises(ValueError, match="delta does not match state"):
        StaminaTransition.model_validate(payload)
    segment = next(
        s for e in engine_result.rally_log.events if e.control_trace
        for s in e.control_trace.segments if s.state_before != s.state_after
    )
    wrong_kind = segment.model_dump()
    wrong_kind["transition_kind"] = "STAY"
    with pytest.raises(ValueError, match="does not match its distance"):
        RallyControlSegment.model_validate(wrong_kind)
    assert RallyControlSegment.model_validate(segment.model_dump()) == segment
    with pytest.raises(ValueError, match="exactly one level"):
        RallyEffortChange(player_id="SV-A", from_level="CONSERVE", to_level="INCREASED",
                          reason=next(iter(RallyEffortChangeReason)))


# --- historical and stored records keep the complete load validation ------------------

LEGACY_V8 = Path(__file__).resolve().parents[1] / "fixtures" / "matches" / "legacy_engine_v8.json"


def _stored_results():
    from beta_engine.domain.matches.models import MatchResult

    legacy = json.loads(LEGACY_V8.read_text())["result"]
    current = MatchEngine(rng=DeterministicRng(89)).simulate(_context(best_of=5))
    return MatchResult, {"legacy_v8": legacy, "current": current.model_dump(mode="json")}


@pytest.mark.parametrize("inside_engine_scope", [False, True])
def test_historical_and_current_records_reload_and_reject_changes(inside_engine_scope):
    MatchResult, stored = _stored_results()
    scope = content_hash.engine_event_scope() if inside_engine_scope else contextlib.nullcontext()
    with scope:
        for label, payload in stored.items():
            reloaded = MatchResult.model_validate(payload)
            for chain in ("rally_log", "timeline_log", "stamina_log"):
                assert getattr(reloaded, chain).match_log_hash == payload[chain]["match_log_hash"]
            if label == "current":  # the legacy dump gains later defaulted fields
                assert reloaded.model_dump(mode="json") == payload
            assert MatchResult.model_validate_json(reloaded.model_dump_json()) == reloaded

            def rejected(mutate, payload=payload):
                changed = json.loads(json.dumps(payload))
                mutate(changed)
                with pytest.raises(ValueError):
                    MatchResult.model_validate(changed)

            rejected(lambda r: r["rally_log"]["events"][0].update(rally_seed="1"))
            rejected(lambda r: r["rally_log"]["events"][-1].update(previous_event_hash="b" * 64))
            rejected(lambda r: r["timeline_log"]["events"][0].update(elapsed_seconds=0.5))
            rejected(lambda r: r["stamina_log"]["transitions"][0]["states_after"][0]["bars"][0]
                     .update(current=1.0))
            rejected(lambda r: r["stamina_log"]["transitions"].pop())  # incomplete chain
            rejected(lambda r: r["rally_log"]["events"].pop())  # incomplete rally log
            if payload["rally_log"]["events"][0].get("gameplan_context"):
                rejected(lambda r: r["rally_log"]["events"][0]["gameplan_context"]
                             ["player_decisions"][0].update(observed_rallies=7))
