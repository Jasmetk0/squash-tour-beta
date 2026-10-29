import type { ViewerOfficialRankingHistory, ViewerOfficialRankingHistoryItem } from '../../../api/types'

export const RANKING_HISTORY_PAGE_SIZE = 25
export type RankingHistoryOrder = 'newest' | 'oldest'
export type RankingHistoryFilters = {
  season: string
  bestN: string
  search: string
  order: RankingHistoryOrder
}

// These are the bounds of the existing viewer_official_ranking_history.v1
// legacy RankingWeek projection, NOT universal Run-calendar constraints.
const LEGACY_WEEKS_PER_SEASON = 61
const LEGACY_SEASONS = 50
const LEGACY_MAX_ORDINAL = LEGACY_WEEKS_PER_SEASON * LEGACY_SEASONS - 1

function validInteger(value: unknown, minimum: number, maximum: number): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum && value <= maximum
}

export function validRankingHistory(
  value: unknown,
  productRunId: string,
  viewerBranchId: string
): value is ViewerOfficialRankingHistory {
  if (!value || typeof value !== 'object') return false
  const history = value as Partial<ViewerOfficialRankingHistory>
  if (
    history.schema_version !== 'viewer_official_ranking_history.v1' ||
    history.product_run_id !== productRunId ||
    history.viewer_branch_id !== viewerBranchId ||
    !validInteger(history.public_head_ordinal, 0, LEGACY_MAX_ORDINAL) ||
    !Array.isArray(history.publications) ||
    !validInteger(history.publication_count, 0, LEGACY_MAX_ORDINAL + 1) ||
    history.publication_count !== history.publications.length
  ) return false

  const ordinals = new Set<number>()
  for (const row of history.publications) {
    if (!row || typeof row !== 'object') return false
    const item = row as Partial<ViewerOfficialRankingHistoryItem>
    if (
      !validInteger(item.season_index, 0, LEGACY_SEASONS - 1) ||
      !validInteger(item.week, 1, LEGACY_WEEKS_PER_SEASON) ||
      !validInteger(item.week_ordinal, 0, LEGACY_MAX_ORDINAL) ||
      item.week_ordinal !== item.season_index * LEGACY_WEEKS_PER_SEASON + item.week - 1 ||
      item.week_ordinal > history.public_head_ordinal ||
      typeof item.policy_id !== 'string' ||
      typeof item.snapshot_fingerprint !== 'string' ||
      !/^[0-9a-f]{64}$/.test(item.snapshot_fingerprint) ||
      !validInteger(item.best_n, 1, Number.MAX_SAFE_INTEGER) ||
      !validInteger(item.row_count, 0, Number.MAX_SAFE_INTEGER) ||
      ordinals.has(item.week_ordinal)
    ) return false
    ordinals.add(item.week_ordinal)
  }
  // The current published world head must itself be present when the
  // legacy endpoint returns any history. Never silently fill a missing head.
  return history.publications.length === 0 || ordinals.has(history.public_head_ordinal)
}

export function legacyRankingSeasonLabel(index: number): string {
  const year = 2000 + index
  return String(year) + '/' + String((year + 1) % 100).padStart(2, '0')
}

export function filterRankingHistory(
  publications: readonly ViewerOfficialRankingHistoryItem[],
  filters: RankingHistoryFilters
): ViewerOfficialRankingHistoryItem[] {
  const search = filters.search.trim().toLowerCase().replace(/^#/, '')
  return publications.filter((item) => (
    (filters.season === '' || String(item.season_index) === filters.season) &&
    (filters.bestN === '' || String(item.best_n) === filters.bestN) &&
    (search === '' || item.policy_id.toLowerCase().includes(search) || String(item.week_ordinal).includes(search))
  )).sort((a, b) => filters.order === 'oldest'
    ? a.week_ordinal - b.week_ordinal
    : b.week_ordinal - a.week_ordinal)
}

export function rankingHistoryPageCount(total: number): number {
  return Math.ceil(total / RANKING_HISTORY_PAGE_SIZE)
}

export function rankingHistoryPageJump(raw: string, count: number): number | null {
  if (!/^[1-9][0-9]*$/.test(raw.trim())) return null
  const requested = Number(raw.trim())
  return Number.isSafeInteger(requested) && requested <= count ? requested : null
}
