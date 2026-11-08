import {describe,expect,it} from 'vitest'
import type { ServerTask } from '../api/fullSimulationTasks'
import type { GlobalFullSimulationOperations } from '../api/types'
import {
  buildTaskCenterRecoveryDiagnostics,serializeTaskCenterRecoveryDiagnostics
} from './taskCenterRecoveryDiagnostics'

function task(id:string, parent='parent-A', additions:Record<string,unknown>={}):ServerTask{
  return {
    task_id:id,run_id:'run-A',branch_id:'branch-A',parent_command_id:parent,
    run_name:'Demo Run',branch_name:'Timeline 1',
    state:'awaiting_operator',desired_state:'paused',revision:4,checkpoint:'native_entry_review_required',
    heartbeat_health:'inactive',heartbeat_unix:1760000000,lease_expires_at_unix:null,
    needs_operator_action:true,
    current_week:{season_index:1,week:15},
    progress_evidence:{kind:'live_branch'},
    original_command:{command_id:parent,private_provenance:'do-not-export'},
    events:[{reason:'secret audit detail'}],
    ...additions
  } as unknown as ServerTask
}
function receipt(parent='parent-A',overrides:Record<string,unknown>={}){
  return {
    run_id:'run-A',branch_id:'branch-A',command_id:parent,
    control_state:'paused',lease_state:'absent',
    run_name:'Demo Run',branch_name:'Timeline 1',
    ...overrides
  }
}
function inventory(operations= [receipt()],legacy=1):GlobalFullSimulationOperations{
  return {
    schema_version:'global_full_simulation_operations.v1',
    visibility:'durable_receipts_only',
    pending_count:operations.length,legacy_pending_count:legacy,
    operations
  } as unknown as GlobalFullSimulationOperations
}
describe('global Task Center persisted recovery diagnostic (no mutations)',()=>{
  it('links only an exact Run/Branch/parent tuple and excludes original commands',()=>{
    const data=buildTaskCenterRecoveryDiagnostics([task('task-1')],inventory())
    expect(data.format).toBe('task_center_recovery_diagnostics.v1')
    expect(data.task_count).toBe(1)
    expect(data.operator_action_count).toBe(1)
    expect(data.legacy_receipt_count).toBe(1)
    expect(data.unknown_legacy_count).toBe(1)
    expect(data.tasks[0].priority).toBe('operator_action')
    expect(data.tasks[0].linked_legacy_receipt).toBe(true)
    expect(data.legacy_receipts[0].link_status).toBe('one_task')
    expect(data.legacy_receipts[0].linked_task_ids).toEqual(['task-1'])
    expect(data.atomic_snapshot).toBe(false)
    expect(data.worker_liveness_verified).toBe(false)
    expect(data.continuation_authorized).toBe(false)
    const json=serializeTaskCenterRecoveryDiagnostics(data)
    expect(JSON.parse(json).evidence_scope).toBe('two_independent_persisted_reads')
    expect(json).not.toContain('do-not-export')
    expect(json).not.toContain('secret audit detail')
    expect(json).not.toContain('original_command')
  })
  it('does not link a different Run or Branch with the same parent ID',()=>{
    const data=buildTaskCenterRecoveryDiagnostics([
      task('task-1','parent-A',{branch_id:'another'})
    ],inventory())
    expect(data.legacy_receipts[0].link_status).toBe('no_task')
    expect(data.unmatched_legacy_receipt_count).toBe(1)
    expect(data.tasks[0].linked_legacy_receipt).toBe(false)
  })
  it('does not collide on string separators inside scoped IDs',()=>{
    const data=buildTaskCenterRecoveryDiagnostics([
      task('task-1','parent',{run_id:'run-A::branch-A',branch_id:'B'})
    ],inventory([receipt('parent',{run_id:'run-A',branch_id:'branch-A::B'})]))
    expect(data.legacy_receipts[0].link_status).toBe('no_task')
  })
  it('keeps duplicate parent associations ambiguous and never invents one task',()=>{
    const data=buildTaskCenterRecoveryDiagnostics([
      task('task-2'),task('task-1')
    ],inventory())
    expect(data.ambiguous_legacy_receipt_count).toBe(1)
    expect(data.legacy_receipts[0].linked_task_ids).toEqual(['task-1','task-2'])
    expect(data.legacy_receipts[0].link_status).toBe('ambiguous')
    expect(data.task_count).toBe(2)
  })
  it('distinguishes stale heartbeat from operator decision and a reported lease',()=>{
    const data=buildTaskCenterRecoveryDiagnostics([
      task('action'),
      task('stale','b',{needs_operator_action:false,state:'active',
        heartbeat_health:'stale',lease_expires_at_unix:1730000000}),
      task('recover','c',{needs_operator_action:false,state:'recoverable',
        heartbeat_health:'inactive',lease_expires_at_unix:1730000000}),
      task('active','d',{needs_operator_action:false,state:'active',
        heartbeat_health:'recent',lease_expires_at_unix:1890000000}),
      task('paused','e',{needs_operator_action:false,state:'paused',
        heartbeat_health:'inactive'})
    ],inventory([],0))
    expect(data.operator_action_count).toBe(1)
    expect(data.stale_heartbeat_count).toBe(1)
    expect(data.expired_lease_count).toBe(1)
    expect(Object.fromEntries(data.tasks.map(t=>[t.task_id,t.priority]))).toEqual({
      action:'operator_action',stale:'stale_heartbeat',recover:'lease_expired',
      active:'active_unconfirmed',paused:'not_active'
    })
    expect(data.worker_liveness_verified).toBe(false)
  })
  it('accepts zero tasks as a valid empty inventory, not a worker failure',()=>{
    const data=buildTaskCenterRecoveryDiagnostics([],inventory([],2))
    expect(data.task_count).toBe(0)
    expect(data.unknown_legacy_count).toBe(2)
    expect(data.unmatched_legacy_receipt_count).toBe(0)
  })
  it('refuses duplicated task IDs and duplicate legacy receipts',()=>{
    expect(()=>buildTaskCenterRecoveryDiagnostics([task('t'),task('t')],inventory()))
      .toThrow('ambiguous task')
    expect(()=>buildTaskCenterRecoveryDiagnostics([],
      inventory([receipt(),receipt()])))
      .toThrow('Duplicate legacy')
  })
  it('rejects foreign/invalid inventory counts or unverified task identities',()=>{
    expect(()=>buildTaskCenterRecoveryDiagnostics([],{
      ...inventory(),pending_count:100
    })).toThrow('cannot be verified')
    expect(()=>buildTaskCenterRecoveryDiagnostics([task('')],inventory()))
      .toThrow('ambiguous task')
    expect(()=>buildTaskCenterRecoveryDiagnostics([task('x','parent-A',{
      heartbeat_health:'invalid'
    })],inventory())).toThrow('ambiguous task')
  })
})
