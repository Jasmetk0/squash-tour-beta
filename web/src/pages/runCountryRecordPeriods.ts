/** Country published tournament evidence: full immutable source BEFORE period aggregation.
 * Neither country data-year nor row/page limits define sporting history.
 */
import type {RunCountryRecordResult,RunCountryRecords} from '../api/types'
import {calendarSeasonIndex} from './runWorldCountryTournaments'

export type CountryPeriodMode='whole'|'season'|'custom'
export type SportPoint={season:number;week:number}
export type CountryPeriodRequest={
  mode:CountryPeriodMode;season:number;from:SportPoint;to:SportPoint
}
export type CountryRecordLeader={
  id:string;name:string;count:number;events:RunCountryRecordResult[]
}
const ordinal=(p:SportPoint)=>p.season*61+p.week
export const validPoint=(p:SportPoint)=>Number.isInteger(p.season)&&p.season>=0&&p.season<50&&
  Number.isInteger(p.week)&&p.week>=1&&p.week<=61
export const sportLabel=(p:SportPoint)=>String(2000+p.season)+'/'+String(2001+p.season)+
  ' · Week '+p.week
export function selectedSportPoint(season:unknown,week:unknown):SportPoint|null{
  const n=calendarSeasonIndex(season)
  return n!==null&&typeof week==='number'&&validPoint({season:n,week})?
    {season:n,week}:null
}
export function parsePeriod(params:URLSearchParams,through:SportPoint):CountryPeriodRequest|null{
  if(!validPoint(through))return null
  const mode=params.get('rperiod')??'whole'
  if(mode!=='whole'&&mode!=='season'&&mode!=='custom')return null
  const value=(key:string,fallback:number,max:number)=>{
    const raw=params.get(key)
    if(raw===null)return fallback
    return /^(0|[1-9]\d*)$/.test(raw)&&Number(raw)<=max?Number(raw):NaN
  }
  const season=value('rseason',through.season,49)
  const from={season:value('rfromSeason',0,49),week:value('rfromWeek',1,61)}
  const to={season:value('rtoSeason',through.season,49),week:value('rtoWeek',through.week,61)}
  if(!Number.isInteger(season)||!validPoint(from)||!validPoint(to))return null
  if(mode==='whole')return {mode,season,from:{season:0,week:1},to:through}
  if(mode==='season'){
    const effectiveTo=season===through.season?through.week:61
    if(season>through.season)return null
    return {mode,season,from:{season,week:1},to:{season,week:effectiveTo}}
  }
  if(ordinal(from)>ordinal(to)||ordinal(from)>ordinal(through))return null
  return {mode,season,from,to:ordinal(to)>ordinal(through)?through:to}
}

/** Last observed canonical published Country event; a conservative evidence
 * ceiling only, NEVER an asserted Run simulation clock. Nothing is synthesized
 * from Calendar plans, current World or another Saved Revision. */
export function lastEvidencedCountryPoint(source:RunCountryRecords):SportPoint|null{
  let last:SportPoint|null=null
  for(const row of [...source.player_results,...source.hosted_results]){
    const season=calendarSeasonIndex(row.season)
    const next=season===null?null:{season,week:row.season_week}
    if(!next||!validPoint(next))throw Error('Country published source has unsupported sport time')
    if(last===null||ordinal(next)>ordinal(last))last=next
  }
  return last
}

export type CountryPeriodStats={
  from:SportPoint;to:SportPoint
  athletes:RunCountryRecordResult[];hosted:RunCountryRecordResult[]
  titles:number;runnerUps:number;finalAppearances:number
  champions:CountryRecordLeader[];finalists:CountryRecordLeader[]
}
export function projectCountryPeriod(
  source:RunCountryRecords,country:string,request:CountryPeriodRequest
):CountryPeriodStats{
  if(source.country_code!==country||!validPoint(request.from)||!validPoint(request.to)||
    ordinal(request.to)<ordinal(request.from))throw Error('Country record period is invalid')
  const inRange=(r:RunCountryRecordResult)=>{
    const season=calendarSeasonIndex(r.season)
    if(season===null||!Number.isInteger(r.season_week)||r.season_week<1||r.season_week>61)
      throw Error('Country record has unsupported historical sport time')
    const time=ordinal({season,week:r.season_week})
    return time>=ordinal(request.from)&&time<=ordinal(request.to)
  }
  // Evaluate all rows, including outside the chosen period, to fail closed on
  // corrupt historic identities rather than silently hiding them in another slice.
  const athleteInRange=source.player_results.map(r=>[r,inRange(r)] as const)
  const hostedInRange=source.hosted_results.map(r=>[r,inRange(r)] as const)
  const athletes=athleteInRange.filter(([,ok])=>ok).map(([r])=>r)
  const hosted=hostedInRange.filter(([,ok])=>ok).map(([r])=>r)
  const leaders=(category:'title'|'final'):CountryRecordLeader[]=>{
    const byId=new Map<string,CountryRecordLeader>()
    const add=(id:string,name:string,e:RunCountryRecordResult)=>{
      const entry=byId.get(id)??{id,name,count:0,events:[]}
      if(entry.name!==name)throw Error('Country record holder identity mismatch')
      entry.count++;entry.events.push(e);byId.set(id,entry)
    }
    for(const r of athletes){
      if(r.champion_country===country)add(r.champion_player_id,r.champion_name,r)
      if(category==='final'&&r.finalist_country===country)
        add(r.finalist_player_id,r.finalist_name,r)
    }
    const all=[...byId.values()],max=Math.max(0,...all.map(x=>x.count))
    return all.filter(x=>x.count===max).sort((a,b)=>a.id.localeCompare(b.id))
  }
  const titles=athletes.filter(r=>r.champion_country===country).length
  const runnerUps=athletes.filter(r=>r.finalist_country===country).length
  return {from:request.from,to:request.to,athletes,hosted,titles,runnerUps,
    finalAppearances:titles+runnerUps,champions:leaders('title'),finalists:leaders('final')}
}
