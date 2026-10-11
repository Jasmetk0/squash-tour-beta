import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearViewerStorage,
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
  setViewerActiveProductRunId
} from '../../../test/viewerTestUtils'
import { ViewerHistoryPage } from './ViewerHistoryPage'

const api = vi.hoisted(() => ({
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn()
}))

vi.mock('../../../api/client', () => api)

function renderHistory(): void {
  renderWithViewerProviders(<ViewerHistoryPage />)
}

function mockCanonicalHistory(): void {
  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'history run',
    viewer_branch_id: 'branch-history',
    tournament_count: 2,
    published_result_count: 1,
    tournaments: [
      {
        event_id: 'EVT-1',
        season: '2032/2033',
        season_week: 11,
        event_name: 'History Open',
        template_id: 'TPL-1',
        category: 'GOLD',
        tour_level: 'WORLD_TOUR',
        host_country: 'CZE',
        host_city: 'Brno',
        region: 'EUROPE',
        main_draw_size: 32,
        qualification_draw_size: 16,
        seeds_count: 8,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: true,
        champion_player_id: 'P1',
        finalist_player_id: 'P2'
      }
    ]
  })
  api.listViewerOfficialRankingHistory.mockResolvedValue({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'history run',
    viewer_branch_id: 'branch-history',
    public_head_ordinal: 2000,
    publication_count: 2,
    publications: [
      { season_index: 32, week: 10, week_ordinal: 1999, snapshot_fingerprint: 'a'.repeat(64), policy_id: 'best-15', best_n: 15, row_count: 64 },
      { season_index: 32, week: 11, week_ordinal: 2000, snapshot_fingerprint: 'b'.repeat(64), policy_id: 'best-15', best_n: 15, row_count: 64 }
    ]
  })
  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'history run',
    viewer_branch_id: 'branch-history',
    latest_target_season_index: 32,
    publications: [
      {
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'history run',
        viewer_branch_id: 'branch-history',
        target_season_index: 32,
        cutoff_season_index: 32,
        cutoff_week: 11,
        best_n: 9,
        selection_published: false,
        finals_event_id: null,
        rows: []
      }
    ]
  })
}

describe('ViewerHistoryPage canonical landing', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    mockCanonicalHistory()
  })

  it('shows a Product Run empty state when nothing is selected', () => {
    renderHistory()

    expect(screen.getByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders canonical Saved-Revision history counts and run-scoped links', async () => {
    setViewerActiveProductRunId('history run')
    renderHistory()

    expect(await screen.findByRole('article', { name: 'Canonical history summary' })).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('history run')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('history run')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('history run')

    expect(await screen.findByText('branch-history')).toBeInTheDocument()
    expect(screen.getByText('Completed tournaments')).toBeInTheDocument()
    expect(screen.getByText('Official Ranking publications')).toBeInTheDocument()
    expect(screen.getByText('Finals Race publications')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open full run history' })).toHaveAttribute(
      'href',
      '/viewer/runs/history%20run/history'
    )
    expect(screen.getByRole('link', { name: 'Tournaments' })).toHaveAttribute(
      'href',
      '/viewer/runs/history%20run/tournaments'
    )
    expectNoForbiddenViewerActions()
  })

  it('fails closed when one canonical history authority is unavailable', async () => {
    setViewerActiveProductRunId('history run')
    api.listViewerOfficialRankingHistory.mockRejectedValueOnce(new Error('ranking unavailable'))

    renderHistory()

    expect(await screen.findByText('Canonical history is temporarily unavailable.')).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Canonical history summary fields' })).not.toBeInTheDocument()
    expect(screen.queryByText(/ranking unavailable/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
