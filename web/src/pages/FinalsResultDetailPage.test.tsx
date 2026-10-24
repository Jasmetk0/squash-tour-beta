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
// Legacy assertions verify the existing English copy; CS/EN transitions have separate coverage.
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

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

  it('reports failed result requests as Failed, not indefinitely Loading', async () => {
    api.getFinalsResult.mockRejectedValueOnce(new api.ApiError('result unavailable', 503))
    renderWithRoute(<FinalsResultDetailPage />, '/runs/run-a/finals/result')
    expect(await screen.findByText('Failed to load Finals result: result unavailable')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.queryByText('Loading Finals result detail...')).not.toBeInTheDocument()
  })

  it('does not claim qualification was never generated if summary evidence is missing', async () => {
    api.getFinalsSummary.mockRejectedValueOnce(new api.ApiError('summary unavailable', 503))
    renderWithRoute(<FinalsResultDetailPage />, '/runs/run-a/finals/result')
    expect(await screen.findByText('Failed to load Finals summary: summary unavailable')).toBeInTheDocument()
    expect(screen.getByText('Unknown')).toBeInTheDocument()
    expect(screen.queryByText('Not generated')).not.toBeInTheDocument()
  })

  it('keeps qualification and result loading states while both requests are unresolved', async () => {
    api.getFinalsSummary.mockImplementationOnce(() => new Promise(() => {}))
    api.getFinalsResult.mockImplementationOnce(() => new Promise(() => {}))
    renderWithRoute(<FinalsResultDetailPage />, '/runs/run-a/finals/result')
    expect(await screen.findByText('Loading Finals result detail...')).toBeInTheDocument()
    expect(screen.getAllByText('Loading')).toHaveLength(2)
  })

  it('shows readable empty state when result is missing', async () => {
    api.getFinalsResult.mockRejectedValueOnce(new api.ApiError('{"detail":"No finals result for run"}', 404))
    renderWithRoute(<FinalsResultDetailPage />, '/runs/run-a/finals/result')

    expect(await screen.findByText('Finals result has not been recorded for this run yet.')).toBeInTheDocument()
    expect(screen.getByText('No Finals result payload is available yet.')).toBeInTheDocument()
  })
  it.each([
    ['event ID', { event_id: 'OTHER_FINALS', source_as_of_season: 2027, source_as_of_week: 42 }],
    ['source season', { event_id: 'WORLD_TOUR_FINALS', source_as_of_season: 2026, source_as_of_week: 42 }],
    ['source week', { event_id: 'WORLD_TOUR_FINALS', source_as_of_season: 2027, source_as_of_week: 41 }]
  ])('hides a Finals result detail contradicting summary %s', async (_dimension, source) => {
    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: 'run-a', season: 2027, qualification: { run_id: 'run-a', season: 2027 },
      result: { run_id: 'run-a', season: 2027, ...source }
    })
    renderWithRoute(<FinalsResultDetailPage />, '/runs/run-a/finals/result')
    expect(await screen.findByText('Finals result detail conflicts with the stored summary or selected Run.')).toBeInTheDocument()
    expect(screen.queryByText(/runner_up_player_id/)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Finals overview page' })).toBeInTheDocument()
  })

  it('keeps a valid standalone Finals result when summary evidence is unavailable', async () => {
    api.getFinalsSummary.mockRejectedValueOnce(new api.ApiError('summary offline', 503))
    renderWithRoute(<FinalsResultDetailPage />, '/runs/run-a/finals/result')
    expect(await screen.findByText('Failed to load Finals summary: summary offline')).toBeInTheDocument()
    expect(screen.getByText(/runner_up_player_id/)).toBeInTheDocument()
    expect(screen.queryByText('Finals result detail conflicts with the stored summary or selected Run.')).not.toBeInTheDocument()
  })

})
