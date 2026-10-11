import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { FinalsResultDetailPage } from './FinalsResultDetailPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getFinalsResult: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('FinalsResultDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      qualification: { run_id: 'run-a' },
      result: { run_id: 'run-a' }
    })
    api.getFinalsResult.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      event_id: 'WORLD_TOUR_FINALS',
      source_as_of_season: 2027,
      source_as_of_week: 42,
      result: { champion_player_id: 'P1', runner_up_player_id: 'P2' }
    })
  })

  it('renders result detail route with summary-first content', async () => {
    renderWithRoute(<FinalsResultDetailPage />, '/runs/run-a/finals/result')

    expect(await screen.findByRole('heading', { name: 'Finals result detail' })).toBeInTheDocument()
    expect(screen.getByText('Summary')).toBeInTheDocument()
    expect(await screen.findByText('Champion')).toBeInTheDocument()
    expect(screen.getByText('Runner-up')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Finals overview page' })).toHaveAttribute('href', '/runs/run-a/finals')
    expect(screen.getByText(/runner_up_player_id/i)).toBeInTheDocument()
  })

  it('shows readable empty state when result is missing', async () => {
    api.getFinalsResult.mockRejectedValueOnce(new api.ApiError('{"detail":"No finals result for run"}', 404))
    renderWithRoute(<FinalsResultDetailPage />, '/runs/run-a/finals/result')

    expect(await screen.findByText('Finals result has not been recorded for this run yet.')).toBeInTheDocument()
    expect(screen.getByText('No Finals result payload is available yet.')).toBeInTheDocument()
  })
})
