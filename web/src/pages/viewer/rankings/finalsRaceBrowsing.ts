import type { ViewerFinalsRaceHistory, ViewerFinalsRacePublication, ViewerFinalsRaceRow } from '../../../api/types'

// The shipped viewer_finals_race_history.v1 is the legacy 50 x W61 projection,
// not a constraint on calendar-native W52/W80 Runs.
const MAX_SEASON = 49
const MAX_WEEK = 61
const maxSafe = Number.MAX_SAFE_INTEGER

function natural(value: unknown, min = 0, max = maxSafe): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= min && value <= max
}
function identifier(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

export function raceSeasonLabel(index: number): string {
  const start = 2000 + index
  return String(start) + '/' + String((start + 1) % 100).padStart(2, '0')
}

export function viewerRaceBranch(context: unknown, runId: string): string | null {
  if (!context || typeof context !== 'object' || !identifier(runId)) return null
  const candidate = context as { product_run_id?: unknown; official_branch_id?: unknown }
  return candidate.product_run_id === runId && identifier(candidate.official_branch_id)
    ? candidate.official_branch_id : null
}

function validRow(row: unknown, index: number, bestN: number, season: number, cutoffWeek: number): row is ViewerFinalsRaceRow {
  if (!row || typeof row !== 'object') return false
  const v = row as Partial<ViewerFinalsRaceRow>
  if (v.rank !== index + 1 || !identifier(v.player_id) ||
      !natural(v.race_points) || !natural(v.tournaments_counted) ||
      !Array.isArray(v.counted_results) || v.tournaments_counted !== v.counted_results.length ||
      v.counted_results.length > bestN ||
      (v.finals_selected !== null && typeof v.finals_selected !== 'boolean') ||
      (v.finals_seed !== null && !natural(v.finals_seed, 1)) ||
      (v.qualification_source !== null && v.qualification_source !== 'direct_entry' && v.qualification_source !== 'race')) return false

  let sum = 0
  let previousPoints = Number.POSITIVE_INFINITY
  for (const item of v.counted_results) {
    if (!item || typeof item !== 'object') return false
    const result = item as { event_id?: unknown; completed_season_index?: unknown; completed_week?: unknown; race_points?: unknown }
    if (!identifier(result.event_id) ||
        !natural(result.completed_season_index, 0, MAX_SEASON) || result.completed_season_index !== season ||
        !natural(result.completed_week, 1, MAX_WEEK) || result.completed_week > cutoffWeek ||
        !natural(result.race_points) || result.race_points > previousPoints) return false
    sum += result.race_points
    if (!Number.isSafeInteger(sum)) return false
    previousPoints = result.race_points
  }
  return sum === v.race_points
}

function validPublication(value: unknown, runId: string, branchId: string): value is ViewerFinalsRacePublication {
  if (!value || typeof value !== 'object') return false
  const v = value as Partial<ViewerFinalsRacePublication>
  if (
    v.schema_version !== 'viewer_finals_race_publication.v1' ||
    v.product_run_id !== runId || v.viewer_branch_id !== branchId ||
    !natural(v.target_season_index, 0, MAX_SEASON) ||
    v.cutoff_season_index !== v.target_season_index ||
    !natural(v.cutoff_week, 1, MAX_WEEK) || !natural(v.best_n, 1) ||
    typeof v.selection_published !== 'boolean' ||
    (v.finals_event_id !== null && !identifier(v.finals_event_id)) ||
    (v.selection_published !== (v.finals_event_id !== null)) ||
    !Array.isArray(v.rows)
  ) return false
  const players = new Set<string>()
  let previousPoints = Number.POSITIVE_INFINITY
  const seeds = new Set<number>()
  for (const [index, row] of v.rows.entries()) {
    if (!validRow(row, index, v.best_n, v.target_season_index, v.cutoff_week) ||
        players.has(row.player_id) || row.race_points > previousPoints) return false
    if (!v.selection_published) {
      if (row.finals_selected !== null || row.finals_seed !== null || row.qualification_source !== null) return false
    } else if (row.finals_selected === true) {
      if (row.finals_seed === null || row.qualification_source === null ||
          seeds.has(row.finals_seed)) return false
      seeds.add(row.finals_seed)
    } else if (row.finals_selected !== false || row.finals_seed !== null || row.qualification_source !== null) {
      return false
    }
    previousPoints = row.race_points
    players.add(row.player_id)
  }
  return true
}

export function validViewerRaceHistory(data: unknown, runId: string, branchId: string): data is ViewerFinalsRaceHistory {
  if (!data || typeof data !== 'object' || !identifier(runId) || !identifier(branchId)) return false
  const v = data as Partial<ViewerFinalsRaceHistory>
  if (v.schema_version !== 'viewer_finals_race_history.v1' ||
      v.product_run_id !== runId || v.viewer_branch_id !== branchId ||
      !Array.isArray(v.publications) ||
      (v.latest_target_season_index !== null && !natural(v.latest_target_season_index, 0, MAX_SEASON))) return false
  const seasons = new Set<number>()
  let maxSeason: number | null = null
  for (const publication of v.publications) {
    if (!validPublication(publication, runId, branchId) ||
        seasons.has(publication.target_season_index)) return false
    seasons.add(publication.target_season_index)
    if (maxSeason === null || publication.target_season_index > maxSeason) maxSeason = publication.target_season_index
  }
  return v.latest_target_season_index === maxSeason
}

export function raceSeasonsNewestFirst(history: ViewerFinalsRaceHistory): ViewerFinalsRacePublication[] {
  return [...history.publications].sort((a, b) => b.target_season_index - a.target_season_index)
}

export const RACE_PAGE_SIZE = 50
export function filterRacePlayerRows(rows: readonly ViewerFinalsRaceRow[], needle: string): ViewerFinalsRaceRow[] {
  const search = needle.trim().toLocaleLowerCase()
  return search ? rows.filter(row => row.player_id.toLocaleLowerCase().includes(search)) : [...rows]
}
export function parseRacePage(value: string, pages: number): number | null {
  if (!/^[1-9][0-9]*$/.test(value.trim())) return null
  const number = Number(value.trim())
  return Number.isSafeInteger(number) && number <= pages ? number : null
}
