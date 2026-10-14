import {describe,expect,it} from 'vitest'
import {exactHybridEntrants,exactHybridBracket} from './tournamentHybridKnockout'
import type {HybridKnockoutEntrants,HybridKnockoutBracket} from './tournamentHybridKnockout'
import type {CompletedGroupStandings} from './tournamentGroupStandings'
const sha='a'.repeat(64),other='b'.repeat(64),third='c'.repeat(64)
const row=(group_index:number,position:number,player_id:string)=>({
  group_index,position,player_id,wins:1,losses:0,group_points:3,played_matches:1,
  walkovers_received:0,walkovers_conceded:0,games_won:3,games_lost:1,points_won:33,points_lost:24,
})
const table:CompletedGroupStandings={
  schema_version:'tournament_group_standings_authority.v2',
  run_id:'r',branch_id:'b',event_id:'e',authority_fingerprint:sha,
  group_match_schedule_fingerprint:other,generated_by_command_id:'table',
  source_results:[{match_id:'g1',result_kind:'played'},{match_id:'g2',result_kind:'played'}],
  groups:[
    {group_index:1,rows:[row(1,1,'A'),row(1,2,'B')]},
    {group_index:2,rows:[row(2,1,'C'),row(2,2,'D')]}
  ],
}
const entrants:HybridKnockoutEntrants={
  schema_version:'tournament_hybrid_knockout_entrants_authority.v1',
  run_id:'r',branch_id:'b',event_id:'e',generated_by_command_id:'entrants',
  authority_fingerprint:other,topology_authority_fingerprint:third,
  group_standings_authority_fingerprint:sha,
  source_policy_id:'configured_group_crossings_no_reseed.v1',
  first_round_matches:[
    {match_id:'m1',match_index:1,
      top_source:{group_index:1,finishing_position:1},top_player_id:'A',
      bottom_source:{group_index:2,finishing_position:2},bottom_player_id:'D'},
    {match_id:'m2',match_index:2,
      top_source:{group_index:2,finishing_position:1},top_player_id:'C',
      bottom_source:{group_index:1,finishing_position:2},bottom_player_id:'B'},
  ],
}
const bracket:HybridKnockoutBracket={
  schema_version:'tournament_hybrid_knockout_bracket_authority.v1',
  run_id:'r',branch_id:'b',event_id:'e',generated_by_command_id:'bracket',
  authority_fingerprint:third,entrants_authority_fingerprint:other,
  bracket_policy_id:'configured_crossings_standard_winner_tree_no_reseed.v1',
  entrant_count:4,round_count:2,terminal_match_id:'final',
  matches:[
    {match_id:'m1',round_number:1,match_index:1,participant_sources:['player:A','player:D']},
    {match_id:'m2',round_number:1,match_index:2,participant_sources:['player:C','player:B']},
    {match_id:'final',round_number:2,match_index:1,participant_sources:['winner:m1','winner:m2']},
  ],
}
describe('exact immutable hybrid group-to-knockout source validation',()=>{
  it('confirms only actual final group positions, never initial seeds or ranked players',()=>{
    expect(exactHybridEntrants(entrants,'r','b','e',table)).toBe(true)
    expect(exactHybridEntrants(entrants,'r','b','e',table,'entrants')).toBe(true)
    expect(exactHybridEntrants(entrants,'r','b','e',table,'stale')).toBe(false)
    expect(exactHybridBracket(bracket,'r','b','e',entrants,'bracket')).toBe(true)
  })
  it('refuses corrupt scope, fingerprints, duplicate players, stale table and switched group places',()=>{
    expect(exactHybridEntrants({...entrants,branch_id:'other'},'r','b','e',table)).toBe(false)
    expect(exactHybridEntrants({...entrants,group_standings_authority_fingerprint:third},'r','b','e',table)).toBe(false)
    const changed={...entrants,first_round_matches:entrants.first_round_matches.map(m=>({...m}))}
    changed.first_round_matches[0].top_player_id='B'
    expect(exactHybridEntrants(changed,'r','b','e',table)).toBe(false)
    const duplicate={...entrants,first_round_matches:[
      entrants.first_round_matches[0],{
        ...entrants.first_round_matches[1],
        bottom_source:{group_index:1,finishing_position:1},
        bottom_player_id:'A',
      }
    ]}
    expect(exactHybridEntrants(duplicate,'r','b','e',table)).toBe(false)
    expect(exactHybridEntrants({...entrants,first_round_matches:[]},'r','b','e',table)).toBe(false)
  })
  it('rejects a falsified bracket including incorrect first round, future feeder or missing match',()=>{
    expect(exactHybridBracket({...bracket,branch_id:'other'},'r','b','e',entrants)).toBe(false)
    expect(exactHybridBracket({...bracket,entrants_authority_fingerprint:sha},'r','b','e',entrants)).toBe(false)
    expect(exactHybridBracket({...bracket,matches:bracket.matches.slice(0,2)},'r','b','e',entrants)).toBe(false)
    const switched={...bracket,matches:bracket.matches.map(m=>({...m}))}
    switched.matches[0].participant_sources=['player:B','player:D']
    expect(exactHybridBracket(switched,'r','b','e',entrants)).toBe(false)
    const falseFinal={...bracket,matches:bracket.matches.map(m=>({...m}))}
    falseFinal.matches[2].participant_sources=['winner:m2','winner:m1']
    expect(exactHybridBracket(falseFinal,'r','b','e',entrants)).toBe(false)
  })
})
