import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../test/viewerTestUtils'
import { ViewerRunBrowserPage } from './ViewerRunBrowserPage'

const api = vi.hoisted(() => ({
  listRuns: vi.fn()
}))

vi.mock('../../api/client', () => api)


function renderRunBrowser(): void {
  renderWithViewerProviders(<ViewerRunBrowserPage />)
}

function sampleRun() {
  return {
    run_id: 'run alpha',
    season: 2031,
    seed: 42,
    progress: {
      next_event_index: 3,
      total_events: 11,
      completed_event_count: 2
    },
    source_type: 'fresh_seed',
    parent_run_id: 'parent-run',
    child_run_count: 0,
    created_at: '2031-09-01T00:00:00Z',
    updated_at: '2031-09-02T00:00:00Z'
  }
}

describe('ViewerRunBrowserPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({ runs: [] })
  })

  it('shows no active run when no active Viewer run is selected', async () => {
    renderRunBrowser()

    expect(await screen.findByText('No active Viewer run selected.')).toBeInTheDocument()
  })

  it('shows the loading state while listRuns is loading', () => {
    api.listRuns.mockReturnValue(new Promise(() => undefined))

    renderRunBrowser()

    expect(screen.getAllByText('Loading available runs…').length).toBeGreaterThan(0)
  })

  it('shows the empty runs state when listRuns returns no runs', async () => {
    renderRunBrowser()

    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
  })

  it('renders sample run metadata and encoded quick links exactly', async () => {
    setViewerActiveRunId('run alpha')
    api.listRuns.mockResolvedValue({ runs: [sampleRun()] })

    renderRunBrowser()

    expect(await screen.findByRole('heading', { level: 4, name: 'run alpha' })).toBeInTheDocument()
    expect(screen.getByText('Current active Viewer run id:')).toBeInTheDocument()
    const metadata = screen.getByLabelText('Run run alpha metadata')
    for (const [label, value] of [
      ['Run id', 'run alpha'],
      ['Season', '2031'],
      ['Seed', '42'],
      ['Next event index', '3'],
      ['Total events', '11'],
      ['Completed event count', '2'],
      ['Source', 'fresh_seed'],
      ['Parent run', 'parent-run'],
      ['Created', '2031-09-01T00:00:00Z'],
      ['Updated', '2031-09-02T00:00:00Z']
    ]) {
      expect(within(metadata).getByText(label)).toBeInTheDocument()
      expect(within(metadata).getByText(value)).toBeInTheDocument()
    }

    expect(screen.getByRole('link', { name: 'Open calendar' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar')
    expect(screen.getByRole('link', { name: 'Open rankings' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(screen.getByRole('link', { name: 'Open race' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
    expect(screen.getByRole('link', { name: 'Open tournaments' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments')
    expect(screen.getByRole('link', { name: 'Open players' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players')
    expect(screen.getByRole('link', { name: 'Open countries' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/countries')
    expect(screen.getByRole('link', { name: 'Open history' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/history')
    expect(screen.getByRole('link', { name: 'Open finals' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/finals')
  })

  it('does not expose forbidden Viewer action labels', async () => {
    renderRunBrowser()

    expect(await screen.findByRole('heading', { level: 2, name: 'Run Browser' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
