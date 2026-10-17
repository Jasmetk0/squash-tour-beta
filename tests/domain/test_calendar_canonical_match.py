"""57-attribute source and projection are actually consumed, not display-only data."""
import json
from functools import lru_cache
from types import SimpleNamespace
import pytest

from beta_engine.application.calendar_opening_knockout_service import CalendarOpeningKnockoutService
from beta_engine.domain.players.calendar_canonical_match import (
    CalendarCanonicalMatchSource, CalendarCanonicalPlayerSource, canonical_participant,
)
from beta_engine.domain.players.sporting import PlayerSportingBootstrapPolicy
from beta_engine.domain.players.sporting_bootstrap import derive_bootstrap_record
from beta_engine.domain.players.calendar_match_state import CalendarKnockoutSportingState, advance_played_slot
from beta_engine.infrastructure.db.calendar_standalone_match_state import _parse_calendar_match
from tests.domain.test_calendar_knockout_player_state import bracket
from tests.domain.test_match_engine import _player

pytestmark=pytest.mark.pr_critical


def source():
    players=tuple(CalendarCanonicalPlayerSource(player=_player(player_id=pid,base=65+i),
        source_generation_fingerprint='generated-'+pid,potential_ability=88) for i,pid in enumerate('abcd'))
    policy=PlayerSportingBootstrapPolicy()
    return CalendarCanonicalMatchSource(source_initial_world_fingerprint='d'*64,
        players=players,records=tuple(derive_bootstrap_record(p,policy) for p in players))


@lru_cache
def canonical_bracket():
    old=bracket(); canonical=source(); policy=old.sporting.policy; initial=old.sporting.initial
    def play(name,slot,seed,a,b,states):
        projections=tuple(canonical.project(pid,states) for pid in (a,b))
        ctx=tuple(canonical_participant(p) for p in projections)
        return CalendarOpeningKnockoutService._play(run_id=old.run_id,branch_id=old.branch_id,
            clock=old.week.calendar,saved_head=old.source_saved_head,
            world_fingerprint=old.source_initial_world_fingerprint,pre_slot_anchor=old.pre_slot_anchor,
            root_id=old.match_id,round_name=name,slot=slot,seed=seed,
            first=ctx[0].player,second=ctx[1].player,first_context=ctx[0],second_context=ctx[1],
            canonical_projections=projections)
    one=play('semifinal_1',1,6,'a','b',initial); two=play('semifinal_2',1,7,'c','d',initial)
    after,effects=advance_played_slot(initial,(one,two),policy)
    final=play('final',2,8,one.result.winner_player_id,two.result.winner_player_id,after)
    terminal,last=advance_played_slot(after,(final,),policy)
    raw=old.model_dump(mode='json');raw.update(schema_version='calendar_opening_knockout.v4',
        canonical_source=canonical.model_dump(mode='json'),matches=[m.model_dump(mode='json') for m in (one,two,final)],
        sporting=CalendarKnockoutSportingState(policy=policy,initial=initial,after_semifinals=after,
            terminal=terminal,effects=effects+last).model_dump(mode='json'))
    return _parse_calendar_match(json.dumps(raw))


def test_canonical_57_are_frozen_and_projected_into_all_actual_matches():
    ko=canonical_bracket(); canonical=ko.canonical_source
    assert all(len(p.attributes)==57 for p in canonical.records)
    assert len({v for _,v in canonical.records[0].attributes})>1
    assert _parse_calendar_match(ko.model_dump_json())==ko
    for m in ko.matches:
        for projection,ctx in zip(m.canonical_projections,(m.input_context.player_a,m.input_context.player_b),strict=True):
            record=next(p for p in canonical.records if p.player_id==projection.player_id)
            assert projection.canonical_attributes==record.attributes
            assert dict(projection.legacy_engine_values)['technique']==ctx.player.technique
            assert ctx==canonical_participant(projection)
        assert m.result.rally_log.input_snapshot_hash==m.log_anchor_hash
    assert advance_played_slot(ko.sporting.initial,ko.matches[:2],ko.sporting.policy)==advance_played_slot(
        ko.sporting.initial,tuple(reversed(ko.matches[:2])),ko.sporting.policy)


@pytest.mark.parametrize('fault',['missing','attribute','policy','projection','context','anchor','old_version','world'])
def test_rehashed_false_canonical_inputs_fail_closed(fault):
    raw=canonical_bracket().model_dump(mode='json')
    if fault=='missing': del raw['canonical_source']
    elif fault=='attribute': raw['canonical_source']['records'][0]['attributes'][0][1]+=1
    elif fault=='policy': raw['canonical_source']['bootstrap_policy']['scale_denominator']=0
    elif fault=='projection': raw['matches'][0]['canonical_projections'][0]['canonical_attributes'][0][1]+=1
    elif fault=='context': raw['matches'][0]['input_context']['player_a']['player']['technique']+=1
    elif fault=='anchor': raw['matches'][0]['log_anchor_hash']='a'*64
    elif fault=='old_version': raw['schema_version']='calendar_opening_knockout.v2'
    else: raw['canonical_source']['source_initial_world_fingerprint']='a'*64
    with pytest.raises(ValueError): _parse_calendar_match(json.dumps(raw))


def test_shared_bootstrap_keeps_legacy_state_shape_and_guard():
    from beta_engine.infrastructure.db.player_sporting_state import derive_bootstrap_sporting
    canonical=source()
    world=SimpleNamespace(schema_version='initial_world_state.v1',players=canonical.players,
        run_id='legacy',branch_id='branch',fingerprint='legacy-source')
    state=derive_bootstrap_sporting(world)
    assert state.players==canonical.records
    assert state.fingerprint=='7bcec372db61064c2ebfd70bb127920e5ce4279da0e6a4f0ccdeade5e56b029c'
    world.schema_version='initial_world_state.v2'
    with pytest.raises(ValueError,match='annual development'): derive_bootstrap_sporting(world)


def test_57_values_affect_engine_projection_not_only_audit_payload():
    from beta_engine.domain.simulation_slots import project_player
    from beta_engine.domain.players.attribute_catalog import ATTRIBUTE_GROUPS
    canonical=source();record=canonical.records[0];profile=canonical.players[0]
    kwargs=dict(source_sporting_fingerprint='state',policy=canonical.projection_policy,
        profile_source_fingerprint=profile.source_generation_fingerprint,profile_provenance='Saved input',
        age=profile.player.age,name=profile.player.name,nationality=profile.player.nationality,
        play_style=profile.player.play_style,archetype=profile.player.archetype,
        hidden_career_traits=profile.player.hidden_career_traits)
    before=project_player(record,**kwargs)
    # An individual canonical group is a sporting input independent of the
    # original seven-field profile; an audit-only attachment would leave this equal.
    changed=record.model_copy(update={'attributes':tuple((name,200 if name in ATTRIBUTE_GROUPS['Technical'] else value)
        for name,value in record.attributes)})
    after=project_player(changed,**kwargs)
    assert dict(after.legacy_engine_values)['technique']>dict(before.legacy_engine_values)['technique']
    assert dict(after.legacy_engine_values)['movement']==dict(before.legacy_engine_values)['movement']
