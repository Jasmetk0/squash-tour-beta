/** Read-only Saved Revision Run Tour contracts from the canonical backend. */
export type SavedTourEvent = {
  event_id:string;season:string;season_week:number;event_name:string
  template_id:string;category:string;tour_level:string|null
  host_country:string;host_city:string|null;region:string
  main_draw_size:number;qualification_draw_size:number
  seeds_count:number;qualifier_spots:number;wild_cards:number;byes:number
  ranking_status:string;result_published:boolean
  champion_player_id:string|null;finalist_player_id:string|null
}
export type SavedTourCalendar = {
  schema_version:'run_saved_tour_calendar.v1';source:'reachable_saved_revision'
  run_id:string;branch_id:string;revision_branch_id:string
  saved_revision_id:string;season_index:number;season:string;week_count:61
  calendar_status:'empty'|'ready';edition_count:number;editions:SavedTourEvent[]
}
export type SavedTourResult = {
  schema_version:'viewer_tournament_result.v1'
  product_run_id:string;viewer_branch_id:string;event_id:string
  completed_season_index:number;completed_week:number
  champion_player_id:string;finalist_player_id:string
  qualification_winner_ids:string[]
  players:Array<{player_id:string;draw_type:string;reached_stage:string;wins:number;losses:number}>
  matches:Array<{match_id:string;draw_type:string;round_number:number;bracket_position:number;winner_player_id:string;loser_player_id:string|null;scoreline:string}>
}
export type SavedTourEntryField = {
  schema_version:'viewer_tournament_entry_field.v1'
  product_run_id:string;viewer_branch_id:string;event_id:string
  field_sequence:number;mode:'initial'|'pre_draw_repair'
  main_draw_capacity:number;active_main_entrant_count:number;effective_main_bye_count:number
  direct_main_player_ids:string[];qualification_player_ids:string[]
  alternate_player_ids:string[];withdrawn_player_ids:string[]
}
export type SavedTourDrawSlot = {
  slot_index:number;entrant_kind:'player'|'qualifier_placeholder'|'lucky_loser_placeholder'|'bye'
  player_id:string|null;placeholder_id:string|null;seed_number:number|null
  entry_status:'wild_card'|'lucky_loser'|null
}
export type SavedTourDrawBracket = {
  draw_type:'main'|'qualification';section_id:string|null;bracket_size:number;slots:SavedTourDrawSlot[]
}
export type SavedTourDraw = {
  schema_version:'viewer_tournament_draw.v1'
  product_run_id:string;viewer_branch_id:string;event_id:string;revision_count:number
  main:SavedTourDrawBracket;qualification_sections:SavedTourDrawBracket[]
}
export type SavedTourScheduledMatch = {
  global_slot_ordinal:number;match_day_ordinal:number;match_order:number
  draw_phase:'qualification'|'main'|'group';round_number:number
  group_id:string;match_id:string|null
}
export type SavedTourMatchSchedule = {
  schema_version:'run_saved_tour_match_schedule.v1'
  source:'saved_week_simulation_schedule.v2'
  run_id:string;revision_branch_id:string;event_id:string
  season_index:number;season_week:number;week_schedule_fingerprint:string
  slots:SavedTourScheduledMatch[]
}
export type SavedTourEdition = {
  schema_version:'run_saved_tour_edition.v1';source:'reachable_saved_revision'
  run_id:string;branch_id:string;revision_branch_id:string
  saved_revision_id:string;season_index:number
  edition:SavedTourEvent;published_result:SavedTourResult|null
  entry_field?:SavedTourEntryField|null;draw?:SavedTourDraw|null
  match_schedule?:SavedTourMatchSchedule|null
  lifecycle_status:'unavailable'
}

export type SavedTourRallyFrame = {
  rally_index:number;set_number:number;server_player_id:string;winner_player_id:string|null
  score_a_before:number;score_b_before:number;score_a_after:number;score_b_after:number
  sets_a_after:number;sets_b_after:number;set_complete:boolean;match_complete:boolean
}
export type SavedTourMatchDetail = {
  schema_version:'run_saved_tour_match_detail.v1'
  source:'reachable_saved_revision'
  run_id:string;branch_id:string;revision_branch_id:string
  saved_revision_id:string;season_index:number;event_id:string;match_id:string
  match:SavedTourResult['matches'][number]
  replay_status:'available'|'unavailable';player_a_id:string|null;player_b_id:string|null
  offset:number;limit:number;total_rallies:number;has_more:boolean
  rallies:SavedTourRallyFrame[]
}
/** Exact selected branch and original revision-owner validation for historical match pages. */
export function validSavedTourMatchDetail(
  data:SavedTourMatchDetail,runId:string,branchId:string,revisionId:string,
  seasonIndex:number,eventId:string,matchId:string,offset:number,limit:number
):boolean{
  if(data.schema_version!=='run_saved_tour_match_detail.v1'
    ||data.source!=='reachable_saved_revision'
    ||data.run_id!==runId||data.branch_id!==branchId
    ||!data.revision_branch_id||data.saved_revision_id!==revisionId
    ||data.season_index!==seasonIndex||data.event_id!==eventId
    ||data.match_id!==matchId||data.match?.match_id!==matchId
    ||!data.match.winner_player_id||!data.match.loser_player_id
    ||data.match.winner_player_id===data.match.loser_player_id
    ||data.offset!==offset||data.limit!==limit
    ||!Number.isInteger(data.total_rallies)||data.total_rallies<0
    ||!Array.isArray(data.rallies)||data.rallies.length>limit
    ||!['available','unavailable'].includes(data.replay_status)
    ||data.has_more!==(data.replay_status==='available'&&offset+limit<data.total_rallies))
    return false
  if(data.replay_status==='unavailable')
    return data.total_rallies===0&&data.rallies.length===0&&!data.player_a_id&&!data.player_b_id
  if(!data.player_a_id||!data.player_b_id||data.player_a_id===data.player_b_id
    ||new Set([data.player_a_id,data.player_b_id,data.match.winner_player_id,data.match.loser_player_id]).size!==2
    ||data.total_rallies===0
    ||data.rallies.length!==Math.max(0,Math.min(limit,data.total_rallies-offset)))
    return false
  return data.rallies.every((frame,i)=>
    frame.rally_index===offset+i+1&&frame.set_number>=1&&
    [data.player_a_id,data.player_b_id].includes(frame.server_player_id)&&
    (frame.winner_player_id===null||[data.player_a_id,data.player_b_id].includes(frame.winner_player_id))
  )
}

/** Fail closed before displaying data from stale caches or cross-Branch responses. */
export function matchesSavedTourContext(
  payload:SavedTourCalendar|SavedTourEdition,
  runId:string,branchId:string,revisionId:string,seasonIndex:number
):boolean{
  return payload.source==='reachable_saved_revision'
    && payload.run_id===runId && payload.branch_id===branchId
    && payload.saved_revision_id===revisionId
    && payload.season_index===seasonIndex
    && typeof payload.revision_branch_id==='string'
    && payload.revision_branch_id.length>0
    && (payload.schema_version==='run_saved_tour_calendar.v1'
      || payload.schema_version==='run_saved_tour_edition.v1')
}
export function validSavedTourCalendar(
  payload:SavedTourCalendar,runId:string,branchId:string,revisionId:string,seasonIndex:number
):boolean{
  if(!matchesSavedTourContext(payload,runId,branchId,revisionId,seasonIndex)
    ||payload.schema_version!=='run_saved_tour_calendar.v1'
    ||payload.week_count!==61||!Array.isArray(payload.editions)
    ||payload.edition_count!==payload.editions.length)return false
  const seen=new Set<string>()
  return payload.editions.every(e=>{
    if(!e.event_id||seen.has(e.event_id)
      ||!Number.isInteger(e.season_week)||e.season_week<1||e.season_week>61
      ||e.season!==payload.season)return false
    seen.add(e.event_id)
    return true
  })
}
export function validSavedTourEdition(
  payload:SavedTourEdition,runId:string,branchId:string,revisionId:string,seasonIndex:number,eventId:string
):boolean{
  if(!matchesSavedTourContext(payload,runId,branchId,revisionId,seasonIndex)
    ||payload.schema_version!=='run_saved_tour_edition.v1'
    ||payload.edition.event_id!==eventId
    ||payload.lifecycle_status!=='unavailable')return false
  const result=payload.published_result
  const published=result===null?!payload.edition.result_published:
    payload.edition.result_published &&
    result.event_id===eventId&&result.product_run_id===runId
    &&result.viewer_branch_id===payload.revision_branch_id
    &&result.completed_season_index===seasonIndex
    &&result.completed_week===payload.edition.season_week
  if(!published)return false
  const entry=payload.entry_field,draw=payload.draw
  const owned=(value:{product_run_id:string;viewer_branch_id:string;event_id:string})=>
    value.product_run_id===runId&&value.viewer_branch_id===payload.revision_branch_id
      &&value.event_id===eventId
  if(entry){
    if(entry.schema_version!=='viewer_tournament_entry_field.v1'||!owned(entry)
      ||!Array.isArray(entry.direct_main_player_ids)
      ||!Array.isArray(entry.qualification_player_ids)
      ||!Array.isArray(entry.alternate_player_ids)
      ||!Array.isArray(entry.withdrawn_player_ids))return false
    const active=[...entry.direct_main_player_ids,...entry.qualification_player_ids,
      ...entry.alternate_player_ids]
    if(new Set(active).size!==active.length
      ||entry.withdrawn_player_ids.some(id=>active.includes(id)))return false
  }
  if(draw){
    if(!entry||draw.schema_version!=='viewer_tournament_draw.v1'||!owned(draw)
      ||!Array.isArray(draw.qualification_sections))return false
    const brackets=[draw.main,...draw.qualification_sections]
    for(const bracket of brackets){
      if(!Array.isArray(bracket.slots)||bracket.slots.length!==bracket.bracket_size
        ||new Set(bracket.slots.map(slot=>slot.slot_index)).size!==bracket.bracket_size
        ||bracket.slots.some(slot=>slot.slot_index<1||slot.slot_index>bracket.bracket_size
          ||(slot.entrant_kind==='player'?!slot.player_id:slot.player_id!==null)))
        return false
    }
  }
  const schedule=payload.match_schedule
  if(schedule){
    if(schedule.schema_version!=='run_saved_tour_match_schedule.v1'
      ||schedule.source!=='saved_week_simulation_schedule.v2'
      ||schedule.run_id!==runId||schedule.revision_branch_id!==payload.revision_branch_id
      ||schedule.event_id!==eventId||schedule.season_index!==seasonIndex
      ||schedule.season_week!==payload.edition.season_week
      ||!Array.isArray(schedule.slots)
      ||!/^[0-9a-f]{64}$/.test(schedule.week_schedule_fingerprint))return false
    const groups=new Set<string>(),ordinals=new Set<number>()
    for(const slot of schedule.slots){
      if(!slot.group_id||groups.has(slot.group_id)||ordinals.has(slot.global_slot_ordinal)
        ||!Number.isInteger(slot.global_slot_ordinal)||slot.global_slot_ordinal<1
        ||!Number.isInteger(slot.match_day_ordinal)||slot.match_day_ordinal<1
        ||!Number.isInteger(slot.match_order)||slot.match_order<1
        ||!Number.isInteger(slot.round_number)||slot.round_number<1
        ||!['main','qualification','group'].includes(slot.draw_phase)
        ||(slot.match_id!==null&&!slot.match_id))return false
      groups.add(slot.group_id);ordinals.add(slot.global_slot_ordinal)
    }
  }
  return true
}
