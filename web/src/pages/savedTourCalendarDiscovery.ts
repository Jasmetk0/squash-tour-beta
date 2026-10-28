/** Local Saved Calendar discovery only: no server queries, mutations or inferred match results. */
import type {SavedTourEvent} from '../api/savedTour'

export type PublicationFilter='all'|'published'|'not-published'
export type SavedCalendarDiscoveryFilters={
  tour:string;category:string;country:string;search:string;publication:PublicationFilter
}

/** Unknown URL values never accidentally filter out an entire historical season. */
export function savedCalendarPublication(raw:string|null):PublicationFilter{
  return raw==='published'||raw==='not-published'?raw:'all'
}

const normalize=(text:unknown):string=>(typeof text==='string'?text:'').normalize('NFD')
  .replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase().trim()

/** A non-published result is not proof that an edition has yet been played. */
export function filterSavedTourEvents(
  editions:readonly SavedTourEvent[],filters:SavedCalendarDiscoveryFilters
):SavedTourEvent[]{
  const query=normalize(filters.search)
  return editions.filter(event=>
    (!filters.tour||event.tour_level===filters.tour)
    &&(!filters.category||event.category===filters.category)
    &&(!filters.country||event.host_country===filters.country)
    &&(filters.publication==='all'||event.result_published===(filters.publication==='published'))
    &&(!query||[event.event_name,event.event_id,event.host_city??'',event.host_country]
      .some(value=>normalize(value).includes(query))))
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
