import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveProductRunId } from '../../../test/viewerTestUtils'
import { ViewerCurrentWeekPage } from './ViewerTourCurrentWeekPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn()
}))

vi.mock('../../../api/client', () => api)

describe('ViewerCurrentWeekPage canonical authority', () => {
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
        season: '2000',
        event_count: 1,
        events: [{ event_id: 'EVT-5', season: '2000', season_week: 1, calendar_year: 2000, year_week: 1, template_id: 'tmpl', event_name: 'Week One Open', category: 'Gold', tour_level: 'WORLD_TOUR', host_country: 'CZE', host_city: 'Prague', region: 'Europe', duration_in_season_weeks: 1, start_season_week: 1, end_season_week: 1, status: 'planned', main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80 }]
      }]
    })
  })

  it('reads selected week from canonical Saved Calendar', async () => {
    setViewerActiveProductRunId('run alpha')
    renderWithViewerProviders(<ViewerCurrentWeekPage />)

    expect(await screen.findByText('Week One Open')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run alpha')
    expect(screen.getByRole('link', { name: 'Week One Open' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT-5')
    expectNoForbiddenViewerActions()
  })
})
