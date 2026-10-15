import {afterEach,describe,expect,it,vi} from 'vitest'
import {getBoundaryOptions,isBoundaryTarget,setBoundaryTarget} from './fullSimulationBoundaryTargets'
import {boundaryExample,boundaryReview} from './fullSimulationBoundaryTargets.fixture'
afterEach(()=>vi.unstubAllGlobals())
describe('precise target HTTP contract',()=>{
 it('encodes exact scope and rejects cross-branch options',async()=>{
  const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify(boundaryReview()),{status:200}));vi.stubGlobal('fetch',fetcher)
  expect((await getBoundaryOptions('run','branch','parent')).options).toHaveLength(1)
  expect(fetcher.mock.calls[0][0]).toContain('/run/branches/branch/authoritative-simulation/full-simulation/target-options?command_id=parent')
  fetcher.mockResolvedValue(new Response(JSON.stringify({...boundaryReview(),branch_id:'other'})))
  await expect(getBoundaryOptions('run','branch','parent')).rejects.toThrow('Invalid precise target review')
 })
 it('validates slot/event shapes without guessing from labels',()=>{
  expect(isBoundaryTarget(boundaryExample('before_slot'))).toBe(true)
  expect(isBoundaryTarget(boundaryExample('after_tournament'))).toBe(true)
  for(const change of [{slot_ordinal:true},{edition_id:'foreign'},{slot_kind:'entry'},{topology_fingerprint:null}])expect(isBoundaryTarget({...boundaryExample(),...change})).toBe(false)
 })
 it('requires the acknowledged exact original selector and parent',async()=>{
  const body={control_command_id:'request',target_command_id:'parent',boundary_target:boundaryExample(),operator_label:'Operator',audit_reason:'Reason'}
  const ack={schema_version:'authoritative_full_simulation_target_result.v2',run_id:'run',branch_id:'branch',target_command_id:'parent',control_command_id:'request',boundary_target:body.boundary_target,applied_revision:2,review_fingerprint:'e'.repeat(64),committed_child_work_persists:true,replayed:false}
  const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify(ack)));vi.stubGlobal('fetch',fetcher)
  expect(await setBoundaryTarget('run','branch',body)).toEqual(ack)
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual(body)
  fetcher.mockResolvedValue(new Response(JSON.stringify({...ack,target_command_id:'other'})))
  await expect(setBoundaryTarget('run','branch',body)).rejects.toThrow('Invalid precise target acknowledgement')
 })
})
