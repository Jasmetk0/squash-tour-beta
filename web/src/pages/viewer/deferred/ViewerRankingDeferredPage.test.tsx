import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../../viewer/activeRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerRankingDeferredPage } from './ViewerRankingDeferredPage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn(),
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
  'Overwrite',
]

function renderRankingDeferredPage(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerRankingDeferredPage kind="elo" />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ViewerRankingDeferredPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: {
        run_id: 'run alpha',
        season: 2034,
        seed: 1001,
        config_version: null,
        config_fingerprint: null,
        next_event_index: 0,
        total_events: 99,
        completed_event_ids: [],
      },
      season_state: {
        season: 2034,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [],
      },
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run alpha',
      season: 2034,
      seed: 1001,
      progress: {
        next_event_index: 0,
        total_events: 61,
        completed_event_count: 5,
      },
      finals: {
        qualification_available: false,
        result_available: false,
      },
      rollover: null,
      source: null,
      lineage: {
        child_run_count: 0,
      },
      history_counts: {
        events: 5,
        ranking_snapshots: 1,
        race_snapshots: 1,
      },
    })
    api.listEvents.mockResolvedValue({
      run_id: 'run alpha',
      events: [
        {
          event_sequence: 1,
          event_id: 'British Open 2034',
          season: 2034,
          week: 20,
          template_id: 'BO',
          tournament_result: {},
        },
      ],
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'run alpha',
      snapshots: [
        {
          snapshot_sequence: 12,
          snapshot_kind: 'ranking',
          source_event_id: 'British Open 2034',
          payload: {},
        },
      ],
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'run alpha',
      snapshots: [
        {
          snapshot_sequence: 8,
          snapshot_kind: 'race',
          source_event_id: 'British Open 2034',
          payload: {},
        },
      ],
    })
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run alpha',
      season: 2034,
      qualification: null,
      result: null,
    })
  })

  it('preserves ranking nullish ordered-event fallback and encoded source links', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run alpha')

    renderRankingDeferredPage()

    expect(screen.getByRole('heading', { level: 2, name: 'Elo Ranking' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Available source metadata' })).toBeInTheDocument()

    const orderedCalendarItem = screen.getByText('Ordered calendar event count').closest('div')
    expect(orderedCalendarItem).not.toBeNull()
    await waitFor(() => expect(within(orderedCalendarItem as HTMLElement).getByText('0')).toBeInTheDocument())

    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments')
    expect(screen.getByRole('link', { name: 'Open active run calendar' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar')
    expect(screen.getByRole('link', { name: 'Open run browser' })).toHaveAttribute('href', '/viewer/runs')

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })
})
