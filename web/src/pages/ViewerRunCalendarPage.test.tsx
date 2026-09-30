import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunCalendarPage, ViewerRunPlannedEventPage, ViewerRunWeekPage } from './ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  listRaceSnapshots: vi.fn(),
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

function mockCanonicalData(): void {
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
            season_week: 2,
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

  api.listRaceSnapshots.mockResolvedValue({
    run_id: 'viewer-run-2d',
    snapshots: [
      { snapshot_sequence: 7, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-NEXT', payload: {} },
      { snapshot_sequence: 8, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-FUTURE', payload: {} }
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
    expect(screen.getByRole('link', { name: 'Week W1' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2d/weeks/1')
    expectNoForbiddenViewerActions()
  })

  it('keeps unknown Planned Event IDs local without inventing data', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/UNKNOWN')

    expect(await screen.findByText('This event is not present in the Saved Calendar Package.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tournament detail' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders Week Detail from Saved Calendar plus canonical ranking history and Race compatibility', async () => {
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
    expect(screen.getByRole('link', { name: 'Race publication #7' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/race/7'
    )
    expect(screen.queryByRole('link', { name: 'Race publication #8' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not call canonical or Race readers for an invalid week route', () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/not-a-week')

    expect(screen.getByText('Week must be a whole number from 1 to 61 in the URL.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
