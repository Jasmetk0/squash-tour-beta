import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../../test/viewerTestUtils'
import { ViewerRankingsPage } from './ViewerRankingsPage'

const api = vi.hoisted(() => ({
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)


function renderRankings(): void {
  renderWithViewerProviders(<ViewerRankingsPage />)
}

describe('ViewerRankingsPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderRankings()

    expect(screen.getByRole('heading', { level: 2, name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()

    expectNoForbiddenViewerActions()
  })

  it('renders active-run snapshot metadata and encoded links', async () => {
    setViewerActiveRunId('run alpha')
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
