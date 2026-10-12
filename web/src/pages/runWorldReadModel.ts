/** Read-only Run World projection: NEVER consult the mutable World Package library.
 * Current Run Package state owns all rendered country facts and source provenance.
 */
import type { RunPackageStateResponse } from '../api/types'

const ratingKeys = [
  'squash_popularity','squash_access','development_quality',
  'competition_quality','elite_support','squash_tradition'
] as const
export type WorldRatingKey = typeof ratingKeys[number]
export const worldRatingKeys: readonly WorldRatingKey[] = ratingKeys

type UnknownRecord = Record<string,unknown>
function record(value:unknown):UnknownRecord|null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as UnknownRecord : null
}
function string(value:unknown):string|null {
  return typeof value === 'string' && value.trim() ? value : null
}
function nonnegativeNumber(value:unknown):number|null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null
}
function populationNumber(value:unknown):number|null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 ? value : null
}
export type WorldPopulation = {
  value:number|null
  kind:'exact'|'nearest'|'default'|'legacy'|'missing'
  sourceYear:number|null
}
export type WorldRating = {
  value:number|null
  sourceYear:number|null
  sourceYears:number[]
  sourceValues:number[]
  kind:'exact'|'interpolated'|'fallback'|'legacy'|'missing'
  provenance:string
}
export type RunWorldCountry = {
  code:string; name:string; region:string|null; travelRegion:string|null
  timezoneArea:string|null; areaKm2:number|null
  population:WorldPopulation
  ratings:Record<WorldRatingKey,WorldRating>
  ratingScale:5|10
  incomplete:boolean
  manual:boolean
  notes:string|null
}
export type RunWorldOverview = {
  worldId:string; worldName:string; sourceLabel:string; sourceVersion:number
  stateFingerprint:string
  countries:RunWorldCountry[]
  exactPopulation:number
  knownPopulation:number
  populationComplete:boolean
  estimatedPopulationCount:number
  missingCountryCount:number
  manualCountryCount:number
}
export function worldCountryPopulation(country:UnknownRecord,year:number):WorldPopulation {
  const timeline=record(country.population_by_year)
  const exact=timeline?populationNumber(timeline[String(year)]):null
  if(exact!=null) return {value:exact,kind:'exact',sourceYear:year}
  const known=Object.entries(timeline??{}).map(([key,value])=>({
    year:Number(key),value:populationNumber(value)
  })).filter((p):p is {year:number;value:number}=>Number.isSafeInteger(p.year)&&p.value!=null)
  known.sort((a,b)=>Math.abs(a.year-year)-Math.abs(b.year-year)||a.year-b.year)
  if(known.length) return {value:known[0].value,kind:'nearest',sourceYear:known[0].year}
  const fallback=populationNumber(country.default_population)
  if(fallback!=null) return {value:fallback,kind:'default',sourceYear:2020}
  const legacy=populationNumber(country.population)
  if(legacy!=null) return {value:legacy,kind:'legacy',sourceYear:null}
  return {value:null,kind:'missing',sourceYear:null}
}
const LINEAR_RESOLVER_V3='country_rating_resolution.linear_v3'
/** Authored tenths interpolate using integer arithmetic, exact half-up to 4 places. */
function ratingInterpolation(left:{year:number;value:number},right:{year:number;value:number},year:number):number {
  const span=right.year-left.year
  const numerator=Math.round(left.value*10)*(right.year-year)+Math.round(right.value*10)*(year-left.year)
  return Math.floor((2*numerator*1000+span)/(2*span))/10000
}
function countryRatings(country:UnknownRecord,year:number):
  {ratings:Record<WorldRatingKey,WorldRating>;scale:5|10} {
  const scale=country.rating_scale==='country_ratings_1_10.v2'?10:5
  const resolver=country.rating_resolution_version
  if(resolver!=null&&resolver!==LINEAR_RESOLVER_V3)
    throw new Error('Unsupported persisted country rating resolver version')
  const history=record(country.rating_history)
  if(resolver===LINEAR_RESOLVER_V3&&
    (scale!==10||!history||history.schema_version!=='country_rating_history.v2'))
    throw new Error('Linear rating resolver requires versioned source evidence')
  const years=record(history?.years)
  const known=Object.entries(years??{}).map(([key,value])=>({year:Number(key),entry:record(value)}))
    .filter((p):p is {year:number;entry:UnknownRecord}=>Number.isSafeInteger(p.year)&&p.entry!=null)
    .sort((a,b)=>a.year-b.year)
  const ratings={} as Record<WorldRatingKey,WorldRating>
  for(const key of ratingKeys) {
    const points=known.map(({year:sourceYear,entry})=>({
      year:sourceYear,value:nonnegativeNumber(record(record(entry.ratings)?.[key])?.value)
    })).filter((p):p is {year:number;value:number}=>p.value!==null&&p.value>=1&&p.value<=scale)
    const sourced=(point:{year:number;value:number},kind:WorldRating['kind']):WorldRating=>({
      value:point.value,sourceYear:point.year,sourceYears:[point.year],
      sourceValues:[point.value],kind,
      provenance:kind==='exact'?'authored historical observation':
        resolver===LINEAR_RESOLVER_V3?'one-sided historical fallback':'legacy v2 nearest historical'
    })
    if(resolver===LINEAR_RESOLVER_V3&&points.length){
      const exact=points.find(p=>p.year===year)
      if(exact){ratings[key]=sourced(exact,'exact');continue}
      const left=[...points].reverse().find(p=>p.year<year)
      const right=points.find(p=>p.year>year)
      if(left&&right){
        ratings[key]={
          value:ratingInterpolation(left,right,year),sourceYear:null,
          sourceYears:[left.year,right.year],sourceValues:[left.value,right.value],
          kind:'interpolated',
          provenance:`linear interpolation: ${left.year} (${left.value}) → ${right.year} (${right.value})`
        }
      }else ratings[key]=sourced(left??right!,'fallback')
      continue
    }
    if(history&&known.length){
      // Old v2 snapshots continue to use the nearest authored YEAR for every field.
      const nearest=known.reduce((best,p)=>
        Math.abs(p.year-year)<Math.abs(best.year-year)||
        (Math.abs(p.year-year)===Math.abs(best.year-year)&&p.year<best.year)?p:best)
      const value=nonnegativeNumber(record(record(nearest.entry.ratings)?.[key])?.value)
      ratings[key]=value!==null&&value>=1&&value<=scale
        ?sourced({year:nearest.year,value},nearest.year===year?'exact':'fallback')
        :{value:null,sourceYear:null,sourceYears:[],sourceValues:[],kind:'missing',
           provenance:'missing historical rating'}
      continue
    }
    const direct=nonnegativeNumber(country[key])
    ratings[key]=direct!==null&&direct>=1&&direct<=scale
      ?{value:direct,sourceYear:null,sourceYears:[],sourceValues:[],kind:'legacy',
         provenance:'legacy scalar — no year attribution'}
      :{value:null,sourceYear:null,sourceYears:[],sourceValues:[],kind:'missing',
         provenance:'rating unavailable'}
  }
  return {ratings,scale}
}
/** Reject missing ownership, ambiguous worlds and duplicate/malformed Run entities.
 * A missing year is not silently converted to a complete global population.
 */
export function projectRunWorld(
  response:RunPackageStateResponse,runId:string,branchId:string,year:number
):RunWorldOverview|null {
  if (!Number.isSafeInteger(year)||year<1955||year>2050) throw new Error('Unsupported world year')
  const state=record(response.state)
  if(!state) return null
  if(state.run_id!==runId||state.branch_id!==branchId)
    throw new Error('Run World state ownership mismatch')
  const entities=state.entities
  const versions=state.package_versions
  if(!Array.isArray(entities)||!Array.isArray(versions))
    throw new Error('Run World state is incomplete')
  const worlds=versions.map(record).filter((v):v is UnknownRecord=>v!=null&&v.package_type==='World')
  if(!worlds.length) return null
  const worldIds=[...new Set(worlds.map(v=>string(v.package_id)).filter((id):id is string=>id!=null))]
  if(worldIds.length!==1 || worlds.some(v=>v.package_id!==worldIds[0]))
    throw new Error('World overview requires one unambiguous Run-owned World')
  const worldId=worldIds[0]
  const own=entities.map(record).filter((e):e is UnknownRecord=>e!=null&&e.source_package_id===worldId)
  const meta=own.filter(e=>e.entity_kind==='world.metadata.v1')
  if(meta.length!==1) throw new Error('Run World metadata is incomplete')
  const metadata=record(meta[0].payload)
  if(!metadata) throw new Error('Run World metadata payload is missing')
  const countryEntities=own.filter(e=>e.entity_kind==='world.country.v1')
  const codes=new Set<string>()
  const countries=countryEntities.map(e=>{
    const c=record(e.payload)
    if(!c) throw new Error('Invalid Run World country payload')
    const code=string(c.code)
    if(!code||code!==e.source_entity_id||codes.has(code))
      throw new Error('Duplicate or mismatched Run World country identity')
    codes.add(code)
    const population=worldCountryPopulation(c,year)
    const {ratings,scale}=countryRatings(c,year)
    const missingRating=ratingKeys.some(key=>ratings[key].value==null)
    return {
      code,name:string(c.name)??code,region:string(c.region),
      travelRegion:string(c.travel_region),timezoneArea:string(c.timezone_area),
      areaKm2:nonnegativeNumber(c.area_km2),population,ratings,ratingScale:scale,
      incomplete:population.kind!=='exact'||missingRating||
        ratingKeys.some(key=>ratings[key].kind!=='exact'),
      manual:e.provenance==='manual',notes:string(c.notes)
    } satisfies RunWorldCountry
  }).sort((a,b)=>a.name.localeCompare(b.name)||a.code.localeCompare(b.code))
  if(!countries.length) throw new Error('Run World contains no materialized countries')
  const world=worlds.find(v=>v.package_id===worldId)!
  const yearValues=countries.map(country=>country.population)
  const exactPopulation=yearValues.filter(p=>p.kind==='exact')
    .reduce((n,p)=>n+p.value!,0)
  const knownPopulation=yearValues.reduce((n,p)=>n+(p.value??0),0)
  return {
    worldId,worldName:string(metadata.name)??worldId,
    sourceLabel:string(metadata.source)??worldId,
    sourceVersion:typeof world.source_version==='number'?world.source_version:0,
    stateFingerprint:response.fingerprint??'',
    countries,exactPopulation,knownPopulation,
    populationComplete:yearValues.every(p=>p.kind==='exact'),
    estimatedPopulationCount:yearValues.filter(p=>p.kind!=='exact').length,
    missingCountryCount:countries.filter(c=>c.incomplete).length,
    manualCountryCount:countries.filter(c=>c.manual).length
  }
}
