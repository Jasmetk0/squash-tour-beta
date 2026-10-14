import {describe,expect,it} from 'vitest'
import {
  requiredHybridStages,reviewedHybridRankingPayload,exactHybridRankingPolicy,
  exactHybridRankingClosure,
} from './tournamentHybridRanking'
import type {HybridKnockoutBracket} from './tournamentHybridKnockout'
import type {CompletedGroupStandings} from './tournamentGroupStandings'
const sha='a'.repeat(64)
const bracket={
  schema_version:'tournament_hybrid_knockout_bracket_authority.v1',
  run_id:'r',branch_id:'b',event_id:'e',authority_fingerprint:sha,
  generated_by_command_id:'bracket',entrants_authority_fingerprint:sha,
  bracket_policy_id:'configured_crossings_standard_winner_tree_no_reseed.v1',
  entrant_count:2,round_count:1,terminal_match_id:'final',matches:[],
} as HybridKnockoutBracket
const table={
  run_id:'r',branch_id:'b',event_id:'e',authority_fingerprint:sha,
  source_results:[{result_kind:'played'}],
} as CompletedGroupStandings
const args:[typeof bracket,typeof table,string,Record<string,string>,string]=[
  bracket,table,'10',{champion:'100',finalist:'60'},'reviewed',
]
describe('Explicit immutable hybrid ranking points',()=>{
  it('requires review of every value and produces sorted canonical phase points',()=>{
    expect(requiredHybridStages(bracket)).toEqual(['champion','finalist'])
    expect(reviewedHybridRankingPayload(...args)).toEqual({
      command_id:'reviewed',played_group_win_points:10,
      knockout_stage_points:[['champion',100],['finalist',60]],
    })
    expect(requiredHybridStages({...bracket,entrant_count:8,round_count:3}))
      .toEqual(['champion','finalist','quarterfinal','semifinal'])
  })
  it('rejects missing defaults, NaN, fractions, negative points, and unspecified W/O policy',()=>{
    for(const [group,points] of [
      ['',{champion:'100',finalist:'60'}],
      ['10',{champion:'',finalist:'60'}],
      ['10',{champion:'100',finalist:'-5'}],
      ['10',{champion:'100.5',finalist:'60'}],
      ['99999999999999999',{champion:'100',finalist:'60'}],
    ] as Array<[string,Record<string,string>]>){
      expect(()=>reviewedHybridRankingPayload(bracket,table,group,points,'cmd')).toThrow()
    }
    expect(()=>reviewedHybridRankingPayload(bracket,
      {...table,source_results:[{result_kind:'walkover'}]} as CompletedGroupStandings,
      '10',{champion:'100',finalist:'60'},'cmd')).toThrow(/walkover/)
    expect(reviewedHybridRankingPayload(bracket,
      {...table,source_results:[{result_kind:'walkover'}]} as CompletedGroupStandings,
      '0',{champion:'100',finalist:'60'},'cmd').played_group_win_points).toBe(0)
  })
  it('rejects foreign source scopes and changed frozen stage points',()=>{
    const policy={
      schema_version:'tournament_hybrid_ranking_policy_authority.v1',
      run_id:'r',branch_id:'b',event_id:'e',configured_by_command_id:'reviewed',
      authority_fingerprint:sha,group_component_policy_id:'played_group_match_win_only.v1',
      played_group_win_points:10,knockout_stage_points:[['champion',100],['finalist',60]],
      composition_policy_id:'single_tournament_sum_group_plus_knockout_no_double_count.v1',
    } as const
    expect(exactHybridRankingPolicy(policy as any,'r','b','e',bracket,
      reviewedHybridRankingPayload(...args))).toBe(true)
    expect(exactHybridRankingPolicy({...policy,event_id:'wrong'} as any,'r','b','e',bracket)).toBe(false)
    expect(exactHybridRankingPolicy({...policy,knockout_stage_points:[['champion',60],['finalist',100]]} as any,
      'r','b','e',bracket,reviewedHybridRankingPayload(...args))).toBe(false)
    const closure={
      schema_version:'tournament_hybrid_closure_response.v1',
      run_id:'r',branch_id:'b',event_id:'e',
      source_fingerprint:sha,result_fingerprint:sha,award_fingerprint:sha,
      prize_award_fingerprint:sha,prize_configuration_status:'configured',
      total_ranking_points:180,
    } as const
    expect(exactHybridRankingClosure(closure,'r','b','e')).toBe(true)
    expect(exactHybridRankingClosure({...closure,award_fingerprint:'invalid'},'r','b','e')).toBe(false)
    expect(exactHybridRankingClosure({...closure,branch_id:'other'},'r','b','e')).toBe(false)
  })
})
