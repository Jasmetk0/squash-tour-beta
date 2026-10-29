import type { ViewerOfficialRanking, ViewerOfficialRunContext } from '../../../api/types'

// Specific to the existing viewer_official_ranking.v1 legacy RankingWeek
// read model. These 50 × 61 limits must NOT be used for calendar-native Runs.
const LAST_LEGACY_ORDINAL = 50 * 61 - 1

function whole(value: unknown, min: number, max: number): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= min && value <= max
}

export function currentRankingViewerBranch(context: unknown, runId: string): string | null {
  if (!context || typeof context !== 'object' || !runId.trim()) return null
  const value = context as Partial<ViewerOfficialRunContext>
  return value.product_run_id === runId &&
    typeof value.official_branch_id === 'string' && value.official_branch_id.trim()
    ? value.official_branch_id : null
}

export function validCurrentOfficialRanking(
  data: unknown, runId: string, branchId: string
): data is ViewerOfficialRanking {
  if (!data || typeof data !== 'object' || !runId.trim() || !branchId.trim()) return false
  const value = data as Partial<ViewerOfficialRanking>
  if (
    value.schema_version !== 'viewer_official_ranking.v1' ||
    value.product_run_id !== runId || value.viewer_branch_id !== branchId ||
    !whole(value.season_index, 0, 49) || !whole(value.week, 1, 61) ||
    !whole(value.week_ordinal, 0, LAST_LEGACY_ORDINAL) ||
    value.week_ordinal !== value.season_index * 61 + value.week - 1 ||
    !whole(value.best_n, 1, Number.MAX_SAFE_INTEGER) ||
    !whole(value.row_count, 0, Number.MAX_SAFE_INTEGER) ||
    typeof value.policy_id !== 'string' ||
    typeof value.snapshot_fingerprint !== 'string' ||
    !/^[0-9a-f]{64}$/.test(value.snapshot_fingerprint) ||
    !Array.isArray(value.rows) || value.row_count !== value.rows.length
  ) return false

  const ids = new Set<string>()
  let previousPoints = Number.POSITIVE_INFINITY
  for (const [index, item] of value.rows.entries()) {
    if (!item || typeof item !== 'object') return false
    const row = item as { rank?: unknown; player_id?: unknown; points?: unknown }
    if (row.rank !== index + 1 ||
      typeof row.player_id !== 'string' || !row.player_id.trim() ||
      ids.has(row.player_id) ||
      !whole(row.points, 0, Number.MAX_SAFE_INTEGER) ||
      row.points > previousPoints
    ) return false
    ids.add(row.player_id)
    previousPoints = row.points
  }
  return true
}

export function legacyCurrentRankingSeason(index: number): string {
  const start = 2000 + index
  return String(start) + '/' + String((start + 1) % 100).padStart(2, '0')
}
