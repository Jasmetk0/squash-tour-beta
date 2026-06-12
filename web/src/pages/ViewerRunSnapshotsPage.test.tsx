import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
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

function mockRunMetadata(runId = 'viewer-run-1', sourceEventId = 'EVENT-1'): void {
  api.getRun.mockResolvedValue({
    run: {
      run_id: runId,
      season: 2027,
      seed: 42,
      config_version: 'v1',
      config_fingerprint: 'fp',
      next_event_index: 1,
      total_events: 2,
      completed_event_ids: [sourceEventId]
    },
    season_state: {
      season: 2027,
      next_event_index: 1,
      completed_event_ids: [sourceEventId],
      ordered_events: [
        { event_id: sourceEventId, season: 2027, week: 3, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
        { event_id: 'EVENT-2', season: 2027, week: 4, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
      ]
    }
  })
  api.listEvents.mockResolvedValue({
    run_id: runId,
    events: [{ event_sequence: 8, event_id: sourceEventId, season: 2027, week: 3, template_id: 'WT-PLAT', tournament_result: {} }]
  })
}

function mockRunMetadataWithEvents(
  runId = 'viewer-run-1',
  events: Array<{ event_id: string; week: number; tour: string; category: string; template_id: string }>
): void {
  api.getRun.mockResolvedValue({
    run: {
      run_id: runId,
      season: 2027,
      seed: 42,
      config_version: 'v1',
      config_fingerprint: 'fp',
      next_event_index: events.length,
      total_events: events.length,
      completed_event_ids: events.map((event) => event.event_id)
    },
    season_state: {
      season: 2027,
      next_event_index: events.length,
      completed_event_ids: events.map((event) => event.event_id),
      ordered_events: events.map((event) => ({ ...event, season: 2027 }))
    }
  })
  api.listEvents.mockResolvedValue({
    run_id: runId,
    events: events.map((event, index) => ({
      event_sequence: index + 1,
      event_id: event.event_id,
      season: 2027,
      week: event.week,
      template_id: event.template_id,
      tournament_result: {}
    }))
  })
}

function mockPhase9ESnapshotContext(): void {
  mockRunMetadataWithEvents('viewer-run-1', [
    { event_id: 'EVENT-1', week: 3, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
    { event_id: 'EVENT-2', week: 4, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' },
    { event_id: 'EVENT-3', week: 5, tour: 'World Tour', category: 'Bronze', template_id: 'WT-BRONZE' }
  ])
}

function mockRankingSnapshotsForSelection(): void {
  api.listRankingSnapshots.mockResolvedValue({
    run_id: 'viewer-run-1',
    snapshots: [
      { snapshot_sequence: 11, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} },
      { snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-2', payload: {} }
    ]
  })
}

function selectedPublicationSummary(): HTMLElement {
  const heading = screen.getByRole('heading', { name: 'Latest selected publication summary' })
  const summary = heading.closest('article')
  expect(summary).not.toBeNull()
  return summary as HTMLElement
}

function expectSelectedSummarySequence(sequence: number): void {
  const summary = selectedPublicationSummary()
  expect(within(summary).getByText('Snapshot sequence')).toBeInTheDocument()
  expect(within(summary).getByText(String(sequence))).toBeInTheDocument()
  expect(within(summary).getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute(
    'href',
    `/viewer/runs/viewer-run-1/rankings/${sequence}`
  )
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

function expectNoAdminLinks(): void {
  screen.queryAllByRole('link').forEach((link) => {
    expect(link.getAttribute('href') ?? '').not.toMatch(/^\/admin/)
  })
}

function expectNoPreviewTables(): void {
  expect(screen.queryByRole('table', { name: /ranking preview table/i })).not.toBeInTheDocument()
  expect(screen.queryByRole('table', { name: /race preview table/i })).not.toBeInTheDocument()
}

describe('ViewerRunSnapshotListPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
  })

  it('keeps the ranking list API error state safe and read-only', async () => {
    api.listRankingSnapshots.mockRejectedValue(new Error('ranking list outage'))

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load publications/i)).toBeInTheDocument()
    expect(screen.getByText(/ranking list outage/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Latest selected publication summary' })).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })

  it('keeps the race list API error state safe and read-only', async () => {
    api.listRaceSnapshots.mockRejectedValue(new Error('race list outage'))

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load publications/i)).toBeInTheDocument()
    expect(screen.getByText(/race list outage/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Latest selected publication summary' })).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })

  it('renders an empty ranking list without fake selected publication data', async () => {
    api.listRankingSnapshots.mockResolvedValue([])

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Latest selected publication summary' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Snapshot sequence \d+/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Source event EVENT/i)).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('renders an empty race list without fake selected publication data', async () => {
    api.listRaceSnapshots.mockResolvedValue([])

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Latest selected publication summary' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Snapshot sequence \d+/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Source event EVENT/i)).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('drops unsafe ranking snapshot entries and renders only the valid snapshot', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        null,
        123,
        'bad',
        {},
        { snapshot_sequence: 'bad', snapshot_kind: 'WEEKLY_PUBLICATION', payload: {} },
        {
          snapshot_sequence: 18,
          snapshot_kind: 'WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-1',
          payload: {}
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Ranking publication 18' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/18')
    expect(screen.getAllByText('WEEKLY_PUBLICATION').length).toBeGreaterThan(0)
    expect(screen.queryByRole('article', { name: /Ranking publication bad/i })).not.toBeInTheDocument()
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('drops unsafe race snapshot entries and renders only the valid snapshot', async () => {
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        null,
        123,
        'bad',
        {},
        { snapshot_sequence: 'bad', snapshot_kind: 'RACE_WEEKLY_PUBLICATION', payload: {} },
        {
          snapshot_sequence: 7,
          snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-1',
          payload: {}
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Race publication 7' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open race detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/race/7')
    expect(screen.getAllByText('RACE_WEEKLY_PUBLICATION').length).toBeGreaterThan(0)
    expect(screen.queryByRole('article', { name: /Race publication bad/i })).not.toBeInTheDocument()
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('normalizes lists with only unsafe snapshot entries to the empty state', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [null, 123, 'bad', {}, { snapshot_sequence: 'bad', snapshot_kind: 'WEEKLY_PUBLICATION', payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Latest selected publication summary' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Snapshot sequence \d+/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Source event EVENT/i)).not.toBeInTheDocument()
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })


  it('falls back from an invalid selectedSequence query param to the first valid filtered snapshot', async () => {
    mockPhase9ESnapshotContext()
    mockRankingSnapshotsForSelection()

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings?selectedSequence=abc')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expectSelectedSummarySequence(11)
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/11')
    expect(screen.queryByText(/abc/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('article', { name: /Ranking publication abc/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('falls back when selectedSequence points to a missing snapshot without inventing the missing summary', async () => {
    mockPhase9ESnapshotContext()
    mockRankingSnapshotsForSelection()

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings?selectedSequence=999')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expectSelectedSummarySequence(11)
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/11')
    expect(screen.queryByRole('article', { name: 'Ranking publication 999' })).not.toBeInTheDocument()
    expect(screen.queryByText('999')).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('honors a valid selectedSequence query param for an existing filtered snapshot', async () => {
    mockPhase9ESnapshotContext()
    mockRankingSnapshotsForSelection()

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings?selectedSequence=12')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expectSelectedSummarySequence(12)
    expect(screen.getByRole('button', { name: /Ranking publication #12/i })).toHaveAttribute('aria-current', 'true')
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/12')
    expectNoForbiddenViewerActions()
  })

  it('moves the selected publication when the week filter removes the URL-selected snapshot', async () => {
    const user = userEvent.setup()
    mockPhase9ESnapshotContext()
    mockRankingSnapshotsForSelection()

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings?selectedSequence=12')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expectSelectedSummarySequence(12)

    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter publications by week' }), '3')

    await waitFor(() => expectSelectedSummarySequence(11))
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/11')
    expect(screen.queryByRole('article', { name: 'Ranking publication 12' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('moves the selected publication when the category filter removes the URL-selected snapshot', async () => {
    const user = userEvent.setup()
    mockPhase9ESnapshotContext()
    mockRankingSnapshotsForSelection()

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings?selectedSequence=12')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expectSelectedSummarySequence(12)

    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter publications by category' }), 'Platinum')

    await waitFor(() => expectSelectedSummarySequence(11))
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/11')
    expect(screen.queryByRole('article', { name: 'Ranking publication 12' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('moves the selected publication when the case-insensitive source event filter removes it', async () => {
    const user = userEvent.setup()
    mockPhase9ESnapshotContext()
    mockRankingSnapshotsForSelection()

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings?selectedSequence=12')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expectSelectedSummarySequence(12)

    await user.type(screen.getByRole('textbox', { name: 'Filter publications by source event' }), 'event-1')

    await waitFor(() => expectSelectedSummarySequence(11))
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/11')
    expect(screen.queryByRole('article', { name: 'Ranking publication 12' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('filters slash/hash source events and keeps generated links encoded and Viewer-only', async () => {
    const user = userEvent.setup()
    const sourceEventId = 'EVENT/SLASH#HASH'
    const encodedSourceEventId = encodeURIComponent(sourceEventId)
    mockRunMetadataWithEvents('viewer-run-1', [
      { event_id: sourceEventId, week: 6, tour: 'World Tour', category: 'Platinum', template_id: 'WT-SLASH' },
      { event_id: 'EVENT-OTHER', week: 7, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-OTHER' }
    ])
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        { snapshot_sequence: 31, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: sourceEventId, payload: {} },
        { snapshot_sequence: 32, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-OTHER', payload: {} }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Filter publications by source event' }), 'slash#hash')

    await waitFor(() => expectSelectedSummarySequence(31))
    expect(screen.getByRole('article', { name: 'Ranking publication 31' })).toBeInTheDocument()
    expect(screen.queryByRole('article', { name: 'Ranking publication 32' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      `/viewer/runs/viewer-run-1/calendar/${encodedSourceEventId}`
    )
    expect(screen.getByRole('link', { name: /Open tournament detail/i })).toHaveAttribute(
      'href',
      `/viewer/runs/viewer-run-1/tournaments/${encodedSourceEventId}`
    )
    screen.queryAllByRole('link').forEach((link) => {
      const href = link.getAttribute('href') ?? ''
      expect(href).toMatch(/^\/viewer\//)
      expect(href).not.toContain(`/calendar/${sourceEventId}`)
      expect(href).not.toContain(`/tournaments/${sourceEventId}`)
    })
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })

  it('clears selected publication UI when filters match no publications without inventing snapshot data', async () => {
    const user = userEvent.setup()
    mockPhase9ESnapshotContext()
    mockRankingSnapshotsForSelection()

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings?selectedSequence=12')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expectSelectedSummarySequence(12)

    await user.type(screen.getByRole('textbox', { name: 'Filter publications by source event' }), 'NO-MATCH')

    expect(await screen.findByText('No publications match the current filters.')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Latest selected publication summary' })).not.toBeInTheDocument()
    })
    expect(screen.queryByRole('link', { name: /Open ranking detail/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('article', { name: /Ranking publication 999/i })).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
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

  it('renders a safe selected ranking publication preview table with Viewer-only links', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        {
          snapshot_sequence: 12,
          snapshot_kind: 'WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-1',
          payload: { rankings: rankingRows(2) }
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    const table = await screen.findByRole('table', { name: 'Latest selected Top 10 ranking preview table' })
    expect(within(table).getByRole('link', { name: 'Ali Farag' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/players/P1/career'
    )
    expect(within(table).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/countries/EGY')
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/12')
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/calendar/EVENT-1'
    )
    expect(screen.getByRole('link', { name: /Open tournament detail/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments/EVENT-1'
    )
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })

  it('renders a safe selected race publication preview table with Viewer-only links', async () => {
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        {
          snapshot_sequence: 5,
          snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-1',
          payload: { race_to_finals: { rows: raceRows(2) } }
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race')

    const table = await screen.findByRole('table', { name: 'Latest selected Top 10 race preview table' })
    expect(within(table).getByRole('link', { name: 'Mostafa Asal' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/players/R1/career'
    )
    expect(within(table).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/countries/EGY')
    expect(screen.getByRole('link', { name: /Open race detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/race/5')
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/calendar/EVENT-1'
    )
    expect(screen.getByRole('link', { name: /Open tournament detail/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments/EVENT-1'
    )
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })

  it('keeps malformed selected publication payloads on the existing empty preview state while preserving detail links', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        {
          snapshot_sequence: 16,
          snapshot_kind: 'WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-1',
          payload: { rankings: [{ rank: { value: 1 }, player_name: { label: 'Unsafe' }, points: { value: 100 } }] }
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Latest selected Top 10 ranking preview table' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/16')
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps malformed selected race payloads on the existing empty preview state while preserving detail links', async () => {
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        {
          snapshot_sequence: 6,
          snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
          source_event_id: 'EVENT-1',
          payload: { race_to_finals: { rows: [{ position: { value: 1 }, player_name: { label: 'Unsafe' }, race_points: { value: 100 } }] } }
        }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race')

    expect(await screen.findByRole('heading', { name: 'Latest selected publication summary' })).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Latest selected Top 10 race preview table' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open race detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/race/6')
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('encodes run and source event IDs in Viewer-only ranking list links', async () => {
    const runId = 'viewer run/with#hash'
    const sourceEventId = 'EVENT/SLASH#HASH'
    const encodedRunId = encodeURIComponent(runId)
    const encodedSourceEventId = encodeURIComponent(sourceEventId)
    mockRunMetadata(runId, sourceEventId)
    api.listRankingSnapshots.mockResolvedValue({
      run_id: runId,
      snapshots: [
        {
          snapshot_sequence: 22,
          snapshot_kind: 'WEEKLY_PUBLICATION',
          source_event_id: sourceEventId,
          payload: { rankings: rankingRows(1) }
        }
      ]
    })

    renderViewerSnapshotRoute(`/viewer/runs/${encodedRunId}/rankings`)

    const table = await screen.findByRole('table', { name: 'Latest selected Top 10 ranking preview table' })
    expect(screen.getByRole('link', { name: /Open ranking detail/i })).toHaveAttribute(
      'href',
      `/viewer/runs/${encodedRunId}/rankings/22`
    )
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      `/viewer/runs/${encodedRunId}/calendar/${encodedSourceEventId}`
    )
    expect(screen.getByRole('link', { name: /Open tournament detail/i })).toHaveAttribute(
      'href',
      `/viewer/runs/${encodedRunId}/tournaments/${encodedSourceEventId}`
    )
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', `/viewer/runs/${encodedRunId}/weeks/3`)
    expect(within(table).getByRole('link', { name: 'Ali Farag' })).toHaveAttribute(
      'href',
      `/viewer/runs/${encodedRunId}/players/P1/career`
    )
    expect(screen.queryByRole('link', { name: /Admin/i })).not.toBeInTheDocument()
    screen.queryAllByRole('link').forEach((link) => {
      const href = link.getAttribute('href') ?? ''
      expect(href).toMatch(/^\/viewer\//)
      expect(href).not.toContain(`/viewer/runs/${runId}/`)
      expect(href).not.toContain(`/calendar/${sourceEventId}`)
      expect(href).not.toContain(`/tournaments/${sourceEventId}`)
    })
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })

})

describe('ViewerRunSnapshotDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
  })

  it('keeps invalid ranking detail sequence strings local without calling detail APIs', async () => {
    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/not-a-sequence')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText(/Snapshot sequence "not-a-sequence" is invalid/i)).toBeInTheDocument()
    expect(api.getRankingSnapshot).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })

  it('rejects zero and negative detail sequences without detail API calls or fake snapshots', async () => {
    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/0')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText(/Snapshot sequence "0" is invalid/i)).toBeInTheDocument()
    expect(api.getRankingSnapshot).not.toHaveBeenCalled()
    expect(screen.queryByRole('heading', { name: 'Payload summary' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Technical snapshot record/i)).not.toBeInTheDocument()
    expectNoPreviewTables()

    cleanup()
    vi.resetAllMocks()
    mockRunMetadata()

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race/-1')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(screen.getByText(/Snapshot sequence "-1" is invalid/i)).toBeInTheDocument()
    expect(api.getRaceSnapshot).not.toHaveBeenCalled()
    expect(screen.queryByRole('heading', { name: 'Payload summary' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Technical snapshot record/i)).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('renders missing ranking snapshots as a safe no-data detail state', async () => {
    api.getRankingSnapshot.mockRejectedValue(new api.ApiError('missing publication', 404))
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/404')

    expect(await screen.findByText(/Snapshot sequence 404 was not found for this run/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Payload summary' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Read-only data' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Technical snapshot record/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Open source event/i)).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('renders race snapshot API errors without inferring rows or unsafe actions', async () => {
    api.getRaceSnapshot.mockRejectedValue(new Error('detail outage'))
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/race/5')

    expect(await screen.findByText(/Failed to load publication: detail outage/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Payload summary' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Player Alpha|Mostafa Asal/i)).not.toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('still renders current detail metadata when neighboring ranking list lookup fails', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { secret_debug_marker: 'detail-survives-list-outage' }
    })
    api.listRankingSnapshots.mockRejectedValue(new Error('neighbor outage'))

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(screen.getByText('WEEKLY_PUBLICATION')).toBeInTheDocument()
    expect(screen.getAllByText('None').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(/Snapshot payload table rendering deferred/i)).toBeInTheDocument()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('keeps source context unavailable and does not invent links when run and event context fail', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { context: 'missing' }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })
    api.getRun.mockRejectedValue(new Error('run outage'))
    api.listEvents.mockRejectedValue(new Error('event outage'))

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    expect(await screen.findByRole('heading', { name: 'Source links' })).toBeInTheDocument()
    expect(screen.getAllByText('No ordered-plan match').length).toBeGreaterThan(0)
    expect(screen.getByText('Source event detail unavailable.')).toBeInTheDocument()
    expect(screen.getByText('No ordered-plan match for source event.')).toBeInTheDocument()
    expect(screen.getByText('No week context available.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open source event/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open planned event/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week/i })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('normalizes unsafe neighboring list entries before rendering previous and next links', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { safe: true }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        null,
        { snapshot_sequence: 11, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-0', payload: {} },
        { snapshot_sequence: { bad: true }, snapshot_kind: 'WEEKLY_PUBLICATION', payload: {} },
        { snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} },
        { snapshot_sequence: -99, snapshot_kind: 'WEEKLY_PUBLICATION', payload: {} },
        { snapshot_sequence: 13, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-2', payload: {} },
        { snapshot_sequence: 14, snapshot_kind: { bad: true }, payload: {} }
      ]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '#11' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/11')
    expect(screen.getByRole('link', { name: '#13' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/rankings/13')
    expect(screen.queryByRole('link', { name: /#-99|#14/i })).not.toBeInTheDocument()
    expect(document.body.textContent).not.toContain('[object Object]')
    expectNoForbiddenViewerActions()
  })

  it('treats non-string source_event_id values as absent source context', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: { bad: true } as unknown,
      payload: { source_event_id: { bad: true }, visible_payload_marker: 'non-string-source-payload-summary' }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    expect(await screen.findByText('No source event recorded')).toBeInTheDocument()
    expect(screen.getByText('Source event detail unavailable.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open source event|Open planned event|Open week/i })).not.toBeInTheDocument()
    expect(document.body.textContent).not.toContain('[object Object]')
    expect(screen.getByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(screen.getByText('Field: source_event_id')).toBeInTheDocument()
    expect(screen.getByText('Object (1 key)')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('encodes source_event_id links and keeps them Viewer-only', async () => {
    const sourceEventId = 'EVENT/SLASH#HASH'
    mockRunMetadataWithEvents('viewer-run-1', [
      { event_id: sourceEventId, week: 9, tour: 'World Tour', category: 'Gold', template_id: 'WT-GOLD' }
    ])
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 22,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: sourceEventId,
      payload: { source: sourceEventId }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 22, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: sourceEventId, payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/22')

    expect(await screen.findByRole('heading', { name: 'Source links' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open source event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments/EVENT%2FSLASH%23HASH'
    )
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/calendar/EVENT%2FSLASH%23HASH'
    )
    expect(screen.getByRole('link', { name: /Open week W9/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/9')
    screen.getAllByRole('link').forEach((link) => {
      expect(link.getAttribute('href') ?? '').toMatch(/^\/viewer\//)
    })
    expectNoAdminLinks()
    expectNoForbiddenViewerActions()
  })

  it('keeps technical payload disclosure collapsed by default until explicitly opened', async () => {
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { secret_debug_marker: 'collapsed-technical-marker', rankings: rankingRows(2) }
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })

    renderViewerSnapshotRoute('/viewer/runs/viewer-run-1/rankings/12')

    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    const technicalSection = screen.getByText('Show technical payload').closest('details') as HTMLElement
    expect(technicalSection).not.toHaveAttribute('open')
    const hiddenMarker = within(technicalSection).queryByText(/collapsed-technical-marker/i)
    if (hiddenMarker) expect(hiddenMarker).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical payload'))
    expect(within(technicalSection).getByText(/collapsed-technical-marker/i)).toBeVisible()
    expectNoPreviewTables()
    expectNoForbiddenViewerActions()
  })

  it('keeps parseable MSA Rankings detail payloads on the conservative summary path', async () => {
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
    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(await screen.findByText(/Snapshot payload table rendering deferred/i)).toBeInTheDocument()
    expect(screen.queryByText('Top 10 Ranking Preview')).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Top 10 ranking preview table' })).not.toBeInTheDocument()
    const details = screen.getByText('Show technical payload').closest('details')
    expect(details).not.toHaveAttribute('open')
    expectNoForbiddenViewerActions()
  })


  it('does not render ranking preview player links on detail pages', async () => {
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

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(screen.queryByText('Top 10 Ranking Preview')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Name Only Player' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not render missing ranking preview country cells on detail pages', async () => {
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

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(screen.queryByText('Top 10 Ranking Preview')).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Top 10 ranking preview table' })).not.toBeInTheDocument()
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
    expect(await screen.findByText(/Snapshot payload table rendering deferred/i)).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Top 10 ranking preview table' })).not.toBeInTheDocument()
    const details = screen.getByText('Show technical payload').closest('details')
    expect(details).not.toHaveAttribute('open')
    expectNoForbiddenViewerActions()
  })

  it('keeps parseable Race to Finals detail payloads on the conservative summary path', async () => {
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
    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(await screen.findByText(/Snapshot payload table rendering deferred/i)).toBeInTheDocument()
    expect(screen.queryByText('Top 10 Race Preview')).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Top 10 race preview table' })).not.toBeInTheDocument()
    const technicalSection = screen.getByText('Show technical payload').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
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
    expect(await screen.findByText(/Snapshot payload table rendering deferred/i)).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Top 10 race preview table' })).not.toBeInTheDocument()
    expect(screen.getAllByText('EVENT-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('W3').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Back to race publications/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/race')
    const technicalSection = screen.getByText('Show technical payload').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    await userEvent.click(screen.getByText('Show technical payload'))
    expect(within(technicalSection as HTMLElement).getByText(/race-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })
})
