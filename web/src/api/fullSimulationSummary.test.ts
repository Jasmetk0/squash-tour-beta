import {afterEach,describe,expect,it,vi} from 'vitest'
import {getFullSimulationSummary} from './fullSimulationSummary'

export function summaryExample() {
  const week={season_index:0,week:1}
  return {schema_version:'full_simulation_terminal_summary_response.v1',run_id:'run',branch_id:'branch',command_id:'parent',
    status:'stopped',available:true,summary:{schema_version:'full_simulation_terminal_summary.v1',
      run_id:'run',branch_id:'branch',command_id:'parent',status:'stopped',
      receipt_request_fingerprint:'a'.repeat(64),summary_fingerprint:'b'.repeat(64),
      start_week:week,end_week:week,original_final_week:{season_index:49,week:61},
      effective_target_week:{season_index:49,week:61},target_revision:0,
      reason:'operator_stop',target_reached:false,initial_saved_revision_id:'saved-old',terminal_saved_revision_id:'saved-old',
      terminal_control_command_id:'stop-id',terminal_operator_label:'Original operator',terminal_audit_reason:'Actual stop reason',
      persisted_child_command_count:3,completed_tournaments:[],
      position:{run_id:'run',branch_id:'branch',current_week:week,position_fingerprint:'c'.repeat(64)},
      unavailable_sections:['ranking_changes','watched_events','notifications']}}
}
afterEach(()=>vi.restoreAllMocks())
describe('Frozen Full Simulation summary HTTP contract',()=>{
  const read=async(payload:unknown)=>{
    vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify(payload),{status:200}))
    return getFullSimulationSummary('run','branch','parent')
  }
  it('reads the exact original scope and does not issue a mutation',async()=>{
    expect(await read(summaryExample())).toEqual(summaryExample())
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/runs/run/branches/branch/authoritative-simulation/full-simulation/parents/parent/summary'))
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it.each(['scope','end','position','reason','hash','count','terminal'] as const)('rejects invalid %s evidence',async(kind)=>{
    const data=summaryExample()
    if(kind==='scope') data.summary.branch_id='other'
    if(kind==='end') data.summary.end_week={season_index:0,week:62}
    if(kind==='position') data.summary.position.current_week={season_index:0,week:2}
    if(kind==='reason') data.summary.reason='made-up'
    if(kind==='hash') data.summary.summary_fingerprint='invalid'
    if(kind==='count') data.summary.persisted_child_command_count=-1
    if(kind==='terminal') data.status='pending'
    await expect(read(data)).rejects.toThrow('invalid')
  })
  it('accepts unavailable legacy history without inventing an endpoint',async()=>{
    const data={...summaryExample(),available:false,summary:null}
    expect(await read(data)).toEqual(data)
  })
})

it('preserves v2 slot and owned-source terminal evidence and rejects mismatches',async()=>{
 const {boundaryExample}=await import('./fullSimulationBoundaryTargets.fixture')
 for(const kind of ['before_final','after_tournament'] as const){
  const target=boundaryExample(kind)
  const trigger={schema_version:'full_simulation_boundary_evidence.v1',target,week:target.week,schedule_fingerprint:target.schedule_fingerprint,
   ...(kind==='before_final'?{slot_id:target.slot_id,slot_ordinal:target.slot_ordinal,group_ids:target.group_ids}:{edition_id:target.edition_id,event_id:target.event_id,source_fingerprint:'e'.repeat(64),source_command_id:'closure-command'})}
  const base=summaryExample();const data={...base,status:'target_reached',summary:{...base.summary,schema_version:'full_simulation_terminal_summary.v2',status:'target_reached',reason:'boundary_target_reached',target_reached:true,target_revision:1,effective_boundary_target:target,target_trigger_evidence:trigger}}
  vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify(data)))
  expect(await getFullSimulationSummary('run','branch','parent')).toEqual(data)
  vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({...data,summary:{...data.summary,target_trigger_evidence:{...trigger,week:{season_index:0,week:2}}}})))
  await expect(getFullSimulationSummary('run','branch','parent')).rejects.toThrow('Invalid precise terminal evidence')
 }
})
