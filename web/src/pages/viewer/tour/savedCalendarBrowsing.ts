import type { ViewerCalendarEvent, ViewerRunCalendar } from '../../../api/types'

// viewer_run_calendar.v1 is the existing legacy W61 read model. A future
// calendar-native W52/W80 projection requires its own versioned contract.
const whole = (value: unknown, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) &&
  value >= minimum && value <= maximum
const nonEmpty = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0

export function savedCalendarSeasonKey(value: unknown): string | null {
  if (nonEmpty(value)) return value
  return whole(value) ? String(value) : null
}

export function savedCalendarViewerBranch(context: unknown, runId: string): string | null {
  if (!nonEmpty(runId) || !context || typeof context !== 'object') return null
  const record = context as { product_run_id?: unknown; official_branch_id?: unknown }
  return record.product_run_id === runId && nonEmpty(record.official_branch_id)
    ? record.official_branch_id : null
}

export type SavedSeasonCalendar = {
  seasons: string[]
  events: ViewerCalendarEvent[]
  eventCount: number
}

export function verifiedSavedSeasonCalendar(
  data: unknown, runId: string, branchId: string
): SavedSeasonCalendar | null {
  if (!data || typeof data !== 'object' || !nonEmpty(runId) || !nonEmpty(branchId)) return null
  const value = data as Partial<ViewerRunCalendar>
  if (
    value.schema_version !== 'viewer_run_calendar.v1' ||
    value.product_run_id !== runId || value.viewer_branch_id !== branchId ||
    !whole(value.season_count) || !whole(value.event_count) ||
    !Array.isArray(value.seasons) || value.season_count !== value.seasons.length
  ) return null

  const seasons: string[] = []
  const all: ViewerCalendarEvent[] = []
  const seasonKeys = new Set<string>()
  const eventIds = new Set<string>()
  for (const season of value.seasons) {
    if (!season || typeof season !== 'object') return null
    const key = savedCalendarSeasonKey(season.season)
    if (key === null || seasonKeys.has(key) || !whole(season.event_count) ||
        !Array.isArray(season.events) || season.event_count !== season.events.length) return null
    seasonKeys.add(key)
    seasons.push(key)
    for (const event of season.events) {
      if (!event || !nonEmpty(event.event_id) || eventIds.has(event.event_id) ||
          savedCalendarSeasonKey(event.season) !== key ||
          !whole(event.season_week, 1, 61) ||
          !whole(event.start_season_week, 1, 61) ||
          !whole(event.end_season_week, 1) ||
          !whole(event.duration_in_season_weeks, 1) ||
          event.end_season_week < event.start_season_week ||
          (event.year_week !== null && !whole(event.year_week, 1, 61)) ||
          (event.calendar_year !== null && !whole(event.calendar_year)) ||
          !nonEmpty(event.template_id) ||
          typeof event.event_name !== 'string' ||
          typeof event.category !== 'string' ||
          !nonEmpty(event.host_country) ||
          (event.host_city !== null && typeof event.host_city !== 'string') ||
          (event.tour_level !== null && event.tour_level !== 'WORLD_TOUR' &&
            event.tour_level !== 'ELITE_TOUR') ||
          !['planned', 'active', 'completed', 'cancelled', 'scheduled'].includes(event.status) ||
          typeof event.prestige !== 'number' || !Number.isFinite(event.prestige) || event.prestige < 0
      ) return null
      eventIds.add(event.event_id)
      all.push(event)
    }
  }
  if (all.length !== value.event_count) return null
  return { seasons, events: all, eventCount: all.length }
}

function seasonOrder(a: string, b: string): number {
  const aStart = Number(a.split('/')[0])
  const bStart = Number(b.split('/')[0])
  if (Number.isFinite(aStart) && Number.isFinite(bStart) && aStart !== bStart)
    return aStart - bStart
  return a.localeCompare(b, undefined, { numeric: true })
}

export function savedCalendarSeasonsNewestFirst(calendar: SavedSeasonCalendar): string[] {
  return [...calendar.seasons].sort((a, b) => seasonOrder(b, a))
}

export type SavedCalendarStatus = 'all' | 'planned' | 'scheduled' | 'active' | 'completed' | 'cancelled'

export function savedCalendarWeeks(calendar: SavedSeasonCalendar, season: string): number[] {
  const unique = new Set(
    calendar.events.filter(event => season === 'all' || savedCalendarSeasonKey(event.season) === season)
      .map(event => event.season_week)
  )
  return [...unique].sort((a, b) => a - b)
}

export function filterSavedCalendarEvents(
  calendar: SavedSeasonCalendar,
  season: string, week: string, status: SavedCalendarStatus, search: string
): ViewerCalendarEvent[] {
  const text = search.trim().toLocaleLowerCase()
  return calendar.events
    .filter(event =>
      (season === 'all' || savedCalendarSeasonKey(event.season) === season) &&
      (week === 'all' || String(event.season_week) === week) &&
      (status === 'all' || event.status === status) &&
      (!text || [event.event_id, event.event_name, event.host_country, event.host_city ?? '']
        .some(field => field.toLocaleLowerCase().includes(text)))
    )
    .sort((a, b) =>
      seasonOrder(String(b.season), String(a.season)) ||
      a.season_week - b.season_week ||
      a.event_id.localeCompare(b.event_id)
    )
}

export const SAVED_CALENDAR_PAGE_SIZE = 25
export function parseSavedCalendarPage(value: string, pages: number): number | null {
  const input = value.trim()
  if (!/^[1-9][0-9]*$/.test(input)) return null
  const page = Number(input)
  return Number.isSafeInteger(page) && page <= pages ? page : null
}
