import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { makeRunPlayer } from '../../../test/viewerDeferredFixtures'
import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../../test/viewerTestUtils'
import { ViewerPlayersPage } from './ViewerPlayersPage'

const api = vi.hoisted(() => ({
  listRunPlayers: vi.fn()
}))

vi.mock('../../../api/client', () => api)


function renderPlayersPage(): void {
  renderWithViewerProviders(<ViewerPlayersPage />)
}

describe('ViewerPlayersPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run alpha',
      total: 1,
      limit: 5,
      offset: 0,
      players: [
        makeRunPlayer({
          player_id: 'player one',
          name: 'Ali Farag',
          country_code: 'EG',
          age: 31,
          overall: 96,
          quality_band: 'Elite'
        })
      ]
    })
  })

  it('shows the existing empty state when no active run is selected', () => {
    renderPlayersPage()

    expect(screen.getByRole('heading', { level: 2, name: 'Players' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(api.listRunPlayers).not.toHaveBeenCalled()

    expectNoForbiddenViewerActions()
  })

  it('renders active-run player metadata and encoded source/profile links', async () => {
    setViewerActiveRunId('run alpha')

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
