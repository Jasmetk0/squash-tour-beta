import type { RunContainer, RunBranch, ViewerBranchWorkingDraft } from './types'

/**
 * A deep link only nominates a Calendar and Branch; the current Saved Revision,
 * Branch permissions and clean Draft must be established from real Run Admin.
 * This mirrors Run Home's first-tournament guard, rather than trusting the URL.
 */
export function verifiedRunCalendarHandoff(
  run: RunContainer | null | undefined,
  branches: RunBranch[] | null | undefined,
  draft: ViewerBranchWorkingDraft | null | undefined,
  runId: string,
  branchId: string
): boolean {
  if (!runId || !branchId || !run ||
    run.run_id !== runId ||
    run.storage_kind !== 'custom_local' ||
    run.read_only ||
    !Array.isArray(branches)) return false

  const branch = branches.find(item =>
    item.run_id === runId && item.branch_id === branchId)
  return Boolean(branch &&
    branch.status === 'active' &&
    !branch.read_only &&
    typeof branch.saved_head_revision_id === 'string' &&
    branch.saved_head_revision_id.length > 0 &&
    draft?.run_id === runId &&
    draft.branch_id === branchId &&
    draft.status === 'clean' &&
    draft.base_saved_revision_id === branch.saved_head_revision_id)
}
