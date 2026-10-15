import { ApiError } from './client'
import type { AuthoritativeRankingWeek } from './types'

export type BoundaryTarget = {
  schema_version: 'full_simulation_boundary_target.v1'
  kind: 'before_slot' | 'before_final' | 'after_tournament'
  week: AuthoritativeRankingWeek; schedule_fingerprint: string
  slot_ordinal: number | null; slot_id: string | null; slot_kind: 'entry' | 'match' | null
  group_ids: string[]; event_id: string | null; edition_id: string | null
  event_fingerprint: string | null; topology_fingerprint: string | null; selector_fingerprint: string
}
export type BoundaryOptions = {
  schema_version: 'full_simulation_boundary_options.v1'; run_id: string; branch_id: string; parent_command_id: string
  week: AuthoritativeRankingWeek; options: BoundaryTarget[]
  unavailable: {event_id:string; kind:string; reason:string}[]
}
export type BoundaryRequest = { control_command_id:string; target_command_id:string; boundary_target:BoundaryTarget;
  operator_label:string; audit_reason:string }
export type BoundaryAck = {schema_version:'authoritative_full_simulation_target_result.v2'; run_id:string; branch_id:string;
  target_command_id:string; control_command_id:string; boundary_target:BoundaryTarget; applied_revision:number;
  review_fingerprint:string; committed_child_work_persists:true; replayed:boolean}
const hash=(v:unknown)=>typeof v==='string' && /^[0-9a-f]{64}$/.test(v)
const id=(v:unknown)=>typeof v==='string' && v.length>0
export function isBoundaryTarget(value:unknown):value is BoundaryTarget {
  const t=value as BoundaryTarget
  if(!t || t.schema_version!=='full_simulation_boundary_target.v1' ||
    !['before_slot','before_final','after_tournament'].includes(t.kind) ||
    !t.week || !Number.isInteger(t.week.season_index) || t.week.season_index<0 || t.week.season_index>49 ||
    !Number.isInteger(t.week.week) || t.week.week<1 || t.week.week>61 ||
    !hash(t.schedule_fingerprint) || !hash(t.selector_fingerprint) || !Array.isArray(t.group_ids) ||
    t.group_ids.some(v=>!id(v)) || new Set(t.group_ids).size!==t.group_ids.length)return false
  if(t.kind==='after_tournament'){
    if(t.slot_id!==null || t.slot_ordinal!==null || t.slot_kind!==null || t.group_ids.length || t.topology_fingerprint!==null)return false
  }else if(!Number.isInteger(t.slot_ordinal) || (t.slot_ordinal??0)<1 || !id(t.slot_id) ||
    !['match','entry'].includes(t.slot_kind??'') || (t.slot_kind==='match')!==(t.group_ids.length>0))return false
  if(t.kind==='before_slot')return t.event_id===null && t.edition_id===null && t.event_fingerprint===null && t.topology_fingerprint===null
  return id(t.event_id) && t.edition_id===t.event_id && hash(t.event_fingerprint) &&
    (t.kind!=='before_final' || (t.slot_kind==='match' && hash(t.topology_fingerprint)))
}
const root=()=>import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const scope=(r:string,b:string)=>`${root()}/admin/runs/${encodeURIComponent(r)}/branches/${encodeURIComponent(b)}/authoritative-simulation/full-simulation`
export async function getBoundaryOptions(run:string,branch:string,parent:string):Promise<BoundaryOptions>{
  const response=await fetch(`${scope(run,branch)}/target-options?command_id=${encodeURIComponent(parent)}`)
  if(!response.ok)throw new ApiError(await response.text(),response.status)
  const d=await response.json() as BoundaryOptions
  if(!d || d.schema_version!=='full_simulation_boundary_options.v1' || d.run_id!==run || d.branch_id!==branch ||
    d.parent_command_id!==parent || !Array.isArray(d.options) || d.options.some(t=>!isBoundaryTarget(t) ||
      t.week.season_index!==d.week?.season_index || t.week.week!==d.week?.week) ||
    new Set(d.options.map(t=>t.selector_fingerprint)).size!==d.options.length ||
    !Array.isArray(d.unavailable) || d.unavailable.some(v=>!id(v.event_id)||!id(v.kind)||!id(v.reason)))throw Error('Invalid precise target review')
  return d
}
export async function setBoundaryTarget(run:string,branch:string,body:BoundaryRequest):Promise<BoundaryAck>{
  const response=await fetch(`${scope(run,branch)}/target`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  if(!response.ok)throw new ApiError(await response.text(),response.status)
  const d=await response.json() as BoundaryAck
  if(!d || d.schema_version!=='authoritative_full_simulation_target_result.v2' || d.run_id!==run || d.branch_id!==branch ||
    d.target_command_id!==body.target_command_id || d.control_command_id!==body.control_command_id ||
    !isBoundaryTarget(d.boundary_target) || d.boundary_target.selector_fingerprint!==body.boundary_target.selector_fingerprint ||
    !Number.isInteger(d.applied_revision) || d.applied_revision<1 || !hash(d.review_fingerprint) ||
    d.committed_child_work_persists!==true || typeof d.replayed!=='boolean')throw Error('Invalid precise target acknowledgement')
  return d
}
