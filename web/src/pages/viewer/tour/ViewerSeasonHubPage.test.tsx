import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveProductRunId } from '../../../test/viewerTestUtils'
import { ViewerSeasonHubPage } from './ViewerSeasonHubPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  getViewerFinalsRace: vi.fn()
}))

vi.mock('../../../api/client', () => api)

describe('ViewerSeasonHubPage canonical tour authority', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.getViewerRunCalendar.mockResolvedValue({
      schema_version: 'viewer_run_calendar.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-tour',
      season_count: 1,
      event_count: 2,
      seasons: [{
        season: '2026/27',
        event_count: 2,
        events: [
          { event_id: 'EVT-1', season: '2026/27', season_week: 1, calendar_year: 2026, year_week: 40, template_id: 'tmpl-1', event_name: 'Event One', category: 'Gold', tour_level: 'WORLD_TOUR', host_country: 'CZE', host_city: 'Prague', region: 'Europe', duration_in_season_weeks: 1, start_season_week: 1, end_season_week: 1, status: 'completed', main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80 },
          { event_id: 'EVT 2', season: '2026/27', season_week: 2, calendar_year: 2026, year_week: 41, template_id: 'tmpl-2', event_name: 'Event Two', category: 'Platinum', tour_level: 'WORLD_TOUR', host_country: 'ENG', host_city: 'London', region: 'Europe', duration_in_season_weeks: 1, start_season_week: 2, end_season_week: 2, status: 'planned', main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 90 }
        ]
      }]
    })
    api.getViewerTournamentHistory.mockResolvedValue({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-tour',
      tournament_count: 2,
      published_result_count: 1,
      tournaments: [
        { event_id: 'EVT-1', season: '2026/27', season_week: 1, event_name: 'Event One', template_id: 'tmpl-1', category: 'Gold', tour_level: 'WORLD_TOUR', host_country: 'CZE', host_city: 'Prague', region: 'Europe', main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, ranking_status: 'published', result_published: true, champion_player_id: 'P1', finalist_player_id: 'P2' }
      ]
    })
    api.getViewerFinalsRace.mockResolvedValue({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-tour',
      latest_target_season_index: 2,
      publications: [{ target_season_index: 2, cutoff_season_index: 1, cutoff_week: 61, best_n: 8, selection_published: true, finals_event_id: 'FINALS-2', rows: [] }]
    })
  })

  it('shows Product Run empty state when none is selected', () => {
    renderWithViewerProviders(<ViewerSeasonHubPage />)
    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders canonical tour summary and Product Run links', async () => {
    setViewerActiveProductRunId('run alpha')
    renderWithViewerProviders(<ViewerSeasonHubPage />)

    expect(await screen.findByText('Season Hub summary')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run alpha')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('run alpha')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run alpha')
    expect(screen.getByText('branch-tour')).toBeInTheDocument()
    expect(screen.getByText('Event Two')).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT%202')
    expect(screen.getByText('S2 · cutoff S1 W61')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Product Run tournaments' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments')
    expectNoForbiddenViewerActions()
  })
})
