import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../test/viewerTestUtils'
import { ViewerHomePage } from './ViewerHomePage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRun: vi.fn(),
  getRunActivity: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRuns: vi.fn()
}))

vi.mock('../../api/client', () => api)


function sampleRun() {
  return {
    run_id: 'run alpha',
    season: 2031,
    seed: 42,
    progress: {
      next_event_index: 0,
      total_events: 2,
      completed_event_count: 1
    },
    source_type: 'fresh_seed',
    parent_run_id: null,
    child_run_count: 0,
    created_at: '2031-09-01T00:00:00Z',
    updated_at: '2031-09-02T00:00:00Z'
  }
}

function resetApiMocks(): void {
  api.listRuns.mockResolvedValue({ runs: [sampleRun()] })
  api.getRun.mockResolvedValue({
    run: { run_id: 'run alpha', season: 2031, seed: 42, next_event_index: 0, total_events: 2, completed_event_ids: ['EVT-OLD'] },
    season_state: {
      season: 2031,
      next_event_index: 0,
      completed_event_ids: ['EVT-OLD'],
      ordered_events: [
        { event_id: 'EVT-NEXT', season: 2031, week: 7, tour: 'World Tour', category: 'Gold', template_id: 'TPL-NEXT' },
        { event_id: 'EVT-SAME-WEEK', season: 2031, week: 7, tour: 'Elite Tour', category: 'Silver', template_id: 'TPL-SAME' },
        { event_id: 'EVT-LATER', season: 2031, week: 8, tour: 'World Tour', category: 'Platinum', template_id: 'TPL-LATER' }
      ]
    }
  })
  api.getRunStatusSummary.mockResolvedValue({
    run_id: 'run alpha',
    season: 2031,
    seed: 42,
    progress: { next_event_index: 0, total_events: 2, completed_event_count: 1 },
    finals: { qualification_available: true, result_available: false },
    rollover: null,
    source: { source_type: 'child_run', parent_run_id: 'parent run' },
    lineage: { child_run_count: 0 },
    history_counts: { events: 1, ranking_snapshots: 1, race_snapshots: 1 }
  })
  api.listEvents.mockResolvedValue({ run_id: 'run alpha', events: [{ event_id: 'EVT-OLD', event_sequence: 1, template_id: 'TPL-OLD', week: 6 }] })
  api.listRankingSnapshots.mockResolvedValue({ snapshots: [{ snapshot_sequence: 4, snapshot_kind: 'ranking', source_event_id: 'EVT-OLD', payload: {} }] })
  api.listRaceSnapshots.mockResolvedValue({ snapshots: [{ snapshot_sequence: 5, snapshot_kind: 'race', source_event_id: 'EVT-OLD', payload: {} }] })
  api.getRunActivity.mockResolvedValue({ run_id: 'run alpha', items: [{ kind: 'event_completed', label: 'Event completed', event_id: 'EVT-OLD', season: 2031, week: 6 }] })
  api.getFinalsSummary.mockResolvedValue({ run_id: 'run alpha', season: 2031, qualification: { status: 'available' }, result: null })
}

function renderHome(): void {
  renderWithViewerProviders(<ViewerHomePage />)
}

describe('ViewerHomePage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    resetApiMocks()
  })

  it('shows the existing empty state when no active run is selected', () => {
    api.listRuns.mockResolvedValue({ runs: [] })

    renderHome()

    expect(screen.getByRole('heading', { level: 2, name: /MSA Squash/ })).toBeInTheDocument()
    expect(screen.getAllByText('No data is available for this run yet.').length).toBeGreaterThan(0)
  })

  it('renders active-run summary, hub links, featured event, and nearby events', async () => {
    setViewerActiveRunId('run alpha')

    renderHome()

    expect(await screen.findByText('Active run data is available')).toBeInTheDocument()
    expect(screen.getAllByText('run alpha').length).toBeGreaterThan(0)
    expect(await screen.findByText('child_run from parent run')).toBeInTheDocument()
    expect(screen.getByText('1/2 events complete')).toBeInTheDocument()
    expect(screen.getByText('Qualification available')).toBeInTheDocument()

    for (const [label, href] of [
      ['Active Run Rankings', '/viewer/runs/run%20alpha/rankings'],
      ['Active Run Race', '/viewer/runs/run%20alpha/race'],
      ['Active Run Tournaments', '/viewer/runs/run%20alpha/tournaments'],
      ['Active Run Calendar', '/viewer/runs/run%20alpha/calendar'],
      ['Active Run Players', '/viewer/runs/run%20alpha/players'],
      ['Active Run Countries', '/viewer/runs/run%20alpha/countries'],
      ['Active Run History', '/viewer/runs/run%20alpha/history'],
      ['Active Run Finals', '/viewer/runs/run%20alpha/finals']
    ]) {
      expect(screen.getByRole('link', { name: label })).toHaveAttribute('href', href)
    }

    expect(screen.getByText('Next scheduled event:')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'EVT-NEXT' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT-NEXT')
    expect(screen.getAllByRole('link', { name: 'W7' })[0]).toHaveAttribute('href', '/viewer/runs/run%20alpha/weeks/7')
    expect(screen.getByRole('link', { name: 'EVT-SAME-WEEK' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT-SAME-WEEK')
    expect(screen.getByText(/Latest ranking snapshot/)).toBeInTheDocument()
    expect(screen.getByText(/Latest race snapshot/)).toBeInTheDocument()
  })

  it('does not expose forbidden Viewer action labels', () => {
    renderHome()

    expectNoForbiddenViewerActions()
  })
})
