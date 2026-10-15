import { ApiError } from './client'

export type WeekExtensionCandidate = {
  command_id:string
  week:{season_index:number;week:number}
  status:'append_only_proven'|'unchanged'|'blocked'
  reason:string
  old_schedule_fingerprint:string
  current_schedule_fingerprint:string|null
  original_slot_count:number
  receipt_fingerprint:string
  new_slots:{ordinal:number;group_id:string;event_id:string;round_number:number|null}[]
  read_only:true
  automatic_rebase:false
}
const validId=(v:unknown):v is string=>typeof v==='string' && v.length>0
const hash=(v:unknown):v is string=>typeof v==='string' && /^[0-9a-f]{64}$/.test(v)
export function validateWeekExtensionInspection(value:unknown,run:string,branch:string):WeekExtensionCandidate[]{
 const v=value as {schema_version:string;run_id:string;branch_id:string;read_only:boolean;items:WeekExtensionCandidate[]}
 if(!v || v.schema_version!=='next_week_extension_inspection.v1' || v.run_id!==run || v.branch_id!==branch ||
    v.read_only!==true || !Array.isArray(v.items))throw Error('Invalid Next Week inspection scope')
 const ids=new Set<string>()
 for(const item of v.items){
   if(!item || !validId(item.command_id) || ids.has(item.command_id) ||
      !item.week || !Number.isInteger(item.week.season_index) || item.week.season_index<0 || item.week.season_index>49 ||
      !Number.isInteger(item.week.week) || item.week.week<1 || item.week.week>61 ||
      !['append_only_proven','unchanged','blocked'].includes(item.status) ||
      !validId(item.reason) || !hash(item.receipt_fingerprint) || !hash(item.old_schedule_fingerprint) ||
      !(item.current_schedule_fingerprint===null || hash(item.current_schedule_fingerprint)) ||
      !Number.isInteger(item.original_slot_count) || item.original_slot_count<1 ||
      item.read_only!==true || item.automatic_rebase!==false || !Array.isArray(item.new_slots) ||
      item.new_slots.some(s=>!Number.isInteger(s.ordinal)||s.ordinal<1||!validId(s.group_id)||!validId(s.event_id)||
         (s.round_number!==null && (!Number.isInteger(s.round_number)||s.round_number<1))) ||
      (item.status!=='append_only_proven' && item.new_slots.length!==0) ||
      (item.status==='append_only_proven' && item.new_slots.length===0))throw Error('Invalid Next Week inspection evidence')
   ids.add(item.command_id)
 }
 return v.items
}
export async function getNextWeekExtensionInspection(run:string,branch:string):Promise<WeekExtensionCandidate[]>{
 const root=import.meta.env.VITE_API_BASE_URL??'http://127.0.0.1:8000'
 const path=`/admin/runs/${encodeURIComponent(run)}/branches/${encodeURIComponent(branch)}/authoritative-simulation/next-week/extension-inspection`
 const response=await fetch(root+path)
 if(!response.ok)throw new ApiError(await response.text(),response.status)
 return validateWeekExtensionInspection(await response.json(),run,branch)
}

export type WeekExtensionApprovalRequest = {
  control_command_id:string
  task_id:string
  target_week_command_id:string
  expected_task_revision:number
  expected_receipt_fingerprint:string
  expected_current_schedule_fingerprint:string
  operator_label:string
  audit_reason:string
  confirm_committed_work_is_immutable:true
}
export async function approveNextWeekExtension(
 run:string,branch:string,body:WeekExtensionApprovalRequest
):Promise<{schema_version:string;task_revision:number;replayed:boolean}>{
 const root=import.meta.env.VITE_API_BASE_URL??'http://127.0.0.1:8000'
 const path=`/admin/runs/${encodeURIComponent(run)}/branches/${encodeURIComponent(branch)}/authoritative-simulation/next-week/extension-approve`
 const response=await fetch(root+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
 if(!response.ok)throw new ApiError(await response.text(),response.status)
 const data=await response.json()
 if(data?.schema_version!=='next_week_extension_approval.v1' ||
   !Number.isInteger(data.task_revision) || data.task_revision<1 ||
   typeof data.replayed!=='boolean')throw Error('Invalid extension approval acknowledgement')
 return data
}
