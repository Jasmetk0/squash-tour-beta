import {validateCalendarPoolPreview, type CalendarPoolPreview, type CalendarPoolInput} from './calendarInitialPool'
import type {RunCalendarMetadata} from './runCalendarCreation'

export type CalendarPopulationRequest = {
  command_id: string; expected_saved_head: string; expected_draft_version: number
  expected_package_fingerprint: string; generation: CalendarPoolInput; audit_label: string; audit_reason: string
  lifecycle_policy?: {policy_id:string;automatic_retirement_age:number;provenance:string}
}
export type CalendarPopulationReview = {
  schema_version: 'calendar_initial_world_review.v2'; preview_only: true
  request: CalendarPopulationRequest; pool_preview: CalendarPoolPreview
  initial_world_fingerprint: string; lifecycle_fingerprint: string
  player_count_before: 0; player_count_after: number
}
export type CalendarPopulation = {
  state: {schema_version: 'initial_world_state.v2'; run_id: string; branch_id: string; run_calendar: RunCalendarMetadata
    players: {player_id:string; name:string; birth_year:number; birth_year_week:number; age_years_at_season_start:number
      age_weeks_at_season_start:number; active_status:string}[]}
  fingerprint: string; lifecycle_fingerprint: string; sporting_execution_supported: false
}
const hash = (v:unknown):boolean => typeof v==='string' && /^[0-9a-f]{64}$/.test(v)
export function validateCalendarPopulationSave(value:unknown,runId:string,branchId:string,fingerprint:string) {
  const p=value as {saved_revision:{revision_id:string;run_id:string;branch_id:string;
    payload:{content:{initial_world:{fingerprint:string}}}};working_draft:{run_id:string;branch_id:string;
      status:string;base_saved_revision_id:string}}
  if(!p || p.saved_revision?.run_id!==runId || p.saved_revision.branch_id!==branchId
    || typeof p.saved_revision.revision_id!=='string' || !p.saved_revision.revision_id
    || p.saved_revision.payload?.content?.initial_world?.fingerprint!==fingerprint
    || p.working_draft?.run_id!==runId || p.working_draft.branch_id!==branchId
    || p.working_draft.status!=='clean' || p.working_draft.base_saved_revision_id!==p.saved_revision.revision_id) {
    throw Error('Population Save receipt differs from the reviewed Run/Branch/content')
  }
  return p
}
export function validateCalendarPopulation(value:unknown, runId:string, branchId:string, clock:RunCalendarMetadata):CalendarPopulation {
  const p=value as CalendarPopulation
  if (!p || !hash(p.fingerprint) || !hash(p.lifecycle_fingerprint) || p.sporting_execution_supported!==false
    || p.state?.schema_version!=='initial_world_state.v2' || p.state.run_id!==runId || p.state.branch_id!==branchId
    || !p.state.run_calendar || Object.entries(clock).some(([k,v])=>p.state.run_calendar[k as keyof RunCalendarMetadata]!==v)
    || !Array.isArray(p.state.players) || !p.state.players.length || p.state.players.length>10000) {
    throw Error('Installed population does not match the selected Run/Branch/calendar')
  }
  const ids=new Set<string>()
  for (const player of p.state.players) {
    const weeks=(clock.start_year-player.birth_year)*clock.weeks_per_year+clock.season_start_year_week-player.birth_year_week
    if (!player.player_id || ids.has(player.player_id) || typeof player.name!=='string' || !player.name
      || !Number.isSafeInteger(player.birth_year) || !Number.isSafeInteger(player.birth_year_week)
      || player.birth_year_week<1 || player.birth_year_week>clock.weeks_per_year
      || weeks!==player.age_weeks_at_season_start || weeks<=15*clock.weeks_per_year
      || Math.floor(weeks/clock.weeks_per_year)!==player.age_years_at_season_start || player.active_status!=='active') {
      throw Error('Installed population contains an invalid calendar identity')
    }
    ids.add(player.player_id)
  }
  return p
}
export function validateCalendarPopulationReview(value:unknown, request:CalendarPopulationRequest,
  pool:CalendarPoolPreview, runId:string, branchId:string, clock:RunCalendarMetadata):CalendarPopulationReview {
  const p=value as CalendarPopulationReview
  if (!p || p.schema_version!=='calendar_initial_world_review.v2' || p.preview_only!==true
    || !hash(p.initial_world_fingerprint) || !hash(p.lifecycle_fingerprint) || p.player_count_before!==0
    || p.player_count_after!==pool.result.players.length || !p.request
    || ['command_id','expected_saved_head','expected_draft_version','expected_package_fingerprint','audit_label','audit_reason']
      .some(k=>p.request[k as keyof CalendarPopulationRequest]!==request[k as keyof CalendarPopulationRequest])
    || !p.request.generation || Object.entries(request.generation).some(([k,v])=>
      JSON.stringify(p.request.generation[k as keyof CalendarPoolInput])!==JSON.stringify(v))
    || (request.lifecycle_policy && JSON.stringify(p.request.lifecycle_policy)!==JSON.stringify(request.lifecycle_policy))) {
    throw Error('Population adoption review does not match the explicit request')
  }
  validateCalendarPoolPreview(p.pool_preview,runId,branchId,request.expected_saved_head,
    request.expected_package_fingerprint,clock,request.generation)
  if (p.pool_preview.preview_fingerprint!==pool.preview_fingerprint) {
    throw Error('Player preview changed; generate and review again')
  }
  return p
}
