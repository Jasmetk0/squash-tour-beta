/** HTTP-client contracts only; no sporting execution claims. */
import {afterEach,describe,expect,it,vi} from 'vitest'
import {nativeClosureAction,previewNativeTask,nativeTaskSummary,nativeTaskCommand,type NativeTaskPreviewRequest} from './fullSimulationTasksNative'

const request:NativeTaskPreviewRequest={schema_version:'authoritative_full_simulation_command.v2',run_id:'r',branch_id:'b',command_id:'c',
 seed:231,operator_label:'Admin',audit_reason:'Reviewed native scope',target_week:{season_index:1,week:80}}
const clock={schema_version:'run_calendar.v1',weeks_per_year:80,season_start_year_week:79,start_year:2100,season_count:2}
const response=()=>({schema_version:'authoritative_full_simulation_preview.v2',request:structuredClone(request),execution_calendar:clock,
 start_week:{season_index:0,week:79},final_week:{season_index:1,week:80},target_week:request.target_week,
 target_semantics:'open_target_week',expected_revision_id:'source',expected_position_fingerprint:'a'.repeat(64),
 preview_fingerprint:'b'.repeat(64),manual_save_required_after_each_sporting_child:true,initial_transition_blockers:[]})
afterEach(()=>vi.unstubAllGlobals())
describe('native Full Simulation client validation',()=>{
 it('accepts the exact original W80 clock and target',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>response()}))
  expect((await previewNativeTask(request)).execution_calendar.weeks_per_year).toBe(80)
 })
 it.each(['wrong-scope','wrong-target','bad-clock','changed-boundary','false-source'])('rejects %s without a legacy fallback',async change=>{
  const value=response()
  if(change==='wrong-scope')value.request.branch_id='other'
  if(change==='wrong-target')value.target_week={season_index:1,week:81}
  if(change==='bad-clock')value.execution_calendar={...clock,season_start_year_week:81}
  if(change==='changed-boundary')value.final_week={season_index:0,week:80}
  if(change==='false-source')value.expected_revision_id=''
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>value}))
  await expect(previewNativeTask(request)).rejects.toThrow()
 })
 it('rejects a closure acknowledgement for another reviewed source',async()=>{
  const body={request_id:'approval',review_fingerprint:'c'.repeat(64),operator_label:'Admin',audit_reason:'Reviewed',explicit_confirmation:true as const}
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({request:body,review:{run_id:'r',branch_id:'other',parent_command_id:'c',review_fingerprint:body.review_fingerprint}})}))
  await expect(nativeClosureAction('r','b','c','approve',body)).rejects.toThrow('acknowledgement')
 })
})

import {calendarTaskExample} from './fullSimulationTasks.fixture'
import type {TaskCalendar} from './fullSimulationTasksCalendar'

function terminal(){
 const original=calendarTaskExample(clock as TaskCalendar)
 const command=nativeTaskCommand(response() as Awaited<ReturnType<typeof previewNativeTask>>)
 const task={...original,run_id:'r',branch_id:'b',parent_command_id:'c',
  original_command:command,calendar_revision_id:'source',state:'target_reached',
  current_week:{season_index:1,week:80},
  progress_evidence:{...original.progress_evidence,kind:'terminal_frozen' as const,
   week:{season_index:1,week:80},weeks_advanced_since_start:81,
   completed_slot_receipts_this_week:null,committed_group_receipts_this_week:null,receipt_scope:null}}
 const summary={schema_version:'full_simulation_terminal_summary.v3',run_id:'r',branch_id:'b',command_id:'c',
  status:'target_reached',start_week:command.expected_start_week,end_week:task.current_week,
  original_final_week:{season_index:1,week:80},effective_target_week:command.target_week,
  execution_calendar:clock,initial_saved_revision_id:'source',terminal_saved_revision_id:'terminal',
  persisted_child_command_count:32,reason:'week_target_reached',target_reached:true,
  completed_tournaments:['edition-a','edition-b'],summary_fingerprint:'a'.repeat(64)}
 const envelope={schema_version:'full_simulation_terminal_summary_response.v2',run_id:'r',branch_id:'b',command_id:'c',
  status:'target_reached',available:true,summary}
 return {task,envelope}
}
describe('native terminal summary source validation',()=>{
 it('returns frozen W80 start, end, target and exact confirmed Edition IDs',async()=>{
  const {task,envelope}=terminal()
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>envelope}))
  expect(await nativeTaskSummary(task)).toEqual(envelope.summary)
 })
 it.each(['scope','envelope-state','start','end','target','reason','duplicate','revision','progress'])(
  'rejects inconsistent %s evidence',async change=>{
   const {task,envelope}=terminal()
   const s=envelope.summary
   if(change==='scope')s.branch_id='other'
   if(change==='envelope-state')envelope.status='stopped'
   if(change==='start')s.start_week={season_index:0,week:78}
   if(change==='end')s.end_week={season_index:1,week:79}
   if(change==='target')s.effective_target_week={season_index:1,week:79}
   if(change==='reason')s.reason='operator_stop'
   if(change==='duplicate')s.completed_tournaments=['edition-a','edition-a']
   if(change==='revision')s.terminal_saved_revision_id=''
   if(change==='progress')task.progress_evidence.weeks_advanced_since_start=80
   vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>envelope}))
   await expect(nativeTaskSummary(task)).rejects.toThrow('Invalid native terminal summary')
  })
 it('distinguishes closing the Run from opening its last week',async()=>{
  const {task,envelope}=terminal()
  task.original_command.target_week=null
  task.state='complete';envelope.status='complete';envelope.summary.status='complete'
  envelope.summary.reason='run_completed';envelope.summary.target_reached=false
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>envelope}))
  expect((await nativeTaskSummary(task)).reason).toBe('run_completed')
 })
})
