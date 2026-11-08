import type { GlobalFullSimulationOperations } from '../api/types'
import type { ServerTask } from '../api/fullSimulationTasks'

export type TaskDiagnosticPriority =
  | 'operator_action' | 'stale_heartbeat' | 'lease_expired'
  | 'active_unconfirmed' | 'not_active'

export type TaskDiagnostic = {
  task_id: string
  run_id: string
  branch_id: string
  parent_command_id: string
  run_name: string
  branch_name: string
  state: string
  desired_state: string
  revision: number
  checkpoint: string | null
  heartbeat_health: ServerTask['heartbeat_health']
  heartbeat_unix: number
  lease_expires_at_unix: number | null
  needs_operator_action: boolean
  week: { season_index: number; week: number } | null
  progress_kind: ServerTask['progress_evidence']['kind']
  priority: TaskDiagnosticPriority
  matching_receipt_count: number
  /** The legacy inventory is not a second simulation or progress authority. */
  linked_legacy_receipt: boolean
}

export type LegacyReceiptDiagnostic = {
  run_id: string
  branch_id: string
  command_id: string
  control_state: string
  lease_state: string
  linked_task_ids: string[]
  link_status: 'one_task' | 'no_task' | 'ambiguous'
}

export type TaskCenterRecoveryDiagnostics = {
  format: 'task_center_recovery_diagnostics.v1'
  evidence_scope: 'two_independent_persisted_reads'
  atomic_snapshot: false
  worker_liveness_verified: false
  continuation_authorized: false
  run_scope: 'global'
  task_count: number
  legacy_receipt_count: number
  unknown_legacy_count: number
  operator_action_count: number
  stale_heartbeat_count: number
  expired_lease_count: number
  unmatched_legacy_receipt_count: number
  ambiguous_legacy_receipt_count: number
  tasks: TaskDiagnostic[]
  legacy_receipts: LegacyReceiptDiagnostic[]
}

const tuple = (run: string, branch: string, command: string): string =>
  JSON.stringify([run,branch,command])

/**
 * Both arguments MUST have passed their respective HTTP validators
 * (getServerTasks / getGlobalFullSimulationOperations). This pure projection
 * is a snapshot of independently read persisted records, never a Resume preflight.
 * Original commands, event audit text and full progress payloads are excluded.
 */
export function buildTaskCenterRecoveryDiagnostics(
  serverTasks: readonly ServerTask[], inventory: GlobalFullSimulationOperations
): TaskCenterRecoveryDiagnostics {
  if (!Array.isArray(serverTasks) || !inventory
    || inventory.schema_version !== 'global_full_simulation_operations.v1'
    || inventory.visibility !== 'durable_receipts_only'
    || !Array.isArray(inventory.operations)
    || inventory.pending_count !== inventory.operations.length
    || !Number.isSafeInteger(inventory.legacy_pending_count)
    || inventory.legacy_pending_count < 0) {
    throw Error('Persisted Task Center evidence cannot be verified')
  }
  const tasksByParent = new Map<string, ServerTask[]>()
  const uniqueTasks = new Set<string>()
  for (const t of serverTasks) {
    if (!t || !t.run_id || !t.branch_id || !t.task_id || !t.parent_command_id
      || uniqueTasks.has(t.task_id)
      || !Number.isSafeInteger(t.revision) || t.revision < 1
      || typeof t.needs_operator_action !== 'boolean'
      || !['recent','stale','inactive'].includes(t.heartbeat_health)
      || !Number.isSafeInteger(t.heartbeat_unix) || t.heartbeat_unix < 0
      || (t.lease_expires_at_unix !== null &&
        (!Number.isSafeInteger(t.lease_expires_at_unix) || t.lease_expires_at_unix < 0))
      || !t.progress_evidence || !['live_branch','terminal_frozen','unavailable'].includes(t.progress_evidence.kind))
      throw Error('Persisted Task Center contains an ambiguous task identity or status')
    uniqueTasks.add(t.task_id)
    const key = tuple(t.run_id,t.branch_id,t.parent_command_id)
    const group = tasksByParent.get(key)??[]
    group.push(t)
    tasksByParent.set(key,group)
  }
  const seenReceipts = new Set<string>()
  const receipts: LegacyReceiptDiagnostic[] = inventory.operations.map(r => {
    if (!r || !r.run_id || !r.branch_id || !r.command_id
      || !['running','pause_requested','paused'].includes(r.control_state))
      throw Error('Legacy receipt identity or state is invalid')
    const key=tuple(r.run_id,r.branch_id,r.command_id)
    if(seenReceipts.has(key)) throw Error('Duplicate legacy Full Simulation receipt')
    seenReceipts.add(key)
    const matching=(tasksByParent.get(key)??[]).map(t=>t.task_id).sort()
    return {
      run_id:r.run_id,branch_id:r.branch_id,command_id:r.command_id,
      control_state:r.control_state,lease_state:r.lease_state,
      linked_task_ids:matching,
      link_status:matching.length===0?'no_task':matching.length===1?'one_task':'ambiguous'
    }
  })
  const resultTasks: TaskDiagnostic[] = serverTasks.map(t=>{
    // A stale heartbeat is NOT proof of crash. A lease is NOT a worker process.
    const priority: TaskDiagnosticPriority = t.needs_operator_action ? 'operator_action'
      : t.heartbeat_health==='stale' && ['active','queued','pause_requested'].includes(t.state)
        ? 'stale_heartbeat'
      : t.lease_expires_at_unix!==null && t.heartbeat_health!=='recent'
        && ['recoverable','ownership_unverified'].includes(t.state)
        ? 'lease_expired'
      : ['active','queued','pause_requested'].includes(t.state)
        ? 'active_unconfirmed' : 'not_active'
    return {
      task_id:t.task_id,run_id:t.run_id,branch_id:t.branch_id,
      parent_command_id:t.parent_command_id,run_name:t.run_name,
      branch_name:t.branch_name,state:t.state,desired_state:t.desired_state,
      revision:t.revision,checkpoint:t.checkpoint,
      heartbeat_health:t.heartbeat_health,heartbeat_unix:t.heartbeat_unix,
      lease_expires_at_unix:t.lease_expires_at_unix,
      needs_operator_action:t.needs_operator_action,
      week:t.current_week,progress_kind:t.progress_evidence.kind,priority,
      matching_receipt_count:seenReceipts.has(tuple(t.run_id,t.branch_id,t.parent_command_id))?1:0,
      linked_legacy_receipt:seenReceipts.has(tuple(t.run_id,t.branch_id,t.parent_command_id))
    }
  }).sort((a,b)=>
    (a.needs_operator_action?0:1)-(b.needs_operator_action?0:1)
    || a.run_name.localeCompare(b.run_name)
    || a.branch_name.localeCompare(b.branch_name)
    || a.task_id.localeCompare(b.task_id))
  return {
    format:'task_center_recovery_diagnostics.v1',
    evidence_scope:'two_independent_persisted_reads',
    atomic_snapshot:false,worker_liveness_verified:false,
    continuation_authorized:false,run_scope:'global',
    task_count:resultTasks.length,
    legacy_receipt_count:receipts.length,
    unknown_legacy_count:inventory.legacy_pending_count,
    operator_action_count:resultTasks.filter(t=>t.needs_operator_action).length,
    stale_heartbeat_count:resultTasks.filter(t=>t.priority==='stale_heartbeat').length,
    expired_lease_count:resultTasks.filter(t=>t.priority==='lease_expired').length,
    unmatched_legacy_receipt_count:receipts.filter(r=>r.link_status==='no_task').length,
    ambiguous_legacy_receipt_count:receipts.filter(r=>r.link_status==='ambiguous').length,
    tasks:resultTasks,
    legacy_receipts:receipts
  }
}
export function serializeTaskCenterRecoveryDiagnostics(value:TaskCenterRecoveryDiagnostics):string{
  return JSON.stringify(value,null,2)+'\n'
}
