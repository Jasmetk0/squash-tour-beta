/** Frozen hybrid group-position entrants and bracket; no rank/Race reseeding. */
import type {CompletedGroupStandings} from './tournamentGroupStandings'

export type GroupPosition={group_index:number;finishing_position:number}
export type HybridFirstRoundMatch={
  match_id:string;match_index:number;top_source:GroupPosition;top_player_id:string
  bottom_source:GroupPosition;bottom_player_id:string
}
export type HybridKnockoutEntrants={
  schema_version:'tournament_hybrid_knockout_entrants_authority.v1'
  run_id:string;branch_id:string;event_id:string
  generated_by_command_id:string;authority_fingerprint:string
  topology_authority_fingerprint:string
  group_standings_authority_fingerprint:string
  source_policy_id:'configured_group_crossings_no_reseed.v1'
  first_round_matches:HybridFirstRoundMatch[]
}
export type HybridBracketMatch={
  match_id:string;round_number:number;match_index:number
  participant_sources:[string,string]
}
export type HybridKnockoutBracket={
  schema_version:'tournament_hybrid_knockout_bracket_authority.v1'
  run_id:string;branch_id:string;event_id:string
  generated_by_command_id:string;authority_fingerprint:string
  entrants_authority_fingerprint:string
  bracket_policy_id:'configured_crossings_standard_winner_tree_no_reseed.v1'
  entrant_count:number;round_count:number
  terminal_match_id:string;matches:HybridBracketMatch[]
}
const sha=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v)
const id=(v:unknown):v is string=>typeof v==='string'&&v.length>0
const position=(v:unknown):v is GroupPosition=>Boolean(v&&typeof v==='object'&&
  Number.isSafeInteger((v as GroupPosition).group_index)&&
  (v as GroupPosition).group_index>=1&&
  Number.isSafeInteger((v as GroupPosition).finishing_position)&&
  (v as GroupPosition).finishing_position>=1)
const scope=(x:{run_id:string;branch_id:string;event_id:string},
  r:string,b:string,e:string)=>x.run_id===r&&x.branch_id===b&&x.event_id===e

/** Every enrolled player must be proven in the exact already-frozen group table. */
export function exactHybridEntrants(
  raw:unknown,r:string,b:string,e:string,table:CompletedGroupStandings,
  commandId?:string,
):raw is HybridKnockoutEntrants{
  if(!raw||typeof raw!=='object')return false
  const x=raw as HybridKnockoutEntrants
  if(x.schema_version!=='tournament_hybrid_knockout_entrants_authority.v1'
    ||!scope(x,r,b,e)||!scope(table,r,b,e)
    ||!sha(x.authority_fingerprint)||!sha(x.topology_authority_fingerprint)
    ||!sha(x.group_standings_authority_fingerprint)
    ||x.group_standings_authority_fingerprint!==table.authority_fingerprint
    ||x.source_policy_id!=='configured_group_crossings_no_reseed.v1'
    ||!id(x.generated_by_command_id)
    ||(commandId!==undefined&&x.generated_by_command_id!==commandId)
    ||!Array.isArray(x.first_round_matches))return false
  const count=x.first_round_matches.length*2
  if(count<2||count>128||(count&(count-1))!==0)return false
  const found=new Set<string>(),players=new Set<string>(),matches=new Set<string>()
  for(const [i,m] of x.first_round_matches.entries()){
    if(!m||m.match_index!==i+1||!id(m.match_id)||matches.has(m.match_id)
      ||!position(m.top_source)||!position(m.bottom_source)
      ||!id(m.top_player_id)||!id(m.bottom_player_id))return false
    matches.add(m.match_id)
    for(const [source,player] of [
      [m.top_source,m.top_player_id],[m.bottom_source,m.bottom_player_id],
    ] as const){
      const key=source.group_index+':'+source.finishing_position
      if(found.has(key)||players.has(player))return false
      found.add(key);players.add(player)
      const group=table.groups.find(g=>g.group_index===source.group_index)
      if(group?.rows.find(row=>row.position===source.finishing_position)?.player_id!==player)
        return false
    }
  }
  return players.size===count
}

/** Verify the complete ordinary winner tree, not just matching foreign fingerprints. */
export function exactHybridBracket(
  raw:unknown,r:string,b:string,e:string,entrants:HybridKnockoutEntrants,
  commandId?:string,
):raw is HybridKnockoutBracket{
  if(!raw||typeof raw!=='object')return false
  const x=raw as HybridKnockoutBracket
  if(x.schema_version!=='tournament_hybrid_knockout_bracket_authority.v1'
    ||!scope(x,r,b,e)||!scope(entrants,r,b,e)
    ||!sha(x.authority_fingerprint)
    ||x.entrants_authority_fingerprint!==entrants.authority_fingerprint
    ||x.bracket_policy_id!=='configured_crossings_standard_winner_tree_no_reseed.v1'
    ||!id(x.generated_by_command_id)
    ||(commandId!==undefined&&x.generated_by_command_id!==commandId)
    ||!Array.isArray(x.matches))return false
  const count=entrants.first_round_matches.length*2
  if(x.entrant_count!==count||x.round_count!==Math.log2(count)
    ||x.matches.length!==count-1||!id(x.terminal_match_id))return false
  let previous:string[]=[]
  const ids=new Set<string>()
  for(let round=1;round<=x.round_count;round++){
    const rows=x.matches.filter(m=>m?.round_number===round)
    if(rows.length!==count/(2**round))return false
    const next:string[]=[]
    for(const [i,m] of rows.entries()){
      if(m.match_index!==i+1||!id(m.match_id)||ids.has(m.match_id)
        ||!Array.isArray(m.participant_sources)||m.participant_sources.length!==2
        ||!m.participant_sources.every(id)||m.participant_sources[0]===m.participant_sources[1])
        return false
      const expected=round===1?[
        'player:'+entrants.first_round_matches[i].top_player_id,
        'player:'+entrants.first_round_matches[i].bottom_player_id,
      ]:[
        'winner:'+previous[2*i],'winner:'+previous[2*i+1],
      ]
      if(!m.participant_sources.every((source,j)=>source===expected[j]))return false
      if(round===1&&m.match_id!==entrants.first_round_matches[i].match_id)return false
      ids.add(m.match_id);next.push(m.match_id)
    }
    previous=next
  }
  return previous.length===1&&previous[0]===x.terminal_match_id
}
