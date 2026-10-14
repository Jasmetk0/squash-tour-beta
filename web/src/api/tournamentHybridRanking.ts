import type {HybridKnockoutBracket} from './tournamentHybridKnockout'
import type {CompletedGroupStandings} from './tournamentGroupStandings'

export type HybridRankingPolicy={
  schema_version:'tournament_hybrid_ranking_policy_authority.v1'
  run_id:string;branch_id:string;event_id:string
  configured_by_command_id:string;authority_fingerprint:string
  group_component_policy_id:'played_group_match_win_only.v1'
  played_group_win_points:number
  knockout_stage_points:[string,number][]
  composition_policy_id:'single_tournament_sum_group_plus_knockout_no_double_count.v1'
}
export type HybridRankingClosure={
  schema_version:'tournament_hybrid_closure_response.v1'
  run_id:string;branch_id:string;event_id:string
  source_fingerprint:string;result_fingerprint:string;award_fingerprint:string
  prize_award_fingerprint:string;prize_configuration_status:string
  total_ranking_points:number
}
export type HybridRankingPayload={
  command_id:string;played_group_win_points:number
  knockout_stage_points:[string,number][]
}
export const isFingerprint=(x:unknown)=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x)
const stagesByDistance=[
  'finalist','semifinal','quarterfinal','round_of_16',
  'round_of_32','round_of_64','round_of_128',
]
export function requiredHybridStages(bracket:HybridKnockoutBracket):string[]{
  if(!Number.isSafeInteger(bracket.round_count)||bracket.round_count<1
    ||bracket.round_count>7||bracket.entrant_count!==2**bracket.round_count)
    throw new Error('Hybrid knockout bracket size or round count is unsupported.')
  return ['champion',...stagesByDistance.slice(0,bracket.round_count)].sort()
}
export function reviewedHybridRankingPayload(
  bracket:HybridKnockoutBracket,standings:CompletedGroupStandings,
  groupText:string,values:Record<string,string>,command_id:string,
):HybridRankingPayload{
  const nonNegative=(s:string)=>/^(0|[1-9]\d*)$/.test(s)
  const stages=requiredHybridStages(bracket)
  if(!command_id.trim()||command_id.length>128||!nonNegative(groupText))
    throw new Error('Provide a non-negative whole number of points for a played group win.')
  if(stages.some(stage=>!nonNegative(values[stage]??'')))
    throw new Error('Explicit non-negative integer points are required for every knockout stage.')
  const played_group_win_points=Number(groupText)
  const knockout_stage_points=stages.map(stage=>[stage,Number(values[stage])] as [string,number])
  if(!Number.isSafeInteger(played_group_win_points)
    ||knockout_stage_points.some(([_,n])=>!Number.isSafeInteger(n)))
    throw new Error('Ranking points must be safe whole numbers.')
  if(played_group_win_points>0&&standings.source_results.some(x=>x.result_kind==='walkover'))
    throw new Error('Ranking reward for a group walkover is not yet specified; choose zero or resolve the policy.')
  return {command_id,played_group_win_points,knockout_stage_points}
}
export function exactHybridRankingPolicy(
  x:HybridRankingPolicy|undefined,r:string,b:string,e:string,
  bracket:HybridKnockoutBracket,
  expected?:HybridRankingPayload,
):x is HybridRankingPolicy{
  if(!x||x.schema_version!=='tournament_hybrid_ranking_policy_authority.v1'
    ||x.run_id!==r||x.branch_id!==b||x.event_id!==e
    ||!isFingerprint(x.authority_fingerprint)
    ||x.group_component_policy_id!=='played_group_match_win_only.v1'
    ||x.composition_policy_id!=='single_tournament_sum_group_plus_knockout_no_double_count.v1'
    ||typeof x.configured_by_command_id!=='string'||!x.configured_by_command_id
    ||!Number.isSafeInteger(x.played_group_win_points)||x.played_group_win_points<0
    ||!Array.isArray(x.knockout_stage_points))return false
  const stages=requiredHybridStages(bracket)
  const pairs=x.knockout_stage_points
  if(pairs.length!==stages.length||pairs.some((pair,i)=>
    !Array.isArray(pair)||pair.length!==2||pair[0]!==stages[i]
    ||!Number.isSafeInteger(pair[1])||pair[1]<0))return false
  return !expected||(expected.command_id===x.configured_by_command_id
    &&expected.played_group_win_points===x.played_group_win_points
    &&JSON.stringify(expected.knockout_stage_points)===JSON.stringify(pairs))
}
export function exactHybridRankingClosure(x:HybridRankingClosure|undefined,
  r:string,b:string,e:string):x is HybridRankingClosure{
  return Boolean(x&&x.schema_version==='tournament_hybrid_closure_response.v1'
    &&x.run_id===r&&x.branch_id===b&&x.event_id===e
    &&isFingerprint(x.source_fingerprint)&&isFingerprint(x.result_fingerprint)
    &&isFingerprint(x.award_fingerprint)&&isFingerprint(x.prize_award_fingerprint)
    &&typeof x.prize_configuration_status==='string'
    &&x.prize_configuration_status.length>0
    &&Number.isSafeInteger(x.total_ranking_points)&&x.total_ranking_points>=0)
}
