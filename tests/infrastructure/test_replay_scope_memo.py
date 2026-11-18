"""The replay memo reuses only identical objects and only inside its scope."""

from types import SimpleNamespace

import pytest

from beta_engine.domain import replay_scope
from beta_engine.domain.players import calendar_native_birth_replay as birth

pytestmark = pytest.mark.pr_critical


def week(ordinal):
    return SimpleNamespace(week=SimpleNamespace(ordinal=ordinal))


def submission(ordinal):
    return SimpleNamespace(submission_week=SimpleNamespace(ordinal=ordinal))


def remember(states, source, submissions):
    birth._remember_birth_steps(states, source, "world", submissions,
                                [(f"b{i}", ()) for i in range(1, len(states))])


def test_nothing_is_memoized_outside_a_replay_scope():
    calls = []
    assert replay_scope.identity_value(object(), "x", lambda: calls.append(1) or 1) == 1
    states = tuple(week(i) for i in range(4))
    remember(states, object(), ())
    assert birth._reusable_birth_steps(states, object(), "world", ()) == ([], 0)
    assert not replay_scope.already_checked("c", (object(),))


def test_identity_values_and_checks_are_per_object():
    with replay_scope.replay_value_scope():
        a, b = object(), object()
        assert replay_scope.identity_value(a, "fp", lambda: 1) == 1
        assert replay_scope.identity_value(a, "fp", lambda: 2) == 1
        assert replay_scope.identity_value(b, "fp", lambda: 3) == 3
        replay_scope.remember_checked("step", (a, b))
        assert replay_scope.already_checked("step", (a, b))
        assert not replay_scope.already_checked("step", (b, a))
        assert not replay_scope.already_checked("other", (a, b))


def test_cold_match_replay_reuses_only_exact_inputs_and_returns_isolated_logs(monkeypatch):
    from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
    from beta_engine.domain.tournaments import calendar_global_slots as slots
    from tests.domain.test_match_stamina import _context

    context = _context().model_copy(update={"best_of": 1, "games_to": 3})
    health = EffectiveMatchHealthSnapshot.create_healthy(player_a_id="A", player_b_id="B")
    anchor = "1" * 64
    simulate = slots.MatchEngine.simulate
    calls = []

    def count_simulation(engine, context, **kwargs):
        calls.append(context.match_id)
        return simulate(engine, context, **kwargs)

    monkeypatch.setattr(slots.MatchEngine, "simulate", count_simulation)
    with slots.global_replay_projection_scope(_reuse_simulated_matches=True):
        first = slots._simulate_slot_match(context, seed=123, anchor=anchor, health=health)
        expected = first.model_dump_json()
        first.sets_won.clear()
        replayed = slots._simulate_slot_match(context, seed=123, anchor=anchor, health=health)
        assert replayed.model_dump_json() == expected
        assert len(calls) == 1
        slots._simulate_slot_match(context, seed=124, anchor=anchor, health=health)
        slots._simulate_slot_match(context, seed=123, anchor="2" * 64, health=health)
        changed = context.model_copy(update={"upset_variance": 0.2})
        slots._simulate_slot_match(changed, seed=123, anchor=anchor, health=health)
        changed_health = health.model_copy(update={"unsupported_components": ("health_check",)})
        slots._simulate_slot_match(context, seed=123, anchor=anchor, health=changed_health)
        assert len(calls) == 5

    with slots.global_replay_projection_scope():
        for _ in range(2):
            replayed = slots._simulate_slot_match(context, seed=123, anchor=anchor, health=health)
            assert replayed.model_dump_json() == expected
        assert len(calls) == 7

    monkeypatch.setattr(slots, "_MATCH_REPLAY_BYTES", 1)
    with slots.global_replay_projection_scope(_reuse_simulated_matches=True):
        slots._simulate_slot_match(context, seed=123, anchor=anchor, health=health)
        slots._simulate_slot_match(context, seed=123, anchor=anchor, health=health)
        assert len(calls) == 9


def test_birth_steps_are_reused_only_for_an_identical_prefix_and_inputs():
    with replay_scope.replay_value_scope():
        source = object()
        states = tuple(week(i) for i in range(6))
        subs = (submission(0), submission(2))
        remember(states, source, subs)
        longer = (*states, week(6))
        steps, reused = birth._reusable_birth_steps(longer, source, "world", (*subs, submission(5)))
        assert reused == 5 and len(steps) == 5
        # A later submission beyond the reused steps' weeks does not matter, but
        # a backdated one (week <= the last reused predecessor) disables reuse.
        assert birth._reusable_birth_steps(longer, source, "world", (*subs, submission(3)))[1] == 0
        assert birth._reusable_birth_steps(longer, source, "world", (subs[1], subs[0]))[1] == 0
        assert birth._reusable_birth_steps(longer, object(), "world", subs)[1] == 0
        assert birth._reusable_birth_steps(longer, source, "other", subs)[1] == 0
        changed = (states[0], states[1], week(2), *states[3:], week(6))
        assert birth._reusable_birth_steps(changed, source, "world", subs)[1] == 1


def test_replay_evidence_requires_one_exact_replayed_input_set(monkeypatch):
    from beta_engine.infrastructure.db import calendar_native_competition as competition

    payload = {"content": {
        "calendar_player_sporting_checkpoint": {"state": {"schema_version": "calendar_sporting_checkpoint.v13"},
                                                "fingerprint": "cp"},
        "calendar_tour_authority": {"state": {"schema_version": "calendar_tour_authority.v5"},
                                    "fingerprint": "tour"},
    }}
    monkeypatch.setattr(competition, "_proven_hash", lambda proof, path, value: "cp" if "checkpoint" in path[1] else "tour")
    actual = ("binding-c-prime", ("l",), ("h",))
    monkeypatch.setattr(competition, "_raw_global_inputs", lambda payload, proof=None: actual)

    def proofs(*inputs):
        return {"_prefixes": {"_global_replayed_values": {("cp", "tour"): inputs}}}

    assert competition.has_replayed_global_components(payload, proofs(actual))
    assert competition.has_replayed_global_components(payload, proofs(("binding-c", ("l",), ("h",)), actual))
    assert not competition.has_replayed_global_components(payload, proofs(("binding-c", ("l",), ("h",))))
    assert not competition.has_replayed_global_components(payload, proofs(("binding-c-prime", ("l",), ("h", "x"))))
