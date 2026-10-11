import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveProductRunId } from '../../../test/viewerTestUtils'
import { ViewerPlayersPage } from './ViewerPlayersPage'

const api = vi.hoisted(() => ({
  getViewerPlayers: vi.fn()
}))

vi.mock('../../../api/client', () => api)

function renderPlayersPage(): void {
  renderWithViewerProviders(<ViewerPlayersPage />)
}

describe('ViewerPlayersPage canonical people', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.getViewerPlayers.mockResolvedValue({
      schema_version: 'viewer_players.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-a',
      season_index: 3,
      week: 8,
      player_count: 1,
      active_player_count: 1,
      retired_player_count: 0,
      players: [{
        player_id: 'player one',
        name: 'Ali Farag',
        country_code: 'EGY',
        age: 31,
        status: 'active',
        tour_entry_season_index: 0,
        tour_entry_week: 1,
        current_ovr: 196,
        potential_ovr: 198,
        current_form: 180,
        match_sharpness: 90,
        long_term_fatigue: 5,
        identity_source: 'initial_world'
      }]
    })
  })

  it('shows Product Run empty state when nothing is selected', () => {
    renderPlayersPage()

    expect(screen.getByRole('heading', { level: 2, name: 'Players' })).toBeInTheDocument()
    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()
    expect(api.getViewerPlayers).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders canonical player metadata and encoded profile links', async () => {
    setViewerActiveProductRunId('run alpha')
    renderPlayersPage()

    expect(await screen.findByText('Ali Farag')).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledWith('run alpha')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText('Active players')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ali Farag' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player%20one/career')
    expect(screen.getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/EGY')
    expect(screen.getByRole('link', { name: 'Open Product Run players' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players')
    expectNoForbiddenViewerActions()
  })
})
