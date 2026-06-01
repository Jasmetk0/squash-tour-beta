import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ViewerRunSnapshotDetailPage, ViewerRunSnapshotListPage } from './ViewerRunSnapshotsPage'

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

function renderViewerSnapshotRoute(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/viewer/runs/:runId/rankings" element={<ViewerRunSnapshotListPage mode="ranking" />} />
          <Route path="/viewer/runs/:runId/rankings/:snapshotSequence" element={<ViewerRunSnapshotDetailPage mode="ranking" />} />
          <Route path="/viewer/runs/:runId/race" element={<ViewerRunSnapshotListPage mode="race" />} />
          <Route path="/viewer/runs/:runId/race/:snapshotSequence" element={<ViewerRunSnapshotDetailPage mode="race" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function mockRunMetadata(): void {
  api.getRun.mockResolvedValue({
    run: {
      run_id: 'viewer-run-1',
      season: 2027,
      seed: 42,
      config_version: 'v1',
      config_fingerprint: 'fp',
      next_event_index: 1,
      total_events: 2,
      completed_event_ids: ['EVENT-1']
    },
    season_state: {
      season: 2027,
      next_event_index: 1,
      completed_event_ids: ['EVENT-1'],
      ordered_events: [
        { event_id: 'EVENT-1', season: 2027, week: 3, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
        { event_id: 'EVENT-2', season: 2027, week: 4, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
      ]
    }
  })
  api.listEvents.mockResolvedValue({
    run_id: 'viewer-run-1',
    events: [{ event_sequence: 8, event_id: 'EVENT-1', season: 2027, week: 3, template_id: 'WT-PLAT', tournament_result: {} }]
  })
}

function expectNoForbiddenViewerActions(): void {
  const forbiddenLabels = [
    'Simulate',
    'Generate',
    'Persist',
    'Apply',
    'Execute',
    'Delete',
    'Edit',
    'Import',
    'Rollover',
    'Rebuild',
    'Override',
    'Save changes',
    'Commit',
    'Regenerate',
    'Repair',
    'Merge',
    'Overwrite'
  ]

  forbiddenLabels.forEach((label) => {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  })
}

describe('ViewerRunSnapshotListPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
  })

  it('renders the run-scoped MSA Rankings page without primary raw payload content', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        {
          snapshot_sequence: 12,
          snapshot_kind: 'WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-1',
          payload: { secret_debug_marker: 'ranking-payload-should-not-render-on-list' }
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-1').length).toBeGreaterThan(0)
    expect(screen.getByText('Ranking publications')).toBeInTheDocument()
    expect(await screen.findByText('WEEKLY_PUBLICATION')).toBeInTheDocument()
    expect(screen.getByText('EVENT-1')).toBeInTheDocument()
    expect(screen.getAllByText('W3').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /View ranking publication/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/rankings/12'
    )
    expect(screen.queryByText(/ranking-payload-should-not-render-on-list/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })

  it('renders the run-scoped Race to Finals page without primary raw payload content', async () => {
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        {
          snapshot_sequence: 5,
          snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-1',
          payload: { secret_debug_marker: 'race-payload-should-not-render-on-list' }
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-1').length).toBeGreaterThan(0)
    expect(screen.getByText('Race publications')).toBeInTheDocument()
    expect(await screen.findByText('RACE_WEEKLY_PUBLICATION')).toBeInTheDocument()
    expect(screen.getByText('EVENT-1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View race publication/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/race/5')
    expect(screen.queryByText(/race-payload-should-not-render-on-list/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })
})

describe('ViewerRunSnapshotDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
  })

  it('renders a sports-facing MSA Ranking Publication detail with collapsed technical payload', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { secret_debug_marker: 'ranking-detail-hidden-payload' }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        { snapshot_sequence: 11, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-0', payload: {} },
        { snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    expect(await screen.findByRole('heading', { name: 'MSA Ranking Publication' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('12').length).toBeGreaterThan(0)
    expect(await screen.findByText('WEEKLY_PUBLICATION')).toBeInTheDocument()
    expect(screen.getByText('EVENT-1')).toBeInTheDocument()
    expect(screen.getAllByText('W3').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour').length).toBeGreaterThan(0)
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()
    expect(screen.getByText('Detailed standings preview is not connected for this payload shape yet.')).toBeInTheDocument()
    const details = screen.getByText('Show technical payload').closest('details')
    expect(details).not.toHaveAttribute('open')
    expect(screen.getByText(/ranking-detail-hidden-payload/i)).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical payload'))
    expect(screen.getByText(/ranking-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })

  it('renders a sports-facing Race to Finals Publication detail with collapsed technical payload', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 5,
      snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { secret_debug_marker: 'race-detail-hidden-payload' }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 5, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race/5')

    expect(await screen.findByRole('heading', { name: 'Race to Finals Publication' })).toBeInTheDocument()
    expect(await screen.findByText('RACE_WEEKLY_PUBLICATION')).toBeInTheDocument()
    expect(screen.getByText('EVENT-1')).toBeInTheDocument()
    expect(screen.getAllByText('W3').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Back to race publications/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/race')
    const technicalSection = screen.getByText('Show technical payload').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/race-detail-hidden-payload/i)).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical payload'))
    expect(within(technicalSection as HTMLElement).getByText(/race-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })
})
