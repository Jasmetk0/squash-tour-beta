import type { ViewerOfficialRanking, ViewerOfficialRankingRow } from '../../../api/types'

// Only the currently shipped viewer_official_ranking.v1 legacy RankingWeek
// projection uses W=61 and 50 seasons. Never apply these limits to a future
// calendar-native publication schema.
const WEEKS_PER_SEASON = 61
const SEASON_COUNT = 50
const LAST_ORDINAL = WEEKS_PER_SEASON * SEASON_COUNT - 1

function integerBetween(value: unknown, lower: number, upper: number): value is number {
  return typeof value === 'number' &&
    Number.isSafeInteger(value) && value >= lower && value <= upper
}

export function parseLegacyRankingOrdinal(raw: string): number | null {
  // No signed, fractional, scientific, noncanonical or out-of-range identities.
  if (!/^(0|[1-9][0-9]*)$/.test(raw)) return null
  const parsed = Number(raw)
  return integerBetween(parsed, 0, LAST_ORDINAL) ? parsed : null
}

export function validViewerRankingDetail(
  data: unknown,
  productRunId: string,
  viewerBranchId: string,
  ordinal: number
): data is ViewerOfficialRanking {
  if (!data || typeof data !== 'object' || !integerBetween(ordinal, 0, LAST_ORDINAL)) return false
  const value = data as Partial<ViewerOfficialRanking>
  if (
    value.schema_version !== 'viewer_official_ranking.v1' ||
    value.product_run_id !== productRunId ||
    value.viewer_branch_id !== viewerBranchId ||
    !integerBetween(value.season_index, 0, SEASON_COUNT - 1) ||
    !integerBetween(value.week, 1, WEEKS_PER_SEASON) ||
    value.week_ordinal !== ordinal ||
    value.season_index * WEEKS_PER_SEASON + value.week - 1 !== ordinal ||
    !integerBetween(value.best_n, 1, Number.MAX_SAFE_INTEGER) ||
    !integerBetween(value.row_count, 0, Number.MAX_SAFE_INTEGER) ||
    !Array.isArray(value.rows) || value.row_count !== value.rows.length ||
    typeof value.policy_id !== 'string' ||
    typeof value.snapshot_fingerprint !== 'string' ||
    !/^[a-f0-9]{64}$/.test(value.snapshot_fingerprint)
  ) return false

  const playerIds = new Set<string>()
  for (let index = 0; index < value.rows.length; index += 1) {
    const row = value.rows[index] as Partial<ViewerOfficialRankingRow> | null
    if (!row || typeof row !== 'object' ||
      row.rank !== index + 1 ||
      typeof row.player_id !== 'string' || !row.player_id.trim() ||
      playerIds.has(row.player_id) ||
      !integerBetween(row.points, 0, Number.MAX_SAFE_INTEGER)
    ) return false
    playerIds.add(row.player_id)
  }
  return true
}

export function legacySeasonLabel(seasonIndex: number): string {
  const start = 2000 + seasonIndex
  return String(start) + '/' + String((start + 1) % 100).padStart(2, '0')
}

export const DETAIL_PAGE_SIZE = 50

export function rankingRowsMatchingId(
  rows: readonly ViewerOfficialRankingRow[],
  search: string
): ViewerOfficialRankingRow[] {
  const needle = search.trim().toLocaleLowerCase()
  return needle
    ? rows.filter(row => row.player_id.toLocaleLowerCase().includes(needle))
    : [...rows]
}

export function detailPages(count: number): number {
  return Math.ceil(count / DETAIL_PAGE_SIZE)
}

export function parseDetailPage(raw: string, maxPage: number): number | null {
  if (!/^[1-9][0-9]*$/.test(raw.trim())) return null
  const value = Number(raw.trim())
  return Number.isSafeInteger(value) && value <= maxPage ? value : null
}
