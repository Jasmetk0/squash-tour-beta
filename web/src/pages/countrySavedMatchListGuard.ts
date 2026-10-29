/** Fail-closed read contract for the exact paged Country Saved match list. */
import type {CountryMatchOutcome,CountryMatchResultKind,CountrySavedMatchRecords} from '../api/types'
import {calendarSeasonIndex} from './runWorldCountryTournaments'

export const COUNTRY_SAVED_MATCH_PAGE_SIZE = 25
export type CountrySavedMatchScope = {
  runId:string;branchId:string;countryCode:string;revision:string
  seasonIndex:number|null;resultKind:CountryMatchResultKind
  outcome:CountryMatchOutcome;offset:number
}
const isCount=(value:number)=>Number.isSafeInteger(value)&&value>=0
const counts=['published_event_count','total_played_matches','total_walkovers',
  'country_played_wins','country_played_losses','country_walkover_wins',
  'country_walkover_losses','hosted_played_matches','hosted_walkovers',
  'country_match_count','filtered_match_count'] as const

export function validCountrySavedMatchPage(
  d:CountrySavedMatchRecords|undefined,expected:CountrySavedMatchScope,
):d is CountrySavedMatchRecords {
  if(!d||d.schema_version!=='country_saved_match_records.v1'||
    d.source!=='reachable_saved_revision'||d.run_id!==expected.runId||
    d.branch_id!==expected.branchId||d.saved_revision_id!==expected.revision||
    !d.revision_branch_id?.trim()||d.country_code!==expected.countryCode||
    d.season_index!==expected.seasonIndex||d.result_kind!==expected.resultKind||
    d.outcome!==expected.outcome||d.offset!==expected.offset||
    d.limit!==COUNTRY_SAVED_MATCH_PAGE_SIZE||
    (d.calendar_status!=='ready'&&d.calendar_status!=='empty')||
    !counts.every(key=>isCount(d[key]))||
    !Array.isArray(d.available_seasons)||!Array.isArray(d.matches)||
    typeof d.has_more!=='boolean')return false

  const seasons=d.available_seasons
  if(seasons.some((n,i)=>!Number.isSafeInteger(n)||n<0||n>49||
    (i>0&&n<=seasons[i-1])))return false
  const expectedCount=Math.max(0,Math.min(COUNTRY_SAVED_MATCH_PAGE_SIZE,
    d.filtered_match_count-expected.offset))
  if(d.matches.length!==expectedCount||
    d.has_more!==(expected.offset+COUNTRY_SAVED_MATCH_PAGE_SIZE<d.filtered_match_count)||
    d.filtered_match_count>d.country_match_count||
    d.country_match_count>d.total_played_matches+d.total_walkovers)return false

  const seen=new Set<string>()
  for(const m of d.matches){
    if(!m||!m.event_id?.trim()||!m.match_id?.trim()||
      !m.event_name?.trim()||!m.winner_player_id?.trim()||
      !m.loser_player_id?.trim()||m.winner_player_id===m.loser_player_id||
      !m.winner_name?.trim()||!m.loser_name?.trim()||!m.scoreline?.trim()||
      (m.completion!=='played'&&m.completion!=='walkover')||
      !Number.isSafeInteger(m.season_week)||m.season_week<1||m.season_week>61)return false
    const season=calendarSeasonIndex(m.season)
    if(season===null||(expected.seasonIndex!==null&&season!==expected.seasonIndex)||
      (expected.resultKind!=='all'&&m.completion!==expected.resultKind))return false
    const id=JSON.stringify([m.event_id,m.match_id])
    if(seen.has(id))return false
    seen.add(id)
    const win=m.winner_country===expected.countryCode
    const loss=m.loser_country===expected.countryCode
    if(!(win||loss)||(expected.outcome==='win'&&!win)||
      (expected.outcome==='loss'&&!loss))return false
  }
  return true
}

export function countrySavedMatchPageCount(total:number):number {
  return total===0?0:Math.ceil(total/COUNTRY_SAVED_MATCH_PAGE_SIZE)
}
