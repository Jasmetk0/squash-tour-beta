import type { ViewerTournamentHistory, ViewerTournamentHistoryItem } from '../../../api/types'

const rootKeys = ['schema_version', 'product_run_id', 'viewer_branch_id', 'tournament_count', 'published_result_count', 'tournaments']
const rowKeys = ['event_id', 'season', 'season_week', 'event_name', 'template_id', 'category', 'tour_level', 'host_country', 'host_city', 'region', 'main_draw_size', 'qualification_draw_size', 'seeds_count', 'qualifier_spots', 'wild_cards', 'byes', 'ranking_status', 'result_published', 'champion_player_id', 'finalist_player_id']

function exactKeys(value: unknown, expected: readonly string[]): boolean {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).length === expected.length &&
    expected.every(key => Object.prototype.hasOwnProperty.call(value, key)))
}
const id = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0
const natural = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0

// Canonical legacy public DTO, not native W52/W80 or an independent result authority.
export function verifiedTournamentHistory(value: unknown, runId: string, branchId: string): ViewerTournamentHistory | null {
  if (!id(runId) || !id(branchId) || !exactKeys(value, rootKeys)) return null
  const data = value as ViewerTournamentHistory
  if (data.schema_version !== 'viewer_tournament_history.v1' || data.product_run_id !== runId ||
      data.viewer_branch_id !== branchId || !natural(data.tournament_count) || !natural(data.published_result_count) ||
      !Array.isArray(data.tournaments) || data.tournaments.length !== data.tournament_count) return null
  const seen = new Set<string>()
  let published = 0
  for (const item of data.tournaments) {
    if (!item || !exactKeys(item, rowKeys) || !id(item.event_id) || seen.has(item.event_id) ||
        !id(item.season) || !natural(item.season_week) || item.season_week < 1 || item.season_week > 61 ||
        typeof item.event_name !== 'string' || !id(item.template_id) || typeof item.category !== 'string' ||
        (item.tour_level !== null && typeof item.tour_level !== 'string') ||
        !id(item.host_country) || item.host_country.length !== 3 ||
        (item.host_city !== null && typeof item.host_city !== 'string') || !id(item.region) ||
        ![item.main_draw_size, item.qualification_draw_size, item.seeds_count, item.qualifier_spots, item.wild_cards, item.byes].every(natural) ||
        typeof item.ranking_status !== 'string' || typeof item.result_published !== 'boolean' ||
        (item.result_published
          ? !id(item.champion_player_id) || !id(item.finalist_player_id) || item.champion_player_id === item.finalist_player_id
          : item.champion_player_id !== null || item.finalist_player_id !== null)) return null
    seen.add(item.event_id)
    if (item.result_published) published++
  }
  return published === data.published_result_count ? data : null
}

export function compareTournamentSeasons(a: string, b: string): number {
  const aYear = Number.parseInt(a.split('/')[0], 10)
  const bYear = Number.parseInt(b.split('/')[0], 10)
  if (Number.isFinite(aYear) && Number.isFinite(bYear) && aYear !== bYear) return aYear - bYear
  return a.localeCompare(b, undefined, { numeric: true })
}

export function compareTournamentHistoryEvents(a: ViewerTournamentHistoryItem, b: ViewerTournamentHistoryItem): number {
  return compareTournamentSeasons(b.season, a.season) ||
    a.season_week - b.season_week || a.event_id.localeCompare(b.event_id)
}

export function tournamentMatchesSearch(item: ViewerTournamentHistoryItem, normalizedNeedle: string): boolean {
  return !normalizedNeedle || [item.event_name, item.event_id, item.host_country, item.host_city ?? '', item.category, item.template_id]
    .some(value => value.toLocaleLowerCase().includes(normalizedNeedle))
}
