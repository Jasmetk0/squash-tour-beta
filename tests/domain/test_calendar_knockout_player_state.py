"""Frozen slot inputs, deterministic carried effects and historical byte safety."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from beta_engine.core import DeterministicRng
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches import MatchEngine, MatchContext, MatchParticipantContext
from beta_engine.domain.players.calendar_match_state import (
    CalendarMatchStatePolicy, CalendarKnockoutSportingState,
    advance_played_slot, participant_with_state,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    CalendarKnockoutMatch, CalendarOpeningKnockout, _parse_calendar_match,
)
from tests.domain.test_match_engine import _player

pytestmark = pytest.mark.pr_critical


def played_pair(name, seed, first, second):
    ctx = MatchContext(match_id=name, player_a=first, player_b=second,
                       best_of=1, games_to=3, win_by=1)
    result = MatchEngine(DeterministicRng(seed)).simulate(ctx, log_anchor_hash='a' * 64)
    return CalendarKnockoutMatch(
        round=name, slot=2 if name == 'final' else 1, seed=seed,
        input_context=ctx, result=result, log_anchor_hash='a' * 64,
    )


def bracket():
    policy = CalendarMatchStatePolicy()
    players = {pid: _player(player_id=pid, base=65 + i) for i, pid in enumerate('abcd')}
    initial = policy.initial_states(players)
    states = {p.player_id: p for p in initial}
    contexts = {pid: participant_with_state(p, states[pid], policy) for pid, p in players.items()}
    one = played_pair('semifinal_1', 6, contexts['a'], contexts['b'])
    two = played_pair('semifinal_2', 7, contexts['c'], contexts['d'])
    after, effects = advance_played_slot(initial, (one, two), policy)
    roster = {p.player_id: p for p in after}
    a, b = one.result.winner_player_id, two.result.winner_player_id
    final = played_pair('final', 8, participant_with_state(players[a], roster[a], policy),
                        participant_with_state(players[b], roster[b], policy))
    terminal, final_effects = advance_played_slot(after, (final,), policy)
    sporting = CalendarKnockoutSportingState(
        policy=policy, initial=initial, after_semifinals=after, terminal=terminal,
        effects=effects + final_effects,
    )
    return CalendarOpeningKnockout(
        schema_version='calendar_opening_knockout.v2', sporting=sporting,
        run_id='r', branch_id='b', match_id='ko', command_id='play',
        request_fingerprint='c' * 64, source_saved_head='head',
        source_initial_world_fingerprint='d' * 64,
        week=RunWeekPosition(calendar=RunCalendar(80, 37, 2100, 3), season_index=0, week=1),
        seed=6, entrant_ids=tuple('abcd'), pre_slot_anchor='e' * 64,
        matches=(one, two, final), operator_label='Admin', audit_reason='Test frozen slots',
    )


def test_simultaneous_semifinals_are_order_independent_and_final_consumes_terminal_state():
    ko = bracket()
    s = ko.sporting
    assert advance_played_slot(s.initial, ko.matches[:2], s.policy) == advance_played_slot(
        s.initial, tuple(reversed(ko.matches[:2])), s.policy,
    )
    assert all(e.source_checkpoint_fingerprint == canonical_hash(
        [p.model_dump(mode='json') for p in s.initial]
    ) for e in s.effects[:4])
    assert {e.source_checkpoint_fingerprint for e in s.effects[4:]} != {
        s.effects[0].source_checkpoint_fingerprint,
    }
    assert any(p.long_term_fatigue > 0 for p in s.terminal)
    assert _parse_calendar_match(ko.model_dump_json()) == ko


@pytest.mark.parametrize('corruption', ['terminal', 'effect', 'final_input', 'roster', 'policy', 'missing'])
def test_rehashed_semantically_corrupt_checkpoint_is_rejected(corruption):
    raw = bracket().model_dump(mode='json')
    if corruption == 'terminal':
        raw['sporting']['terminal'][0]['long_term_fatigue'] += 1
    elif corruption == 'effect':
        raw['sporting']['effects'][0]['form_after'] += 1
    elif corruption == 'final_input':
        raw['matches'][2]['input_context']['player_a']['fatigue_modifier'] = -0.35
    elif corruption == 'roster':
        raw['sporting']['terminal'][0]['player_id'] = 'foreign'
    elif corruption == 'policy':
        raw['sporting']['policy']['projection']['fatigue_modifier_divisor'] = 0
    else:
        del raw['sporting']
    # Even an attacker updating the outer hash cannot install false deltas.
    with pytest.raises(ValueError):
        _parse_calendar_match(json.dumps(raw))


def test_duplicate_player_cannot_receive_two_simultaneous_effects():
    ko = bracket()
    with pytest.raises(ValueError, match='repeats'):
        advance_played_slot(ko.sporting.initial, (ko.matches[0], ko.matches[0]), ko.sporting.policy)


def test_historical_v1_fixture_preserves_json_hash_and_real_replay():
    path = Path(__file__).parent / 'fixtures' / 'calendar_knockout_v1.json'
    raw = json.loads(path.read_text())
    match = _parse_calendar_match(json.dumps(raw['state']))
    assert match.schema_version == 'calendar_opening_knockout.v1'
    assert match.sporting is None
    assert match.model_dump(mode='json') == raw['state']
    assert match.fingerprint == raw['fingerprint']
    for played in match.matches:
        result = MatchEngine(DeterministicRng(played.seed)).simulate(
            played.input_context, log_anchor_hash=played.log_anchor_hash,
        )
        assert result == played.result
    forbidden = deepcopy(raw['state'])
    forbidden['sporting'] = bracket().sporting.model_dump(mode='json')
    with pytest.raises(ValueError, match='Historical v1'):
        _parse_calendar_match(json.dumps(forbidden))
