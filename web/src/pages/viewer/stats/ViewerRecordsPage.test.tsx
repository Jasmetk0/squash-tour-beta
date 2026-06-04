import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../../viewer/activeRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerRecordsPage } from './ViewerRecordsPage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)

const forbiddenViewerActionLabels = [
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

function renderRecords(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerRecordsPage />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function resetApiMocks(): void {
  api.getRunStatusSummary.mockResolvedValue({
    run_id: 'record run',
    season: 2032,
    seed: 7,
    progress: { next_event_index: 2, total_events: 4, completed_event_count: 2 },
    finals: { qualification_available: false, result_available: false },
    rollover: null,
    source: { source_type: 'fresh_seed', parent_run_id: null },
    lineage: { child_run_count: 0 },
    history_counts: { events: 2, ranking_snapshots: 2, race_snapshots: 1 }
  })
  api.listEvents.mockResolvedValue({
    run_id: 'record run',
    events: [
      { event_id: 'EVT-1', event_sequence: 1, template_id: 'TPL-1', week: 11 },
      { event_id: 'EVT-2', event_sequence: 2, template_id: 'TPL-2', week: 12 }
    ]
  })
  api.listRankingSnapshots.mockResolvedValue({ snapshots: [{ snapshot_sequence: 9, snapshot_kind: 'ranking', source_event_id: 'EVT-2', payload: {} }] })
  api.listRaceSnapshots.mockResolvedValue({ snapshots: [{ snapshot_sequence: 4, snapshot_kind: 'race', source_event_id: 'EVT-2', payload: {} }] })
  api.getFinalsSummary.mockResolvedValue({ qualification: null, result: null })
}

describe('ViewerRecordsPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    resetApiMocks()
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderRecords()

    expect(screen.getByRole('heading', { level: 2, name: 'Records' })).toBeInTheDocument()
    expect(screen.getByText('Record book destination prepared for statistics, milestones, and historical achievements.')).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })

  it('renders active-run source metadata, deferred groups, and encoded links', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'record run')

    renderRecords()

    expect(await screen.findByText('Records Overview')).toBeInTheDocument()
    expect(screen.getByText('record run')).toBeInTheDocument()
    expect(screen.getByText('Completed/persisted event count')).toBeInTheDocument()
    expect(screen.getByText('Ranking snapshot count')).toBeInTheDocument()
    expect(screen.getByText('Race snapshot count')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'EVT-2' })).toHaveAttribute('href', '/viewer/runs/record%20run/tournaments/EVT-2')
    expect(await screen.findByRole('link', { name: '#9' })).toHaveAttribute('href', '/viewer/runs/record%20run/rankings/9')
    expect(await screen.findByRole('link', { name: '#4' })).toHaveAttribute('href', '/viewer/runs/record%20run/race/4')

    const deferredText = screen.getByRole('list', { name: 'Deferred record groups' }).textContent ?? ''
    expect(deferredText.indexOf('Title Leaders')).toBeLessThan(deferredText.indexOf('Weeks at No.1'))
    expect(deferredText.indexOf('Weeks at No.1')).toBeLessThan(deferredText.indexOf('Streaks'))
    expect(deferredText.indexOf('Streaks')).toBeLessThan(deferredText.indexOf('Biggest Upsets'))
    expect(deferredText.indexOf('Biggest Upsets')).toBeLessThan(deferredText.indexOf('Best Seasons'))
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/record%20run/tournaments')
  })
})
