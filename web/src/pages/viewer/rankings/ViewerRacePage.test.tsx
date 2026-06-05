import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../../test/viewerTestUtils'
import { ViewerRacePage } from './ViewerRacePage'

const api = vi.hoisted(() => ({
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)


function renderRace(): void {
  renderWithViewerProviders(<ViewerRacePage />)
}

describe('ViewerRacePage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderRace()

    expect(screen.getByRole('heading', { level: 2, name: 'Race to Finals' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()

    expectNoForbiddenViewerActions()
  })

  it('renders active-run snapshot metadata and encoded links', async () => {
    setViewerActiveRunId('run alpha')
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
