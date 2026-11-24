import type { ViewerTournamentHistory, ViewerTournamentHistoryItem, ViewerTournamentResult } from '../../../api/types'

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

// Validate the fields consumed by the public result view and the identity
// invariants of TournamentResultAuthority. Do not infer a knockout format,
// enforce a scoreline grammar, or treat a later completion week as corruption.
export function validTournamentResultData(value: unknown): value is ViewerTournamentResult {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const result = value as ViewerTournamentResult
  const positive = (n: unknown): boolean => natural(n) && n > 0
  const nullablePositive = (n: unknown): boolean => n === null || positive(n)
  if (!natural(result.completed_season_index) || !positive(result.completed_week) || result.completed_week > 61 ||
      !id(result.champion_player_id) || !id(result.finalist_player_id) ||
      result.champion_player_id === result.finalist_player_id ||
      !Array.isArray(result.qualification_winner_ids) || !Array.isArray(result.players) || !Array.isArray(result.matches)) return false
  const players = new Set<string>()
  for (const player of result.players) {
    if (!player || typeof player !== 'object' || !id(player.player_id) || players.has(player.player_id) ||
        !['qualification', 'main', 'both', 'hybrid', 'group'].includes(player.draw_type) ||
        !id(player.reached_stage) || !natural(player.wins) || !natural(player.losses) ||
        !nullablePositive(player.seed_number) || typeof player.qualifier !== 'boolean' ||
        !nullablePositive(player.group_index) || !nullablePositive(player.group_position)) return false
    players.add(player.player_id)
  }
  if (!players.has(result.champion_player_id) || !players.has(result.finalist_player_id) ||
      !result.qualification_winner_ids.every(player => id(player) && players.has(player))) return false
  const matches = new Set<string>()
  for (const match of result.matches) {
    if (!match || typeof match !== 'object' || !id(match.match_id) || matches.has(match.match_id) ||
        !['qualification', 'main', 'group', 'knockout'].includes(match.draw_type) ||
        !positive(match.round_number) || !positive(match.bracket_position) ||
        !id(match.winner_player_id) || (match.loser_player_id !== null && !id(match.loser_player_id)) ||
        !id(match.scoreline)) return false
    matches.add(match.match_id)
  }
  return true
}
