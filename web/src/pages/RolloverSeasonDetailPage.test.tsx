import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RolloverSeasonDetailPage } from './RolloverSeasonDetailPage'

const api = vi.hoisted(() => ({
  getRolloverBySeason: vi.fn(),
  getPlayerTransitions: vi.fn(),
  getNextSeasonPlayers: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

function renderPage(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/runs/:runId/rollover/:toSeason" element={<RolloverSeasonDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('RolloverSeasonDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders rollover season detail for a valid toSeason route param', async () => {
    api.getRolloverBySeason.mockResolvedValueOnce({
      rollover: {
        run_id: 'run-a',
        from_season: 2027,
        to_season: 2028,
        transitioned_players: 3,
        metadata: { mode: 'deterministic' }
      }
    })
    api.getPlayerTransitions.mockResolvedValueOnce({
      run_id: 'run-a',
      to_season: 2028,
      transitions: [
        { player_id: 'P2', transition: { state: 'steady' } },
        { player_id: 'P1', transition: { state: 'rise' } }
      ]
    })
    api.getNextSeasonPlayers.mockResolvedValueOnce({
      run_id: 'run-a',
      to_season: 2028,
      players: [
        { player_id: 'P2', state: { readiness: 0.77 } },
        { player_id: 'P1', state: { readiness: 0.82 } }
      ]
    })

    renderPage('/runs/run-a/rollover/2028')

    expect(await screen.findByRole('heading', { name: 'Rollover season detail' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Rollover summary (S2028)' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to rollover overview' })).toHaveAttribute('href', '/runs/run-a/rollover')

    const transitionsSection = screen.getByRole('heading', { name: 'Player transitions' }).closest('article')
    expect(transitionsSection).not.toBeNull()
    expect(await within(transitionsSection as HTMLElement).findByText(/\"player_id\": \"P2\"/)).toBeInTheDocument()
    expect(within(transitionsSection as HTMLElement).getByText(/\"player_id\": \"P1\"/)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('player_id filter'), { target: { value: 'p1' } })
    expect(within(transitionsSection as HTMLElement).queryByText(/\"player_id\": \"P2\"/)).not.toBeInTheDocument()
    expect(within(transitionsSection as HTMLElement).getByText(/\"player_id\": \"P1\"/)).toBeInTheDocument()
  })

  it('renders readable invalid/missing season behavior without crashing', async () => {
    renderPage('/runs/run-a/rollover/not-a-season')

    expect(await screen.findByText(/Invalid or missing target season/i)).toBeInTheDocument()
    expect(api.getRolloverBySeason).not.toHaveBeenCalled()
    expect(api.getPlayerTransitions).not.toHaveBeenCalled()
    expect(api.getNextSeasonPlayers).not.toHaveBeenCalled()
  })

  it('renders readable not found behavior for missing rollover season', async () => {
    api.getRolloverBySeason.mockRejectedValueOnce(new api.ApiError('{"detail":"not found"}', 404))
    api.getPlayerTransitions.mockResolvedValueOnce({ run_id: 'run-a', to_season: 2030, transitions: [] })
    api.getNextSeasonPlayers.mockResolvedValueOnce({ run_id: 'run-a', to_season: 2030, players: [] })

    renderPage('/runs/run-a/rollover/2030')

    expect(await screen.findByText('No rollover summary found for season 2030.')).toBeInTheDocument()
    expect(screen.getByText('No transition records are available for this season.')).toBeInTheDocument()
    expect(screen.getByText('No next-season players are available for this season.')).toBeInTheDocument()
  })
})
