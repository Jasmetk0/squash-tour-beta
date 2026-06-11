import { screen, within } from '@testing-library/react'
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
    expect(screen.getByText(/No active Viewer run selected/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open run browser' })).toHaveAttribute('href', '/viewer/runs')
    expect(screen.queryByRole('link', { name: 'Active Run Rankings' })).not.toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.getRunStatusSummary).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(api.getRunActivity).not.toHaveBeenCalled()
    expect(api.getFinalsSummary).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'Viewer hub links' })).toBeInTheDocument()
  })

  it('renders active-run summary, hub links, featured event, and nearby events', async () => {
    setViewerActiveRunId('run alpha')

    renderHome()

    expect(await screen.findByRole('heading', { name: 'Active Viewer run: run alpha' })).toBeInTheDocument()
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
    const hubLinks = within(screen.getByRole('list', { name: 'Viewer Home top-level hub links' }))
    expect(hubLinks.getByRole('link', { name: 'Run Browser' })).toHaveAttribute('href', '/viewer/runs')
    expect(hubLinks.getByRole('link', { name: 'Predictions' })).toHaveAttribute('href', '/viewer/predictions')
  })

  it('treats a whitespace-only active run as no active run without active-run queries', () => {
    setViewerActiveRunId('   ')
    api.listRuns.mockResolvedValue({ runs: [] })

    renderHome()

    expect(screen.getByRole('heading', { level: 2, name: /MSA Squash/ })).toBeInTheDocument()
    expect(screen.getByText(/No active Viewer run selected/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Active Run Rankings' })).not.toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.getRunStatusSummary).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(api.getRunActivity).not.toHaveBeenCalled()
    expect(api.getFinalsSummary).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('trims leading and trailing active-run whitespace for queries, labels, and route links', async () => {
    setViewerActiveRunId(' run alpha ')

    renderHome()

    expect(await screen.findByRole('heading', { name: 'Active Viewer run: run alpha' })).toBeInTheDocument()
    expect(await screen.findByText('child_run from parent run')).toBeInTheDocument()
    for (const activeRunApi of [
      api.getRun,
      api.getRunStatusSummary,
      api.listEvents,
      api.listRankingSnapshots,
      api.listRaceSnapshots,
      api.getRunActivity,
      api.getFinalsSummary
    ]) {
      expect(activeRunApi).toHaveBeenCalledWith('run alpha')
      expect(activeRunApi).not.toHaveBeenCalledWith(' run alpha ')
    }
    expect(screen.getByLabelText('Active Viewer run status')).toHaveTextContent('Using Viewer run run alpha')
    expect(screen.getAllByText('run alpha').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Active Run Rankings' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(screen.getByRole('link', { name: 'Active Run Calendar' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar')
    for (const link of screen.getAllByRole('link')) {
      expect(link.getAttribute('href') ?? '').not.toContain('%20run%20alpha%20')
    }
    expectNoForbiddenViewerActions()
  })

  it('renders safely when active-run storage is unavailable during render', () => {
    api.listRuns.mockResolvedValue({ runs: [] })
    const getItemSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable')
    })

    try {
      renderHome()

      expect(screen.getByRole('heading', { level: 2, name: /MSA Squash/ })).toBeInTheDocument()
      expect(screen.getByText(/No active Viewer run selected/)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Open run browser' })).toHaveAttribute('href', '/viewer/runs')
      expect(screen.queryByText(/storage unavailable/i)).not.toBeInTheDocument()
    } finally {
      getItemSpy.mockRestore()
    }
  })

  it('keeps active-run scoped Home links encoded and free of Admin destinations', async () => {
    setViewerActiveRunId('run/alpha #1')

    renderHome()

    expect(await screen.findByRole('heading', { name: 'Active Viewer run: run/alpha #1' })).toBeInTheDocument()
    for (const link of screen.getAllByRole('link')) {
      expect(link.getAttribute('href') ?? '').not.toMatch(/^\/admin(?:\/|$)/)
    }
    expect(screen.getByRole('link', { name: 'Active Run Rankings' })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/rankings')
    expect(screen.getByRole('link', { name: 'Active Run Calendar' })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/calendar')
  })

  it('does not expose forbidden Viewer action labels', () => {
    renderHome()

    expectNoForbiddenViewerActions()
  })
})
