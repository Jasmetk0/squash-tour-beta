import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearViewerStorage,
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
  setViewerActiveProductRunId,
  setViewerActiveRunId,
} from '../../../test/viewerTestUtils'
import { ViewerH2HSubroutePage } from './ViewerH2HSubroutePage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  listRunPlayers: vi.fn(),
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
  api.listRunPlayers.mockResolvedValue({
    run_id: 'legacy run',
    total: 2,
    limit: 50,
    offset: 0,
    players: [
      { player_id: 'P1', name: 'Player One', country_code: 'CZE', age: 24, overall: 88 },
      { player_id: 'P2', name: 'Player Two', country_code: 'EGY', age: 26, overall: 86 },
    ],
  })
}

describe('ViewerH2HSubroutePage canonical metadata boundary', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    mockCanonicalSources()
  })

  it('uses Product Run canonical metadata while retaining the explicit legacy player source', async () => {
    setViewerActiveProductRunId('product run')
    setViewerActiveRunId('legacy run')
    setViewerActiveProductRunId('product run')

    renderWithViewerProviders(<ViewerH2HSubroutePage kind="rivalries" />)

    expect(await screen.findByText('branch-h2h')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('product run')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('product run')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('product run')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('product run')
    expect(api.listRunPlayers).toHaveBeenCalledWith('legacy run', { limit: 50, offset: 0 })

    expect(screen.getByText('Legacy SimulationRun player registry')).toBeInTheDocument()
    expect(screen.getByText('Player One')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute(
      'href',
      '/viewer/runs/product%20run/players',
    )
    expectNoForbiddenViewerActions()
  })

  it('does not block canonical H2H metadata when the legacy player source is absent', async () => {
    setViewerActiveProductRunId('product run')

    renderWithViewerProviders(<ViewerH2HSubroutePage kind="most-played" />)

    expect(await screen.findByText('branch-h2h')).toBeInTheDocument()
    expect(api.listRunPlayers).not.toHaveBeenCalled()
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
    expect(
      screen.getByText('Canonical sporting metadata is available, but the legacy player source is not mapped for this selection.'),
    ).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('fails closed without a selected Product Run', () => {
    renderWithViewerProviders(<ViewerH2HSubroutePage kind="finals-rivalries" />)

    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.listRunPlayers).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
