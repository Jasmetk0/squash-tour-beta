import type {
  ViewerFinalsRacePublication, ViewerOfficialRankingHistoryItem,
  ViewerTournamentHistory, ViewerTournamentHistoryItem,
} from '../../api/types'
import { validViewerRaceHistory } from './rankings/finalsRaceBrowsing'
import { validRankingHistory } from './rankings/rankingHistoryBrowsing'

// Home has only the published history projection, not a calendar-to-edition
// join. Never claim this read model proves every result's separate calendar.
const id = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0
const whole = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
const nullableId = (value: unknown): value is string | null =>
  value === null || id(value)

export function verifiedHomeTournamentHistory(
  source: unknown, runId: string, branchId: string,
): ViewerTournamentHistory | null {
  if (!id(runId) || !id(branchId) || !source || typeof source !== 'object') return null
  const data = source as Partial<ViewerTournamentHistory>
  if (data.schema_version !== 'viewer_tournament_history.v1' ||
      data.product_run_id !== runId || data.viewer_branch_id !== branchId ||
      !whole(data.tournament_count) || !whole(data.published_result_count) ||
      data.published_result_count > data.tournament_count ||
      !Array.isArray(data.tournaments) || data.tournaments.length !== data.tournament_count) return null

  const seen = new Set<string>()
  let published = 0
  for (const event of data.tournaments) {
    if (!event || !id(event.event_id) || seen.has(event.event_id) ||
        !id(event.season) || !whole(event.season_week) ||
        event.season_week < 1 || event.season_week > 61 ||
        typeof event.event_name !== 'string' || !id(event.template_id) ||
        typeof event.category !== 'string' ||
        (event.tour_level !== null && typeof event.tour_level !== 'string') ||
        !id(event.host_country) || event.host_country.length !== 3 ||
        (event.host_city !== null && typeof event.host_city !== 'string') ||
        !id(event.region) ||
        !whole(event.main_draw_size) || !whole(event.qualification_draw_size) ||
        !whole(event.seeds_count) || !whole(event.qualifier_spots) ||
        !whole(event.wild_cards) || !whole(event.byes) ||
        typeof event.ranking_status !== 'string' ||
        typeof event.result_published !== 'boolean' ||
        !nullableId(event.champion_player_id) || !nullableId(event.finalist_player_id) ||
        (event.result_published &&
          (!id(event.champion_player_id) || !id(event.finalist_player_id) ||
            event.champion_player_id === event.finalist_player_id)) ||
        (!event.result_published &&
          (event.champion_player_id !== null || event.finalist_player_id !== null))) return null
    seen.add(event.event_id)
    if (event.result_published) published++
  }
  return published === data.published_result_count ? data as ViewerTournamentHistory : null
}

export type VerifiedHomeSources = {
  tournaments: ViewerTournamentHistory
  publishedTournaments: ViewerTournamentHistoryItem[]
  latestPublishedTournament: ViewerTournamentHistoryItem | null
  rankingPublicationCount: number
  latestRankingPublication: ViewerOfficialRankingHistoryItem | null
  racePublicationCount: number
  latestRacePublication: ViewerFinalsRacePublication | null
}

function tournamentOrder(a: ViewerTournamentHistoryItem, b: ViewerTournamentHistoryItem): number {
  return a.season.localeCompare(b.season, undefined, { numeric: true }) ||
    a.season_week - b.season_week ||
    a.event_id.localeCompare(b.event_id)
}

/** Fail closed unless all three independent public sources agree. */
export function verifiedHomeSources(
  tournaments: unknown, rankings: unknown, race: unknown,
  runId: string, branchId: string,
): VerifiedHomeSources | null {
  const history = verifiedHomeTournamentHistory(tournaments, runId, branchId)
  if (!history ||
      !validRankingHistory(rankings, runId, branchId) ||
      !validViewerRaceHistory(race, runId, branchId)) return null
  const publishedTournaments = history.tournaments
    .filter(event => event.result_published)
    .sort(tournamentOrder)
  const ranked = [...rankings.publications].sort((a, b) => b.week_ordinal - a.week_ordinal)
  const latestRacePublication = race.latest_target_season_index === null
    ? null
    : race.publications.find(item =>
      item.target_season_index === race.latest_target_season_index) ?? null
  return {
    tournaments: history,
    publishedTournaments,
    latestPublishedTournament: publishedTournaments.length ? publishedTournaments[publishedTournaments.length - 1] : null,
    rankingPublicationCount: rankings.publication_count,
    latestRankingPublication: ranked[0] ?? null,
    racePublicationCount: race.publications.length,
    latestRacePublication,
  }
}
