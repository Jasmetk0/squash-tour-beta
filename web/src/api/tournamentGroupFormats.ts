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
  group_configuration:{
    group_count:number;group_size:number;match_best_of:3|5
    advancing_per_group:number;seeded_slots_per_group:number
    knockout_crossings:HybridCrossing[]
  }|null
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

/** An explicit ordered pairing of attained *group places*, never a guess from IDs. */
export type HybridCrossing={
  match_index:number
  top:{group_index:number;finishing_position:number}
  bottom:{group_index:number;finishing_position:number}
}
export type HybridGroupSetupPayload={
  command_id:string;format_kind:'groups_knockout'
  group_count:number;group_size:number;seeded_slots_per_group:0
  group_seed_placements:[];match_best_of_override:null
  advancing_per_group:number;knockout_crossings:HybridCrossing[]
}
export type HybridCrossingChoice={top:string;bottom:string}

/** No implicit crossing, seed placement, odd-sized bracket or repeated source. */
export function proposedHybridGroups(
  countText:string,sizeText:string,advancingText:string,entrantCount:number,
  choices:HybridCrossingChoice[],commandId:string
):HybridGroupSetupPayload{
  const valid=(s:string)=>/^[1-9]\d*$/.test(s)
  if(!valid(countText)||!valid(sizeText)||!valid(advancingText))
    throw new Error('Hybrid group counts, size and advancers must be positive whole numbers.')
  const group_count=Number(countText),group_size=Number(sizeText)
  const advancing_per_group=Number(advancingText)
  if(!Number.isSafeInteger(group_count)||group_count>64
    ||!Number.isSafeInteger(group_size)||group_size<2||group_size>128
    ||group_count*group_size!==entrantCount||entrantCount<2)
    throw new Error('Hybrid groups must exactly partition frozen direct entrants.')
  if(!Number.isSafeInteger(advancing_per_group)||advancing_per_group>group_size)
    throw new Error('Advancers cannot exceed the players in each group.')
  const total=group_count*advancing_per_group
  if(total<2||total>128||(total&(total-1))!==0)
    throw new Error('Hybrid knockout field must contain 2, 4, 8 … 128 players.')
  if(!Array.isArray(choices)||choices.length!==total/2)
    throw new Error('One explicit crossing is required for each first-round match.')
  const seen=new Set<string>()
  const parse=(v:string)=>{
    const m=/^([1-9]\d*):([1-9]\d*)$/.exec(v)
    if(!m)throw new Error('Choose every advancing group position explicitly.')
    const group_index=Number(m[1]),finishing_position=Number(m[2])
    if(group_index>group_count||finishing_position>advancing_per_group
      ||seen.has(v))throw new Error('Each valid advancing position must be used exactly once.')
    seen.add(v)
    return {group_index,finishing_position}
  }
  const knockout_crossings=choices.map((choice,i)=>({
    match_index:i+1,top:parse(choice.top),bottom:parse(choice.bottom)
  }))
  if(seen.size!==total)throw new Error('Every advancing group position must be paired once.')
  return {
    command_id,format_kind:'groups_knockout',group_count,group_size,
    seeded_slots_per_group:0,group_seed_placements:[],match_best_of_override:null,
    advancing_per_group,knockout_crossings
  }
}
