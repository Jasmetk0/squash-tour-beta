import {ApiError} from './client'
import {serverTaskCalendar,taskWeekOrdinal,validTaskWeek,type TaskCalendar} from './fullSimulationTasksCalendar'
import type {ServerTask} from './fullSimulationTasks'

export type NativeTaskWeek={season_index:number;week:number}
export type NativeTaskPreviewRequest={schema_version:'authoritative_full_simulation_command.v2';command_id:string;run_id:string;branch_id:string;
 target_week:NativeTaskWeek|null;seed:number;operator_label:string;audit_reason:string}
export type NativeTaskCommand=NativeTaskPreviewRequest&{execution_calendar:TaskCalendar;expected_start_week:NativeTaskWeek;
 expected_position_fingerprint:string;expected_revision_id:string;expected_preview_fingerprint:string}
export type NativeTaskPreview={schema_version:'authoritative_full_simulation_preview.v2';request:NativeTaskPreviewRequest;execution_calendar:TaskCalendar;
 start_week:NativeTaskWeek;final_week:NativeTaskWeek;target_week:NativeTaskWeek|null;target_semantics:'open_target_week'|'saved_final_run_closure';
 expected_position_fingerprint:string;expected_revision_id:string;preview_fingerprint:string;initial_transition_blockers:string[];
 manual_save_required_after_each_sporting_child:true}
export type NativeClosureReview={review_fingerprint:string;parent_command_id:string;run_id:string;branch_id:string;source_revision_id:string;
 completed_week:NativeTaskWeek;execution_calendar:TaskCalendar;closing_ranking:{rows:{rank:number;player_id:string;points:number}[]};
 season_summary:{played_match_count:number;awarded_points:number}}
export type NativeClosureAction={request_id:string;review_fingerprint:string;operator_label:string;audit_reason:string;explicit_confirmation:true}
export type NativeSeasonReview={review_fingerprint:string;run_id:string;branch_id:string;parent_command_id:string;
 preview:{impact:{completed_week:NativeTaskWeek;target_week:NativeTaskWeek}};
 outgoing_season_closure:{closing_ranking:{rows:unknown[]};season_summary:{played_match_count:number;awarded_points:number}}}
const base=()=>import.meta.env.VITE_API_BASE_URL??'http://127.0.0.1:8000'
const scope=(run:string,branch:string)=>`/admin/runs/${encodeURIComponent(run)}/branches/${encodeURIComponent(branch)}/authoritative-simulation/full-simulation`
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
const same=(a:unknown,b:unknown):boolean=>{
 if(a===b)return true
 if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b))return false
 const left=a as Record<string,unknown>,right=b as Record<string,unknown>
 return Object.keys(left).length===Object.keys(right).length&&Object.keys(left).every(key=>key in right&&same(left[key],right[key]))
}
const verifiedClock=(clock:TaskCalendar,source:string)=>serverTaskCalendar({schema_version:'full_simulation_task_view.v2',execution_calendar:clock,
 calendar_revision_id:source,original_command:{expected_revision_id:source}})
async function send(path:string,body?:unknown){
 const response=await fetch(base()+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
 if(!response.ok)throw new ApiError(await response.text(),response.status)
 return response.json()
}
export async function previewNativeTask(request:NativeTaskPreviewRequest):Promise<NativeTaskPreview>{
 const p=await send(scope(request.run_id,request.branch_id)+'/native/preview',request)
 if(p?.schema_version!=='authoritative_full_simulation_preview.v2'||!same(p.request,request))throw Error('Native task preview scope/input mismatch')
 const clock=verifiedClock(p.execution_calendar,p.expected_revision_id)
 if(clock.schema_version!=='run_calendar.v1'||!hash(p.preview_fingerprint)||!hash(p.expected_position_fingerprint)||p.manual_save_required_after_each_sporting_child!==true||
  !validTaskWeek(p.start_week,clock)||!same(p.final_week,{season_index:clock.season_count-1,week:clock.weeks_per_year})||
  !same(p.target_week,request.target_week)||!(p.target_week===null||validTaskWeek(p.target_week,clock))||
  p.target_semantics!==(p.target_week===null?'saved_final_run_closure':'open_target_week')||
  (p.target_week!==null&&taskWeekOrdinal(p.target_week,clock)<taskWeekOrdinal(p.start_week,clock))||
  !Array.isArray(p.initial_transition_blockers)||p.initial_transition_blockers.some((v:unknown)=>typeof v!=='string'))throw Error('Invalid native task preview')
 return p
}
export const nativeTaskCommand=(p:NativeTaskPreview):NativeTaskCommand=>({...p.request,execution_calendar:p.execution_calendar,expected_start_week:p.start_week,
 expected_position_fingerprint:p.expected_position_fingerprint,expected_revision_id:p.expected_revision_id,expected_preview_fingerprint:p.preview_fingerprint})
export async function nativeClosureReview(run:string,branch:string,parent:string):Promise<NativeClosureReview>{
 const value=await send(scope(run,branch)+`/native/${encodeURIComponent(parent)}/closure`)
 if(value?.run_id!==run||value.branch_id!==branch||value.parent_command_id!==parent||!hash(value.review_fingerprint)||!Array.isArray(value.closing_ranking?.rows))throw Error('Invalid native closure review')
 const clock=verifiedClock(value.execution_calendar,value.source_revision_id)
 if(!same(value.completed_week,{season_index:clock.season_count-1,week:clock.weeks_per_year})||
  !Number.isSafeInteger(value.season_summary?.played_match_count)||value.season_summary.played_match_count<0||
  !Number.isSafeInteger(value.season_summary?.awarded_points)||value.season_summary.awarded_points<0||
  value.closing_ranking.rows.some((r:{rank:number;player_id:string;points:number},i:number)=>r.rank!==i+1||typeof r.player_id!=='string'||!r.player_id||!Number.isSafeInteger(r.points)||r.points<0))throw Error('Invalid native closure facts')
 return value
}
export async function nativeClosureAction(run:string,branch:string,parent:string,action:'approve'|'save',body:NativeClosureAction){
 const value=await send(scope(run,branch)+`/native/${encodeURIComponent(parent)}/closure/${action}`,body)
 if(!same(value?.request,body)||
  (action==='approve'&&(value.review?.run_id!==run||value.review?.branch_id!==branch||value.review?.parent_command_id!==parent||value.review?.review_fingerprint!==body.review_fingerprint))||
  (action==='save'&&(value.schema_version!=='native_final_run_closure_save.v1'||typeof value.revision_id!=='string'||!value.revision_id||!hash(value.marker_fingerprint))))throw Error('Invalid native closure acknowledgement')
 return value
}
export async function nativeTaskControl(run:string,branch:string,parent:string,action:'pause'|'stop',operator:string,reason:string,id:string){
 const value=await send(scope(run,branch)+'/control',{target_command_id:parent,control_command_id:id,action,operator_label:operator,audit_reason:reason})
 if(value?.schema_version!=='native_full_simulation_control_result.v1'||value.run_id!==run||value.branch_id!==branch||value.command_id!==parent||value.control_command_id!==id)throw Error('Invalid native control acknowledgement')
 return value
}
export async function nativeTaskSummary(task:ServerTask){
 const value=await send(scope(task.run_id,task.branch_id)+`/parents/${encodeURIComponent(task.parent_command_id)}/summary`)
 const s=value?.summary
 if(value?.schema_version!=='full_simulation_terminal_summary_response.v2'||value.run_id!==task.run_id||value.branch_id!==task.branch_id||value.command_id!==task.parent_command_id||
  value.available!==true||!s||s.schema_version!=='full_simulation_terminal_summary.v3'||s.run_id!==task.run_id||s.branch_id!==task.branch_id||s.command_id!==task.parent_command_id||s.status!==task.state||
  !same(s.end_week,task.current_week)||!same(s.execution_calendar,task.execution_calendar)||!hash(s.summary_fingerprint)||!Number.isSafeInteger(s.persisted_child_command_count)||s.persisted_child_command_count<0||
  !Array.isArray(s.completed_tournaments)||s.completed_tournaments.some((id:unknown)=>typeof id!=='string'||!id))throw Error('Invalid native terminal summary')
 return s as {persisted_child_command_count:number;completed_tournaments:string[];terminal_saved_revision_id:string;reason:string}
}
export async function nativeSeasonReview(task:ServerTask):Promise<NativeSeasonReview>{
 const value=await send(scope(task.run_id,task.branch_id)+`/native/${encodeURIComponent(task.parent_command_id)}/season-transition`)
 if(value?.schema_version!=='native_full_simulation_season_review.v1'||value.run_id!==task.run_id||value.branch_id!==task.branch_id||value.parent_command_id!==task.parent_command_id||
  !hash(value.review_fingerprint)||value.preview?.preview_fingerprint!==value.review_fingerprint||
  !same({season_index:value.preview?.impact?.completed_week?.season_index,week:value.preview?.impact?.completed_week?.week},task.current_week)||
  !task.current_week||task.current_week.week!==task.execution_calendar?.weeks_per_year||
  value.preview?.impact?.target_week?.season_index!==task.current_week.season_index+1||value.preview?.impact?.target_week?.week!==1||
  !Array.isArray(value.outgoing_season_closure?.closing_ranking?.rows))throw Error('Invalid native Season Transition review')
 return value
}
export async function nativeSeasonApprove(task:ServerTask,body:NativeClosureAction){
 const value=await send(scope(task.run_id,task.branch_id)+`/native/${encodeURIComponent(task.parent_command_id)}/season-transition/approve`,body)
 if(!same(value?.request,body))throw Error('Invalid native Season Transition acknowledgement')
 return value
}
