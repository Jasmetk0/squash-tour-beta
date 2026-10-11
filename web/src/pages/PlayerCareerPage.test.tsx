import { screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { PlayerCareerPage } from './PlayerCareerPage'
import { render } from '@testing-library/react'

const api = vi.hoisted(() => ({
  getRunPlayerCareerHistory: vi.fn(),
  getRunPlayerCareerPerformance: vi.fn(),
  getRunPlayerTournamentResults: vi.fn()
}))

vi.mock('../api/client', () => api)

function renderCareerRoute(route: string): ReturnType<typeof render> {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/runs/:runId/players/:playerId/career" element={<PlayerCareerPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('PlayerCareerPage', () => {
  it('renders career timeline and season performance table', async () => {
    api.getRunPlayerCareerHistory.mockResolvedValue({
      requested_run_id: 'run-child',
      player_id: 'EGY-0001',
      player_name: 'Ali A',
      country_code: 'EGY',
      entries: [
        {
          run_id: 'run-parent',
          season: 2027,
          age: 20,
          overall: 67,
          technique: 70,
          movement: 68,
          physical: 66,
          mental: 65,
          source_type: 'planner_generated',
          quality_band: 'elite_talent',
          is_top_band: true,
          origin_source_type: 'planner_generated',
          origin_quality_band: 'elite_talent',
          origin_override_id: null,
          origin_season: 2027
        },
        {
          run_id: 'run-child',
          season: 2028,
          age: 21,
          overall: 70,
          technique: 72,
          movement: 71,
          physical: 68,
          mental: 69,
          source_type: 'rollover_carried',
          quality_band: 'elite_talent',
          is_top_band: true,
          origin_source_type: 'planner_generated',
          origin_quality_band: 'elite_talent',
          origin_override_id: null,
          origin_season: 2027
        }
      ]
    })

    api.getRunPlayerCareerPerformance.mockResolvedValue({
      requested_run_id: 'run-child',
      player_id: 'EGY-0001',
      player_name: 'Ali A',
      country_code: 'EGY',
      entries: [
        {
          run_id: 'run-parent',
          season: 2027,
          ranking_position: 10,
          race_position: 9,
          tournaments_played: 5,
          titles: 1,
          finals: 1,
          semifinals: 2,
          quarterfinals: 3,
          wins: 12,
          losses: 4
        },
        {
          run_id: 'run-child',
          season: 2028,
          ranking_position: null,
          race_position: null,
          tournaments_played: 0,
          titles: 0,
          finals: 0,
          semifinals: 0,
          quarterfinals: 0,
          wins: 0,
          losses: 0
        }
      ]
    })

    api.getRunPlayerTournamentResults.mockResolvedValue({
      requested_run_id: 'run-child',
      player_id: 'EGY-0001',
      player_name: 'Ali A',
      country_code: 'EGY',
      entries: [
        {
          run_id: 'run-parent',
          season: 2027,
          week: 7,
          event_sequence: 3,
          event_id: '2027-WT-AAA-250',
          event_name: 'Alpha Open 250',
          event_category: 'WT250',
          template_id: 'wt_250',
          finish: 'CHAMPION',
          is_title: true,
          wins: 4,
          losses: 0,
          ranking_points_awarded: 250
        },
        {
          run_id: 'run-child',
          season: 2028,
          week: null,
          event_sequence: 1,
          event_id: '2028-WT-AAA-250',
          event_name: null,
          event_category: null,
          template_id: null,
          finish: null,
          is_title: false,
          wins: 0,
          losses: 0,
          ranking_points_awarded: null
        }
      ]
    })

    renderCareerRoute('/runs/run-child/players/EGY-0001/career')

    expect(await screen.findByRole('heading', { name: 'Player Career History' })).toBeInTheDocument()
    expect(await screen.findByText(/Ali A/)).toBeInTheDocument()
    expect(await screen.findByText(/Seasons tracked: 2/)).toBeInTheDocument()
    expect(await screen.findByText(/Overall delta: \+3/)).toBeInTheDocument()
    expect((await screen.findAllByText('run-parent')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('run-child')).length).toBeGreaterThan(0)
    expect(await screen.findByRole('columnheader', { name: 'Tournaments' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Tournament results timeline' })).toBeInTheDocument()
    expect(await screen.findByRole('columnheader', { name: 'Event' })).toBeInTheDocument()
    expect(await screen.findByText(/Alpha Open 250/)).toBeInTheDocument()
    expect((await screen.findAllByText('—')).length).toBeGreaterThan(0)
  })

  it('shows loading and error states', async () => {
    api.getRunPlayerCareerHistory.mockRejectedValueOnce(new Error('boom'))
    api.getRunPlayerCareerPerformance.mockRejectedValueOnce(new Error('perf-boom'))
    api.getRunPlayerTournamentResults.mockRejectedValueOnce(new Error('results-boom'))
    renderCareerRoute('/runs/run-child/players/EGY-0001/career')
    expect(await screen.findByText(/Failed to load career history/)).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load season performance/)).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load tournament results timeline/)).toBeInTheDocument()
  })

  it('shows empty state for tournament results timeline', async () => {
    api.getRunPlayerCareerHistory.mockResolvedValue({
      requested_run_id: 'run-child',
      player_id: 'EGY-0001',
      player_name: 'Ali A',
      country_code: 'EGY',
      entries: []
    })
    api.getRunPlayerCareerPerformance.mockResolvedValue({
      requested_run_id: 'run-child',
      player_id: 'EGY-0001',
      player_name: 'Ali A',
      country_code: 'EGY',
      entries: []
    })
    api.getRunPlayerTournamentResults.mockResolvedValue({
      requested_run_id: 'run-child',
      player_id: 'EGY-0001',
      player_name: 'Ali A',
      country_code: 'EGY',
      entries: []
    })

    renderCareerRoute('/runs/run-child/players/EGY-0001/career')

    expect(await screen.findByText(/No tournament results are available for this player yet/)).toBeInTheDocument()
  })

})
