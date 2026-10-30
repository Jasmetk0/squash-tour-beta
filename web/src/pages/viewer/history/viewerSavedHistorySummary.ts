import type {
  ViewerFinalsRaceHistory, ViewerOfficialRankingHistory, ViewerOfficialRankingHistoryItem,
  ViewerTournamentHistory, ViewerTournamentHistoryItem
} from '../../../api/types'

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
        typeof event.result_published !== 'boolean' ||
        (event.champion_player_id !== null && !isId(event.champion_player_id)) ||
        (event.finalist_player_id !== null && !isId(event.finalist_player_id)) ||
        (!event.result_published && (event.champion_player_id !== null || event.finalist_player_id !== null))) return false
    ids.add(event.event_id)
    if (event.result_published) published += 1
  }
  return published === data.published_result_count
}

function validRanking(value: unknown, runId: string, branchId: string): value is ViewerOfficialRankingHistory {
  if (!value || typeof value !== 'object') return false
  const data = value as Partial<ViewerOfficialRankingHistory>
  if (data.schema_version !== 'viewer_official_ranking_history.v1' ||
      data.product_run_id !== runId || data.viewer_branch_id !== branchId ||
      !Array.isArray(data.publications) ||
      !whole(data.public_head_ordinal, 0, 3049) ||
      data.publication_count !== data.publications.length) return false
  const ordinals = new Set<number>()
  for (const item of data.publications) {
    if (!item || !whole(item.season_index, 0, 49) ||
        !whole(item.week, 1, 61) || !whole(item.week_ordinal, 0, 3049) ||
        item.week_ordinal !== item.season_index * 61 + item.week - 1 ||
        item.week_ordinal > data.public_head_ordinal ||
        ordinals.has(item.week_ordinal) ||
        typeof item.snapshot_fingerprint !== 'string' ||
        !/^[a-f0-9]{64}$/.test(item.snapshot_fingerprint) ||
        typeof item.policy_id !== 'string' ||
        !whole(item.best_n, 1, Number.MAX_SAFE_INTEGER) ||
        !whole(item.row_count, 0, Number.MAX_SAFE_INTEGER)) return false
    ordinals.add(item.week_ordinal)
  }
  return data.publications.length === 0 || ordinals.has(data.public_head_ordinal)
}

function validRace(value: unknown, runId: string, branchId: string): value is ViewerFinalsRaceHistory {
  if (!value || typeof value !== 'object') return false
  const data = value as Partial<ViewerFinalsRaceHistory>
  if (data.schema_version !== 'viewer_finals_race_history.v1' ||
      data.product_run_id !== runId || data.viewer_branch_id !== branchId ||
      !Array.isArray(data.publications) ||
      (data.latest_target_season_index !== null && !whole(data.latest_target_season_index, 0, 49))) return false
  const seasons = new Set<number>()
  let max: number | null = null
  for (const item of data.publications) {
    if (!item || item.schema_version !== 'viewer_finals_race_publication.v1' ||
        item.product_run_id !== runId || item.viewer_branch_id !== branchId ||
        !whole(item.target_season_index, 0, 49) ||
        item.cutoff_season_index !== item.target_season_index ||
        !whole(item.cutoff_week, 1, 61) ||
        !whole(item.best_n, 1, Number.MAX_SAFE_INTEGER) ||
        typeof item.selection_published !== 'boolean' ||
        !Array.isArray(item.rows) ||
        seasons.has(item.target_season_index)) return false
    seasons.add(item.target_season_index)
    if (max === null || max < item.target_season_index) max = item.target_season_index
  }
  return max === data.latest_target_season_index
}

export function verifiedSavedHistory(
  tournaments: unknown, rankings: unknown, race: unknown,
  runId: string, viewerBranchId: string
): SavedHistorySummary | null {
  if (!isId(runId) || !isId(viewerBranchId) ||
      !validTournaments(tournaments, runId, viewerBranchId) ||
      !validRanking(rankings, runId, viewerBranchId) ||
      !validRace(race, runId, viewerBranchId)) return null

  const completed = tournaments.tournaments.filter(event => event.result_published)
  const latestTournament = [...completed].sort((a, b) =>
    b.season.localeCompare(a.season) || b.season_week - a.season_week ||
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
