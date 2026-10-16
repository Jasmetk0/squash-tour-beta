import type {RunCalendarMetadata} from './runCalendarCreation'
export type InitialHealthRequest = {
  command_id:string; expected_saved_head:string; expected_draft_version:number
  expected_population_fingerprint:string; initialization_policy:'fresh_without_history.v1'
  audit_label:string; audit_reason:string
}
export type InitialHealthState = {
  schema_version:'calendar_initial_health_state.v1'; run_id:string; branch_id:string
  week:{calendar:RunCalendarMetadata;season_index:number;week:number}
  players:{player_id:string;records:unknown[];permanent_consequences:unknown[]}[]
  initialization_policy:'fresh_without_history.v1'; predecessor_fingerprint:null
  source_initial_world_fingerprint:string; command_id:string; request_fingerprint:string
  audit_label:string; audit_reason:string
}
export type InitialHealthView = {
  schema_version:'calendar_initial_health_view.v1'; run_id:string;branch_id:string
  saved_head_revision_id:string;population_fingerprint:string;run_calendar:RunCalendarMetadata
  player_count:number;state:InitialHealthState|import('./types').PlayerHealthWeekState|null;health_fingerprint:string|null
  health_component_fingerprint:string|null;saved:boolean;draft_version:number;draft_status:string
}
export type InitialHealthReview = {
  schema_version:'calendar_initial_health_review.v1';request:InitialHealthRequest
  state:InitialHealthState;health_fingerprint:string
}
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
const sameClock=(a:RunCalendarMetadata|undefined,b:RunCalendarMetadata)=>a&&Object.entries(b).every(([k,v])=>a[k as keyof RunCalendarMetadata]===v)
export function validateInitialHealthState(s:InitialHealthState,run:string,branch:string,clock:RunCalendarMetadata,ids:string[]) {
  if(!s||s.schema_version!=='calendar_initial_health_state.v1'||s.run_id!==run||s.branch_id!==branch
    ||!sameClock(s.week?.calendar,clock)||s.week.season_index!==0||s.week.week!==1
    ||s.initialization_policy!=='fresh_without_history.v1'||s.predecessor_fingerprint!==null
    ||!hash(s.source_initial_world_fingerprint)||!hash(s.request_fingerprint)||!s.command_id
    ||!Array.isArray(s.players)||s.players.length!==ids.length
    ||s.players.some((p,i)=>p.player_id!==ids[i]||!Array.isArray(p.records)||p.records.length!==0
      ||!Array.isArray(p.permanent_consequences)||p.permanent_consequences.length!==0)) {
    throw Error('Initial health differs from the selected population/calendar')
  }
}
export function validateInitialHealthView(value:unknown,run:string,branch:string,head:string,population:string,clock:RunCalendarMetadata,ids:string[]):InitialHealthView {
  const v=value as InitialHealthView
  if(!v||v.schema_version!=='calendar_initial_health_view.v1'||v.run_id!==run||v.branch_id!==branch
    ||v.saved_head_revision_id!==head||v.population_fingerprint!==population||!sameClock(v.run_calendar,clock)
    ||v.player_count!==ids.length||!Number.isSafeInteger(v.draft_version)||v.draft_version<0
    ||!['clean','dirty'].includes(v.draft_status)||typeof v.saved!=='boolean')throw Error('Initial health proof changed; reload this Run')
  if(v.state){
    if(v.state.schema_version==='player_health_calendar_state.v2') {
      const s=v.state
      if(s.run_id!==run||s.branch_id!==branch||!sameClock(s.week.calendar,clock)
        ||s.week.season_index!==0||s.week.week!==1||!Array.isArray(s.players)
        ||s.players.length!==ids.length||s.players.some((p,i)=>p.player_id!==ids[i]))throw Error('Health facts differ from this population')
    } else validateInitialHealthState(v.state as InitialHealthState,run,branch,clock,ids)
    if(!hash(v.health_fingerprint)||!hash(v.health_component_fingerprint))throw Error('Initial health proof is missing')
  } else if(v.health_fingerprint!==null||v.health_component_fingerprint!==null||v.saved)throw Error('Unexpected initial health proof')
  return v
}
export function validateInitialHealthReview(value:unknown,request:InitialHealthRequest,run:string,branch:string,clock:RunCalendarMetadata,ids:string[]):InitialHealthReview {
  const v=value as InitialHealthReview
  if(!v||v.schema_version!=='calendar_initial_health_review.v1'||!hash(v.health_fingerprint)||!v.request
    ||Object.entries(request).some(([k,x])=>v.request[k as keyof InitialHealthRequest]!==x))throw Error('Initial health review differs from the request')
  validateInitialHealthState(v.state,run,branch,clock,ids)
  if(v.state.command_id!==request.command_id||v.state.source_initial_world_fingerprint!==request.expected_population_fingerprint
    ||v.state.audit_label!==request.audit_label||v.state.audit_reason!==request.audit_reason)throw Error('Initial health review provenance differs')
  return v
}
export function validateInitialHealthSave(value:unknown,run:string,branch:string,component:string) {
  const v=value as {saved_revision:{revision_id:string;run_id:string;branch_id:string;payload:{content:{player_health_state:{fingerprint:string}}}};
    working_draft:{run_id:string;branch_id:string;status:string;base_saved_revision_id:string}}
  if(!v||v.saved_revision?.run_id!==run||v.saved_revision.branch_id!==branch||!v.saved_revision.revision_id
    ||v.saved_revision.payload?.content?.player_health_state?.fingerprint!==component
    ||v.working_draft?.run_id!==run||v.working_draft.branch_id!==branch||v.working_draft.status!=='clean'
    ||v.working_draft.base_saved_revision_id!==v.saved_revision.revision_id)throw Error('Health Save receipt differs from the confirmed content')
  return v
}
