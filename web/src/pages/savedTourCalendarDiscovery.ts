/** Local Saved Calendar discovery only: no server queries, mutations or inferred match results. */
import type {SavedTourEvent} from '../api/savedTour'

export type PublicationFilter='all'|'published'|'not-published'
export type PlayerOutcomeFilter='any'|'champion'|'finalist'
export type SavedCalendarDiscoveryFilters={
  tour:string;category:string;country:string;search:string;publication:PublicationFilter
  playerId:string;playerOutcome:PlayerOutcomeFilter
}

/** Unknown URL values never accidentally filter out an entire historical season. */
export function savedCalendarPublication(raw:string|null):PublicationFilter{
  return raw==='published'||raw==='not-published'?raw:'all'
}

/** An unknown result-role link must never be interpreted as a hidden exclusion. */
export function savedCalendarPlayerOutcome(raw:string|null):PlayerOutcomeFilter{
  return raw==='champion'||raw==='finalist'?raw:'any'
}

const normalize=(text:unknown):string=>(typeof text==='string'?text:'').normalize('NFD')
  .replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase().trim()

/** A non-published result is not proof that an edition has yet been played. */
export function filterSavedTourEvents(
  editions:readonly SavedTourEvent[],filters:SavedCalendarDiscoveryFilters
):SavedTourEvent[]{
  const query=normalize(filters.search)
  const playerQuery=normalize(filters.playerId)
  return editions.filter(event=>
    // An ID is an exact identity, never a partial player-name search.
    // Champion/finalist fields describe published results only, not all participants.
    (!playerQuery||(event.result_published&&
      ((filters.playerOutcome!=='finalist'&&normalize(event.champion_player_id)===playerQuery)
      ||(filters.playerOutcome!=='champion'&&normalize(event.finalist_player_id)===playerQuery))))
    &&(!filters.tour||event.tour_level===filters.tour)
    &&(!filters.category||event.category===filters.category)
    &&(!filters.country||event.host_country===filters.country)
    &&(filters.publication==='all'||event.result_published===(filters.publication==='published'))
    &&(!query||[event.event_name,event.event_id,event.host_city??'',event.host_country]
      .some(value=>normalize(value).includes(query))))
}

/** Compact display-only count of published final outcomes from the visible Saved Editions.
 * Not an official player career, trophy record, or cross-season leaderboard. */
export type PublishedFinalFinish={
  playerId:string;championFinishes:number;runnerUpFinishes:number
}
export function publishedFinalFinishes(editions:readonly SavedTourEvent[]):PublishedFinalFinish[]{
  const result=new Map<string,PublishedFinalFinish>()
  const add=(id:string,role:'championFinishes'|'runnerUpFinishes')=>{
    if(!result.has(id))result.set(id,{playerId:id,championFinishes:0,runnerUpFinishes:0})
    result.get(id)![role]++
  }
  for(const event of editions){
    if(!event.result_published)continue
    const winner=typeof event.champion_player_id==='string'?event.champion_player_id.trim():''
    const runnerUp=typeof event.finalist_player_id==='string'?event.finalist_player_id.trim():''
    // Never award both final positions to a single ID in a malformed historical DTO.
    if(winner&&runnerUp&&winner===runnerUp)continue
    if(winner)add(winner,'championFinishes')
    if(runnerUp)add(runnerUp,'runnerUpFinishes')
  }
  return [...result.values()].sort((a,b)=>b.championFinishes-a.championFinishes
    ||b.runnerUpFinishes-a.runnerUpFinishes||a.playerId.localeCompare(b.playerId))
}

/** Build a same-Saved-season final-results search, never a current-HEAD career link.
 * Edition/Match filters from the originating page must not silently hide results. */
export function savedSeasonFinalLookupHref(
  runId:string,branch:string,revision:string,season:number,playerId:string,params:URLSearchParams
):string{
  const copy=new URLSearchParams(params)
  for(const key of ['tab','matchSearch','week','tour','category','country','eventSearch',
    'playerOutcome','fromCountry','rally'])copy.delete(key)
  copy.set('branch',branch)
  copy.set('revision',revision)
  copy.set('season',String(season))
  copy.set('view','list')
  copy.set('publication','published')
  copy.set('playerId',playerId)
  return '/admin/runs/'+encodeURIComponent(runId)+'/tour/calendar?'+copy.toString()
}

/** Invalid deep links never silently fall back to the whole historical season. */
export function savedCalendarWeek(raw:string|null,weekCount:number):number|null|'invalid'{
  if(raw===null)return null
  if(!/^[1-9]\d*$/.test(raw)||!Number.isSafeInteger(weekCount)||weekCount<1)return 'invalid'
  const week=Number(raw)
  return Number.isSafeInteger(week)&&week<=weekCount?week:'invalid'
}
export function neighboringMatchingWeeks(
  occupiedWeeks:readonly number[],selectedWeek:number|null
):{previous:number|null;next:number|null}{
  if(selectedWeek===null)return {previous:null,next:null}
  return {previous:occupiedWeeks.filter(week=>week<selectedWeek).slice(-1)[0]??null,
    next:occupiedWeeks.find(week=>week>selectedWeek)??null}
}

/** Preserve canonical week order, including simultaneous Editions within one week. */
export function calendarWeeksWithEditions(
  editions:readonly SavedTourEvent[],weekCount:number,onlyOccupied:boolean
):number[]{
  if(!Number.isSafeInteger(weekCount)||weekCount<1)return []
  const occupied=new Set(editions.map(event=>event.season_week))
  return Array.from({length:weekCount},(_,index)=>index+1)
    .filter(week=>!onlyOccupied||occupied.has(week))
}
