import type { ViewerCalendarEvent, ViewerTournamentHistoryItem } from '../../../api/types'
import { compareTournamentHistoryEvents, compareTournamentSeasons, tournamentMatchesSearch, verifiedTournamentHistory } from './viewerTournamentHistoryBrowsing'

import { verifiedSavedSeasonCalendar } from './savedCalendarBrowsing'

// This is the existing viewer_run_calendar.v1 / viewer_tournament_history.v1
// legacy W61 projection; calendar-native W52/W80 data needs a versioned adapter.
const nonempty = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0

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
  const c = verifiedSavedSeasonCalendar(calendar, runId, branchId)
  const h = verifiedTournamentHistory(history, runId, branchId)
  if (!c || !h || c.eventCount !== h.tournament_count) return null

  // One Calendar v1 shape/clock validator for every consuming view. History
  // also requires a nonblank region and host code for its joined metadata.
  const byEvent = new Map<string, ViewerCalendarEvent>()
  for (const event of c.events) {
    if (!nonempty(event.host_country) || !nonempty(event.region)) return null
    byEvent.set(event.event_id, event)
  }

  const matched = new Set<string>()
  const entries: SavedTournamentEntry[] = []
  let publishedCount = 0
  for (const item of h.tournaments) {
    if (matched.has(item.event_id)) return null
    const event = byEvent.get(item.event_id)
    if (!event || item.season !== String(event.season) ||
        item.season_week !== event.season_week ||
        item.event_name !== event.event_name ||
        item.template_id !== event.template_id ||
        item.category !== event.category ||
        item.tour_level !== event.tour_level ||
        item.host_country !== event.host_country ||
        // These are copied from one canonical Calendar projection. A partial
        // metadata match cannot prove that two responses describe the same
        // Saved Edition (e.g. mismatched draw capacities or host city).
        item.host_city !== event.host_city || item.region !== event.region ||
        item.main_draw_size !== event.main_draw_size ||
        item.qualification_draw_size !== event.qualification_draw_size ||
        item.seeds_count !== event.seeds_count ||
        item.qualifier_spots !== event.qualifier_spots ||
        item.wild_cards !== event.wild_cards ||
        item.byes !== event.byes) return null
    matched.add(item.event_id)
    if (item.result_published) publishedCount++
    entries.push({ event, publication: item })
  }
  if (matched.size !== byEvent.size || publishedCount !== h.published_result_count) return null

  return { seasons: c.seasons, entries, eventCount: c.eventCount, publishedCount }
}

export function catalogSeasonsNewestFirst(catalog: SavedTournamentCatalog): string[] {
  return [...catalog.seasons].sort((a, b) => compareTournamentSeasons(b, a))
}

export type TournamentPublicationFilter = 'all' | 'published' | 'unpublished'

export function filteredSavedTournaments(
  catalog: SavedTournamentCatalog, season: string, query: string, filter: TournamentPublicationFilter
): SavedTournamentEntry[] {
  const needle = query.trim().toLocaleLowerCase()
  return catalog.entries.filter(({ event, publication }) =>
    (season === 'all' || String(event.season) === season) &&
    (filter === 'all' || publication.result_published === (filter === 'published')) &&
    tournamentMatchesSearch(publication, needle)
  ).sort((a, b) => compareTournamentHistoryEvents(a.publication, b.publication))
}

export const TOURNAMENT_PAGE_SIZE = 25
export function parseTournamentPage(input: string, maxPages: number): number | null {
  const value = input.trim()
  if (!/^[1-9]\d*$/.test(value)) return null
  const page = Number(value)
  return Number.isSafeInteger(page) && page <= maxPages ? page : null
}
