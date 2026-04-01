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
  getRun: vi.fn(),
  listEvents: vi.fn(),
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

function mockRunData(): void {
  api.getRun.mockResolvedValue({
    run: {
      run_id: 'run-a',
      season: 2027,
      seed: 42,
      config_version: 'v1',
      config_fingerprint: 'fp',
      next_event_index: 1,
      total_events: 3,
      completed_event_ids: ['E1']
    },
    season_state: {
      season: 2027,
      next_event_index: 1,
      completed_event_ids: ['E1'],
      ordered_events: [
        { event_id: 'E1', season: 2027, week: 1, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
        { event_id: 'E3', season: 2027, week: 2, tour: 'World Tour', category: 'Gold', template_id: 'WT-GOLD' },
        { event_id: 'E5', season: 2027, week: 3, tour: 'Elite Tour', category: 'Silver', template_id: 'ET-SILVER' }
      ]
    }
  })
}

describe('SnapshotDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunData()
    api.listEvents.mockResolvedValue({
      run_id: 'run-a',
      events: [{ event_sequence: 2, event_id: 'E3', season: 2027, week: 2, template_id: 'WT-GOLD', tournament_result: {} }]
    })
  })

  it('renders source-event context, planned context, and cross-links for ranking snapshots', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 10,
      snapshot_kind: 'WEEK',
      source_event_id: 'E3',
      payload: { label: 'ranking-10' }
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: { label: 'ranking-10' } },
        { snapshot_sequence: 11, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: { label: 'ranking-11' } }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} },
        { snapshot_sequence: 5, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} }
      ]
    })

    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/10', 'ranking')

    expect(await screen.findByRole('heading', { name: 'Ranking snapshot detail' })).toBeInTheDocument()
    expect(await screen.findByText(/ranking-10/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open source event detail/i })).toHaveAttribute('href', '/runs/run-a/events/E3')
    expect(screen.getByRole('link', { name: /Open planned-event detail/i })).toHaveAttribute('href', '/runs/run-a/calendar/E3')
    expect(screen.getByText('2027')).toBeInTheDocument()
    expect(screen.getByText('Gold')).toBeInTheDocument()
    expect(screen.getByText('Next')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /race snapshot #4/i })).toHaveAttribute('href', '/runs/run-a/snapshots/race/4')
    expect(api.listRankingSnapshots).toHaveBeenCalledWith('run-a')
    expect(api.listRaceSnapshots).toHaveBeenCalledWith('run-a')
  })

  it('renders readable fallback when source_event_id is missing from ordered season plan', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEK',
      source_event_id: 'UNKNOWN-EVENT',
      payload: { label: 'ranking-12' }
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'WEEK', source_event_id: 'UNKNOWN-EVENT', payload: {} }]
    })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })

    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/12', 'ranking')

    expect(await screen.findByText(/source_event_id is present, but this event is not in season_state\.ordered_events/i)).toBeInTheDocument()
    expect(screen.getByText(/Source event detail unavailable/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open planned-event detail/i })).toHaveAttribute(
      'href',
      '/runs/run-a/calendar/UNKNOWN-EVENT'
    )
  })

  it('keeps previous/next navigation in backend order', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 7,
      snapshot_kind: 'WEEK',
      source_event_id: null,
      payload: { label: 'race-7' }
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 6, snapshot_kind: 'WEEK', source_event_id: null, payload: {} },
        { snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: null, payload: {} },
        { snapshot_sequence: 5, snapshot_kind: 'WEEK', source_event_id: null, payload: {} }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })

    renderSnapshotDetailRoute('/runs/run-a/snapshots/race/7', 'race')

    expect(await screen.findByRole('heading', { name: 'Race snapshot detail' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: '#6' })).toHaveAttribute('href', '/runs/run-a/snapshots/race/6')
    expect(screen.getByRole('link', { name: '#5' })).toHaveAttribute('href', '/runs/run-a/snapshots/race/5')
  })

  it('shows readable boundary behavior when no previous or next snapshot exists', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 6,
      snapshot_kind: 'WEEK',
      source_event_id: null,
      payload: { label: 'race-6' }
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 6, snapshot_kind: 'WEEK', source_event_id: null, payload: {} }]
    })
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })

    renderSnapshotDetailRoute('/runs/run-a/snapshots/race/6', 'race')

    expect(await screen.findByText('None (start of history)')).toBeInTheDocument()
    expect(screen.getByText('None (latest snapshot)')).toBeInTheDocument()
  })

  it('shows readable invalid and missing snapshot sequence states', async () => {
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/not-a-number', 'ranking')
    expect(await screen.findByText(/is invalid\. Use a positive integer sequence\./i)).toBeInTheDocument()
    expect(api.getRankingSnapshot).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()

    api.getRankingSnapshot.mockRejectedValue({ status: 404 })
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/99', 'ranking')
    expect(await screen.findByText('Snapshot sequence 99 was not found for this run.')).toBeInTheDocument()
  })

})
