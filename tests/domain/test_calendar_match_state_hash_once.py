"""Hashing each played result once per match keeps every effect byte identical."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import MatchContext, MatchEngine
from beta_engine.domain.players import calendar_match_state as state_module
from beta_engine.domain.players.calendar_match_state import (
    CalendarMatchEffect,
    CalendarMatchPlayerState,
    CalendarMatchStatePolicy,
    advance_played_slot,
    checkpoint_fingerprint,
    participant_with_state,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import derive_match_effect_values
from scripts import benchmark_match_engine as bench

pytestmark = pytest.mark.pr_critical


def _reference(states, matches, policy):
    """The pre-change body: every effect hashes its whole result again."""
    roster = {s.player_id: s for s in states}
    updated, effects = dict(roster), []
    for match in matches:
        projections = []
        for ctx in (match.input_context.player_a, match.input_context.player_b):
            state = roster[ctx.player.player_id]
            projections.append(state_module._EffectInput(
                **state.model_dump(),
                legacy_engine_values=tuple((n, getattr(ctx.player, n)) for n in (
                    'technique', 'movement', 'physical', 'mental', 'consistency', 'clutch', 'recovery')),
                form_modifier=ctx.form_modifier, sharpness_modifier=ctx.sharpness_modifier,
                fatigue_modifier=ctx.fatigue_modifier,
            ))
        for values in derive_match_effect_values(projections, match.result, policy=policy.effects):
            pid = values['player_id']
            effects.append(CalendarMatchEffect(
                **values, match_id=match.input_context.match_id,
                input_fingerprint=canonical_hash(match.input_context.model_dump(mode='json')),
                result_fingerprint=canonical_hash(match.result.model_dump(mode='json')),
                source_checkpoint_fingerprint=checkpoint_fingerprint(states),
            ))
            updated[pid] = CalendarMatchPlayerState(
                player_id=pid, current_form=values['form_after'],
                match_sharpness=values['sharpness_after'], long_term_fatigue=values['fatigue_after'])
    return (tuple(updated[p] for p in sorted(updated)),
            tuple(sorted(effects, key=lambda e: (e.match_id, e.player_id))))


def test_effects_of_a_multi_match_slot_equal_the_previous_per_effect_hashing(monkeypatch):
    policy = CalendarMatchStatePolicy()
    cases = bench.match_set()[:3]
    states, matches = [], []
    for n, (match_id, a, b, _best_of, seed) in enumerate(cases):
        sa = CalendarMatchPlayerState(player_id=a.player_id, current_form=96 + n,
                                      match_sharpness=60 + n, long_term_fatigue=4 * n)
        sb = CalendarMatchPlayerState(player_id=b.player_id, current_form=104 - n,
                                      match_sharpness=55, long_term_fatigue=n)
        states += [sa, sb]
        context = MatchContext(match_id=match_id, player_a=participant_with_state(a, sa, policy),
                               player_b=participant_with_state(b, sb, policy), best_of=5)
        matches.append(SimpleNamespace(input_context=context,
                                       result=MatchEngine(DeterministicRng(seed)).simulate(context)))
    states = tuple(sorted(states, key=lambda s: s.player_id))
    expected = _reference(states, matches, policy)
    calls = []
    original = state_module.canonical_hash
    monkeypatch.setattr(state_module, "canonical_hash", lambda v: calls.append(1) or original(v))
    actual = advance_played_slot(states, matches, policy)
    assert actual == expected
    assert [e.model_dump_json() for e in actual[1]] == [e.model_dump_json() for e in expected[1]]
    # input + result per match and one shared source fingerprint (was 3 per effect)
    assert len(calls) == 2 * len(matches) + 1
    assert advance_played_slot(states, (), policy) == (states, ())
