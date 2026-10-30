import { describe, expect, it } from 'vitest'
import type { ViewerCalendarEvent, ViewerRunCalendar, ViewerTournamentHistoryItem, ViewerTournamentHistory } from '../../../api/types'
import {
  catalogSeasonsNewestFirst, filteredSavedTournaments, parseTournamentPage,
  tournamentViewerBranch, verifiedTournamentCatalog
} from './viewerTournamentCatalog'

function event(id: string, season: string | number = '2031/32', week = 4): ViewerCalendarEvent {
  return {
    event_id: id, season, season_week: week, calendar_year: 2031, year_week: 40,
    template_id: 'test-' + id, event_name: 'Open ' + id, category: 'Gold',
    tour_level: 'WORLD_TOUR', host_country: 'CZE', host_city: 'Brno', region: 'Europe',
    duration_in_season_weeks: 1, start_season_week: week, end_season_week: week,
    status: 'planned', main_draw_size: 32, qualification_draw_size: 16,
    seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 70
  }
}
function historyItem(e: ViewerCalendarEvent, published = false): ViewerTournamentHistoryItem {
  return {
    event_id: e.event_id, season: String(e.season), season_week: e.season_week,
    template_id: e.template_id, event_name: e.event_name,
    category: e.category, tour_level: e.tour_level, host_country: e.host_country,
    host_city: e.host_city, region: e.region, main_draw_size: e.main_draw_size,
    qualification_draw_size: e.qualification_draw_size, seeds_count: e.seeds_count,
    qualifier_spots: e.qualifier_spots, wild_cards: e.wild_cards, byes: e.byes,
    ranking_status: published ? 'ranked' : 'planned', result_published: published,
    champion_player_id: published ? 'champion ' + e.event_id : null,
    finalist_player_id: published ? 'finalist ' + e.event_id : null
  }
}
function source(events: ViewerCalendarEvent[], publishedIds: string[] = [], runId = 'run a', branch = 'branch a') {
  const groups = new Map<string, ViewerCalendarEvent[]>()
  for (const value of events) {
    const key = String(value.season)
    groups.set(key, [...(groups.get(key) ?? []), value])
  }
  const calendar: ViewerRunCalendar = {
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: runId, viewer_branch_id: branch,
    season_count: groups.size, event_count: events.length,
    seasons: Array.from(groups, ([season, items]) => ({ season, event_count: items.length, events: items }))
  }
  const history: ViewerTournamentHistory = {
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: runId, viewer_branch_id: branch,
    tournament_count: events.length, published_result_count: publishedIds.length,
    tournaments: events.map(e => historyItem(e, publishedIds.includes(e.event_id)))
  }
  return { calendar, history }
}

describe('verified Saved Tournament Catalog (legacy V1)', () => {
  it('accepts exact empty and populated calendar/history evidence', () => {
    const empty = source([])
    expect(verifiedTournamentCatalog(empty.calendar, empty.history, 'run a', 'branch a')).toEqual({
      seasons: [], entries: [], eventCount: 0, publishedCount: 0
    })
    const e = event('EVT 1')
    const full = source([e], ['EVT 1'])
    expect(verifiedTournamentCatalog(full.calendar, full.history, 'run a', 'branch a')).toMatchObject({
      eventCount: 1, publishedCount: 1,
      entries: [{ event: { event_id: 'EVT 1' }, publication: { result_published: true } }]
    })
    expect(tournamentViewerBranch({ product_run_id: 'run a', official_branch_id: 'branch a' }, 'run a')).toBe('branch a')
    expect(tournamentViewerBranch({ product_run_id: 'other', official_branch_id: 'branch a' }, 'run a')).toBeNull()
    expect(tournamentViewerBranch({ product_run_id: 'run a', official_branch_id: '  ' }, 'run a')).toBeNull()
  })
  it('rejects foreign Run, wrong Branch, mismatched counts and unpaired events', () => {
    const e = event('E1')
    const { calendar: c, history: h } = source([e], ['E1'])
    const valid = (a: unknown, d: unknown) => verifiedTournamentCatalog(a, d, 'run a', 'branch a')
    expect(valid({ ...c, viewer_branch_id: 'other' }, h)).toBeNull()
    expect(valid(c, { ...h, viewer_branch_id: 'other' })).toBeNull()
    expect(valid({ ...c, product_run_id: 'other' }, h)).toBeNull()
    expect(valid(c, { ...h, product_run_id: 'other' })).toBeNull()
    expect(valid({ ...c, schema_version: 'other' }, h)).toBeNull()
    expect(valid(c, { ...h, schema_version: 'other' })).toBeNull()
    expect(valid({ ...c, event_count: 2 }, h)).toBeNull()
    expect(valid(c, { ...h, tournament_count: 2 })).toBeNull()
    expect(valid(c, { ...h, published_result_count: 0 })).toBeNull()
    expect(valid(c, { ...h, tournaments: [{ ...h.tournaments[0], event_id: 'foreign' }] })).toBeNull()
    expect(valid(c, { ...h, tournaments: [{ ...h.tournaments[0], season_week: 5 }] })).toBeNull()
    expect(valid(c, { ...h, tournaments: [{ ...h.tournaments[0], template_id: 'foreign' }] })).toBeNull()
    expect(valid(c, { ...h, tournaments: [{ ...h.tournaments[0], result_published: false }] })).toBeNull()
  })
  it('rejects duplicates, season identity changes, invalid legacy weeks and malformed publication fields', () => {
    const e = event('A')
    const { calendar: c, history: h } = source([e])
    const valid = (a: unknown, d: unknown) => verifiedTournamentCatalog(a, d, 'run a', 'branch a')
    expect(valid({ ...c, seasons: [{ ...c.seasons[0], event_count: 2, events: [e, e] }], event_count: 2 }, h)).toBeNull()
    expect(valid({ ...c, seasons: [{ ...c.seasons[0], events: [{ ...e, season: 'different' }] }] }, h)).toBeNull()
    expect(valid({ ...c, seasons: [c.seasons[0], c.seasons[0]], season_count: 2, event_count: 2 }, h)).toBeNull()
    expect(valid({ ...c, seasons: [{ ...c.seasons[0], events: [{ ...e, season_week: 62 }] }] }, h)).toBeNull()
    expect(valid(c, { ...h, tournaments: [{ ...h.tournaments[0], event_id: '' }] })).toBeNull()
    expect(valid(c, { ...h, tournaments: [{ ...h.tournaments[0], season: 'different' }] })).toBeNull()
  })
  it('filters all seasons, actual published results and full-text IDs/locations without altering source order', () => {
    const e1 = event('Gold 1', '2000/01', 4)
    const e2 = event('Silver 2', '2001/02', 1)
    const e3 = { ...event('Bronze 3', 2001, 6), host_city: 'Praha' }
    const raw = source([e2, e1, e3], ['Silver 2'])
    const catalog = verifiedTournamentCatalog(raw.calendar, raw.history, 'run a', 'branch a')
    expect(catalog).not.toBeNull()
    if (!catalog) return
    expect(catalogSeasonsNewestFirst(catalog)).toEqual(['2001/02', '2001', '2000/01'])
    expect(filteredSavedTournaments(catalog, 'all', '', 'all').map(item => item.event.event_id))
      .toEqual(['Silver 2', 'Bronze 3', 'Gold 1'])
    expect(filteredSavedTournaments(catalog, '2001/02', '', 'all')).toHaveLength(1)
    expect(filteredSavedTournaments(catalog, 'all', '', 'published').map(item => item.event.event_id)).toEqual(['Silver 2'])
    expect(filteredSavedTournaments(catalog, 'all', ' praHA ', 'all').map(item => item.event.event_id)).toEqual(['Bronze 3'])
    expect(filteredSavedTournaments(catalog, 'all', 'GOLD 1', 'unpublished').map(item => item.event.event_id)).toEqual(['Gold 1'])
  })
  it('accepts only bounded page numbers', () => {
    expect(parseTournamentPage(' 2 ', 10)).toBe(2)
    for (const bad of ['', '0', '01', '-1', '2.0', '2e0', '11', '999999999999999999999']) {
      expect(parseTournamentPage(bad, 10)).toBeNull()
    }
  })
})
