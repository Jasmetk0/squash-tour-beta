import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../../viewer/activeRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerRacePage } from './ViewerRacePage'

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

function renderRace(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerRacePage />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ViewerRacePage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderRace()

    expect(screen.getByRole('heading', { level: 2, name: 'Race to Finals' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })

  it('renders active-run snapshot metadata and encoded links', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run alpha')
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 4, snapshot_kind: 'race', source_event_id: 'EVT-OLD', payload: {} },
        { snapshot_sequence: 15, snapshot_kind: 'race', source_event_id: 'EVT-LATEST', payload: {} }
      ]
    })

    renderRace()

    expect(await screen.findByText('EVT-LATEST')).toBeInTheDocument()
    expect(screen.getByText('run alpha')).toBeInTheDocument()
    expect(screen.getByText('Race snapshot count')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('Latest snapshot sequence')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
    expect(screen.getByRole('link', { name: 'View latest race snapshot' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race/15')
  })
})
