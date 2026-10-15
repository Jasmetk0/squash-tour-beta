import { isBoundaryTarget } from './fullSimulationBoundaryTargets'
import type { BoundaryTarget } from './fullSimulationBoundaryTargets'
import { ApiError } from './client'
import type { AuthoritativeFullSimulationCommandPayload } from './types'

export type ServerTask = {
  schema_version:'full_simulation_task_view.v1'; task_id:string; run_id:string; branch_id:string
  parent_command_id:string; run_name:string; branch_name:string; revision:number
  desired_state:string; state:string; heartbeat_health:'recent'|'stale'|'inactive'; heartbeat_unix:number
  lease_expires_at_unix:number|null; checkpoint:string|null; progress:Record<string,unknown>|null
  effective_boundary_target?:BoundaryTarget|null
  current_week:{season_index:number;week:number}|null
  progress_evidence:{
    schema_version:'full_simulation_task_progress_evidence.v1'
    kind:'live_branch'|'terminal_frozen'|'unavailable'
    week:{season_index:number;week:number}|null
    weeks_advanced_since_start:number|null
    completed_slot_receipts_this_week:number|null
    committed_group_receipts_this_week:number|null
    receipt_scope:'branch_current_week'|null
  }
  error:string|null; needs_operator_action:boolean; original_command:AuthoritativeFullSimulationCommandPayload
  events:{revision:number;previous:string|null;state:string;reason:string;at_unix:number;fingerprint:string}[]
}
export type TaskAck = {schema_version:'full_simulation_task_ack.v1';task_id:string;run_id:string;branch_id:string;
  parent_command_id:string;request_id:string;accepted_revision:number}
export type ContinueTask = {request_id:string;action:'resume'|'recover';expected_revision:number;operator_label:string;audit_reason:string}
const root=()=>import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const scope=(run:string,branch:string)=>`/admin/runs/${encodeURIComponent(run)}/branches/${encodeURIComponent(branch)}/authoritative-simulation/full-simulation/tasks`
const id=(v:unknown):v is string=>typeof v==='string' && v.length>0
const hash=(v:unknown)=>typeof v==='string' && /^[0-9a-f]{64}$/.test(v)
const week=(v:unknown)=>{const w=v as {season_index:number;week:number};return !!w && Number.isInteger(w.season_index) && w.season_index>=0 && w.season_index<50 && Number.isInteger(w.week) && w.week>=1 && w.week<=61}
const desired=['queued','active','paused','awaiting_operator','stopped','target_reached','complete','failed']
function validProgress(t:ServerTask):boolean {
  const p=t.progress_evidence
  if(!p || p.schema_version!=='full_simulation_task_progress_evidence.v1' ||
    !['live_branch','terminal_frozen','unavailable'].includes(p.kind) ||
    !(p.week===null || week(p.week)) || !(t.current_week===null || week(t.current_week)) ||
    (p.week===null)!==(t.current_week===null) ||
    (p.week!==null && t.current_week!==null &&
      (p.week.season_index!==t.current_week.season_index || p.week.week!==t.current_week.week)))return false
  if(p.kind==='unavailable')return p.week===null && p.weeks_advanced_since_start===null &&
    p.completed_slot_receipts_this_week===null && p.committed_group_receipts_this_week===null && p.receipt_scope===null
  if(!p.week || !Number.isInteger(p.weeks_advanced_since_start) ||
    p.weeks_advanced_since_start===null || p.weeks_advanced_since_start<0 ||
    p.weeks_advanced_since_start!==(p.week.season_index*61+p.week.week-1 -
      (t.original_command.expected_start_week.season_index*61+t.original_command.expected_start_week.week-1)))return false
  if(p.kind==='terminal_frozen')return ['stopped','target_reached','complete'].includes(t.state) &&
    p.receipt_scope===null && p.completed_slot_receipts_this_week===null && p.committed_group_receipts_this_week===null
  return !['stopped','target_reached','complete'].includes(t.state) &&
    p.receipt_scope==='branch_current_week' &&
    Number.isInteger(p.completed_slot_receipts_this_week) && (p.completed_slot_receipts_this_week??-1)>=0 &&
    Number.isInteger(p.committed_group_receipts_this_week) && (p.committed_group_receipts_this_week??-1)>=0
}
export function validateTasks(value:unknown,run?:string,branch?:string):ServerTask[] {
  const data=value as {schema_version:string;tasks:ServerTask[]}
  if(!data || data.schema_version!=='full_simulation_tasks.v1' || !Array.isArray(data.tasks))throw Error('Invalid server task collection')
  const ids=new Set<string>()
  for(const t of data.tasks){
    if(!t || t.schema_version!=='full_simulation_task_view.v1' || ![t.task_id,t.run_id,t.branch_id,t.parent_command_id].every(id) ||
      (run!==undefined && (t.run_id!==run || t.branch_id!==branch)) || ids.has(t.task_id) ||
      !Number.isInteger(t.revision) || t.revision<1 || !desired.includes(t.desired_state) ||
      ![...desired,'recoverable','pause_requested','ownership_unverified'].includes(t.state) || !['recent','stale','inactive'].includes(t.heartbeat_health) ||
      !Number.isInteger(t.heartbeat_unix) || t.heartbeat_unix<0 || typeof t.needs_operator_action!=='boolean' ||
      (t.effective_boundary_target!=null && !isBoundaryTarget(t.effective_boundary_target)) ||
      !id(t.run_name) || !id(t.branch_name) || !(t.current_week===null || week(t.current_week)) ||
      !(t.lease_expires_at_unix===null || (Number.isInteger(t.lease_expires_at_unix) && t.lease_expires_at_unix>0)) ||
      !(t.progress===null || (typeof t.progress==='object' && !Array.isArray(t.progress))) ||
      !(t.checkpoint===null || id(t.checkpoint)) || !(t.error===null || typeof t.error==='string') ||
      !Array.isArray(t.events) || t.events.length!==t.revision ||
      t.events.some((e,i)=>e.revision!==i+1 || !desired.includes(e.state) || !id(e.reason) || !Number.isInteger(e.at_unix) || e.at_unix<0 || !hash(e.fingerprint) ||
        (i===0 ? e.previous!==null : e.previous!==t.events[i-1].fingerprint)) ||
      t.events[t.events.length-1].state!==t.desired_state ||
      !t.original_command || t.original_command.command_id!==t.parent_command_id ||
      !id(t.original_command.operator_label) || !id(t.original_command.audit_reason) || !week(t.original_command.expected_start_week) ||
      !hash(t.original_command.expected_position_fingerprint) || !hash(t.original_command.expected_preview_fingerprint) || !id(t.original_command.expected_revision_id) ||
      !validProgress(t)){throw Error('Invalid server task evidence')}
    ids.add(t.task_id)
  }
  return data.tasks
}
async function send(path:string,body?:unknown){
  const response=await fetch(root()+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  if(!response.ok)throw new ApiError(await response.text(),response.status)
  return response.json()
}
export async function getServerTasks(run?:string,branch?:string):Promise<ServerTask[]>{
  return validateTasks(await send(run && branch ? scope(run,branch):'/run-containers/full-simulation/tasks'),run,branch)
}
function ack(value:unknown,run:string,branch:string,request:string,parent?:string):TaskAck{
  const a=value as TaskAck
  if(!a || a.schema_version!=='full_simulation_task_ack.v1' || !id(a.task_id) || a.run_id!==run || a.branch_id!==branch ||
    a.request_id!==request || !id(a.parent_command_id) || (parent!==undefined && a.parent_command_id!==parent) ||
    !Number.isInteger(a.accepted_revision) || a.accepted_revision<1)throw Error('Invalid server task acknowledgement')
  return a
}
export async function startServerTask(run:string,branch:string,request_id:string,command:AuthoritativeFullSimulationCommandPayload){
  return ack(await send(scope(run,branch),{request_id,command}),run,branch,request_id,command.command_id)
}
export async function continueServerTask(t:ServerTask,body:ContinueTask){
  const a=ack(await send(scope(t.run_id,t.branch_id)+`/${encodeURIComponent(t.task_id)}/continue`,body),t.run_id,t.branch_id,body.request_id,t.parent_command_id)
  if(a.task_id!==t.task_id)throw Error('Invalid task continuation identity')
  return a
}
