import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveProductRunId } from '../../../test/viewerTestUtils'
import { ViewerTournamentsPage } from './ViewerTournamentsPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn()
}))

vi.mock('../../../api/client', () => api)

describe('ViewerTournamentsPage canonical authority', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.getViewerRunCalendar.mockResolvedValue({
      schema_version: 'viewer_run_calendar.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-tour',
      season_count: 1,
      event_count: 1,
      seasons: [{
        season: '2026/27',
        event_count: 1,
        events: [{ event_id: 'EVT 1', season: '2026/27', season_week: 4, calendar_year: 2026, year_week: 43, template_id: 'tmpl', event_name: 'Canonical Open', category: 'Gold', tour_level: 'WORLD_TOUR', host_country: 'CZE', host_city: 'Prague', region: 'Europe', duration_in_season_weeks: 1, start_season_week: 4, end_season_week: 4, status: 'planned', main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80 }]
      }]
    })
    api.getViewerTournamentHistory.mockResolvedValue({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-tour',
      tournament_count: 1,
      published_result_count: 0,
      tournaments: []
    })
  })

  it('renders canonical tournament sample', async () => {
    setViewerActiveProductRunId('run alpha')
    renderWithViewerProviders(<ViewerTournamentsPage />)

    expect(await screen.findByText('Canonical Open')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run alpha')
    expect(screen.getByRole('link', { name: 'Canonical Open' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT%201')
    expect(screen.getByRole('link', { name: 'W4' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/weeks/4')
    expectNoForbiddenViewerActions()
  })
})
