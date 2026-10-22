import { render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { FinalsPage } from './FinalsPage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(), getFinalsQualification: vi.fn(), getFinalsResult: vi.fn(),
  simulateWorldTourFinals: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
}))
vi.mock('../api/client', () => api)

function mount() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={['/runs/run-a/finals']}>
      <Routes><Route path="/runs/:runId/finals" element={<FinalsPage />} /></Routes>
    </MemoryRouter>
  </QueryClientProvider>)
}

function contextStatus(label: string): string | null {
  const context = screen.getByRole('list', { name: 'Current context' })
  const item = within(context).getByText(label).closest('li')
  return item?.querySelector('strong')?.textContent ?? null
}

describe('World Tour Finals overview status accuracy', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2027, qualification: null, result: null })
    api.getFinalsQualification.mockRejectedValue(new api.ApiError('No qualification', 404))
    api.getFinalsResult.mockRejectedValue(new api.ApiError('No result', 404))
  })

  it('does not claim Finals are unplayed while all services are still pending', () => {
    const never = () => new Promise<never>(() => {})
    api.getFinalsSummary.mockImplementation(never)
    api.getFinalsQualification.mockImplementation(never)
    api.getFinalsResult.mockImplementation(never)
    mount()
    expect(contextStatus('Qualification')).toBe('Loading')
    expect(contextStatus('Result')).toBe('Loading')
    expect(screen.queryByText('Not simulated')).not.toBeInTheDocument()
  })

  it('shows a service failure rather than a false empty qualification message', async () => {
    api.getFinalsQualification.mockRejectedValue(new api.ApiError('Qualification unavailable', 503))
    mount()
    expect(await screen.findByText(/Failed to load Finals qualification: Qualification unavailable/)).toBeInTheDocument()
    await waitFor(() => expect(contextStatus('Qualification')).toBe('Failed'))
    expect(screen.queryByText('No qualification data available.')).not.toBeInTheDocument()
    expect(contextStatus('Result')).toBe('Missing')
  })

  it('shows a failed result query as Failed rather than Not simulated', async () => {
    api.getFinalsResult.mockRejectedValue(new api.ApiError('Result unavailable', 503))
    mount()
    expect(await screen.findByText(/Failed to load Finals result: Result unavailable/)).toBeInTheDocument()
    expect(contextStatus('Result')).toBe('Failed')
    expect(contextStatus('Qualification')).toBe('Missing')
  })

  it('keeps existing recorded Finals status when both details are available', async () => {
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run-a', season: 2027, qualification: { run_id: 'run-a' }, result: { run_id: 'run-a' },
    })
    api.getFinalsQualification.mockResolvedValue({
      run_id: 'run-a', season: 2027, source_as_of_season: 2027,
      source_as_of_week: 42, qualification: { qualified_player_ids: ['P1'], groups: [] },
    })
    api.getFinalsResult.mockResolvedValue({
      run_id: 'run-a', season: 2027, event_id: 'WORLD_TOUR_FINALS',
      source_as_of_season: 2027, source_as_of_week: 42, result: { champion_player_id: 'P1' },
    })
    mount()
    await waitFor(() => expect(contextStatus('Qualification')).toBe('Ready'))
    await waitFor(() => expect(contextStatus('Result')).toBe('Recorded'))
    expect(screen.getByRole('link', { name: 'Open result detail' })).toBeInTheDocument()
  })
})
