"""Versioned Health inputs must be bound to actual played logs, never reinterpreted."""
import json
from functools import lru_cache

import pytest

from beta_engine.application.calendar_opening_knockout_service import CalendarOpeningKnockoutService
from beta_engine.domain.matches.health import PlayerMatchHealthProjection, MatchHealthRecordProjection
from beta_engine.domain.players.calendar_knockout_health import CalendarKnockoutHealthSource
from beta_engine.domain.players.calendar_match_state import (
    CalendarMatchStatePolicy, CalendarKnockoutSportingState, advance_played_slot, participant_with_state,
)
from beta_engine.infrastructure.db.calendar_standalone_match_state import CalendarOpeningKnockout, _parse_calendar_match
from tests.domain.test_calendar_knockout_player_state import bracket
from tests.domain.test_match_engine import _player

pytestmark = pytest.mark.pr_critical


@lru_cache
def health_bracket():
    old = bracket()
    policy = CalendarMatchStatePolicy()
    initial = policy.initial_states(old.entrant_ids)
    source = CalendarKnockoutHealthSource(
        source_health_schema='player_health_calendar_state.v2', source_health_fingerprint='f' * 64,
        source_week=old.week,
        profiles=tuple(PlayerMatchHealthProjection(
            player_id=pid, highest_current_severity=25 if pid == 'a' else 0,
            highest_permanent_limitation=0, numeric_calibration_required=pid == 'a',
            affected_domains=('movement',) if pid == 'a' else (),
            current_records=(MatchHealthRecordProjection(
                record_id='ankle', kind='Injury', condition_key='ankle', lifecycle='Active',
                severity=25, affected_domains=('movement',), provenance='Known before Run',
            ),) if pid == 'a' else (),
        ) for pid in old.entrant_ids),
    )
    players = {pid: _player(player_id=pid, base=65) for pid in old.entrant_ids}
    common = dict(run_id=old.run_id, branch_id=old.branch_id, clock=old.week.calendar,
        saved_head=old.source_saved_head, world_fingerprint=old.source_initial_world_fingerprint,
        pre_slot_anchor=old.pre_slot_anchor, root_id=old.match_id)
    def play(name, slot, seed, a, b, states):
        roster = {s.player_id: s for s in states}
        return CalendarOpeningKnockoutService._play(
            **common, round_name=name, slot=slot, seed=seed, first=players[a], second=players[b],
            first_context=participant_with_state(players[a], roster[a], policy),
            second_context=participant_with_state(players[b], roster[b], policy),
            effective_health=source.for_players(a, b),
        )
    one=play('semifinal_1',1,6,'a','b',initial)
    two=play('semifinal_2',1,7,'c','d',initial)
    after,effects=advance_played_slot(initial,(one,two),policy)
    final=play('final',2,8,one.result.winner_player_id,two.result.winner_player_id,after)
    terminal,last=advance_played_slot(after,(final,),policy)
    raw=old.model_dump(mode='json')
    raw.update(schema_version='calendar_opening_knockout.v3', health_source=source.model_dump(mode='json'),
        matches=[m.model_dump(mode='json') for m in (one,two,final)],
        sporting=CalendarKnockoutSportingState(policy=policy,initial=initial,after_semifinals=after,
            terminal=terminal,effects=effects+last).model_dump(mode='json'))
    return _parse_calendar_match(json.dumps(raw))


def test_real_played_health_inputs_roundtrip_and_keep_injury_distinct_from_numeric_effect():
    ko=health_bracket()
    assert _parse_calendar_match(ko.model_dump_json()) == ko
    assert ko.health_source.profiles[0].highest_current_severity == 25
    assert not ko.health_source.profiles[0].numeric_effect_applied
    for m in ko.matches:
        assert m.effective_health.numeric_effect_applied is False
        assert m.result.rally_log.input_snapshot_hash == m.log_anchor_hash


@pytest.mark.parametrize('fault', ['missing', 'profile', 'match', 'clock', 'anchor', 'old_schema'])
def test_health_snapshot_cannot_be_detached_from_source_or_played_log(fault):
    raw=health_bracket().model_dump(mode='json')
    if fault == 'missing': del raw['health_source']
    elif fault == 'profile': raw['health_source']['profiles'][0]['player_id']='foreign'
    elif fault == 'match': raw['matches'][0]['effective_health']['player_profiles'].reverse()
    elif fault == 'clock': raw['health_source']['source_week']['calendar']['weeks_per_year']=52
    elif fault == 'anchor': raw['matches'][0]['log_anchor_hash']='a' * 64
    else: raw['schema_version']='calendar_opening_knockout.v2'
    with pytest.raises(ValueError): _parse_calendar_match(json.dumps(raw))


def test_old_v2_still_has_no_health_fields():
    old=bracket()
    # Verified against the original merged pre-Health v2 parser.
    assert old.fingerprint == '7eb8ac10bc09eb6ac9143ff1d4c78f6239c6be3111739afd28a1e6875e2053f2'
    raw=old.model_dump(mode='json')
    assert 'health_source' not in raw
    assert all('effective_health' not in m for m in raw['matches'])
    assert _parse_calendar_match(json.dumps(raw)) == old


def test_numeric_outcome_is_not_changed_by_descriptive_health_projection():
    from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
    ko=health_bracket()
    played=ko.matches[0]
    ctx=played.input_context
    healthy=EffectiveMatchHealthSnapshot.create_healthy(
        player_a_id=ctx.player_a.player.player_id, player_b_id=ctx.player_b.player.player_id)
    comparison=CalendarOpeningKnockoutService._play(
        run_id=ko.run_id, branch_id=ko.branch_id, clock=ko.week.calendar,
        saved_head=ko.source_saved_head, world_fingerprint=ko.source_initial_world_fingerprint,
        pre_slot_anchor=ko.pre_slot_anchor, root_id=ko.match_id,
        round_name=played.round, slot=played.slot, seed=played.seed,
        first=ctx.player_a.player, second=ctx.player_b.player,
        first_context=ctx.player_a, second_context=ctx.player_b, effective_health=healthy,
    )
    assert comparison.result.sets == played.result.sets
    assert comparison.result.winner_player_id == played.result.winner_player_id
    assert comparison.log_anchor_hash != played.log_anchor_hash
