/** Exact field-by-field Saved Calendar Edition A/B comparison.
 * Only validated immutable Saved Revision calendars, never live Run drafts or
 * fingerprint-derived pseudo-events. */
import type {SavedTourCalendar,SavedTourEvent} from '../api/savedTour'
import {validSavedTourCalendar} from '../api/savedTour'
import type {SavedRevisionHistoryEntry} from '../api/types'

export type SavedEditionDiffStatus='added'|'removed'|'changed'|'unchanged'
export type SavedEditionDiff={
  eventId:string;name:string;status:SavedEditionDiffStatus
  changedFields:(keyof SavedTourEvent)[]
  a:SavedTourEvent|null;b:SavedTourEvent|null
}
export type SavedEditionComparison={
  rows:SavedEditionDiff[]
  counts:Record<SavedEditionDiffStatus,number>
  branchOwners:{a:string;b:string}
}
const fields:(keyof SavedTourEvent)[]=[
  'season','season_week','event_name','template_id','category','tour_level',
  'host_country','host_city','region','main_draw_size','qualification_draw_size',
  'seeds_count','qualifier_spots','wild_cards','byes','ranking_status',
  'result_published','champion_player_id','finalist_player_id'
]
const textFields=new Set<keyof SavedTourEvent>([
  'season','event_name','template_id','category','host_country','region','ranking_status'
])
const optionalTextFields=new Set<keyof SavedTourEvent>([
  'tour_level','host_city','champion_player_id','finalist_player_id'
])
const numberFields=new Set<keyof SavedTourEvent>([
  'season_week','main_draw_size','qualification_draw_size','seeds_count','qualifier_spots','wild_cards','byes'
])
function validEvent(e:SavedTourEvent):boolean{
  if(!e||!e.event_id||typeof e.event_id!=='string')return false
  for(const field of fields){
    const v=e[field]
    if(textFields.has(field)&& (typeof v!=='string'||!v.trim()))return false
    if(optionalTextFields.has(field)&&v!==null&&(typeof v!=='string'||!v.trim()))return false
    if(numberFields.has(field)&&(!Number.isSafeInteger(v)||Number(v)<0))return false
  }
  if(e.season_week<1||e.season_week>61||typeof e.result_published!=='boolean')return false
  if(e.result_published&&(!e.champion_player_id||!e.finalist_player_id))return false
  if(e.champion_player_id!==null&&e.champion_player_id===e.finalist_player_id)return false
  return true
}
export function compareSavedSeasonEditions(
  runId:string,branchId:string,seasonIndex:number,
  a:SavedRevisionHistoryEntry,b:SavedRevisionHistoryEntry,
  dataA:SavedTourCalendar,dataB:SavedTourCalendar
):SavedEditionComparison|null{
  if(!a||!b||a.revision_id===b.revision_id||
    !Number.isInteger(seasonIndex)||seasonIndex<0||seasonIndex>=50||
    !validSavedTourCalendar(dataA,runId,branchId,a.revision_id,seasonIndex)||
    !validSavedTourCalendar(dataB,runId,branchId,b.revision_id,seasonIndex)||
    dataA.revision_branch_id!==a.revision_branch_id||
    dataB.revision_branch_id!==b.revision_branch_id||
    dataA.calendar_status!=='ready'&&dataA.editions.length>0||
    dataB.calendar_status!=='ready'&&dataB.editions.length>0||
    dataA.editions.some(e=>!validEvent(e))||
    dataB.editions.some(e=>!validEvent(e)))return null
  const left=new Map(dataA.editions.map(e=>[e.event_id,e]))
  const right=new Map(dataB.editions.map(e=>[e.event_id,e]))
  const ids=[...new Set([...left.keys(),...right.keys()])].sort((x,y)=>x.localeCompare(y))
  const rows:SavedEditionDiff[]=ids.map(id=>{
    const before=left.get(id)??null,after=right.get(id)??null
    const changedFields=before&&after?fields.filter(k=>before[k]!==after[k]):[]
    const status:SavedEditionDiffStatus=!before?'added':!after?'removed':
      changedFields.length?'changed':'unchanged'
    return {eventId:id,name:after?.event_name??before!.event_name,status,
      changedFields,a:before,b:after}
  })
  const counts:Record<SavedEditionDiffStatus,number>={added:0,removed:0,changed:0,unchanged:0}
  rows.forEach(r=>counts[r.status]++)
  return {rows,counts,branchOwners:{a:dataA.revision_branch_id,b:dataB.revision_branch_id}}
}
