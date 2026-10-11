import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearViewerStorage,
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
  setViewerActiveProductRunId,
} from '../../../test/viewerTestUtils'
import { ViewerH2HSubroutePage } from './ViewerH2HSubroutePage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  getViewerPlayers: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

function mockCanonicalSources(): void {
  api.getViewerRunCalendar.mockResolvedValue({
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'product run',
    viewer_branch_id: 'branch-h2h',
    season_count: 1,
    event_count: 2,
    seasons: [],
  })
  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'product run',
    viewer_branch_id: 'branch-h2h',
    tournament_count: 2,
    published_result_count: 1,
    tournaments: [],
  })
  api.listViewerOfficialRankingHistory.mockResolvedValue({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'product run',
    viewer_branch_id: 'branch-h2h',
    public_head_ordinal: 10,
    publication_count: 3,
    publications: [],
  })
  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'product run',
    viewer_branch_id: 'branch-h2h',
    latest_target_season_index: null,
    publications: [],
  })
  api.getViewerPlayers.mockResolvedValue({
    schema_version: 'viewer_players.v1',
    product_run_id: 'product run',
    viewer_branch_id: 'branch-h2h',
    season_index: 2,
    week: 10,
    player_count: 2,
    active_player_count: 2,
    retired_player_count: 0,
    players: [
      { player_id: 'P1', name: 'Player One', country_code: 'CZE', age: 24, status: 'active', tour_entry_season_index: 0, tour_entry_week: 1, current_ovr: 176, potential_ovr: 190, current_form: 160, match_sharpness: 90, long_term_fatigue: 5, identity_source: 'initial_world' },
      { player_id: 'P2', name: 'Player Two', country_code: 'EGY', age: 26, status: 'active', tour_entry_season_index: 0, tour_entry_week: 1, current_ovr: 172, potential_ovr: 188, current_form: 158, match_sharpness: 88, long_term_fatigue: 8, identity_source: 'initial_world' },
    ],
  })
}

describe('ViewerH2HSubroutePage canonical people boundary', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    mockCanonicalSources()
  })

  it('uses only Product Run canonical metadata including player samples', async () => {
    setViewerActiveProductRunId('product run')

    renderWithViewerProviders(<ViewerH2HSubroutePage kind="rivalries" />)

    expect(await screen.findByText('branch-h2h')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('product run')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('product run')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('product run')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('product run')
    expect(api.getViewerPlayers).toHaveBeenCalledWith('product run')

    expect(screen.getByText('Canonical Saved-Revision player projection')).toBeInTheDocument()
    expect(screen.getByText('Player One')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute(
      'href',
      '/viewer/runs/product%20run/players',
    )
    expectNoForbiddenViewerActions()
  })

  it('fails closed without a selected Product Run', () => {
    renderWithViewerProviders(<ViewerH2HSubroutePage kind="finals-rivalries" />)

    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerPlayers).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
