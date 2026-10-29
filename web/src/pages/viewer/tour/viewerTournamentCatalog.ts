import type { ViewerCalendarEvent, ViewerRunCalendar, ViewerTournamentHistory, ViewerTournamentHistoryItem } from '../../../api/types'

// This is the existing viewer_run_calendar.v1 / viewer_tournament_history.v1
// legacy W61 projection; calendar-native W52/W80 data needs a versioned adapter.
const whole = (value: unknown, min = 0, max = Number.MAX_SAFE_INTEGER): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= min && value <= max
const nonempty = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0
const seasonKey = (value: unknown): string | null =>
  (typeof value === 'string' && value.trim().length > 0) ||
  (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0)
    ? String(value) : null

export type SavedTournamentEntry = {
  event: ViewerCalendarEvent
  publication: ViewerTournamentHistoryItem
}

export type SavedTournamentCatalog = {
  seasons: string[]
  entries: SavedTournamentEntry[]
  eventCount: number
  publishedCount: number
}

export function tournamentViewerBranch(context: unknown, runId: string): string | null {
  if (!context || typeof context !== 'object' || !nonempty(runId)) return null
  const value = context as { product_run_id?: unknown; official_branch_id?: unknown }
  return value.product_run_id === runId && nonempty(value.official_branch_id)
    ? value.official_branch_id : null
}

export function verifiedTournamentCatalog(
  calendar: unknown, history: unknown, runId: string, branchId: string
): SavedTournamentCatalog | null {
  if (!nonempty(runId) || !nonempty(branchId) ||
      !calendar || typeof calendar !== 'object' ||
      !history || typeof history !== 'object') return null
  const c = calendar as Partial<ViewerRunCalendar>
  const h = history as Partial<ViewerTournamentHistory>
  if (c.schema_version !== 'viewer_run_calendar.v1' ||
      h.schema_version !== 'viewer_tournament_history.v1' ||
      c.product_run_id !== runId || h.product_run_id !== runId ||
      c.viewer_branch_id !== branchId || h.viewer_branch_id !== branchId ||
      !Array.isArray(c.seasons) || !Array.isArray(h.tournaments) ||
      !whole(c.season_count) || c.season_count !== c.seasons.length ||
      !whole(c.event_count) || !whole(h.tournament_count) ||
      !whole(h.published_result_count) ||
      c.event_count !== h.tournament_count ||
      h.tournament_count !== h.tournaments.length) return null

  const byEvent = new Map<string, ViewerCalendarEvent>()
  const seasons: string[] = []
  const seenSeasons = new Set<string>()
  for (const season of c.seasons) {
    if (!season || typeof season !== 'object') return null
    const key = seasonKey(season.season)
    if (key === null || seenSeasons.has(key) ||
        !Array.isArray(season.events) || !whole(season.event_count) ||
        season.event_count !== season.events.length) return null
    seenSeasons.add(key)
    seasons.push(key)
    for (const event of season.events) {
      if (!event || !nonempty(event.event_id) || byEvent.has(event.event_id) ||
          seasonKey(event.season) !== key ||
          !whole(event.season_week, 1, 61) ||
          !nonempty(event.template_id) ||
          typeof event.event_name !== 'string' ||
          typeof event.category !== 'string' ||
          typeof event.status !== 'string' ||
          !['planned', 'active', 'completed', 'cancelled', 'scheduled'].includes(event.status)) return null
      byEvent.set(event.event_id, event)
    }
  }
  if (byEvent.size !== c.event_count) return null

  const matched = new Set<string>()
  const entries: SavedTournamentEntry[] = []
  let publishedCount = 0
  for (const item of h.tournaments) {
    if (!item || !nonempty(item.event_id) || matched.has(item.event_id) ||
        !nonempty(item.season) || !whole(item.season_week, 1, 61) ||
        typeof item.result_published !== 'boolean' ||
        (item.champion_player_id !== null && !nonempty(item.champion_player_id)) ||
        (item.finalist_player_id !== null && !nonempty(item.finalist_player_id)) ||
        (!item.result_published && (item.champion_player_id !== null || item.finalist_player_id !== null))) return null
    const event = byEvent.get(item.event_id)
    if (!event || item.season !== String(event.season) ||
        item.season_week !== event.season_week ||
        item.event_name !== event.event_name ||
        item.template_id !== event.template_id ||
        item.category !== event.category ||
        item.tour_level !== event.tour_level ||
        item.host_country !== event.host_country) return null
    matched.add(item.event_id)
    if (item.result_published) publishedCount++
    entries.push({ event, publication: item })
  }
  if (matched.size !== byEvent.size || publishedCount !== h.published_result_count) return null

  return { seasons, entries, eventCount: c.event_count, publishedCount }
}

function compareSeason(a: string, b: string): number {
  const aYear = Number.parseInt(a.split('/')[0], 10)
  const bYear = Number.parseInt(b.split('/')[0], 10)
  if (Number.isFinite(aYear) && Number.isFinite(bYear) && aYear !== bYear) return aYear - bYear
  return a.localeCompare(b, undefined, { numeric: true })
}

export function catalogSeasonsNewestFirst(catalog: SavedTournamentCatalog): string[] {
  return [...catalog.seasons].sort((a, b) => compareSeason(b, a))
}

export type TournamentPublicationFilter = 'all' | 'published' | 'unpublished'

export function filteredSavedTournaments(
  catalog: SavedTournamentCatalog, season: string, query: string, filter: TournamentPublicationFilter
): SavedTournamentEntry[] {
  const needle = query.trim().toLocaleLowerCase()
  return catalog.entries.filter(({ event, publication }) =>
    (season === 'all' || String(event.season) === season) &&
    (filter === 'all' || publication.result_published === (filter === 'published')) &&
    (!needle || [event.event_name, event.event_id, event.host_country, event.host_city ?? '']
      .some(value => value.toLocaleLowerCase().includes(needle)))
  ).sort((a, b) =>
    compareSeason(b.event.season.toString(), a.event.season.toString()) ||
    a.event.season_week - b.event.season_week ||
    a.event.event_id.localeCompare(b.event.event_id)
  )
}

export const TOURNAMENT_PAGE_SIZE = 25
export function parseTournamentPage(input: string, maxPages: number): number | null {
  const value = input.trim()
  if (!/^[1-9]\d*$/.test(value)) return null
  const page = Number(value)
  return Number.isSafeInteger(page) && page <= maxPages ? page : null
}
