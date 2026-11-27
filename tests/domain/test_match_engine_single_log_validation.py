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
