import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

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

afterEach(() => cleanup())

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


function rankingRows(count: number): Array<Record<string, unknown>> {
  return Array.from({ length: count }, (_, index) => ({
    rank: index + 1,
    player_id: `P${index + 1}`,
    player_name: index === 0 ? 'Ali Farag' : `Real Player ${index + 1}`,
    country_code: index === 0 ? 'EGY' : 'ENG',
    points: 20000 - index,
    tournaments_counted: index === 0 ? 12 : 10,
    movement: index === 0 ? '+1' : 'same'
  }))
}

function raceRows(count: number): Array<Record<string, unknown>> {
  return Array.from({ length: count }, (_, index) => ({
    position: index + 1,
    player_id: `R${index + 1}`,
    player_name: index === 0 ? 'Mostafa Asal' : `Race Player ${index + 1}`,
    country: index === 0 ? 'EGY' : 'NZL',
    race_points: 9000 - index,
    tournaments_counted: index === 0 ? 8 : 6,
    qualification_status: index === 0 ? 'Qualified' : 'Chasing',
    next_max_points_possible: index === 0 ? 1200 : 900
  }))
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
    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expect((await screen.findAllByText('WEEKLY_PUBLICATION')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('W3').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Open ranking publication detail/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/rankings/12'
    )
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/calendar/EVENT-1'
    )
    expect(screen.getByRole('link', { name: /Open tournament detail/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments/EVENT-1'
    )
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(screen.queryByText(/ranking-payload-should-not-render-on-list/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })


  it('keeps snapshot rows without source or ordered-plan matches on safe fallback text without broken source links', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        {
          snapshot_sequence: 14,
          snapshot_kind: 'WEEKLY_PUBLICATION',
          payload: { secret_debug_marker: 'no-source-payload-should-not-render-on-list' }
        },
        {
          snapshot_sequence: 15,
          snapshot_kind: 'WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-MISSING',
          payload: { secret_debug_marker: 'unmatched-payload-should-not-render-on-list' }
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    const noSourceCard = await screen.findByRole('article', { name: 'Ranking publication 14' })
    expect(within(noSourceCard).getByText('No source event recorded')).toBeInTheDocument()
    expect(within(noSourceCard).getAllByText('No ordered-plan match').length).toBeGreaterThan(0)
    expect(within(noSourceCard).queryByRole('link', { name: /Open planned event/i })).not.toBeInTheDocument()
    expect(within(noSourceCard).queryByRole('link', { name: /Open tournament detail/i })).not.toBeInTheDocument()
    expect(within(noSourceCard).queryByRole('link', { name: /^W\d+$/ })).not.toBeInTheDocument()

    const unmatchedCard = screen.getByRole('article', { name: 'Ranking publication 15' })
    expect(within(unmatchedCard).getByText('EVENT-MISSING')).toBeInTheDocument()
    expect(within(unmatchedCard).getAllByText('No ordered-plan match').length).toBeGreaterThan(0)
    expect(within(unmatchedCard).getByText('No persisted event record')).toBeInTheDocument()
    expect(within(unmatchedCard).queryByRole('link', { name: /Open planned event/i })).not.toBeInTheDocument()
    expect(within(unmatchedCard).queryByRole('link', { name: /Open tournament detail/i })).not.toBeInTheDocument()
    expect(within(unmatchedCard).queryByRole('link', { name: /^W\d+$/ })).not.toBeInTheDocument()
    expect(screen.queryByText(/no-source-payload-should-not-render-on-list/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/unmatched-payload-should-not-render-on-list/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
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
    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expect((await screen.findAllByText('RACE_WEEKLY_PUBLICATION')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-1').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Open race publication detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/race/5')
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/calendar/EVENT-1'
    )
    expect(screen.getByRole('link', { name: /Open tournament detail/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments/EVENT-1'
    )
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
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

  it('renders a real Top 10 ranking preview from a parseable MSA Rankings payload', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { rankings: rankingRows(11), secret_debug_marker: 'ranking-detail-hidden-payload' }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        { snapshot_sequence: 11, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-0', payload: {} },
        { snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Top 10 Ranking Preview' })).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Top 10 ranking preview table' })
    expect(within(table).getByText('1')).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'Ali Farag' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/players/P1/career'
    )
    expect(within(table).getByRole('link', { name: 'EGY' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/countries/EGY'
    )
    expect(within(table).getByText('20000')).toBeInTheDocument()
    expect(within(table).getByText('12')).toBeInTheDocument()
    expect(within(table).getByText('+1')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(11)
    expect(screen.queryByText('Real Player 11')).not.toBeInTheDocument()
    const details = screen.getByText('Show technical payload').closest('details')
    expect(details).not.toHaveAttribute('open')
    expect(screen.getByText(/ranking-detail-hidden-payload/i)).not.toBeVisible()
    expectNoForbiddenViewerActions()
  })


  it('keeps ranking preview players without player IDs as plain text', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: {
        rankings: [{ rank: 1, player_name: 'Name Only Player', country_code: 'WAL', points: 5000, tournaments_counted: 10 }]
      }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    const table = await screen.findByRole('table', { name: 'Top 10 ranking preview table' })
    expect(within(table).getByText('Name Only Player')).toBeInTheDocument()
    expect(within(table).queryByRole('link', { name: 'Name Only Player' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps missing ranking preview countries as plain em dash text', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: {
        rankings: [{ rank: 1, player_id: 'P-MISSING-COUNTRY', player_name: 'Country Missing Player', points: 5000, tournaments_counted: 10 }]
      }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    const table = await screen.findByRole('table', { name: 'Top 10 ranking preview table' })
    const row = within(table).getByText('Country Missing Player').closest('tr') as HTMLElement
    expect(within(row).getAllByRole('cell')[2]).toHaveTextContent('—')
    expect(within(row).queryByRole('link', { name: '—' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders the deferred ranking preview for unknown payload shapes without crashing', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { secret_debug_marker: 'ranking-detail-hidden-payload' }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Top 10 ranking preview table' })).not.toBeInTheDocument()
    const details = screen.getByText('Show technical payload').closest('details')
    expect(details).not.toHaveAttribute('open')
    expect(screen.getByText(/ranking-detail-hidden-payload/i)).not.toBeVisible()
    expectNoForbiddenViewerActions()
  })

  it('renders a real Top 10 Race to Finals preview from a parseable payload', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 5,
      snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { race_to_finals: { rows: raceRows(11) }, secret_debug_marker: 'race-detail-hidden-payload' }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 5, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race/5')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Top 10 Race Preview' })).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Top 10 race preview table' })
    expect(within(table).getByText('1')).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'Mostafa Asal' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/players/R1/career'
    )
    expect(within(table).getByRole('link', { name: 'EGY' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/countries/EGY'
    )
    expect(within(table).getByText('9000')).toBeInTheDocument()
    expect(within(table).getAllByText('8').length).toBeGreaterThan(0)
    expect(within(table).getByText('Qualified')).toBeInTheDocument()
    expect(within(table).getByText('1200')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(11)
    expect(screen.queryByText('Race Player 11')).not.toBeInTheDocument()
    const technicalSection = screen.getByText('Show technical payload').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/race-detail-hidden-payload/i)).not.toBeVisible()
    expectNoForbiddenViewerActions()
  })

  it('renders the deferred Race to Finals preview for unknown payload shapes without crashing', async () => {
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

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(await screen.findByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Top 10 race preview table' })).not.toBeInTheDocument()
    expect(screen.getAllByText('EVENT-1').length).toBeGreaterThan(0)
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
