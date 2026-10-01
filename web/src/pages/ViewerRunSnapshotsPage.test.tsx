import { cleanup, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunSnapshotDetailPage } from './ViewerRunSnapshotsPage'

const api = vi.hoisted(() => ({
  getRaceSnapshot: vi.fn(),
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

function renderRaceRoute(route: string): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/race/:snapshotSequence" element={<ViewerRunSnapshotDetailPage />} />
    </Routes>,
    { route }
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
  for (const label of [
    'Simulate', 'Generate', 'Persist', 'Apply', 'Execute', 'Delete', 'Edit', 'Import',
    'Rollover', 'Rebuild', 'Override', 'Save changes', 'Commit', 'Regenerate', 'Repair',
    'Merge', 'Overwrite'
  ]) {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  }
}

function expectNoAdminLinks(): void {
  screen.queryAllByRole('link').forEach((link) => {
    expect(link.getAttribute('href') ?? '').not.toMatch(/^\/admin/)
  })
}

describe('ViewerRunSnapshotDetailPage Race compatibility', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
  })

  it('keeps invalid detail sequence strings local without API calls', async () => {
    renderRaceRoute('/viewer/runs/viewer-run-1/race/not-a-sequence')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(screen.getByText(/Snapshot sequence "not-a-sequence" is invalid/i)).toBeInTheDocument()
    expect(api.getRaceSnapshot).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders missing Race snapshots as a safe no-data state', async () => {
    api.getRaceSnapshot.mockRejectedValue(new api.ApiError('missing publication', 404))
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })
    renderRaceRoute('/viewer/runs/viewer-run-1/race/404')

    expect(await screen.findByText(/Snapshot sequence 404 was not found for this run/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Payload summary' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Read-only data' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders Race detail API errors without inferring sporting rows', async () => {
    api.getRaceSnapshot.mockRejectedValue(new Error('detail outage'))
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })
    renderRaceRoute('/viewer/runs/viewer-run-1/race/5')

    expect(await screen.findByText(/Failed to load publication: detail outage/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Payload summary' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Mostafa Asal/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('normalizes unsafe neighboring snapshots before previous/next links', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { safe: true }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        null,
        { snapshot_sequence: 11, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-0', payload: {} },
        { snapshot_sequence: { bad: true }, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', payload: {} },
        { snapshot_sequence: 12, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} },
        { snapshot_sequence: -99, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', payload: {} },
        { snapshot_sequence: 13, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-2', payload: {} }
      ]
    })
    renderRaceRoute('/viewer/runs/viewer-run-1/race/12')

    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '#11' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/race/11'
    )
    expect(screen.getByRole('link', { name: '#13' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/race/13'
    )
    expect(screen.queryByRole('link', { name: /#-99/i })).not.toBeInTheDocument()
  })

  it('keeps missing source context fail-soft without inventing links', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { context: 'missing' }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })
    api.getRun.mockRejectedValue(new Error('run outage'))
    api.listEvents.mockRejectedValue(new Error('event outage'))
    renderRaceRoute('/viewer/runs/viewer-run-1/race/12')

    expect(await screen.findByRole('heading', { name: 'Source links' })).toBeInTheDocument()
    expect(screen.getByText('Source event detail unavailable.')).toBeInTheDocument()
    expect(screen.getByText('No ordered-plan match for source event.')).toBeInTheDocument()
    expect(screen.getByText('No week context available.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open source event|Open planned event|Open week/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps parseable Race payloads on conservative detail summary and technical disclosure collapsed', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 5,
      snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: {
        race_to_finals: { rows: raceRows(11) },
        secret_debug_marker: 'race-detail-hidden-payload'
      }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 5, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })
    renderRaceRoute('/viewer/runs/viewer-run-1/race/5')

    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(await screen.findByText(/Snapshot payload table rendering deferred/i)).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: /race preview table/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to race publications/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/race'
    )

    const technicalSection = screen.getByText('Show technical payload').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    await userEvent.click(screen.getByText('Show technical payload'))
    expect(within(technicalSection as HTMLElement).getByText(/race-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })
})
