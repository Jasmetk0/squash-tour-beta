import { screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { PlayerCareerPage } from './PlayerCareerPage'
import { render } from '@testing-library/react'

const api = vi.hoisted(() => ({
  getRunPlayerCareerHistory: vi.fn()
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
  it('renders career timeline and trend summary', async () => {
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

    renderCareerRoute('/runs/run-child/players/EGY-0001/career')

    expect(await screen.findByRole('heading', { name: 'Player Career History' })).toBeInTheDocument()
    expect(await screen.findByText(/Ali A/)).toBeInTheDocument()
    expect(await screen.findByText(/Seasons tracked: 2/)).toBeInTheDocument()
    expect(await screen.findByText(/Overall delta: \+3/)).toBeInTheDocument()
    expect(await screen.findByText('run-parent')).toBeInTheDocument()
    expect((await screen.findAllByText('run-child')).length).toBeGreaterThan(0)
  })

  it('shows loading and error states', async () => {
    api.getRunPlayerCareerHistory.mockRejectedValueOnce(new Error('boom'))
    renderCareerRoute('/runs/run-child/players/EGY-0001/career')
    expect(await screen.findByText(/Failed to load career history/)).toBeInTheDocument()
  })
})
