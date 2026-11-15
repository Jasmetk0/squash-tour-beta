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
