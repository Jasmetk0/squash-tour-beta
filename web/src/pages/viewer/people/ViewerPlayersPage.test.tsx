import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../../viewer/activeRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerPlayersPage } from './ViewerPlayersPage'

const api = vi.hoisted(() => ({
  listRunPlayers: vi.fn()
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

function renderPlayersPage(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerPlayersPage />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ViewerPlayersPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run alpha',
      total: 1,
      limit: 5,
      offset: 0,
      players: [
        {
          player_id: 'player one',
          name: 'Ali Farag',
          country_code: 'EG',
          age: 31,
          overall: 96,
          quality_band: 'Elite'
        }
      ]
    })
  })

  it('shows the existing empty state when no active run is selected', () => {
    renderPlayersPage()

    expect(screen.getByRole('heading', { level: 2, name: 'Players' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(api.listRunPlayers).not.toHaveBeenCalled()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })

  it('renders active-run player metadata and encoded source/profile links', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run alpha')

    renderPlayersPage()

    expect(await screen.findByText('Players summary')).toBeInTheDocument()
    expect(await screen.findByText('Ali Farag')).toBeInTheDocument()
    expect(screen.getByText('Total player count')).toBeInTheDocument()
    expect(screen.getByText('Returned player count')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ali Farag' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player%20one/career')
    expect(screen.getByRole('link', { name: 'player one' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player%20one/career')
    expect(screen.getByRole('link', { name: 'EG' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/EG')
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players')
  })
})
