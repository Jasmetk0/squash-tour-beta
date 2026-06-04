import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../../viewer/activeRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerStatsPage } from './ViewerStatsPage'

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

function renderStats(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerStatsPage />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function resetApiMocks(): void {
  api.getRunStatusSummary.mockResolvedValue({
    run_id: 'stats run',
    season: 2032,
    seed: 7,
    progress: { next_event_index: 2, total_events: 4, completed_event_count: 2 },
    finals: { qualification_available: true, result_available: false },
    rollover: null,
    source: { source_type: 'fresh_seed', parent_run_id: null },
    lineage: { child_run_count: 0 },
    history_counts: { events: 2, ranking_snapshots: 2, race_snapshots: 1 }
  })
  api.listEvents.mockResolvedValue({ run_id: 'stats run', events: [{ event_id: 'EVT-3', event_sequence: 3, template_id: 'TPL-3', week: 13 }] })
  api.listRankingSnapshots.mockResolvedValue({ snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'ranking', source_event_id: 'EVT-3', payload: {} }] })
  api.listRaceSnapshots.mockResolvedValue({ snapshots: [{ snapshot_sequence: 6, snapshot_kind: 'race', source_event_id: 'EVT-3', payload: {} }] })
  api.getFinalsSummary.mockResolvedValue({ qualification: { qualifiers: [] }, result: null })
}

describe('ViewerStatsPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    resetApiMocks()
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderStats()

    expect(screen.getByRole('heading', { level: 2, name: 'Stats' })).toBeInTheDocument()
    expect(screen.getByText('Stats library destination prepared for connected run-scoped statistical read models.')).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })

  it('renders active-run source metadata, deferred groups, and encoded links', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'stats run')

    renderStats()

    expect(await screen.findByText('Stats Overview')).toBeInTheDocument()
    expect(screen.getByText('stats run')).toBeInTheDocument()
    expect(screen.getByText('Completed/persisted event count')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Finals qualification available' })).toHaveAttribute('href', '/viewer/runs/stats%20run/finals')

    const deferredText = screen.getByRole('list', { name: 'Deferred stat groups' }).textContent ?? ''
    expect(deferredText.indexOf('Player Stats')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Tournament Stats')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Country Stats')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Awards')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Hall of Fame')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Era Rankings')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Player Stats')).toBeLessThan(deferredText.indexOf('Tournament Stats'))
    expect(deferredText.indexOf('Tournament Stats')).toBeLessThan(deferredText.indexOf('Country Stats'))
    expect(deferredText.indexOf('Country Stats')).toBeLessThan(deferredText.indexOf('Awards'))
    expect(deferredText.indexOf('Awards')).toBeLessThan(deferredText.indexOf('Hall of Fame'))
    expect(deferredText.indexOf('Hall of Fame')).toBeLessThan(deferredText.indexOf('Era Rankings'))
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/stats%20run/race')
  })
})
