import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SnapshotDetailPage } from './SnapshotDetailPage'
import type { RaceSnapshot } from '../api/types'

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
// Legacy assertions verify the existing English copy; CS/EN transitions have separate coverage.
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

function renderSnapshotDetailRoute(route: string, mode: 'ranking' | 'race'): QueryClient {
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
  return queryClient
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


  it.each([
    ['historical first', [
      { event_sequence: 2, event_id: 'E3', season: 2026, week: 35, template_id: 'OLD', tournament_result: null },
      { event_sequence: 9, event_id: 'E3', season: 2027, week: 2, template_id: 'NEW', tournament_result: null }
    ]],
    ['current first', [
      { event_sequence: 9, event_id: 'E3', season: 2027, week: 2, template_id: 'NEW', tournament_result: null },
      { event_sequence: 2, event_id: 'E3', season: 2026, week: 35, template_id: 'OLD', tournament_result: null }
    ]]
  ])('isolates direct snapshot detail from duplicated persisted source IDs (%s)', async (_name, duplicated) => {
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-a', events: duplicated })
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3',
      payload: { marker: 'INDEPENDENT_SNAPSHOT', points: 0 }
    })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} }
    ] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} }
    ] })
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/10', 'ranking')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Source event ID is reused in persisted history. Source links and week context are unavailable.'
    )
    expect(screen.getByText(/INDEPENDENT_SNAPSHOT/)).toBeInTheDocument()
    expect(screen.getByText(/"points": 0/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open source event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open planned-event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /race snapshot #4/i })).not.toBeInTheDocument()
    expect(screen.getByText('Related snapshots currently unavailable')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open events history' })).toBeInTheDocument()
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
    expect(screen.getByRole('link', { name: 'Open week detail (W2)' })).toHaveAttribute('href', '/runs/run-a/weeks/2')
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
    // A reference absent from the ordered plan must not become an invented detail link.
    expect(screen.queryByRole('link', { name: /Open planned-event detail/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail/i })).not.toBeInTheDocument()
  })

  it('keeps previous/next navigation in backend order', async () => {
    const raceSnapshot: RaceSnapshot = {
      snapshot_sequence: 7,
      snapshot_kind: 'WEEK',
      source_event_id: null,
      payload: { label: 'race-7' }
    }
    api.getRaceSnapshot.mockResolvedValue(raceSnapshot)
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
    const raceSnapshot: RaceSnapshot = {
      snapshot_sequence: 6,
      snapshot_kind: 'WEEK',
      source_event_id: null,
      payload: { label: 'race-6' }
    }
    api.getRaceSnapshot.mockResolvedValue(raceSnapshot)
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 6, snapshot_kind: 'WEEK', source_event_id: null, payload: {} }]
    })
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })

    renderSnapshotDetailRoute('/runs/run-a/snapshots/race/6', 'race')

    expect(await screen.findByText('None (start of history)')).toBeInTheDocument()
    expect(screen.getByText('None (latest snapshot)')).toBeInTheDocument()
  })

  it.each(['12abc', '1.5', '1e2', '0', '99999999999999999999999'])(
    'does not silently parse malformed snapshot sequence %s into a valid endpoint request',
    async (invalidSequence) => {
      renderSnapshotDetailRoute(`/runs/run-a/snapshots/ranking/${invalidSequence}`, 'ranking')
      expect(await screen.findByText(/is invalid\. Use a positive integer sequence\./i)).toBeInTheDocument()
      expect(api.getRankingSnapshot).not.toHaveBeenCalled()
      expect(api.getRaceSnapshot).not.toHaveBeenCalled()
      expect(api.listRankingSnapshots).not.toHaveBeenCalled()
      expect(api.listRaceSnapshots).not.toHaveBeenCalled()
      expect(api.getRun).not.toHaveBeenCalled()
      expect(api.listEvents).not.toHaveBeenCalled()
    }
  )

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

  it('does not claim a previous/latest boundary when the snapshot index read fails', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: { points: 0 }
    })
    api.listRankingSnapshots.mockRejectedValue(new Error('history offline'))
    api.listRaceSnapshots.mockRejectedValue(new Error('related history offline'))
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/10', 'ranking')
    expect(await screen.findByText('Failed to load snapshots history: history offline')).toBeInTheDocument()
    expect(screen.queryByText('None (start of history)')).not.toBeInTheDocument()
    expect(screen.queryByText('None (latest snapshot)')).not.toBeInTheDocument()
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Related snapshots currently unavailable')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /race snapshot #/i })).not.toBeInTheDocument()
  })

  it('does not treat a selected snapshot missing from the returned index as its first or latest entry', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: null, payload: { points: 0 }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'run-a',
      snapshots: [{ snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: null, payload: {} }]
    })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [] })
    renderSnapshotDetailRoute('/runs/run-a/snapshots/race/9', 'race')
    expect(await screen.findByText(/"points": 0/)).toBeInTheDocument()
    expect(screen.queryByText('None (start of history)')).not.toBeInTheDocument()
    expect(screen.queryByText('None (latest snapshot)')).not.toBeInTheDocument()
  })

  it('shows the stored snapshot but does not link to a current plan after a cross-season source collision', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: { score: 0 }
    })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a',
      snapshots: [{ snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} }] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [] })
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-a', events: [
      { event_sequence: 2, event_id: 'E3', season: 2026, week: 2,
        template_id: 'OLD-E3', tournament_result: null }
    ] })
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/10', 'ranking')
    expect(await screen.findByText('Source event season does not match the current plan. Planned links are hidden.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open planned-event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open source event detail' })).toHaveAttribute('href', '/runs/run-a/events/E3')
  })

  it('does not present plan context when run and season-state headers disagree', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: { score: 0 }
    })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a',
      snapshots: [{ snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} }] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [] })
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, next_event_index: 1,
        total_events: 2, completed_event_ids: [] },
      season_state: { season: 2026, next_event_index: 1, completed_event_ids: [],
        ordered_events: [{ event_id: 'E3', season: 2026, week: 2, tour: 'World',
          category: 'Gold', template_id: 'E3-OLD' }] }
    })
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/10', 'ranking')
    expect(await screen.findByText('Run season and ordered plan disagree. Planned links are unavailable.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open planned-event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail/ })).not.toBeInTheDocument()
  })

  it('hides cached direct snapshot payload after refresh failure and restores it on retry', async () => {
    const saved = { snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3',
      payload: { marker: 'RECOVERABLE_SNAPSHOT', points: 0 } }
    api.getRankingSnapshot.mockResolvedValueOnce(saved)
      .mockRejectedValueOnce(new Error('temporary snapshot outage'))
      .mockResolvedValueOnce(saved)
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [saved] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [] })
    renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/10', 'ranking')
    expect(await screen.findByText(/RECOVERABLE_SNAPSHOT/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Refresh read-only data' }))
    expect(await screen.findByText('Failed to load snapshot details: temporary snapshot outage')).toBeInTheDocument()
    expect(screen.queryByText(/RECOVERABLE_SNAPSHOT/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Refresh read-only data' }))
    expect(await screen.findByText(/RECOVERABLE_SNAPSHOT/)).toBeInTheDocument()
    expect(api.getRankingSnapshot).toHaveBeenCalledTimes(3)
  })

  it('does not offer cached neighboring snapshot links after the index refresh fails', async () => {
    const snapshot = { snapshot_sequence: 10, snapshot_kind: 'WEEK',
      source_event_id: 'E3', payload: { points: 0 } }
    api.getRankingSnapshot.mockResolvedValue(snapshot)
    api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} },
      snapshot,
      { snapshot_sequence: 11, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }
    ] }).mockRejectedValueOnce(new Error('temporary history index outage'))
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [] })
    const client = renderSnapshotDetailRoute('/runs/run-a/snapshots/ranking/10', 'ranking')
    expect(await screen.findByRole('link', { name: '#9' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '#11' })).toBeInTheDocument()
    await act(async () => { await client.refetchQueries({ queryKey: ['ranking-snapshots', 'run-a'] }) })
    expect(await screen.findByText('Failed to load snapshots history: temporary history index outage')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '#9' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '#11' })).not.toBeInTheDocument()
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
    expect(screen.getByText(/"points": 0/)).toBeInTheDocument()
  })

})
