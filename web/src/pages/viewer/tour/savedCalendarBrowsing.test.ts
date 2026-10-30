import { describe, expect, it } from 'vitest'
import type { ViewerCalendarEvent, ViewerRunCalendar } from '../../../api/types'
import {
  filterSavedCalendarEvents, parseSavedCalendarPage, savedCalendarSeasonsNewestFirst,
  savedCalendarViewerBranch, savedCalendarWeeks, verifiedSavedSeasonCalendar
} from './savedCalendarBrowsing'

function event(id: string, season: string | number = '2005/06', week = 5): ViewerCalendarEvent {
  return {
    event_id: id, season, season_week: week,
    calendar_year: 2005, year_week: 45, template_id: 'template-' + id,
    event_name: 'Open ' + id, category: 'GOLD',
    tour_level: 'WORLD_TOUR', host_country: 'CZE', host_city: 'Brno', region: 'EUROPE',
    duration_in_season_weeks: 1, start_season_week: week, end_season_week: week,
    status: 'planned', main_draw_size: 32, qualification_draw_size: 16,
    seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 50
  }
}

function calendar(events: ViewerCalendarEvent[] = [event('E1')], run = 'run A', branch = 'branch A'): ViewerRunCalendar {
  const map = new Map<string, ViewerCalendarEvent[]>()
  for (const item of events) {
    const key = String(item.season)
    map.set(key, [...(map.get(key) ?? []), item])
  }
  return {
    schema_version: 'viewer_run_calendar.v1', product_run_id: run, viewer_branch_id: branch,
    season_count: map.size, event_count: events.length,
    seasons: [...map.entries()].map(([season, rows]) => ({ season, event_count: rows.length, events: rows }))
  }
}

const verified = (value: unknown) => verifiedSavedSeasonCalendar(value, 'run A', 'branch A')

describe('Saved Calendar V1 viewer source and filter contract', () => {
  it('resolves the exact saved Viewer Branch, not any other Run', () => {
    expect(savedCalendarViewerBranch({ product_run_id: 'run A', official_branch_id: 'branch A' }, 'run A')).toBe('branch A')
    expect(savedCalendarViewerBranch({ product_run_id: 'run B', official_branch_id: 'branch A' }, 'run A')).toBeNull()
    expect(savedCalendarViewerBranch({ product_run_id: 'run A', official_branch_id: ' ' }, 'run A')).toBeNull()
    expect(savedCalendarViewerBranch(null, 'run A')).toBeNull()
  })

  it('accepts valid empty calendars and valid W61 saved event projections', () => {
    expect(verified(calendar([]))).toEqual({ seasons: [], events: [], eventCount: 0 })
    const c = calendar([event('E1', '2005/06', 61)])
    expect(verified(c)).toMatchObject({ seasons: ['2005/06'], eventCount: 1 })
    expect(verified(calendar([event('E1', 2005)]))).toMatchObject({ seasons: ['2005'] })
  })

  it('rejects wrong scopes, unknown schema, invalid counts and missing data', () => {
    const c = calendar()
    for (const value of [
      { ...c, product_run_id: 'other' },
      { ...c, viewer_branch_id: 'other' },
      { ...c, schema_version: 'viewer_run_calendar.v2' },
      { ...c, event_count: -1 },
      { ...c, season_count: 2 },
      { ...c, event_count: 2 },
      { ...c, seasons: null },
      { ...c, seasons: [{ ...c.seasons[0], event_count: 0 }] },
      null
    ]) expect(verified(value)).toBeNull()
  })

  it('rejects duplicate seasons, duplicate event IDs and impossible clock/status evidence', () => {
    const one = event('E1')
    const c = calendar([one])
    for (const value of [
      { ...c, season_count: 2, event_count: 2, seasons: [c.seasons[0], c.seasons[0]] },
      { ...c, event_count: 2, seasons: [{ ...c.seasons[0], event_count: 2, events: [one, one] }] },
      { ...c, seasons: [{ ...c.seasons[0], events: [{ ...one, season: 'other' }] }] },
      { ...c, seasons: [{ ...c.seasons[0], events: [{ ...one, season_week: 62 }] }] },
      { ...c, seasons: [{ ...c.seasons[0], events: [{ ...one, start_season_week: 62 }] }] },
      { ...c, seasons: [{ ...c.seasons[0], events: [{ ...one, year_week: 62 }] }] },
      { ...c, seasons: [{ ...c.seasons[0], events: [{ ...one, event_id: ' ' }] }] },
      { ...c, seasons: [{ ...c.seasons[0], events: [{ ...one, status: 'not-real' }] }] },
      { ...c, seasons: [{ ...c.seasons[0], events: [{ ...one, end_season_week: 4 }] }] },
      { ...c, seasons: [{ ...c.seasons[0], events: [{ ...one, prestige: -1 }] }] }
    ]) expect(verified(value)).toBeNull()
  })

  it('sorts seasons, filters actual saved weeks, locations and status without changing source data', () => {
    const rows = [
      event('A', '2004/05', 12),
      event('B', '2005/06', 9),
      { ...event('C', '2005/06', 3), host_city: 'Praha', status: 'completed' as const },
      event('D', '2004/05', 12)
    ]
    const source = calendar(rows)
    const result = verified(source)
    expect(result).not.toBeNull()
    if (!result) return
    expect(savedCalendarSeasonsNewestFirst(result)).toEqual(['2005/06', '2004/05'])
    expect(savedCalendarWeeks(result, '2004/05')).toEqual([12])
    expect(savedCalendarWeeks(result, 'all')).toEqual([3, 9, 12])
    expect(filterSavedCalendarEvents(result, 'all', 'all', 'all', '').map(x => x.event_id))
      .toEqual(['C', 'B', 'A', 'D'])
    expect(filterSavedCalendarEvents(result, '2005/06', '3', 'completed', 'prAHa').map(x => x.event_id))
      .toEqual(['C'])
    expect(filterSavedCalendarEvents(result, '2005/06', '9', 'completed', '')).toEqual([])
    expect(source.seasons.map(x => String(x.season))).toEqual(['2004/05', '2005/06'])
  })

  it('only accepts safe bounded page jumps', () => {
    expect(parseSavedCalendarPage(' 2 ', 3)).toBe(2)
    for (const invalid of ['', '0', '01', '-1', '2.0', '2e0', '4', '999999999999999999999']) {
      expect(parseSavedCalendarPage(invalid, 3)).toBeNull()
    }
  })
})
