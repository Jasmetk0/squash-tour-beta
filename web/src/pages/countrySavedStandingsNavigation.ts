/** Exact immutable Country player standings source/window validation.
 * This is statistical evidence, never Official Ranking or rankings points.
 */
import type {CountryPlayerStanding,CountryPlayerStandings} from '../api/types'

export const COUNTRY_STANDINGS_PAGE_SIZE=25
export type CountryStandingsScope={
  runId:string;branchId:string;countryCode:string;revision:string;offset:number
}
const count=(n:number):boolean=>Number.isSafeInteger(n)&&n>=0
const summaryCounts=[
  'published_event_count','country_titles','country_runner_up_finishes',
  'country_played_wins','country_played_losses','country_walkover_wins',
  'country_walkover_losses','total_players',
] as const
const playerCounts=[
  'titles','runner_up_finishes','final_appearances','played_wins','played_losses',
  'walkover_wins','walkover_losses',
] as const

export const standingsPages=(total:number):number=>total===0?0:
  Math.ceil(total/COUNTRY_STANDINGS_PAGE_SIZE)

/** Authored ordering: titles, all finals, on-court wins, fewest on-court losses, ID. */
export function compareCountryStanding(a:CountryPlayerStanding,b:CountryPlayerStanding):number{
  return b.titles-a.titles||b.final_appearances-a.final_appearances||
    b.played_wins-a.played_wins||a.played_losses-b.played_losses||
    a.player_id.localeCompare(b.player_id)
}
export function validCountryStandingPage(
  d:CountryPlayerStandings|undefined,s:CountryStandingsScope,
):d is CountryPlayerStandings {
  if(!d||d.schema_version!=='country_player_standings.v1'||
    d.source!=='reachable_saved_revision'||d.run_id!==s.runId||
    d.branch_id!==s.branchId||d.country_code!==s.countryCode||
    d.saved_revision_id!==s.revision||!d.revision_branch_id?.trim()||
    (d.calendar_status!=='empty'&&d.calendar_status!=='ready')||
    d.offset!==s.offset||d.limit!==COUNTRY_STANDINGS_PAGE_SIZE||
    !summaryCounts.every(k=>count(d[k]))||!Array.isArray(d.players)||
    typeof d.has_more!=='boolean')return false
  if((d.calendar_status==='empty'&&
      (d.published_event_count!==0||d.total_players!==0))||
    d.country_titles>d.published_event_count||
    d.country_runner_up_finishes>d.published_event_count||
    d.total_players>d.country_titles+d.country_runner_up_finishes+
      d.country_played_wins+d.country_played_losses+
      d.country_walkover_wins+d.country_walkover_losses)return false
  if(d.players.length!==Math.max(0,Math.min(COUNTRY_STANDINGS_PAGE_SIZE,
    d.total_players-s.offset))||
    d.has_more!==(s.offset+COUNTRY_STANDINGS_PAGE_SIZE<d.total_players))return false
  const ids=new Set<string>()
  for(let i=0;i<d.players.length;i++){
    const p=d.players[i]
    if(!p||p.country_code!==s.countryCode||!p.player_id?.trim()||
      !p.player_name?.trim()||ids.has(p.player_id)||p.position!==s.offset+i+1||
      !playerCounts.every(k=>count(p[k]))||
      p.final_appearances!==p.titles+p.runner_up_finishes||
      !playerCounts.some(k=>k!=='final_appearances'&&p[k]>0)||
      (i>0&&compareCountryStanding(d.players[i-1],p)>0))return false
    ids.add(p.player_id)
  }
  return true
}

/** Only a bounded, canonical one-based page input is accepted. */
export function parseStandingPage(raw:string,totalPages:number):number|null{
  if(!Number.isSafeInteger(totalPages)||totalPages<1||totalPages>1000000||
    !/^[1-9]\d{0,6}$/.test(raw))return null
  const n=Number(raw)
  return n<=totalPages?n-1:null
}
