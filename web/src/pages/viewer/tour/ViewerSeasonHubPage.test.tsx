import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../../viewer/activeRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerSeasonHubPage } from './ViewerSeasonHubPage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn()
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

function renderSeasonHub(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerSeasonHubPage />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ViewerSeasonHubPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: {
        run_id: 'run alpha',
        season: 2024,
        seed: 123,
        config_version: null,
        config_fingerprint: null,
        next_event_index: 1,
        total_events: 2,
        completed_event_ids: ['EVT-1']
      },
      season_state: {
        season: 2024,
        next_event_index: 1,
        completed_event_ids: ['EVT-1'],
        ordered_events: [
          { event_id: 'EVT-1', season: 2024, week: 1, category: 'Gold', tour: 'World Tour', template_id: 'tmpl-1' },
          { event_id: 'EVT 2', season: 2024, week: 2, category: 'Platinum', tour: 'World Tour', template_id: 'tmpl-2' }
        ]
      }
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run alpha',
      season: 2024,
      seed: 123,
      progress: { next_event_index: 1, total_events: 2, completed_event_count: 1 },
      finals: { qualification_available: true, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
      history_counts: { events: 1, ranking_snapshots: 0, race_snapshots: 0 }
    })
    api.listEvents.mockResolvedValue({
      run_id: 'run alpha',
      events: [{ event_id: 'EVT-1', event_sequence: 1, season: 2024, week: 1, template_id: 'tmpl-1', tournament_result: null }]
    })
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run alpha', season: 2024, qualification: { players: [] }, result: null })
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderSeasonHub()

    expect(screen.getByRole('heading', { level: 2, name: 'Season Hub' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })

  it('renders active-run season metadata and encoded source links', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run alpha')

    renderSeasonHub()

    expect(await screen.findByText('Season Hub summary')).toBeInTheDocument()
    expect(screen.getByText('run alpha')).toBeInTheDocument()
    expect(await screen.findByText('1/2 events complete')).toBeInTheDocument()
    expect(screen.getByText('Finals qualification available')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'EVT 2' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT%202')
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments')
    expect(screen.getByRole('link', { name: 'Open active run schedule' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar')
    expect(screen.getByRole('link', { name: 'Open active run finals' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/finals')
  })
})
