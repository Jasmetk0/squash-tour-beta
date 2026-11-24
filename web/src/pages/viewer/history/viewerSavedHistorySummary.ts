import type {
  ViewerOfficialRankingHistoryItem, ViewerTournamentHistory, ViewerTournamentHistoryItem
} from '../../../api/types'
import { validRankingHistory } from '../rankings/rankingHistoryBrowsing'
import { validViewerRaceHistory } from '../rankings/finalsRaceBrowsing'

const isId = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0
const whole = (value: unknown, low: number, high: number): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= low && value <= high

export type SavedHistorySummary = {
  tournamentCount: number
  publishedTournamentCount: number
  rankingCount: number
  raceCount: number
  lastTournament: ViewerTournamentHistoryItem | null
  lastRanking: ViewerOfficialRankingHistoryItem | null
  latestRaceSeason: number | null
}

function validTournaments(value: unknown, runId: string, branchId: string): value is ViewerTournamentHistory {
  if (!value || typeof value !== 'object') return false
  const data = value as Partial<ViewerTournamentHistory>
  if (data.schema_version !== 'viewer_tournament_history.v1' ||
      data.product_run_id !== runId || data.viewer_branch_id !== branchId ||
      !Array.isArray(data.tournaments) ||
      !whole(data.tournament_count, 0, Number.MAX_SAFE_INTEGER) ||
      !whole(data.published_result_count, 0, Number.MAX_SAFE_INTEGER) ||
      data.tournament_count !== data.tournaments.length) return false
  const ids = new Set<string>()
  let published = 0
  for (const event of data.tournaments) {
    if (!event || !isId(event.event_id) || ids.has(event.event_id) ||
        !isId(event.season) || !whole(event.season_week, 1, 61) ||
        typeof event.event_name !== 'string' ||
        typeof event.result_published !== 'boolean' ||
        (event.champion_player_id !== null && !isId(event.champion_player_id)) ||
        (event.finalist_player_id !== null && !isId(event.finalist_player_id)) ||
        // A publication is a canonical finished result: both distinct finalists
        // must be present before it can become the latest public Tournament.
        (event.result_published &&
          (!isId(event.champion_player_id) || !isId(event.finalist_player_id) ||
            event.champion_player_id === event.finalist_player_id)) ||
        (!event.result_published && (event.champion_player_id !== null || event.finalist_player_id !== null))) return false
    ids.add(event.event_id)
    if (event.result_published) published += 1
  }
  return published === data.published_result_count
}

// Use the same complete published-source validation as the detailed
// Ranking / Finals Race pages. An incomplete Race row must never appear
// as a verified historical publication on the public History hub.
export function verifiedSavedHistory(
  tournaments: unknown, rankings: unknown, race: unknown,
  runId: string, viewerBranchId: string
): SavedHistorySummary | null {
  if (!isId(runId) || !isId(viewerBranchId) ||
      !validTournaments(tournaments, runId, viewerBranchId) ||
      !validRankingHistory(rankings, runId, viewerBranchId) ||
      !validViewerRaceHistory(race, runId, viewerBranchId)) return null

  const completed = tournaments.tournaments.filter(event => event.result_published)
  const latestTournament = [...completed].sort((a, b) =>
    b.season.localeCompare(a.season, undefined, { numeric: true }) ||
    b.season_week - a.season_week ||
    b.event_id.localeCompare(a.event_id))[0] ?? null
  const latestRanking = [...rankings.publications]
    .sort((a, b) => b.week_ordinal - a.week_ordinal)[0] ?? null

  return {
    tournamentCount: tournaments.tournament_count,
    publishedTournamentCount: tournaments.published_result_count,
    rankingCount: rankings.publication_count,
    raceCount: race.publications.length,
    lastTournament: latestTournament,
    lastRanking: latestRanking,
    latestRaceSeason: race.latest_target_season_index
  }
}

export function rankingSeasonLabel(seasonIndex: number): string {
  const start = 2000 + seasonIndex
  return String(start) + '/' + String((start + 1) % 100).padStart(2, '0')
}
