/** Immutable Run-owned Calendar edition projection for a selected country. */
import type {RunPackageStateResponse} from '../api/types'
type R=Record<string,unknown>
const obj=(x:unknown):R|null=>x!==null&&typeof x==='object'&&!Array.isArray(x)?x as R:null
const str=(x:unknown):string|null=>typeof x==='string'&&x.trim()?x:null
export function calendarSeasonIndex(v:unknown):number|null {
  if(typeof v==='number'&&Number.isSafeInteger(v))return v>=0&&v<50?v:v>=2000&&v<2050?v-2000:null
  if(typeof v!=='string')return null
  const m=/^(20[0-4][0-9])\/(\d{2}|20\d{2})$/.exec(v)
  if(m){const a=Number(m[1]),b=Number(m[2])
    return a<2050&&(m[2].length===2?b===(a+1)%100:b===a+1)?a-2000:null}
  return /^(0|[1-9]\d*)$/.test(v)?calendarSeasonIndex(Number(v)):null
}
export type CountryTournamentEdition={
  key:string;packageId:string;eventId:string;name:string;season:string;seasonIndex:number
  week:number;city:string|null;hostCountry:string;category:string|null;tourLevel:string|null
  status:'planned'|'scheduled'|'active'|'completed'|'cancelled'
}
export type CountryTournaments={fingerprint:string;calendarCount:number;editions:CountryTournamentEdition[]}
const statuses=new Set(['planned','scheduled','active','completed','cancelled'])
export function projectCountryTournaments(response:RunPackageStateResponse,runId:string,originBranchId:string,countryCode:string):CountryTournaments|null {
  if(!/^[A-Z]{3}$/.test(countryCode))throw new Error('Invalid selected country code')
  const state=obj(response.state)
  if(!state)return null
  if(state.run_id!==runId||state.branch_id!==originBranchId)
    throw new Error('Saved Calendar Run/Branch ownership mismatch')
  if(typeof response.fingerprint!=='string'||!/^[0-9a-f]{64}$/.test(response.fingerprint)||
    !Array.isArray(state.entities)||!Array.isArray(state.package_versions))
    throw new Error('Saved Calendar Run Package component is incomplete')
  const packages=state.package_versions.map(obj).filter((x):x is R=>x!==null&&x.package_type==='Calendar')
  const ids=new Set<string>(),eventIds=new Set<string>(),editions:CountryTournamentEdition[]=[]
  for(const version of packages){
    const id=str(version.package_id)
    if(!id||ids.has(id))throw new Error('Duplicate or missing Saved Calendar package identity')
    ids.add(id)
    const rows=state.entities.map(obj).filter((e):e is R=>e!==null&&e.source_package_id===id)
    const metas=rows.filter(e=>e.entity_kind==='calendar.metadata.v1')
    if(metas.length!==1||metas[0].source_entity_id!=='calendar.metadata')
      throw new Error('Saved Calendar metadata identity is incomplete')
    const season=str(obj(metas[0].payload)?.season),index=calendarSeasonIndex(season)
    if(!season||index===null)throw new Error('Saved Calendar metadata has unsupported season')
    for(const e of rows.filter(x=>x.entity_kind==='calendar.event.v1')){
      const p=obj(e.payload),eventId=str(p?.event_id),host=str(p?.host_country)
      const status=p?.status??'planned',week=p?.season_week
      if(!eventId||e.source_entity_id!==eventId||
        String(p?.season)!==season||calendarSeasonIndex(p?.season)!==index||
        !host||!/^[A-Z]{3}$/.test(host)||
        typeof week!=='number'||!Number.isInteger(week)||week<1||week>61||
        typeof status!=='string'||!statuses.has(status))
        throw new Error('Saved Calendar contains invalid or duplicate tournament edition')
      if(eventIds.has(eventId))
        throw new Error('Saved Calendar contains duplicate tournament event identity: '+eventId)
      eventIds.add(eventId)
      if(host!==countryCode)continue
      editions.push({key:id+':'+eventId,packageId:id,eventId,
        name:str(p?.event_name)??eventId,season,seasonIndex:index,week,
        hostCountry:host,city:str(p?.host_city),category:str(p?.category),
        tourLevel:str(p?.tour_level),status:status as CountryTournamentEdition['status']})
    }
  }
  return {fingerprint:response.fingerprint,calendarCount:ids.size,
    editions:editions.sort((a,b)=>a.seasonIndex-b.seasonIndex||a.week-b.week||
      a.eventId.localeCompare(b.eventId)||a.packageId.localeCompare(b.packageId))}
}
