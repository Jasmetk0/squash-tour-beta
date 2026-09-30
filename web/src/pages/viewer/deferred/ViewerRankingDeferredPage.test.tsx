import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
} from '../../../test/viewerTestUtils'
import { ViewerRankingDeferredPage } from './ViewerRankingDeferredPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

function mockCanonicalSources(): void {
  api.getViewerRunCalendar.mockResolvedValue({
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    season_count: 1,
    event_count: 2,
    seasons: [{
      season: '2034/2035',
      event_count: 2,
      events: [
        {
          event_id: 'British Open 2034',
          season: '2034/2035',
          season_week: 20,
          calendar_year: 2034,
          year_week: 20,
          template_id: 'BO',
          event_name: 'British Open 2034',
          category: 'PLATINUM',
          tour_level: 'WORLD_TOUR',
          host_country: 'GBR',
          host_city: 'London',
          region: 'EUROPE',
          duration_in_season_weeks: 1,
          start_season_week: 20,
          end_season_week: 20,
          status: 'completed',
          main_draw_size: 32,
          qualification_draw_size: 16,
          seeds_count: 8,
          qualifier_spots: 4,
          wild_cards: 2,
          byes: 0,
          prestige: 9
        },
        {
          event_id: 'Egyptian Open 2034',
          season: '2034/2035',
          season_week: 21,
          calendar_year: 2034,
          year_week: 21,
          template_id: 'EO',
          event_name: 'Egyptian Open 2034',
          category: 'GOLD',
          tour_level: 'WORLD_TOUR',
          host_country: 'EGY',
          host_city: 'Cairo',
          region: 'AFRICA',
          duration_in_season_weeks: 1,
          start_season_week: 21,
          end_season_week: 21,
          status: 'planned',
          main_draw_size: 32,
          qualification_draw_size: 16,
          seeds_count: 8,
          qualifier_spots: 4,
          wild_cards: 2,
          byes: 0,
          prestige: 8
        }
      ]
    }]
  })
  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    tournament_count: 2,
    published_result_count: 1,
    tournaments: [{
      event_id: 'British Open 2034',
      season: '2034/2035',
      season_week: 20,
      event_name: 'British Open 2034',
      template_id: 'BO',
      category: 'PLATINUM',
      tour_level: 'WORLD_TOUR',
      host_country: 'GBR',
      host_city: 'London',
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
    }]
  })
  api.listViewerOfficialRankingHistory.mockResolvedValue({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    public_head_ordinal: 12,
    publication_count: 1,
    publications: [{
      season_index: 34,
      week: 20,
      week_ordinal: 12,
      snapshot_fingerprint: 'a'.repeat(64),
      policy_id: 'best-15',
      best_n: 15,
      row_count: 64
    }]
  })
  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    latest_target_season_index: 34,
    publications: [{
      schema_version: 'viewer_finals_race_publication.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-a',
      target_season_index: 34,
      cutoff_season_index: 34,
      cutoff_week: 20,
      best_n: 9,
      selection_published: false,
      finals_event_id: null,
      rows: []
    }]
  })
}


function renderRankingDeferredPage(): void {
  renderWithViewerProviders(<ViewerRankingDeferredPage kind="elo" />, {
    activeRunId: 'run alpha',
  })
}

describe('ViewerRankingDeferredPage canonical sources', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mockCanonicalSources()
  })

  it('renders canonical source metadata and encoded source links', async () => {
    renderRankingDeferredPage()

    expect(screen.getByRole('heading', { level: 2, name: 'Elo Ranking' })).toBeInTheDocument()
    expect(await screen.findByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText('Saved Calendar events')).toBeInTheDocument()
    expect(screen.getByText('Official Ranking publications')).toBeInTheDocument()
    expect(screen.getByText('Finals Race publications')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Egyptian Open 2034' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar/Egyptian%20Open%202034'
    )
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/rankings'
    )
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/race'
    )
    expectNoForbiddenViewerActions()
  })
})
