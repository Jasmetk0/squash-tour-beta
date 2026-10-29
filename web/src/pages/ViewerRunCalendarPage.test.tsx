import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunCalendarPage, ViewerRunPlannedEventPage, ViewerRunWeekPage } from './ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  getViewerFinalsRace: vi.fn(),
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

function renderViewerCalendarRoute(route: string): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/calendar" element={<ViewerRunCalendarPage />} />
      <Route path="/viewer/runs/:runId/calendar/:eventId" element={<ViewerRunPlannedEventPage />} />
      <Route path="/viewer/runs/:runId/weeks/:week" element={<ViewerRunWeekPage />} />
    </Routes>,
    { route }
  )
}

function mockCanonicalData(eventWeek = 2): void {
  api.getViewerRunCalendar.mockResolvedValue({
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'viewer-run-2d',
    viewer_branch_id: 'branch-viewer',
    season_count: 2,
    event_count: 3,
    seasons: [
      {
        season: '2028/2029',
        event_count: 2,
        events: [
          {
            event_id: 'EVENT-COMPLETE',
            season: '2028/2029',
            season_week: 1,
            calendar_year: 2028,
            year_week: 40,
            template_id: 'WT-PLAT',
            event_name: 'Season Opener',
            category: 'PLATINUM',
            tour_level: 'WORLD_TOUR',
            host_country: 'EGY',
            host_city: 'Cairo',
            region: 'AFRICA',
            duration_in_season_weeks: 1,
            start_season_week: 1,
            end_season_week: 1,
            status: 'completed',
            main_draw_size: 32,
            qualification_draw_size: 16,
            seeds_count: 8,
            qualifier_spots: 4,
            wild_cards: 2,
            byes: 0,
            prestige: 9
          },
          {
            event_id: 'EVENT-NEXT',
            season: '2028/2029',
            season_week: eventWeek,
            calendar_year: 2028,
            year_week: 41,
            template_id: 'ET-GOLD',
            event_name: 'Gold Open',
            category: 'GOLD',
            tour_level: 'ELITE_TOUR',
            host_country: 'CZE',
            host_city: 'Prague',
            region: 'EUROPE',
            duration_in_season_weeks: 1,
            start_season_week: 2,
            end_season_week: 2,
            status: 'planned',
            main_draw_size: 16,
            qualification_draw_size: 8,
            seeds_count: 4,
            qualifier_spots: 4,
            wild_cards: 2,
            byes: 0,
            prestige: 7
          }
        ]
      },
      {
        season: '2029/2030',
        event_count: 1,
        events: [
          {
            event_id: 'EVENT-FUTURE',
            season: '2029/2030',
            season_week: 3,
            calendar_year: 2029,
            year_week: 42,
            template_id: 'WT-BRONZE',
            event_name: 'Future Bronze',
            category: 'BRONZE',
            tour_level: 'WORLD_TOUR',
            host_country: 'USA',
            host_city: null,
            region: 'AMERICAS',
            duration_in_season_weeks: 1,
            start_season_week: 3,
            end_season_week: 3,
            status: 'planned',
            main_draw_size: 8,
            qualification_draw_size: 0,
            seeds_count: 2,
            qualifier_spots: 0,
            wild_cards: 1,
            byes: 0,
            prestige: 4
          }
        ]
      }
    ]
  })

  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'viewer-run-2d',
    viewer_branch_id: 'branch-viewer',
    tournament_count: 3,
    published_result_count: 1,
    tournaments: [
      {
        event_id: 'EVENT-COMPLETE',
        season: '2028/2029',
        season_week: 1,
        event_name: 'Season Opener',
        template_id: 'WT-PLAT',
        category: 'PLATINUM',
        tour_level: 'WORLD_TOUR',
        host_country: 'EGY',
        host_city: 'Cairo',
        region: 'AFRICA',
        main_draw_size: 32,
        qualification_draw_size: 16,
        seeds_count: 8,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: true,
        champion_player_id: 'PLAYER-42',
        finalist_player_id: 'PLAYER-99'
      },
      {
        event_id: 'EVENT-NEXT',
        season: '2028/2029',
        season_week: 2,
        event_name: 'Gold Open',
        template_id: 'ET-GOLD',
        category: 'GOLD',
        tour_level: 'ELITE_TOUR',
        host_country: 'CZE',
        host_city: 'Prague',
        region: 'EUROPE',
        main_draw_size: 16,
        qualification_draw_size: 8,
        seeds_count: 4,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: false,
        champion_player_id: null,
        finalist_player_id: null
      }
    ]
  })

  api.listViewerOfficialRankingHistory.mockResolvedValue({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'viewer-run-2d',
    viewer_branch_id: 'branch-viewer',
    public_head_ordinal: 4,
    publication_count: 1,
    publications: [
      {
        season_index: 28,
        week: 2,
        week_ordinal: 4,
        snapshot_fingerprint: 'a'.repeat(64),
        policy_id: 'best-15',
        best_n: 15,
        row_count: 48
      }
    ]
  })

  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'viewer-run-2d',
    viewer_branch_id: 'branch-viewer',
    latest_target_season_index: 28,
    publications: [
      {
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'viewer-run-2d',
        viewer_branch_id: 'branch-viewer',
        target_season_index: 28,
        cutoff_season_index: 28,
        cutoff_week: 2,
        best_n: 8,
        selection_published: false,
        finals_event_id: null,
        rows: []
      },
      {
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'viewer-run-2d',
        viewer_branch_id: 'branch-viewer',
        target_season_index: 29,
        cutoff_season_index: 29,
        cutoff_week: 3,
        best_n: 8,
        selection_published: false,
        finals_event_id: null,
        rows: []
      }
    ]
  })
}

function expectNoForbiddenViewerActions(): void {
  const forbidden = /^(Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)$/i
  for (const element of [...screen.queryAllByRole('button'), ...screen.queryAllByRole('link')]) {
    expect(forbidden.test(element.textContent?.trim() ?? '')).toBe(false)
  }
}

describe('Viewer canonical Saved Calendar surfaces', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCanonicalData()
  })

  it('renders Season Calendar directly from viewer_run_calendar.v1', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-2d')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('viewer-run-2d')

    const season = await screen.findByRole('list', { name: 'Viewer season calendar events 2028/2029' })
    const opener = within(season).getByText('Season Opener').closest('li') as HTMLElement
    expect(within(opener).getByText('Completed · result published')).toBeInTheDocument()
    expect(within(opener).getByText('PLAYER-42')).toBeInTheDocument()
    expect(within(opener).getByRole('link', { name: 'Open planned event' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar/EVENT-COMPLETE'
    )
    expect(within(opener).getByRole('link', { name: 'Open week detail' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/weeks/1?season=2028%2F2029'
    )
    expect(await screen.findByRole('list', { name: 'Viewer season calendar events 2029/2030' })).toHaveTextContent('Future Bronze')
    expectNoForbiddenViewerActions()
  })

  it('fails closed when no Saved Calendar Package is published', async () => {
    api.getViewerRunCalendar.mockRejectedValueOnce(new api.ApiError('missing calendar', 404))

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByText('No saved Calendar Package is available for this Viewer Branch yet.')).toBeInTheDocument()
    expect(screen.queryByText('Season Opener')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders Planned Event from Saved Calendar and joins published result by stable event ID', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/EVENT-COMPLETE')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-2d')
    expect((await screen.findAllByText('Season Opener')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('PLAYER-42').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Week W1' })).toHaveAttribute(
      'href', '/viewer/runs/viewer-run-2d/weeks/1?season=2028%2F2029'
    )
    expectNoForbiddenViewerActions()
  })

  it('keeps unknown Planned Event IDs local without inventing data', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/UNKNOWN')

    expect(await screen.findByText('This event is not present in the Saved Calendar Package.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tournament detail' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders Week Detail from Saved Calendar plus canonical Ranking and Finals Race history', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-2d')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('viewer-run-2d')

    const events = await screen.findByRole('list', { name: 'Viewer week Saved Calendar events' })
    expect(within(events).getByText('Gold Open')).toBeInTheDocument()
    expect(within(events).queryByText('Season Opener')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ranking publication #4' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/rankings/4'
    )
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-2d')
    expect(screen.getByRole('link', { name: 'Open canonical Finals Race publication for this cutoff week' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/race'
    )
    expectNoForbiddenViewerActions()
  })


  it('opens W80 from the Saved Calendar without an obsolete 61-week limit', async () => {
    mockCanonicalData(80)
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/80')

    expect(await screen.findByText('Gold Open')).toBeInTheDocument()
    expect(screen.getAllByText('W80').length).toBeGreaterThan(0)
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-2d')
    expectNoForbiddenViewerActions()
  })

  it('rejects a foreign Product Run calendar instead of showing its events', async () => {
    const original = await api.getViewerRunCalendar('viewer-run-2d')
    api.getViewerRunCalendar.mockResolvedValue({
      ...original,
      product_run_id: 'foreign-run'
    })
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByText(/Saved Calendar source does not match this Product Run/)).toBeInTheDocument()
    expect(screen.queryByText('Season Opener')).not.toBeInTheDocument()
  })

  it('does not attribute a foreign Viewer Branch result to an event', async () => {
    const original = await api.getViewerTournamentHistory('viewer-run-2d')
    api.getViewerTournamentHistory.mockResolvedValue({
      ...original,
      viewer_branch_id: 'foreign-branch'
    })
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByText('Tournament History source does not match the Saved Calendar Viewer Branch.')).toBeInTheDocument()
    const events = screen.getByRole('list', { name: 'Viewer season calendar events 2028/2029' })
    const opener = within(events).getByText('Season Opener').closest('li') as HTMLElement
    expect(within(opener).queryByText('PLAYER-42')).not.toBeInTheDocument()
    expect(within(opener).queryByText('Completed · result published')).not.toBeInTheDocument()
  })

  it('does not join a result from a different season-week using event ID alone', async () => {
    const original = await api.getViewerTournamentHistory('viewer-run-2d')
    api.getViewerTournamentHistory.mockResolvedValue({
      ...original,
      tournaments: original.tournaments.map((item: {event_id: string}) =>
        item.event_id === 'EVENT-COMPLETE' ? {...item, season_week: 80} : item
      )
    })
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/EVENT-COMPLETE')

    expect((await screen.findAllByText('Season Opener')).length).toBeGreaterThan(0)
    expect(screen.queryByText('PLAYER-42')).not.toBeInTheDocument()
  })

  it('hides week ranking publications from another Viewer Branch', async () => {
    const original = await api.listViewerOfficialRankingHistory('viewer-run-2d')
    api.listViewerOfficialRankingHistory.mockResolvedValue({
      ...original,
      viewer_branch_id: 'foreign-branch'
    })
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByText('Ranking History source does not match the Saved Calendar Viewer Branch.')).toBeInTheDocument()
    expect(screen.queryByRole('link', {name: 'Ranking publication #4'})).not.toBeInTheDocument()
    expect(await screen.findByText('Gold Open')).toBeInTheDocument()
  })


  // The same season week can occur in multiple years of a Run.
  // Keep competing historical evidence separate instead of mixing by W alone.
  async function overlappingWeekTwo(): Promise<void> {
    const original = await api.getViewerRunCalendar('viewer-run-2d')
    api.getViewerRunCalendar.mockResolvedValue({
      ...original,
      seasons: [
        original.seasons[0],
        {
          ...original.seasons[1],
          events: [{
            ...original.seasons[1].events[0],
            season_week: 2,
            event_name: 'Next Season Gold'
          }]
        }
      ]
    })
  }

  it('asks for a season when W2 contains distinct Saved seasons and no active season is known', async () => {
    await overlappingWeekTwo()
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByText(/This week occurs in multiple Saved seasons/)).toBeInTheDocument()
    expect(screen.queryByText('Gold Open')).not.toBeInTheDocument()
    expect(screen.queryByText('Next Season Gold')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', {name: 'Ranking publication #4'})).not.toBeInTheDocument()
    expect(screen.getByRole('link', {name: 'Week W2 · season 2028/2029'})).toHaveAttribute(
      'href', '/viewer/runs/viewer-run-2d/weeks/2?season=2028%2F2029'
    )
    expect(screen.getByRole('link', {name: 'Week W2 · season 2029/2030'})).toHaveAttribute(
      'href', '/viewer/runs/viewer-run-2d/weeks/2?season=2029%2F2030'
    )
    expectNoForbiddenViewerActions()
  })

  it.each([
    ['2028%2F2029', 'Gold Open', 'Next Season Gold', true],
    ['2029%2F2030', 'Next Season Gold', 'Gold Open', false]
  ])('shows only the selected season for W2 (%s)', async (season, included, excluded, hasRanking) => {
    await overlappingWeekTwo()
    renderViewerCalendarRoute(`/viewer/runs/viewer-run-2d/weeks/2?season=${season}`)

    const events = await screen.findByRole('list', {name: 'Viewer week Saved Calendar events'})
    expect(within(events).getByText(included)).toBeInTheDocument()
    expect(within(events).queryByText(excluded)).not.toBeInTheDocument()
    expect(Boolean(screen.queryByRole('link', {name: 'Ranking publication #4'}))).toBe(hasRanking)
    expectNoForbiddenViewerActions()
  })

  it('rejects an unrecognized season query without showing another season or its publications', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2?season=unrecognized')

    expect(await screen.findByText(/requested season is not present in this Viewer Branch/)).toBeInTheDocument()
    expect(screen.queryByText('Gold Open')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', {name: 'Ranking publication #4'})).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('rejects a foreign Finals Race publication even inside a matching branch response', async () => {
    const original = await api.getViewerFinalsRace('viewer-run-2d')
    api.getViewerFinalsRace.mockResolvedValue({
      ...original,
      publications: original.publications.map((publication: {cutoff_week: number}) =>
        publication.cutoff_week === 2 ? {...publication, viewer_branch_id: 'foreign-branch'} : publication
      )
    })
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2?season=2028%2F2029')

    expect(await screen.findByText('Gold Open')).toBeInTheDocument()
    expect(screen.queryByRole('link', {name: 'Open canonical Finals Race publication for this cutoff week'})).not.toBeInTheDocument()
    expect(screen.getByRole('link', {name: 'Ranking publication #4'})).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it.each(['not-a-week', '0', '-1', '1.5', '9007199254740992'])(
    'does not call canonical or Race readers for invalid week route %s', (invalidWeek) => {
    renderViewerCalendarRoute(`/viewer/runs/viewer-run-2d/weeks/${invalidWeek}`)

    expect(screen.getByText('Week must be a positive safe integer in the URL.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
