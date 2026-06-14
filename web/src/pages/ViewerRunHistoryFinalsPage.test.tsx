import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  ViewerRunFinalsPage,
  ViewerRunFinalsQualificationPage,
  ViewerRunFinalsResultPage,
  ViewerRunHistoryPage
} from './ViewerRunHistoryFinalsPage'

const api = vi.hoisted(() => ({
  getRunActivity: vi.fn(),
  getFinalsSummary: vi.fn(),
  getFinalsQualification: vi.fn(),
  getFinalsResult: vi.fn()
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    ...api
  }
})

function renderViewerRoute(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/viewer/runs/:runId/history" element={<ViewerRunHistoryPage />} />
          <Route path="/viewer/runs/:runId/finals" element={<ViewerRunFinalsPage />} />
          <Route path="/viewer/runs/:runId/finals/qualification" element={<ViewerRunFinalsQualificationPage />} />
          <Route path="/viewer/runs/:runId/finals/result" element={<ViewerRunFinalsResultPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function mockApi(): void {
  api.getRunActivity.mockResolvedValue({
    run_id: 'viewer-run-2e',
    items: [
      {
        kind: 'race_snapshot',
        sequence: 8,
        label: 'Race snapshot stored',
        season: 2031,
        week: 40,
        event_id: null,
        snapshot_sequence: 12,
        source_event_id: 'EVENT-40',
        related_run_id: null,
        raw_history_marker_should_be_collapsed: true
      }
    ]
  })
  api.getFinalsSummary.mockResolvedValue({
    run_id: 'viewer-run-2e',
    season: 2031,
    qualification: {
      run_id: 'viewer-run-2e',
      season: 2031,
      source_as_of_season: 2031,
      source_as_of_week: 40,
      qualification: { qualified_player_ids: ['P1', 'P2'], groups: [['P1'], ['P2']] }
    },
    result: {
      run_id: 'viewer-run-2e',
      season: 2031,
      event_id: 'WTF-2031',
      source_as_of_season: 2031,
      source_as_of_week: 41,
      result: { champion_player_id: 'P1', runner_up_player_id: 'P2' }
    }
  })
  api.getFinalsQualification.mockResolvedValue({
    run_id: 'viewer-run-2e',
    season: 2031,
    source_as_of_season: 2031,
    source_as_of_week: 40,
    qualification: { unknown_shape: true, technical_qualification_marker_should_be_collapsed: true }
  })
  api.getFinalsResult.mockResolvedValue({
    run_id: 'viewer-run-2e',
    season: 2031,
    event_id: 'WTF-2031',
    source_as_of_season: 2031,
    source_as_of_week: 41,
    result: { unknown_shape: true, technical_result_marker_should_be_collapsed: true }
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

function expectNoDuplicateRunNav(): void {
  expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  expect(screen.queryByRole('navigation', { name: /Viewer active run quick links/i })).not.toBeInTheDocument()
}

function expectNoUnsafeOutput(): void {
  expect(document.body).not.toHaveTextContent('[object Object]')
  expect(document.body).not.toHaveTextContent(/Fake Champion|Fake Winner|Invented Champion|Invented Winner|Fake Finalist|Invented Finalist|Fake History Entry|Invented History Entry|Fake Standing|Invented Standing|Fake Record|Invented Record|Qualification Standing #1|Champion Player Name/i)
  expectNoForbiddenViewerActions()
}

describe('ViewerRunHistoryFinalsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockApi()
  })

  it('renders History with run activity metadata and no raw JSON as primary content', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2e').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Race snapshot stored')).length).toBeGreaterThan(0)
    expect(screen.getByText('race_snapshot')).toBeInTheDocument()
    expect(await screen.findByText('W40')).toBeInTheDocument()
    expect(screen.getByText('Show technical history data')).toBeInTheDocument()
    expect(within(document.body).queryByText(/raw_history_marker_should_be_collapsed/i)).not.toBeVisible()
    expectNoForbiddenViewerActions()
    expectNoUnsafeOutput()
    expectNoDuplicateRunNav()
  })

  it('renders History route loading/empty/deferred behavior without fake read-model data', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'viewer-run-1', items: [] })
    renderViewerRoute('/viewer/runs/viewer-run-1/history')

    expect(screen.getByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(screen.getByText('Loading history…')).toBeInTheDocument()
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(api.getRunActivity).toHaveBeenCalledWith('viewer-run-1')
    expectNoUnsafeOutput()
  })

  it('renders encoded History run IDs as safe route context and passes decoded runId to the API', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run/alpha #1', items: [] })
    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(api.getRunActivity).toHaveBeenCalledWith('run/alpha #1')
    expect(screen.getAllByText('run/alpha #1').length).toBeGreaterThan(0)
    expectNoUnsafeOutput()
  })

  it('renders History API errors without fake fallback data or expanded technical payloads', async () => {
    api.getRunActivity.mockRejectedValueOnce(new Error('history outage'))
    renderViewerRoute('/viewer/runs/viewer-run-1/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load run activity: history outage/i)).toBeInTheDocument()
    expect(screen.queryByText('Show technical history data')).not.toBeInTheDocument()
    expectNoUnsafeOutput()
  })

  it('renders malformed History payloads scalar-safely without unsafe object output', async () => {
    api.getRunActivity.mockResolvedValueOnce({
      run_id: { unsafe: 'run-object' },
      items: [
        null,
        7,
        'raw history string',
        {},
        {
          kind: { unsafe: 'kind-object' },
          label: { unsafe: 'label-object' },
          sequence: { unsafe: 'sequence-object' },
          event_id: { unsafe: 'event-object' },
          season: { unsafe: 'season-object' },
          week: { unsafe: 'week-object' },
          snapshot_sequence: { unsafe: 'snapshot-object' },
          source_event_id: { unsafe: 'source-event-object' },
          related_run_id: { unsafe: 'related-run-object' }
        }
      ]
    })
    renderViewerRoute('/viewer/runs/viewer-run-1/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(await screen.findByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(screen.getByText('Show technical history data').closest('details')).not.toHaveAttribute('open')
    expectNoUnsafeOutput()
  })

  it('renders Finals overview availability and Viewer links without simulation controls', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2e').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Available')).length).toBeGreaterThan(1)
    expect(await screen.findByText('W40')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Finals qualification' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2e/finals/qualification'
    )
    expect(screen.getByRole('link', { name: 'Open Finals result' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2e/finals/result'
    )
    expect(screen.queryByRole('button', { name: /Simulate World Tour Finals/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Simulate World Tour Finals/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expectNoUnsafeOutput()
    expectNoDuplicateRunNav()
  })

  it('renders Finals loading/empty/deferred behavior without fake qualification data', async () => {
    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: 'viewer-run-1',
      season: 2031,
      qualification: null,
      result: null
    })
    renderViewerRoute('/viewer/runs/viewer-run-1/finals')

    expect(screen.getByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.getByText('Loading Finals summary…')).toBeInTheDocument()
    expect(await screen.findAllByText('This preview is not connected for this data shape yet.')).toHaveLength(2)
    expect(api.getFinalsSummary).toHaveBeenCalledWith('viewer-run-1')
    expectNoUnsafeOutput()
  })

  it('renders encoded Finals run IDs as safe route context and passes decoded runId to the API', async () => {
    api.getFinalsSummary.mockResolvedValueOnce({ run_id: 'run/alpha #1', season: 2031, qualification: null, result: null })
    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(api.getFinalsSummary).toHaveBeenCalledWith('run/alpha #1')
    expect(screen.getAllByText('run/alpha #1').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Open Finals qualification' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/finals/qualification'
    )
    expectNoUnsafeOutput()
  })

  it('renders Finals API errors without fake fallback data', async () => {
    api.getFinalsSummary.mockRejectedValueOnce(new Error('finals outage'))
    renderViewerRoute('/viewer/runs/viewer-run-1/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load Finals summary: finals outage/i)).toBeInTheDocument()
    expect(screen.queryByText('Show technical finals data')).not.toBeInTheDocument()
    expectNoUnsafeOutput()
  })

  it('renders malformed Finals payloads scalar-safely without unsafe object links', async () => {
    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: { unsafe: 'run-object' },
      season: { unsafe: 'season-object' },
      qualification: {
        run_id: { unsafe: 'qualification-run-object' },
        season: { unsafe: 'qualification-season-object' },
        source_as_of_season: { unsafe: 'source-season-object' },
        source_as_of_week: { unsafe: 'source-week-object' },
        qualification: {
          qualified_player_ids: [{ unsafe: 'player-object' }, null, 4],
          groups: [{ unsafe: 'group-object' }],
          ranking_snapshot_sequence: { unsafe: 'ranking-sequence-object' },
          race_snapshot_sequence: { unsafe: 'race-sequence-object' },
          status: { unsafe: 'status-object' },
          points: { unsafe: 'points-object' }
        }
      },
      result: {
        run_id: { unsafe: 'result-run-object' },
        season: { unsafe: 'result-season-object' },
        event_id: { unsafe: 'event-object' },
        source_as_of_season: { unsafe: 'source-season-object' },
        source_as_of_week: { unsafe: 'source-week-object' },
        result: {
          champion_player_id: { unsafe: 'champion-object' },
          runner_up_player_id: { unsafe: 'runner-object' },
          standings: [{ unsafe: 'standing-object' }],
          rank: { unsafe: 'rank-object' },
          points: { unsafe: 'points-object' },
          status: { unsafe: 'status-object' }
        }
      }
    })
    renderViewerRoute('/viewer/runs/viewer-run-1/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Planned event/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Player \[object Object\] profile/i })).not.toBeInTheDocument()
    expectNoUnsafeOutput()
  })

  it('renders Finals Qualification with safe metadata/deferred message and collapsed technical data', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals Qualification' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2e').length).toBeGreaterThan(0)
    expect(await screen.findByText('W40')).toBeInTheDocument()
    expect(screen.getByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    const details = screen.getByText('Show technical finals qualification data').closest('details')
    expect(details).not.toHaveAttribute('open')
    expect(screen.queryByText(/technical_qualification_marker_should_be_collapsed/i)).not.toBeVisible()
    expectNoForbiddenViewerActions()
    expectNoDuplicateRunNav()
  })

  it('renders Finals Result with safe metadata/deferred message and collapsed technical data', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals/result')

    expect(await screen.findByRole('heading', { name: 'Finals Result' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2e').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Available')).length).toBeGreaterThan(0)
    expect(screen.getByText('W41')).toBeInTheDocument()
    expect(screen.getByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    const details = screen.getByText('Show technical finals result data').closest('details')
    expect(details).not.toHaveAttribute('open')
    expect(screen.queryByText(/technical_result_marker_should_be_collapsed/i)).not.toBeVisible()
    expectNoForbiddenViewerActions()
    expectNoDuplicateRunNav()
  })
})
