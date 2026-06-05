import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../../test/viewerTestUtils'
import { ViewerHistoryPage } from './ViewerHistoryPage'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  getRunActivity: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)


function renderHistory(): void {
  renderWithViewerProviders(<ViewerHistoryPage />)
}

function resetApiMocks(): void {
  api.getRun.mockResolvedValue({
    run: { run_id: 'history run', season: 2032, seed: 7, next_event_index: 1, total_events: 3, completed_event_ids: ['EVT-1'] },
    season_state: {
      season: 2032,
      next_event_index: 1,
      completed_event_ids: ['EVT-1'],
      ordered_events: [
        { event_id: 'EVT-1', season: 2032, week: 11, tour: 'World Tour', category: 'Gold', template_id: 'TPL-1' }
      ]
    }
  })
  api.getRunActivity.mockResolvedValue({
    run_id: 'history run',
    items: [
      { kind: 'event', sequence: 2, label: 'Event completed', event_id: 'EVT-1', season: 2032, week: 11 },
      { kind: 'ranking_snapshot', sequence: 5, label: 'Ranking snapshot stored', snapshot_sequence: 9, season: 2032, week: 11 }
    ]
  })
  api.getRunStatusSummary.mockResolvedValue({
    run_id: 'history run',
    season: 2032,
    seed: 7,
    progress: { next_event_index: 1, total_events: 3, completed_event_count: 1 },
    finals: { qualification_available: false, result_available: false },
    rollover: null,
    source: { source_type: 'fresh_seed', parent_run_id: null },
    lineage: { child_run_count: 0 },
    history_counts: { events: 1, ranking_snapshots: 1, race_snapshots: 1 }
  })
  api.listEvents.mockResolvedValue({ run_id: 'history run', events: [{ event_id: 'EVT-1', event_sequence: 1, template_id: 'TPL-1', week: 11 }] })
  api.listRankingSnapshots.mockResolvedValue({ snapshots: [{ snapshot_sequence: 9, snapshot_kind: 'ranking', source_event_id: 'EVT-1', payload: {} }] })
  api.listRaceSnapshots.mockResolvedValue({ snapshots: [{ snapshot_sequence: 4, snapshot_kind: 'race', source_event_id: 'EVT-1', payload: {} }] })
}

describe('ViewerHistoryPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    resetApiMocks()
  })

  it('shows the existing empty state when no active run is selected', () => {
    renderHistory()

    expect(screen.getByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(screen.getByText('Read-only history and season timeline for the selected Viewer run.')).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()

    expectNoForbiddenViewerActions()
  })

  it('renders active run history counts, latest activity, and source links', async () => {
    setViewerActiveRunId('history run')

    renderHistory()

    expect(await screen.findByText('History summary')).toBeInTheDocument()
    expect(screen.getByText('history run')).toBeInTheDocument()
    expect(screen.getByText('Activity item count')).toBeInTheDocument()
    expect(screen.getByText('Event count')).toBeInTheDocument()
    expect(screen.getByText('Ranking snapshot count')).toBeInTheDocument()
    expect(screen.getByText('Race snapshot count')).toBeInTheDocument()
    expect(await screen.findByText('Ranking snapshot stored')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: '#9' })[0]).toHaveAttribute('href', '/viewer/runs/history%20run/rankings/9')
    expect(screen.getByRole('link', { name: '#4' })).toHaveAttribute('href', '/viewer/runs/history%20run/race/4')
    expect(screen.getByRole('link', { name: 'Open active run history' })).toHaveAttribute('href', '/viewer/runs/history%20run/history')
  })
})
