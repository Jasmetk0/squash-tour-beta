import type { TourCareerRecords } from '../../../api/calendarTour'
import type { ViewerSignedRecordsFilters } from '../../../api/viewerSignedTourRecords'

export const RECORD_METRICS = ['titles', 'finals', 'awarded_points'] as const
export const RECORD_SCOPES = ['player', 'country'] as const

const positiveId = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0

const nonnegative = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0

const positive = (value: unknown): value is number =>
  nonnegative(value) && value > 0

function validRow(row: unknown, country: string | null): boolean {
  if (!row || typeof row !== 'object') return false
  const r = row as Record<string, unknown>
  return positiveId(r.entity_id) && positiveId(r.label) && positiveId(r.country_code) &&
    (country === null || r.country_code === country) &&
    RECORD_METRICS.every(metric => nonnegative(r[metric]))
}

function validRecord(record: TourCareerRecords['records'][number], country: string | null, limit: number): boolean {
  if (!record || !RECORD_SCOPES.includes(record.scope) || !RECORD_METRICS.includes(record.metric) ||
      record.record_id !== 'native_tour.' + record.scope + '.' + record.metric + '.v1' ||
      !nonnegative(record.value) || !Array.isArray(record.holders) ||
      !Array.isArray(record.leaderboard) || !Array.isArray(record.holder_history) ||
      !nonnegative(record.leaderboard_total) || record.leaderboard.length > limit ||
      record.leaderboard_total < record.leaderboard.length) return false

  const ids = new Set<string>()
  for (const holder of record.holders) {
    if (!validRow(holder, country) || ids.has(holder.entity_id) ||
        !positive(record.value) || holder[record.metric] !== record.value) return false
    ids.add(holder.entity_id)
  }
  if ((record.value === 0) !== (record.holders.length === 0)) return false

  let previousValue = Number.POSITIVE_INFINITY
  let previousRank = 0
  let previousId = ''
  const rowIds = new Set<string>()
  for (const [index, row] of record.leaderboard.entries()) {
    if (!validRow(row, country) || !positive(row[record.metric]) || rowIds.has(row.entity_id) ||
        row[record.metric] > previousValue || !positive(row.rank)) return false
    const sameValue = row[record.metric] === previousValue
    if (sameValue && (row.rank !== previousRank || row.entity_id <= previousId)) return false
    if (!sameValue && row.rank !== index + 1) return false
    rowIds.add(row.entity_id)
    previousValue = row[record.metric]
    previousRank = row.rank
    previousId = row.entity_id
  }

  let previousHistoryValue = 0
  let previousSeason = -1
  for (const h of record.holder_history) {
    if (!nonnegative(h.season_index) || h.season_index <= previousSeason ||
        !positive(h.record_value) || h.record_value < previousHistoryValue ||
        !positiveId(h.season_label) || !positiveId(h.boundary_command_id) ||
        !Array.isArray(h.holder_ids) || !Array.isArray(h.holder_labels) ||
        h.holder_ids.length === 0 || h.holder_ids.length !== h.holder_labels.length ||
        h.holder_ids.some(id => !positiveId(id)) ||
        new Set(h.holder_ids).size !== h.holder_ids.length ||
        h.holder_labels.some(label => !positiveId(label)) ||
        (h.change !== 'established' && h.change !== 'improved' && h.change !== 'tied') ||
        (previousHistoryValue === 0 ? h.change !== 'established'
          : h.record_value > previousHistoryValue ? h.change !== 'improved'
          : h.change !== 'tied')) return false
    previousHistoryValue = h.record_value
    previousSeason = h.season_index
  }
  if (record.holder_history.length > 0 &&
      record.holder_history[record.holder_history.length - 1].record_value !== record.value) return false
  if (record.value > 0 && record.holder_history.length === 0) return false
  if (record.leaderboard.length > 0 && record.leaderboard[0][record.metric] !== record.value) return false
  return true
}

export function viewerRecordsBranch(context: unknown, runId: string): string | null {
  if (!context || typeof context !== 'object' || !runId.trim()) return null
  const v = context as { product_run_id?: unknown; official_branch_id?: unknown }
  return v.product_run_id === runId && positiveId(v.official_branch_id) ? v.official_branch_id : null
}

/** Fail closed: only authenticated Viewer Saved data can be rendered as records. */
export function verifiedViewerSignedTourRecords(
  input: unknown, runId: string, branchId: string, filters: ViewerSignedRecordsFilters
): TourCareerRecords | null {
  if (!input || typeof input !== 'object' || !runId.trim() || !branchId.trim()) return null
  const v = input as TourCareerRecords
  if (v.schema_version !== 'calendar_tour_signed_records_response.v1' ||
      v.run_id !== runId || v.branch_id !== branchId ||
      !positiveId(v.saved_head_revision_id) ||
      !/^[0-9a-f]{64}$/.test(v.source_tour_fingerprint) ||
      !nonnegative(v.as_of_season_index) || !nonnegative(v.from_season_index) ||
      v.from_season_index !== filters.fromSeason ||
      (filters.asOfSeason !== null && v.as_of_season_index !== filters.asOfSeason) ||
      v.country_code !== filters.countryCode || v.leaderboard_limit !== 20 ||
      !Array.isArray(v.completed_seasons) || v.completed_seasons.length === 0 ||
      !Array.isArray(v.source_seasons) || !Array.isArray(v.records) ||
      v.records.length !== RECORD_METRICS.length * RECORD_SCOPES.length ||
      !nonnegative(v.completed_edition_count)) return null

  const seenSeasons = new Set<number>()
  let total = 0
  for (const [index, season] of v.source_seasons.entries()) {
    if (!season || !nonnegative(season.season_index) ||
        season.season_index < v.from_season_index || season.season_index > v.as_of_season_index ||
        (index > 0 && season.season_index <= v.source_seasons[index - 1].season_index) ||
        !positiveId(season.season_label) || !positiveId(season.boundary_command_id) ||
        !positiveId(season.source_tour_fingerprint) ||
        !positiveId(season.published_ranking_fingerprint) ||
        !nonnegative(season.completed_edition_count)) return null
    seenSeasons.add(season.season_index)
    total += season.completed_edition_count
    if (!Number.isSafeInteger(total)) return null
  }
  if (v.source_seasons.length !== v.completed_seasons.length ||
      v.completed_seasons.some((index, i) => !nonnegative(index) ||
        index !== v.source_seasons[i].season_index) ||
      !seenSeasons.has(v.as_of_season_index) ||
      v.completed_edition_count !== total) return null

  const recordIds = new Set<string>()
  for (const record of v.records) {
    if (!validRecord(record, v.country_code, v.leaderboard_limit) ||
        recordIds.has(record.record_id) ||
        record.holder_history.some(h => !seenSeasons.has(h.season_index))) return null
    recordIds.add(record.record_id)
  }
  if (RECORD_SCOPES.some(scope => RECORD_METRICS.some(metric =>
    !recordIds.has('native_tour.' + scope + '.' + metric + '.v1')))) return null
  return v
}
