import type {TourView,TourWeek} from './calendarTour'
import {tourWeekOffset} from './nativeTourCalendar'

export type NativeTransitionReadiness={
  schema_version:'native_tour_transition_readiness.v1'|'native_tour_transition_readiness.v2';run_id:string;branch_id:string
  saved_head_revision_id:string;checkpoint_fingerprint:string;tour_fingerprint:string
  run_calendar:TourWeek['calendar'];completed_week:TourWeek;target_week:TourWeek|null
  action:'transition'|'season-transition';can_preview_transition:boolean;blockers:string[];source_problems:string[]
  due:{player_id:string;display_name:string;country_code:string}[];due_count:number;admitted_population_count:number
  current_scope:'configured_tour'|'native_natural_transitions'|'native_competition';target_scope:'configured_tour'|'native_natural_transitions'|'native_competition'
  post_birth_competition_supported:boolean;source_epoch_changes_supported:false
  command_preview_required:true;explicit_confirmation_required:true;manual_save_required:true;simulation_started:false
  readiness_fingerprint:string
}
const sameClock=(a:TourWeek['calendar'],b:TourWeek['calendar'])=>a&&b&&
  a.schema_version===b.schema_version&&a.weeks_per_year===b.weeks_per_year&&
  a.season_start_year_week===b.season_start_year_week&&a.start_year===b.start_year&&a.season_count===b.season_count
const sameWeek=(a:TourWeek|null,b:TourWeek|null)=>a===null||b===null?a===b:
  a&&b&&a.season_index===b.season_index&&a.week===b.week&&sameClock(a.calendar,b.calendar)

export function validateNativeTransitionReadiness(raw:unknown,view:TourView):NativeTransitionReadiness{
  const v=raw as NativeTransitionReadiness
  if(!view.state||!v)throw Error('Transition readiness requires a current Tour')
  const clock=view.run_calendar??view.state.week.calendar
  const version='schema_version' in view.state?view.state.schema_version:undefined
  const target=tourWeekOffset({...view.state.week,calendar:clock},1)
  const modern=v.schema_version==='native_tour_transition_readiness.v2'
  const nativeScope=modern?'native_competition':'native_natural_transitions'
  if((!modern&&v.schema_version!=='native_tour_transition_readiness.v1')||v.run_id!==view.run_id||v.branch_id!==view.branch_id
    ||v.saved_head_revision_id!==view.saved_head_revision_id||v.checkpoint_fingerprint!==view.checkpoint_fingerprint
    ||v.tour_fingerprint!==view.tour_fingerprint||!sameClock(v.run_calendar,clock)
    ||!sameWeek(v.completed_week,view.state.week)||!sameWeek(v.target_week,target)
    ||v.action!==(view.state.week.week===clock.weeks_per_year?'season-transition':'transition')
    ||!Array.isArray(v.blockers)||!v.blockers.every(b=>typeof b==='string')
    ||!Array.isArray(v.source_problems)||!v.source_problems.every(p=>typeof p==='string')
    ||v.can_preview_transition!==(v.blockers.length===0)
    ||(v.can_preview_transition&&(target===null||v.source_problems.length>0))
    ||!Array.isArray(v.due)||v.due_count!==v.due.length
    ||v.due.some(p=>!p||typeof p.player_id!=='string'||!p.player_id||typeof p.display_name!=='string'||!p.display_name||!/^[A-Z]{3}$/.test(p.country_code))
    ||new Set(v.due.map(p=>p.player_id)).size!==v.due.length
    ||!Number.isSafeInteger(v.admitted_population_count)||v.admitted_population_count<0
    ||!['configured_tour',nativeScope].includes(v.current_scope)
    ||(version!==undefined&&v.current_scope!==(['calendar_tour_authority.v3','calendar_tour_authority.v4','native_fork_tour.v1'].includes(String(version))?nativeScope:'configured_tour'))
    ||v.target_scope!==((v.current_scope===nativeScope||v.due_count>0)?nativeScope:'configured_tour')
    ||v.command_preview_required!==true||v.explicit_confirmation_required!==true||v.manual_save_required!==true
    ||v.simulation_started!==false||v.post_birth_competition_supported!==modern||v.source_epoch_changes_supported!==false
    ||!/^[0-9a-f]{64}$/.test(v.readiness_fingerprint))throw Error('Transition readiness source, target or capability changed')
  return v
}
