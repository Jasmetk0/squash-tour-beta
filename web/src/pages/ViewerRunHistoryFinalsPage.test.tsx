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
    expectNoDuplicateRunNav()
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
    expectNoDuplicateRunNav()
  })

  it('renders Finals Qualification with safe metadata/deferred message and collapsed technical data', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals Qualification' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2e').length).toBeGreaterThan(0)
    expect(await screen.findByText('W40')).toBeInTheDocument()
    expect(screen.getByText('Finals qualification preview is not connected for this payload shape yet.')).toBeInTheDocument()
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
    expect(screen.getByText('Finals result preview is not connected for this payload shape yet.')).toBeInTheDocument()
    const details = screen.getByText('Show technical finals result data').closest('details')
    expect(details).not.toHaveAttribute('open')
    expect(screen.queryByText(/technical_result_marker_should_be_collapsed/i)).not.toBeVisible()
    expectNoForbiddenViewerActions()
    expectNoDuplicateRunNav()
  })
})
