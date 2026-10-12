/** Country history is reconstructed ONLY from the selected Run/Branch package copy.
 * Authored timeline anchors stay distinct from the selected year's effective fallback.
 * No future interpolation, synthetic anchors, original-package I/O, or writes.
 */
import type { RunPackageStateResponse } from '../api/types'
import {
  projectRunWorld, worldRatingKeys, type WorldRatingKey, type WorldPopulation
} from './runWorldReadModel'

type Row = Record<string,unknown>
function asRecord(value:unknown):Row|null {
  return value!==null && typeof value==='object' && !Array.isArray(value)?value as Row:null
}
function text(value:unknown):string|null {
  return typeof value==='string'&&value.trim()?value:null
}
function yearNumber(value:string):number|null {
  if(!/^(19[5-9][0-9]|20[0-4][0-9]|2050)$/.test(value))return null
  return Number(value)
}
function popValue(value:unknown):number|null {
  return typeof value==='number' && Number.isSafeInteger(value) && value>0?value:null
}
function validRating(value:unknown,max:5|10):number|null {
  return typeof value==='number' && Number.isFinite(value) && value>=1 && value<=max
    ?value:null
}
function listOfStrings(raw:unknown):string[] {
  return Array.isArray(raw)?raw.filter((x):x is string=>typeof x==='string'&&!!x.trim()):[]
}
function listOfYears(raw:unknown):number[] {
  return Array.isArray(raw)?raw.filter((x):x is number=>Number.isSafeInteger(x)&&x>=1955&&x<=2050):[]
}
export type CountryPopulationAnchor={year:number;value:number|null}
export type CountryRatingEvidence={
  value:number
  method:string|null
  confidence:string|null
  sourceIds:string[]
  observationIds:string[]
  rationale:string|null
  anchorYears:number[]
}
export type CountryRatingAnchor={
  year:number
  historicalEntity:string|null
  territoryMappingNote:string|null
  ratings:Record<WorldRatingKey,CountryRatingEvidence>
}
export type RunWorldCountryHistory={
  countryCode:string
  selectedYear:number
  selectedPopulation:WorldPopulation
  populationAnchors:CountryPopulationAnchor[]
  defaultPopulation:number|null
  legacyPopulation:number|null
  ratingAnchors:CountryRatingAnchor[]
  ratingReferenceYear:number|null
  ratingDataCutoff:string|null
  ratingScale:5|10
  selectedRatingSourceYear:number|null
}
/** Fail closed on mismatched country identity, ambiguous World or malformed history.
 * The upstream persisted schema normally validates everything; guards also make
 * corruption or mock API data impossible to misrepresent as complete history.
 */
export function projectRunWorldCountryHistory(
  response:RunPackageStateResponse,runId:string,branchId:string,
  countryCode:string,selectedYear:number
):RunWorldCountryHistory|null {
  const overview=projectRunWorld(response,runId,branchId,selectedYear)
  if(!overview)return null
  const projected=overview.countries.find(c=>c.code===countryCode)
  if(!projected)return null
  const entities=response.state?.entities
  if(!Array.isArray(entities))throw new Error('Run World entity snapshot unavailable')
  const matches=entities.map(asRecord).filter((e):e is Row=>
    e!==null&&e.source_package_id===overview.worldId&&e.entity_kind==='world.country.v1'&&
    e.source_entity_id===countryCode)
  if(matches.length!==1)throw new Error('Run World country source identity is ambiguous')
  const country=asRecord(matches[0].payload)
  if(!country||country.code!==countryCode)throw new Error('Run World country payload identity mismatch')
  const populationSource=asRecord(country.population_by_year)
  const populationAnchors:CountryPopulationAnchor[]=Object.entries(populationSource??{})
    .map(([key,value])=>{
      const year=yearNumber(key)
      if(year===null)throw new Error('Invalid authored population year')
      const population=value===null?null:popValue(value)
      if(value!==null&&population===null)throw new Error('Invalid authored population value')
      return {year,value:population}
    }).sort((a,b)=>a.year-b.year)
  const ratingScale:5|10=country.rating_scale==='country_ratings_1_10.v2'?10:5
  const history=asRecord(country.rating_history)
  const years=asRecord(history?.years)
  if(history && !years)throw new Error('Run World rating history is malformed')
  const ratingAnchors:CountryRatingAnchor[]=Object.entries(years??{}).map(([yearKey,value])=>{
    const year=yearNumber(yearKey)
    const entry=asRecord(value)
    const entries=asRecord(entry?.ratings)
    if(year===null||!entry||!entries)throw new Error('Invalid authored rating history year')
    const ratings={} as Record<WorldRatingKey,CountryRatingEvidence>
    for(const key of worldRatingKeys){
      const evidence=asRecord(entries[key])
      const resolved=validRating(evidence?.value,ratingScale)
      if(!evidence||resolved===null||!text(evidence.method)){
        throw new Error('Incomplete source-evidenced country rating history')
      }
      ratings[key]={
        value:resolved,method:text(evidence.method),confidence:text(evidence.confidence),
        sourceIds:listOfStrings(evidence.source_ids),
        observationIds:listOfStrings(evidence.observation_ids),
        rationale:text(evidence.rationale),anchorYears:listOfYears(evidence.anchor_years)
      }
    }
    return {
      year,ratings,historicalEntity:text(entry.historical_entity),
      territoryMappingNote:text(entry.territory_mapping_note)
    }
  }).sort((a,b)=>a.year-b.year)
  const reference=history?.reference_year
  return {
    countryCode,selectedYear,selectedPopulation:projected.population,
    populationAnchors,
    defaultPopulation:popValue(country.default_population),
    legacyPopulation:popValue(country.population),
    ratingAnchors,
    ratingReferenceYear:typeof reference==='number'&&Number.isSafeInteger(reference)?reference:null,
    ratingDataCutoff:text(history?.data_cutoff),
    ratingScale,
    selectedRatingSourceYear:projected.ratings.squash_popularity.sourceYear
  }
}