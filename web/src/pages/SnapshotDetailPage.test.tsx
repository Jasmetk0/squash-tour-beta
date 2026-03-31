import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SnapshotDetailPage } from './SnapshotDetailPage'

const api = vi.hoisted(() => ({
  getRankingSnapshot: vi.fn(),
  getRaceSnapshot: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

function renderSnapshotDetailRoute(route: string, mode: 'ranking' | 'race'): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/runs/:runId/snapshots/ranking/:snapshotSequence" element={<SnapshotDetailPage mode={mode} />} />
          <Route path="/runs/:runId/snapshots/race/:snapshotSequence" element={<SnapshotDetailPage mode={mode} />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('SnapshotDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders ranking snapshot detail route with summary, payload, and event cross-link', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 10,
      snapshot_kind: 'WEEK',
      source_event_id: 'E3',
      payload: { label: 'ranking-10' }
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: { label: 'ranking-10' } },
        { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: null, payload: { label: 'ranking-9' } }
      ]
    })

    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/10', 'ranking')

    expect(await screen.findByRole('heading', { name: 'Ranking snapshot detail' })).toBeInTheDocument()
    expect(await screen.findByText(/ranking-10/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open source event detail page/i })).toHaveAttribute('href', '/runs/run-a/events/E3')
    expect(api.getRankingSnapshot).toHaveBeenCalledWith('run-a', 10)
  })

  it('renders race snapshot detail route with summary and payload', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 7,
      snapshot_kind: 'WEEK',
      source_event_id: null,
      payload: { label: 'race-7' }
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: null, payload: { label: 'race-7' } },
        { snapshot_sequence: 8, snapshot_kind: 'WEEK', source_event_id: null, payload: { label: 'race-8' } }
      ]
    })

    renderSnapshotDetailRoute('/runs/run-a/snapshots/race/7', 'race')

    expect(await screen.findByRole('heading', { name: 'Race snapshot detail' })).toBeInTheDocument()
    expect(await screen.findByText(/race-7/)).toBeInTheDocument()
    expect(screen.getByText('None')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '#8' })).toHaveAttribute('href', '/runs/run-a/snapshots/race/8')
    expect(api.getRaceSnapshot).toHaveBeenCalledWith('run-a', 7)
    expect(api.listRaceSnapshots).toHaveBeenCalledWith('run-a')
  })

  it('shows readable invalid and missing snapshot sequence states', async () => {
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/not-a-number', 'ranking')
    expect(await screen.findByText(/is invalid\. Use a positive integer sequence\./i)).toBeInTheDocument()
    expect(api.getRankingSnapshot).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()

    api.getRankingSnapshot.mockRejectedValue({ status: 404 })
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/99', 'ranking')
    expect(await screen.findByText('Snapshot sequence 99 was not found for this run.')).toBeInTheDocument()
  })
})
