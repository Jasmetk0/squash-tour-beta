import type { ViewerOfficialRanking, ViewerOfficialRunContext } from '../../../api/types'
import { legacySeasonLabel, validViewerRankingDetail } from './rankingSnapshotDetailBrowsing'

export function currentRankingViewerBranch(context: unknown, runId: string): string | null {
  if (!context || typeof context !== 'object' || !runId.trim()) return null
  const value = context as Partial<ViewerOfficialRunContext>
  return value.product_run_id === runId &&
    typeof value.official_branch_id === 'string' && value.official_branch_id.trim()
    ? value.official_branch_id : null
}

// Current and historical endpoints expose the same versioned public projection.
// Only historical reads additionally specify the expected ordinal externally.
export function validCurrentOfficialRanking(
  data: unknown, runId: string, branchId: string
): data is ViewerOfficialRanking {
  if (!data || typeof data !== 'object') return false
  const ordinal = (data as Partial<ViewerOfficialRanking>).week_ordinal
  return typeof ordinal === 'number' && validViewerRankingDetail(data, runId, branchId, ordinal)
}

export const legacyCurrentRankingSeason = legacySeasonLabel
