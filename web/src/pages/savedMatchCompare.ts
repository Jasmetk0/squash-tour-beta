/** Published match evidence only: two exact reachable Saved Edition snapshots.
 * Never turn an unpublished result into "no matches played". */
import {validSavedTourEdition} from '../api/savedTour'
import type {SavedTourEdition,SavedTourEvent} from '../api/savedTour'
import type {SavedRevisionHistoryEntry} from '../api/types'

export type PublishedMatch = NonNullable<SavedTourEdition['published_result']>['matches'][number]
export type PublishedMatchStatus = 'added'|'removed'|'changed'|'unchanged'
export type PublishedMatchDiff = {
  matchId:string;status:PublishedMatchStatus
  changedFields:(keyof PublishedMatch)[]
  a:PublishedMatch|null;b:PublishedMatch|null
}
export type PublishedMatchComparison = {
  availability:'published'|'unpublished'
  rows:PublishedMatchDiff[]
  counts:Record<PublishedMatchStatus,number>
}
const fields:(keyof PublishedMatch)[]=[
  'draw_type','round_number','bracket_position','winner_player_id',
  'loser_player_id','scoreline'
]
function matchesExactCalendarItem(actual:SavedTourEvent,expected:SavedTourEvent):boolean{
  const left=actual as unknown as Record<string,unknown>
  const right=expected as unknown as Record<string,unknown>
  return Object.keys(left).length===Object.keys(right).length
    &&Object.keys(right).every(key=>left[key]===right[key])
}
function validPublishedMatches(matches:PublishedMatch[]):boolean{
  if(!Array.isArray(matches))return false
  const ids=new Set<string>()
  for(const m of matches){
    if(!m||typeof m.match_id!=='string'||!m.match_id.trim()||ids.has(m.match_id)
      ||!['qualification','main','group','knockout'].includes(m.draw_type)
      ||!Number.isSafeInteger(m.round_number)||m.round_number<1
      ||!Number.isSafeInteger(m.bracket_position)||m.bracket_position<1
      ||typeof m.winner_player_id!=='string'||!m.winner_player_id.trim()
      ||(m.loser_player_id!==null&&(typeof m.loser_player_id!=='string'
        ||!m.loser_player_id.trim()||m.loser_player_id===m.winner_player_id))
      ||typeof m.scoreline!=='string'||!m.scoreline.trim())return false
    ids.add(m.match_id)
  }
  return true
}
export function comparePublishedSavedMatches(
  runId:string,branchId:string,seasonIndex:number,eventId:string,
  revisionA:SavedRevisionHistoryEntry,revisionB:SavedRevisionHistoryEntry,
  calendarA:SavedTourEvent,calendarB:SavedTourEvent,
  stateA:SavedTourEdition,stateB:SavedTourEdition
):PublishedMatchComparison|null{
  if(!calendarA||!calendarB||!revisionA||!revisionB
    ||revisionA.revision_id===revisionB.revision_id
    ||!eventId||calendarA.event_id!==eventId||calendarB.event_id!==eventId
    ||!validSavedTourEdition(stateA,runId,branchId,revisionA.revision_id,seasonIndex,eventId)
    ||!validSavedTourEdition(stateB,runId,branchId,revisionB.revision_id,seasonIndex,eventId)
    ||stateA.revision_branch_id!==revisionA.revision_branch_id
    ||stateB.revision_branch_id!==revisionB.revision_branch_id
    ||!matchesExactCalendarItem(stateA.edition,calendarA)
    ||!matchesExactCalendarItem(stateB.edition,calendarB))return null
  const empty=():Record<PublishedMatchStatus,number>=>({
    added:0,removed:0,changed:0,unchanged:0
  })
  const a=stateA.published_result,b=stateB.published_result
  // Missing publication is not proof that the match never existed/was removed.
  if(!a||!b)return {availability:'unpublished',rows:[],counts:empty()}
  if(a.schema_version!=='viewer_tournament_result.v1'
    ||b.schema_version!=='viewer_tournament_result.v1'
    ||!Array.isArray(a.players)||!Array.isArray(b.players)
    ||!validPublishedMatches(a.matches)||!validPublishedMatches(b.matches))return null
  const before=new Map(a.matches.map(m=>[m.match_id,m]))
  const after=new Map(b.matches.map(m=>[m.match_id,m]))
  const ids=[...new Set([...before.keys(),...after.keys()])].sort()
  const rows:PublishedMatchDiff[]=ids.map(id=>{
    const left=before.get(id)??null,right=after.get(id)??null
    const changedFields=left&&right?fields.filter(f=>left[f]!==right[f]):[]
    const status:PublishedMatchStatus=!left?'added':!right?'removed':
      changedFields.length?'changed':'unchanged'
    return {matchId:id,status,changedFields,a:left,b:right}
  })
  const counts=empty()
  rows.forEach(r=>counts[r.status]++)
  return {availability:'published',rows,counts}
}
