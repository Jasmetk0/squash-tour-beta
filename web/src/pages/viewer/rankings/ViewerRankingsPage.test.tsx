import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../../viewer/activeRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerRankingsPage } from './ViewerRankingsPage'

const api = vi.hoisted(() => ({
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

function renderRankings(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerRankingsPage />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ViewerRankingsPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderRankings()

    expect(screen.getByRole('heading', { level: 2, name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })

  it('renders active-run snapshot metadata and encoded links', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run alpha')
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 3, snapshot_kind: 'ranking', source_event_id: 'EVT-OLD', payload: {} },
        { snapshot_sequence: 12, snapshot_kind: 'ranking', source_event_id: 'EVT-LATEST', payload: {} }
      ]
    })

    renderRankings()

    expect(await screen.findByText('EVT-LATEST')).toBeInTheDocument()
    expect(screen.getByText('run alpha')).toBeInTheDocument()
    expect(screen.getByText('Ranking snapshot count')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('Latest snapshot sequence')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(screen.getByRole('link', { name: 'View latest ranking snapshot' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/12')
  })
})
