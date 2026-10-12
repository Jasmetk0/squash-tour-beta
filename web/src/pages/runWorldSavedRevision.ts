/** Read a reachable Saved Revision's OWN Run World component. Never load mutable
 * Current HEAD for missing historical data, even when an ancestor is shared.
 *
 * The existing Saved Revision detail endpoint authorizes reachability for
 * the requested Run/Branch. Shared ancestors keep their ORIGINAL Branch owner
 * in the payload, so downstream projections use that origin explicitly.
 */
import type { RunPackageStateResponse, SavedRevisionHistoryDetail } from '../api/types'

type Row = Record<string, unknown>
function row(raw: unknown): Row | null {
  return raw !== null && typeof raw === 'object' && !Array.isArray(raw) ? raw as Row : null
}
export type SavedRunWorldRead = {
  revisionId: string
  revisionBranchId: string
  isShared: boolean
  response: RunPackageStateResponse | null
}
export function historicalRunWorldSnapshot(
  detail: SavedRevisionHistoryDetail, runId: string, branchId: string, revisionId: string
): SavedRunWorldRead {
  if (!revisionId || detail.run_id !== runId || detail.branch_id !== branchId ||
      detail.revision_id !== revisionId) {
    throw new Error('Saved World revision scope does not match selected Run and Branch')
  }
  if (!['run_saved_revision_v1','empty_run_saved_revision_v1'].includes(detail.payload_schema_version))
    throw new Error('Unsupported historical Saved Revision payload version')
  const run = row(detail.payload.run)
  const branch = row(detail.payload.branch)
  const content = row(detail.payload.content)
  const origin = detail.revision_branch_id
  if (!origin || run?.run_id !== runId || branch?.branch_id !== origin ||
      detail.is_shared_revision !== (origin !== branchId) || !content) {
    throw new Error('Historical World revision source branch or payload identity mismatch')
  }
  const component = content.run_package_state
  if (component === undefined) {
    return {revisionId,revisionBranchId:origin,isShared:detail.is_shared_revision,response:null}
  }
  const saved = row(component)
  const rawState = row(saved?.state)
  const fingerprint = saved?.fingerprint
  if (!saved || Object.keys(saved).sort().join(',') !== 'fingerprint,state' ||
      typeof fingerprint !== 'string' || !/^[0-9a-f]{64}$/.test(fingerprint) ||
      !rawState || rawState.run_id !== runId || rawState.branch_id !== origin ||
      !Array.isArray(rawState.entities) || !Array.isArray(rawState.package_versions)) {
    throw new Error('Saved Revision has an invalid historical Run World component')
  }
  // Preserve the exact stored state and its declared fingerprint. Do not remap
  // shared source Branch IDs or change any serialized historical hash input.
  const response: RunPackageStateResponse = {
    fingerprint, state: rawState as RunPackageStateResponse['state']
  }
  return {revisionId,revisionBranchId:origin,isShared:detail.is_shared_revision,response}
}
