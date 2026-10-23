/** HTTP-client contracts only; no sporting execution claims. */
import {afterEach,describe,expect,it,vi} from 'vitest'
import {nativeClosureAction,previewNativeTask,type NativeTaskPreviewRequest} from './fullSimulationTasksNative'

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
