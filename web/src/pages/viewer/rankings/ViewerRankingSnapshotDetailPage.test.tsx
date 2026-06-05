import { Routes, Route } from 'react-router-dom'
import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerRankingSnapshotDetailPage } from './ViewerRankingSnapshotDetailPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number

    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  },
  getRankingSnapshot: vi.fn(),
  getRaceSnapshot: vi.fn(),
  getRun: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)

function renderDetail(route = '/viewer/runs/run%20alpha/rankings/12'): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/rankings/:snapshotSequence" element={<ViewerRankingSnapshotDetailPage />} />
    </Routes>,
    { route }
  )
}

describe('ViewerRankingSnapshotDetailPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.getRankingSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'ranking',
      source_event_id: 'EVT ALPHA',
      payload: { rows: [{ player_id: 'p1', rank: 1 }], as_of_week: 8 }
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 11, snapshot_kind: 'ranking', source_event_id: 'EVT OLD', payload: {} },
        { snapshot_sequence: 12, snapshot_kind: 'ranking', source_event_id: 'EVT ALPHA', payload: {} }
      ]
    })
    api.getRun.mockResolvedValue({
      season_state: {
        ordered_events: [
          { event_id: 'EVT ALPHA', week: 8, category: 'Gold', tour: 'World Tour', template_id: 'gold-open' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({ events: [{ event_id: 'EVT ALPHA', event_sequence: 42, week: 8 }] })
  })

  it('renders loading and then successful snapshot details with safe links and payload summary', async () => {
    renderDetail()

    expect(screen.getByText('Loading publication...')).toBeInTheDocument()
    expect(await screen.findByText('EVT ALPHA')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText('run alpha')).toBeInTheDocument()
    expect(screen.getAllByText('12').length).toBeGreaterThan(0)
    expect(screen.getByText('Payload summary')).toBeInTheDocument()
    expect(screen.getByText('Payload type')).toBeInTheDocument()
    expect(screen.getByText('Top-level keys')).toBeInTheDocument()
    expect(screen.getByText('as_of_week, rows')).toBeInTheDocument()
    expect(screen.getByText('Conservative read-only payload summary. The Viewer does not infer standings from unknown fields.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to ranking publications' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(screen.getByRole('link', { name: 'Open source event' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments/EVT%20ALPHA')
    expect(screen.getByRole('link', { name: 'Open planned event' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT%20ALPHA')
    expectNoForbiddenViewerActions()
  })

  it('renders invalid route params as a safe empty state', () => {
    renderDetail('/viewer/runs/run%20alpha/rankings/not-a-sequence')

    expect(screen.getByText('Snapshot sequence "not-a-sequence" is invalid. Use a positive integer sequence.')).toBeInTheDocument()
    expect(api.getRankingSnapshot).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders a temporarily unavailable state for API errors', async () => {
    api.getRankingSnapshot.mockRejectedValue(new Error('network down'))

    renderDetail()

    expect(await screen.findByText('Failed to load publication: network down')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders a no-data state for missing snapshots', async () => {
    api.getRankingSnapshot.mockRejectedValue({ status: 404 })

    renderDetail()

    expect(await screen.findByText('Snapshot sequence 12 was not found for this run.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
