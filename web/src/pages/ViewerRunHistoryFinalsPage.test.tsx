import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import {
  ViewerRunFinalsPage,
  ViewerRunFinalsQualificationPage,
  ViewerRunFinalsResultPage,
  ViewerRunHistoryPage
} from './ViewerRunHistoryFinalsPage'

const api = vi.hoisted(() => ({
  getRunActivity: vi.fn(),
  getViewerFinalsRace: vi.fn(),
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
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/history" element={<ViewerRunHistoryPage />} />
      <Route path="/viewer/runs/:runId/finals" element={<ViewerRunFinalsPage />} />
      <Route path="/viewer/runs/:runId/finals/qualification" element={<ViewerRunFinalsQualificationPage />} />
      <Route path="/viewer/runs/:runId/finals/result" element={<ViewerRunFinalsResultPage />} />
    </Routes>,
    { route }
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
  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'viewer-run-2e',
    viewer_branch_id: 'branch-viewer',
    latest_target_season_index: 31,
    publications: [{
      schema_version: 'viewer_finals_race_publication.v1',
      product_run_id: 'viewer-run-2e',
      viewer_branch_id: 'branch-viewer',
      target_season_index: 31,
      cutoff_season_index: 31,
      cutoff_week: 40,
      best_n: 2,
      selection_published: true,
      finals_event_id: 'WTF-2031',
      rows: [
        { rank: 1, player_id: 'P1', race_points: 125, tournaments_counted: 2, finals_selected: true, finals_seed: 1, qualification_source: 'direct_entry', counted_results: [] },
        { rank: 2, player_id: 'P2', race_points: 90, tournaments_counted: 1, finals_selected: false, finals_seed: null, qualification_source: null, counted_results: [] },
        { rank: 3, player_id: 'P3', race_points: 80, tournaments_counted: 1, finals_selected: true, finals_seed: 2, qualification_source: 'race', counted_results: [] }
      ]
    }]
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

  it('renders canonical confirmed Finals field including effective replacement', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-2e')
    expect((await screen.findAllByText('Published')).length).toBeGreaterThan(0)
    expect(screen.getByText('WTF-2031')).toBeInTheDocument()

    const table = screen.getByRole('table', { name: 'Canonical World Tour Finals participants' })
    expect(within(table).getByRole('link', { name: 'P1' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2e/players/P1/career')
    expect(within(table).getByRole('link', { name: 'P3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2e/players/P3/career')
    expect(within(table).queryByText('P2')).not.toBeInTheDocument()
    expect(within(table).getByText('Direct entry')).toBeInTheDocument()
    expect(within(table).getByText('Race')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expectNoDuplicateRunNav()
  })

  it('renders canonical Finals empty publication without inventing qualification', async () => {
    api.getViewerFinalsRace.mockResolvedValueOnce({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'viewer-run-1',
      viewer_branch_id: 'branch-viewer',
      latest_target_season_index: null,
      publications: []
    })
    renderViewerRoute('/viewer/runs/viewer-run-1/finals')

    expect(screen.getByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.getByText('Loading canonical Finals publication…')).toBeInTheDocument()
    expect(await screen.findByText('No canonical World Tour Finals Race publication exists yet.')).toBeInTheDocument()
    expect(screen.getByText('Confirmed World Tour Finals participants are not published yet.')).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-1')
  })

  it('passes decoded Product Run ID to canonical Finals publication API', async () => {
    api.getViewerFinalsRace.mockResolvedValueOnce({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      latest_target_season_index: null,
      publications: []
    })
    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run/alpha #1')
    expect(screen.getAllByText('run/alpha #1').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Open Finals qualification' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/finals/qualification'
    )
  })

  it('renders canonical Finals API errors without legacy fallback', async () => {
    api.getViewerFinalsRace.mockRejectedValueOnce(new Error('finals publication outage'))
    renderViewerRoute('/viewer/runs/viewer-run-1/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load canonical Finals publication: finals publication outage/i)).toBeInTheDocument()
    expect(screen.queryByText('Show technical finals data')).not.toBeInTheDocument()
  })

  it('renders Finals Qualification from canonical confirmed participant publication', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals Qualification' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-2e')
    expect((await screen.findAllByText('W40')).length).toBeGreaterThan(0)
    expect(screen.getByText('WTF-2031')).toBeInTheDocument()

    const table = screen.getByRole('table', { name: 'Canonical World Tour Finals participants' })
    expect(within(table).getByRole('link', { name: 'P1' })).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'P3' })).toBeInTheDocument()
    expect(within(table).queryByText('P2')).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical finals qualification data')).not.toBeInTheDocument()
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
