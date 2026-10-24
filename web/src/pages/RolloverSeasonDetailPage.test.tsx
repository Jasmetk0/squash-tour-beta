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
// Legacy assertions verify the existing English copy; CS/EN transitions have separate coverage.
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

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

  it.each(['2e3', '0x7ec', '2028.0', '-2028', '999999999999999999999999'])(
    'refuses malformed rollover season %s without issuing any read requests',
    async (invalid) => {
      renderPage(`/runs/run-a/rollover/${invalid}`)
      expect(await screen.findByText(/Invalid or missing target season in URL/)).toBeInTheDocument()
      expect(api.getRolloverBySeason).not.toHaveBeenCalled()
      expect(api.getPlayerTransitions).not.toHaveBeenCalled()
      expect(api.getNextSeasonPlayers).not.toHaveBeenCalled()
    }
  )

  it('preserves a special-character Run identifier in the overview link', async () => {
    api.getRolloverBySeason.mockResolvedValue({ rollover: {
      run_id: 'run x/y', from_season: 2027, to_season: 2028, transitioned_players: 0, metadata: {}
    } })
    api.getPlayerTransitions.mockResolvedValue({ transitions: [] })
    api.getNextSeasonPlayers.mockResolvedValue({ players: [] })
    renderPage('/runs/run%20x%2Fy/rollover/2028')
    expect(await screen.findByRole('link', { name: 'Back to rollover overview' }))
      .toHaveAttribute('href', '/runs/run%20x%2Fy/rollover')
    expect(api.getRolloverBySeason).toHaveBeenCalledWith('run x/y', 2028)
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
  it('rejects foreign rollover data without hiding independently valid player transitions or displaying a false zero', async () => {
    api.getRolloverBySeason.mockResolvedValueOnce({ rollover: {
      run_id: 'another-run', from_season: 2027, to_season: 2028,
      transitioned_players: 50, metadata: {}
    } })
    api.getPlayerTransitions.mockResolvedValueOnce({
      run_id: 'run-a', to_season: 2028,
      transitions: [{ run_id: 'run-a', from_season: 2027, to_season: 2028, player_id: 'P1', transition: { delta: 0 } }]
    })
    api.getNextSeasonPlayers.mockResolvedValueOnce({
      run_id: 'another-run', to_season: 2028,
      players: [{ player_id: 'SHOULD_NOT_DISPLAY', state: { readiness: 1 } }]
    })
    renderPage('/runs/run-a/rollover/2028')
    expect(await screen.findByText('Rollover summary identity differs from the selected Run or target season.')).toBeInTheDocument()
    expect(screen.getByText('Next-season player response belongs to another Run or season.')).toBeInTheDocument()
    expect(screen.queryByText(/SHOULD_NOT_DISPLAY/)).not.toBeInTheDocument()
    expect(await screen.findByText(/"player_id": "P1"/)).toBeInTheDocument()
    const summary = screen.getByRole('heading', { name: 'Inspection summary' }).closest('article')
    expect(summary).not.toBeNull()
    expect(within(summary as HTMLElement).getByText('Unavailable')).toBeInTheDocument()
    expect(screen.queryByText('50')).not.toBeInTheDocument()
  })

})
