import type { AdminHealthEditPreview, AdminHealthEditRequest, AdminPlayerHealthView, PlayerHealthWeek } from './types'
import type { RunCalendarMetadata } from './runCalendarCreation'

// Explicit historical V1 semantics. Never apply these defaults to a V2 response.
const legacy = {weeks_per_year:61, season_start_year_week:37, start_year:2000, season_count:50}
export function healthClock(week: PlayerHealthWeek) { return week.calendar ?? legacy }
export function healthOrdinal(week: PlayerHealthWeek) { return week.season_index * healthClock(week).weeks_per_year + week.week - 1 }
export function healthWeekLabel(week: PlayerHealthWeek, locale: 'cs'|'en' = 'en') {
  const c=healthClock(week), year=c.start_year+week.season_index
  const season=week.calendar ? (c.season_start_year_week===1 ? String(year) : `${year}/${year+1}`)
    : `${year}/${String(year+1).slice(-2)}`
  const elapsed=c.season_start_year_week+week.week-2
  return `${season} · ${locale==='cs'?'Týden':'Week'} ${week.week}` + (week.calendar ? ` · ${year+Math.floor(elapsed/c.weeks_per_year)} W${elapsed%c.weeks_per_year+1}` : '')
}
const hash=(s:unknown)=>typeof s==='string' && /^[0-9a-f]{64}$/.test(s)
function canonical(value:unknown):string {
  if(Array.isArray(value))return '['+value.map(canonical).join(',')+']'
  if(value&&typeof value==='object')return '{'+Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>JSON.stringify(k)+':'+canonical(v)).join(',')+'}'
  return JSON.stringify(value)
}
export function sameHealthWeek(a:PlayerHealthWeek,b:PlayerHealthWeek) {
  return a?.season_index===b?.season_index && a?.week===b?.week && canonical(a?.calendar)===canonical(b?.calendar)
}
export function validateHealthView(v:AdminPlayerHealthView,run:string,branch:string,player:string,head?:string) {
  if(!v||!['admin_health_current_view.v1','admin_health_current_view.v2'].includes(v.schema_version)
    ||v.run_id!==run||v.branch_id!==branch||v.player?.player_id!==player||!v.week
    ||!hash(v.state_fingerprint)||!hash(v.health_component_fingerprint)||!Number.isSafeInteger(v.draft_version)
    ||v.draft_version<0||(head!==undefined&&v.saved_head_revision_id!==head))throw Error('Health source changed; reload this Run.')
  if(v.schema_version==='admin_health_current_view.v2') {
    const c=v.week.calendar
    if(!c||c.schema_version!=='run_calendar.v1'||!v.saved_head_revision_id
      ||![c.weeks_per_year,c.season_start_year_week,c.start_year,c.season_count].every(Number.isSafeInteger)
      ||c.weeks_per_year<1||c.season_count<1||c.start_year<0||c.season_start_year_week<1||c.season_start_year_week>c.weeks_per_year)throw Error('Missing Run health calendar.')
  } else if(v.week.calendar)throw Error('Legacy health contains a different time basis.')
  const c=healthClock(v.week)
  if(!Number.isSafeInteger(v.week.season_index)||v.week.season_index<0||v.week.season_index>=c.season_count
    ||!Number.isSafeInteger(v.week.week)||v.week.week<1||v.week.week>c.weeks_per_year
    ||!Array.isArray(v.player.records)||!Array.isArray(v.player.permanent_consequences))throw Error('Invalid Health position or profile.')
  return v
}
export function validateHealthReview(p:AdminHealthEditPreview,r:AdminHealthEditRequest,current:AdminPlayerHealthView) {
  const player=p?.after_state?.players?.find(x=>x.player_id===r.player_id)
  if(!p||p.run_id!==current.run_id||p.branch_id!==current.branch_id
    ||p.after_state.run_id!==current.run_id||p.after_state.branch_id!==current.branch_id
    ||!sameHealthWeek(p.week,current.week)||!sameHealthWeek(p.after_state.week,current.week)
    ||p.before_state_fingerprint!==current.state_fingerprint||p.before_component_fingerprint!==current.health_component_fingerprint
    ||p.expected_draft_version!==r.expected_draft_version||!hash(p.preview_fingerprint)||!hash(p.after_component_fingerprint)
    ||canonical(player?.records)!==canonical(r.records)||canonical(player?.permanent_consequences)!==canonical(r.permanent_consequences)
    ||(r.schema_version==='admin_health_edit_request.v2'&&(p.schema_version!=='admin_health_edit_preview.v2'
      ||p.saved_head_revision_id!==r.expected_saved_head||p.after_state.schema_version!=='player_health_calendar_state.v2')))throw Error('Health preview differs from the reviewed source and inputs.')
  return p
}
export function parseHealthWeek(season:string,week:string,current:PlayerHealthWeek):PlayerHealthWeek|null {
  if(!season.trim()||!week.trim())return null
  const index=Number(season)-1,w=Number(week),c=healthClock(current)
  if(!Number.isSafeInteger(index)||index<0||index>=c.season_count||!Number.isSafeInteger(w)||w<1||w>c.weeks_per_year)return null
  return {...(current.calendar?{calendar:current.calendar as RunCalendarMetadata}:{}),season_index:index,week:w}
}
