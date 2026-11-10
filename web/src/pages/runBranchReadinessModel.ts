import type { RunBranch } from '../api/types'
import type { RunHomeReadiness, RunReadinessCode, RunReadinessItem } from '../api/runHomeReadiness'
import { validateRunHomeReadiness } from '../api/runHomeReadiness'

/** A read-only comparison of two individually validated Saved HEAD inspections.
 * It is NOT an atomic two-Branch database snapshot or an operation preflight.
 */
export type BranchReadinessSide = {
  branch_id: string
  branch_name: string
  saved_head_revision_id: string
  evidence: RunHomeReadiness
}
export type BranchReadinessDifference = {
  code: RunReadinessCode
  left: RunReadinessItem
  right: RunReadinessItem
  status_changed: boolean
  count_delta: number
}
export type BranchReadinessComparison = {
  schema_version: 'admin_branch_readiness_comparison.v1'
  run_id: string
  left: BranchReadinessSide
  right: BranchReadinessSide
  comparisons: BranchReadinessDifference[]
  same_calendar: boolean
  same_phase: boolean
  same_saved_head: boolean
  saved_transitions_delta: number
  published_rankings_delta: number
  active_tasks_delta: number
  /** A comparison is never an all-operations readiness certificate. */
  operation_preflight_required: true
  cross_branch_atomic_snapshot: false
}

export type ReadinessComparisonReader = {
  branches: (runId: string) => Promise<{ run_branches: RunBranch[] }>
  readiness: (runId: string, branchId: string) => Promise<unknown>
}

const codes: RunReadinessCode[] = [
  'world', 'calendar_package', 'population', 'health', 'official_ranking', 'working_draft'
]

function exactBranches(response: { run_branches: RunBranch[] }, runId: string): Map<string, RunBranch> {
  if (!response || !Array.isArray(response.run_branches)) throw Error('Branch list unavailable')
  const map = new Map<string, RunBranch>()
  for (const b of response.run_branches) {
    if (!b || b.run_id !== runId || typeof b.branch_id !== 'string' || !b.branch_id.trim()
      || map.has(b.branch_id)) throw Error('Branch list has foreign or duplicate entries')
    map.set(b.branch_id, b)
  }
  return map
}

function requireHead(branch: RunBranch | undefined, expected: string | null): string {
  if (!branch || typeof branch.saved_head_revision_id !== 'string' || !branch.saved_head_revision_id.trim())
    throw Error('A Branch Saved HEAD is unavailable')
  if (expected && branch.saved_head_revision_id !== expected)
    throw Error('Selected Branch Saved HEAD changed before comparison')
  return branch.saved_head_revision_id
}

function checkedEvidence(raw: unknown, runId: string, branchId: string, expectedHead: string): RunHomeReadiness {
  const evidence = validateRunHomeReadiness(raw, runId, branchId)
  if (evidence.saved_revision_id !== expectedHead)
    throw Error('Saved readiness does not match the requested Branch HEAD')
  return evidence
}

/** Fetch the same Branch list before/after the two independent read transactions.
 * No write, cache fallback, privileged Viewer branch, or unverified mixing.
 * A concurrent Working Draft change without a HEAD change is not prevented;
 * the UI labels these as separately observed samples, not atomic evidence.
 */
export async function inspectBranchReadinessComparison(
  reader: ReadinessComparisonReader, runId: string, leftId: string, rightId: string,
  expectedLeftHead: string
): Promise<BranchReadinessComparison> {
  if (!runId || !leftId || !rightId || leftId === rightId || !expectedLeftHead)
    throw Error('Select two different Branches within the same Run')
  const first = exactBranches(await reader.branches(runId), runId)
  const leftBranch = first.get(leftId), rightBranch = first.get(rightId)
  const leftHead = requireHead(leftBranch, expectedLeftHead)
  const rightHead = requireHead(rightBranch, null)

  const [rawLeft, rawRight] = await Promise.all([
    reader.readiness(runId, leftId), reader.readiness(runId, rightId)
  ])
  const left = checkedEvidence(rawLeft, runId, leftId, leftHead)
  const right = checkedEvidence(rawRight, runId, rightId, rightHead)
  const final = exactBranches(await reader.branches(runId), runId)
  if (requireHead(final.get(leftId), leftHead) !== leftHead
    || requireHead(final.get(rightId), rightHead) !== rightHead)
    throw Error('A Branch Saved HEAD changed during comparison; inspect again')
  const leftCalendar = left.current_calendar, rightCalendar = right.current_calendar
  const sameCalendar = ([
    'schema_version', 'weeks_per_year', 'season_start_year_week', 'start_year', 'season_count'
  ] as const).every(key => leftCalendar[key] === rightCalendar[key])
  const comparisons = codes.map((code, index) => {
    const a = left.items[index], b = right.items[index]
    if (a.code !== code || b.code !== code) throw Error('Invalid foundation comparison order')
    return {
      code,
      left: { ...a }, right: { ...b },
      status_changed: a.status !== b.status,
      count_delta: b.evidence_count - a.evidence_count
    }
  })
  return {
    schema_version: 'admin_branch_readiness_comparison.v1',
    run_id: runId,
    left: { branch_id: leftId, branch_name: leftBranch!.display_name,
      saved_head_revision_id: leftHead, evidence: left },
    right: { branch_id: rightId, branch_name: rightBranch!.display_name,
      saved_head_revision_id: rightHead, evidence: right },
    comparisons, same_calendar: sameCalendar, same_phase: left.phase === right.phase,
    same_saved_head: leftHead === rightHead,
    saved_transitions_delta: right.saved_transition_count - left.saved_transition_count,
    published_rankings_delta: right.saved_published_ranking_count - left.saved_published_ranking_count,
    active_tasks_delta: right.active_full_simulation_task_count - left.active_full_simulation_task_count,
    operation_preflight_required: true, cross_branch_atomic_snapshot: false
  }
}

/** Compact, stable operator diagnostics. Never include complete player lists or
 * Stored payloads. Exactly the captured source IDs, counts, and statuses.
 */
export function serializeBranchReadinessComparison(report: BranchReadinessComparison): string {
  const side = (s: BranchReadinessSide) => ({
    branch_id: s.branch_id, branch_name: s.branch_name,
    saved_head_revision_id: s.saved_head_revision_id,
    saved_content_hash: s.evidence.saved_revision_content_hash,
    draft_version: s.evidence.draft_version,
    run_status: s.evidence.run_status, phase: s.evidence.phase,
    calendar: s.evidence.current_calendar,
    saved_transitions: s.evidence.saved_transition_count,
    saved_rankings: s.evidence.saved_published_ranking_count,
    active_tasks: s.evidence.active_full_simulation_task_count,
    historical_tasks: s.evidence.historical_full_simulation_task_count,
    legacy_fax_writer_supported: s.evidence.sporting_calendar_supported_by_legacy_writers
  })
  return JSON.stringify({
    format: report.schema_version, run_id: report.run_id,
    evidence_kind: 'independent_read_only_saved_inspections',
    cross_branch_atomic_snapshot: false,
    operation_preflight_required: true,
    left: side(report.left), right: side(report.right),
    same_calendar: report.same_calendar, same_phase: report.same_phase,
    differences: report.comparisons
  }, null, 2) + '\n'
}
