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
export type SavedTourEdition = {
  schema_version:'run_saved_tour_edition.v1';source:'reachable_saved_revision'
  run_id:string;branch_id:string;revision_branch_id:string
  saved_revision_id:string;season_index:number
  edition:SavedTourEvent;published_result:SavedTourResult|null
  lifecycle_status:'unavailable'
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
  return result===null?!payload.edition.result_published:
    payload.edition.result_published &&
    result.event_id===eventId&&result.product_run_id===runId
    &&result.viewer_branch_id===payload.revision_branch_id
    &&result.completed_season_index===seasonIndex
    &&result.completed_week===payload.edition.season_week
}
