/** Real immutable Admin group-format authorities. No implicit seed/crossing rules. */
export type TournamentGroupRulesState = {
  schema_version:'tournament_group_rules_state.v1'
  run_id:string;branch_id:string;target_season_index:number
  effective:{
    schema_version:'tournament_group_rules_policy.v1'
    run_id:string;branch_id:string;effective_from_season_index:number
    default_match_best_of:3|5;authority_fingerprint:string
  }|null
  versions:unknown[]
}
export type TournamentGroupFormatAuthority = {
  schema_version:'tournament_format_authority.v1'
  run_id:string;branch_id:string;event_id:string
  format_kind:'knockout'|'groups'|'groups_knockout'
  configured_by_command_id:string
  entry_field_fingerprint:string
  group_configuration:{group_count:number;group_size:number;match_best_of:3|5}|null
}
export type TournamentGroupTopologyAuthority = {
  schema_version:'tournament_topology_authority.v1'
  run_id:string;branch_id:string;event_id:string;format_kind:'knockout'|'groups'|'groups_knockout'
  format_authority_fingerprint:string
  generated_by_command_id:string
}
export type GroupSetupPayload = {
  command_id:string;format_kind:'groups'
  group_count:number;group_size:number;seeded_slots_per_group:0
  group_seed_placements:[];match_best_of_override:null
  advancing_per_group:0;knockout_crossings:[]
}
/** A deliberate pure round robin. The product has no universal hybrid crossing default. */
export function proposedPureGroups(
  countText:string,sizeText:string,entrantCount:number,commandId:string
):GroupSetupPayload{
  const valid=(s:string)=>/^[1-9]\d*$/.test(s)
  if(!valid(countText)||!valid(sizeText))throw new Error('Use positive whole group counts and sizes.')
  const groupCount=Number(countText),groupSize=Number(sizeText)
  if(!Number.isSafeInteger(groupCount)||groupCount>64
    ||!Number.isSafeInteger(groupSize)||groupSize<2||groupSize>128
    ||groupCount*groupSize!==entrantCount||entrantCount<2)
    throw new Error('Group count × group size must equal the frozen direct entrants, with no BYEs.')
  return {
    command_id:commandId,format_kind:'groups',
    group_count:groupCount,group_size:groupSize,
    seeded_slots_per_group:0,group_seed_placements:[],
    match_best_of_override:null,advancing_per_group:0,knockout_crossings:[]
  }
}
