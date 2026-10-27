export type NativeGroupOptions = {format:'groups'|'groups_knockout';count:number;size:number;advancing:number;groupBestOf:number;knockoutBestOf:number;winPoints:number;crossings:string}
export function crossingPreset(count:number):string {return count===2?'A1-B2 / B1-A2':count===4?'A1-B2 / C1-D2 / B1-A2 / D1-C2':''}
export function pointStages(count:number):string[] {
  const result=['champion']
  for(let n=2;n<=count;n*=2)result.push(({2:'finalist',4:'semifinal',8:'quarterfinal'} as Record<number,string>)[n]??`round_of_${n}`)
  return result
}
function source(text:string) {
  const match=/^([A-Z]+)([1-9]\d*)$/.exec(text.trim())
  if(!match)throw Error('Use group positions such as A1 and B2.')
  let index=0
  for(const c of match[1])index=index*26+c.charCodeAt(0)-64
  return {group_index:index,finishing_position:Number(match[2])}
}
export async function nativeGroupConfiguration(runId:string,branchId:string,commandId:string,season:number,options:NativeGroupOptions) {
  const rules={schema_version:'tournament_group_rules_policy.v1',run_id:runId,branch_id:branchId,effective_from_season_index:season,default_match_best_of:options.groupBestOf,scoring_policy_id:'master_group_table_points.v1',tie_break_policy_id:'wins_points_h2h_ratios_admin_unresolved.v1',walkover_policy_id:'group_wo_win_max_points_no_fabricated_ratios.v1',adopted_by_command_id:commandId}
  const canonical=JSON.stringify(Object.fromEntries(Object.entries(rules).sort(([a],[b])=>a<b?-1:a>b?1:0)))
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical))
  const fingerprint=Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('')
  const crossings=options.format==='groups'?[]:options.crossings.split('/').map((pair,i)=>{
    const parts=pair.trim().split('-')
    if(parts.length!==2)throw Error('Each crossing must contain two group positions.')
    return {match_index:i+1,top:source(parts[0]),bottom:source(parts[1])}
  })
  return {schema_version:'native_group_configuration.v1',format_kind:options.format,rules,knockout_best_of:options.knockoutBestOf,played_group_win_points:options.winPoints,groups:{group_count:options.count,group_size:options.size,seeded_slots_per_group:0,group_seed_placements:[],match_best_of:options.groupBestOf,rules_source_kind:'edition_override',group_rules_policy_fingerprint:fingerprint,group_rules_effective_from_season_index:season,advancing_per_group:options.format==='groups'?0:options.advancing,knockout_crossings:crossings}}
}
