import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../test/viewerTestUtils'
import { ViewerHomePage } from './ViewerHomePage'

const api = vi.hoisted(() => ({
  listRuns: vi.fn(),
  listRunContainers: vi.fn(),
  getViewerOfficialRunContext: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../../api/client', () => api)

function resetApiMocks(): void {
  api.listRuns.mockResolvedValue({
    runs: [{
      run_id: 'run alpha',
      season: 2031,
      seed: 42,
      progress: { next_event_index: 0, total_events: 2, completed_event_count: 1 },
      source_type: 'fresh_seed',
      parent_run_id: null,
      child_run_count: 0,
      created_at: '2031-09-01T00:00:00Z',
      updated_at: '2031-09-02T00:00:00Z'
    }]
  })
  api.listRunContainers.mockResolvedValue({
    run_containers: [{
      run_id: 'run alpha',
      display_name: 'Run Alpha',
      storage_kind: 'custom_local',
      read_only: false,
      world_id: 'fax-world',
      world_package_fingerprint: 'world-fp',
      config_version: 'v1',
      config_fingerprint: 'config-fp',
      global_seed: 42,
      timeline_start_season: 2000,
      timeline_end_season: 2049,
      viewer_branch_id: 'viewer',
      official_branch_id: 'official',
      status: 'active',
      metadata_json: {},
      mapped_simulation_run_count: 1
    }]
  })
  api.getViewerOfficialRunContext.mockImplementation(async (productRunId: string) => ({
    product_run_id: productRunId,
    product_run_display_name: 'Run Alpha',
    product_run_status: 'active',
    product_run_storage_kind: 'custom_local',
    product_run_read_only: false,
    official_branch_id: 'official',
    official_branch_display_name: 'Official',
    official_branch_status: 'active',
    official_branch_read_only: false,
    official_branch_seed: 42,
    legacy_simulation_run_id: 'run alpha',
    head_checkpoint_id: 'checkpoint',
    head_checkpoint_kind: 'week',
    current_season: 31,
    current_week: 40,
    current_event_id: 'EVENT-40',
    current_event_sequence: 7,
    resolution_version: 'viewer_official_branch_v1'
  }))
  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-viewer',
    tournament_count: 2,
    published_result_count: 1,
    tournaments: [
      {
        event_id: 'EVENT-40',
        season: '2031/32',
        season_week: 40,
        event_name: 'Diamond Open',
        template_id: 'diamond-open',
        category: 'diamond',
        tour_level: 'world_tour',
        host_country: 'CZE',
        host_city: 'Brno',
        region: 'Europe',
        main_draw_size: 32,
        qualification_draw_size: 16,
        seeds_count: 8,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'completed',
        result_published: true,
        champion_player_id: 'P3',
        finalist_player_id: 'P1'
      },
      {
        event_id: 'EVENT-41',
        season: '2031/32',
        season_week: 41,
        event_name: 'Future Open',
        template_id: 'future-open',
        category: 'gold',
        tour_level: 'world_tour',
        host_country: 'CZE',
        host_city: 'Praha',
        region: 'Europe',
        main_draw_size: 32,
        qualification_draw_size: 16,
        seeds_count: 8,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'planned',
        result_published: false,
        champion_player_id: null,
        finalist_player_id: null
      }
    ]
  })
  api.listViewerOfficialRankingHistory.mockResolvedValue({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-viewer',
    public_head_ordinal: 1931,
    publication_count: 1,
    publications: [{
      season_index: 31,
      week: 40,
      week_ordinal: 1931,
      snapshot_fingerprint: 'hidden-fingerprint',
      policy_id: 'best-n-9',
      best_n: 9,
      row_count: 48
    }]
  })
  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-viewer',
    latest_target_season_index: 31,
    publications: [{
      schema_version: 'viewer_finals_race_publication.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      target_season_index: 31,
      cutoff_season_index: 31,
      cutoff_week: 40,
      best_n: 9,
      selection_published: true,
      finals_event_id: 'WTF-2031',
      rows: [{
        rank: 1,
        player_id: 'P3',
        race_points: 120,
        tournaments_counted: 8,
        finals_selected: true,
        finals_seed: 1,
        qualification_source: 'race',
        counted_results: []
      }]
    }]
  })
}

function renderHome(): void {
  renderWithViewerProviders(<ViewerHomePage />)
}

describe('ViewerHomePage canonical sources', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    resetApiMocks()
  })

  it('keeps the default Viewer route read-only without active-run canonical queries', () => {
    renderHome()

    expect(screen.getByRole('heading', { level: 2, name: /MSA Squash/ })).toBeInTheDocument()
    expect(screen.getByText(/canonical Viewer Saved-Revision projections/i)).toBeInTheDocument()
    expect(screen.getByText(/No active Viewer run selected/)).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders canonical Home summaries for the active Product Run', async () => {
    setViewerActiveRunId('run alpha')
    renderHome()

    expect(await screen.findByRole('heading', { name: 'Active Viewer run: run alpha' })).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledWith('run alpha')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('run alpha')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('run alpha')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run alpha')

    expect(await screen.findByRole('link', { name: 'Diamond Open' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments/EVENT-40')
    expect(screen.queryByText('Future Open')).not.toBeInTheDocument()
    expect(screen.getByText(/ordinal 1931/i)).toBeInTheDocument()
    expect(screen.getByText(/Target season 31/i)).toBeInTheDocument()
    expect(screen.getByText(/1 completed tournaments · 1 ranking publications · 1 Finals Race publications/i)).toBeInTheDocument()
    expect(screen.queryByText(/hidden-fingerprint/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps canonical run-scoped links encoded and Viewer-only', async () => {
    setViewerActiveRunId('run/alpha #1')
    api.listRunContainers.mockResolvedValue({
      run_containers: [{
        run_id: 'run/alpha #1',
        display_name: 'Run special',
        storage_kind: 'custom_local',
        read_only: false,
        world_id: 'world',
        world_package_fingerprint: 'world',
        config_version: 'v1',
        config_fingerprint: 'config',
        global_seed: 1,
        timeline_start_season: 2000,
        timeline_end_season: 2049,
        viewer_branch_id: 'viewer',
        official_branch_id: 'official',
        status: 'active',
        metadata_json: {},
        mapped_simulation_run_count: 1
      }]
    })

    renderHome()

    expect(await screen.findByRole('heading', { name: 'Active Viewer run: run/alpha #1' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Active Run Rankings' })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/rankings')
    expect(screen.getByRole('link', { name: 'Active Run History' })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/history')
    for (const link of screen.getAllByRole('link')) {
      expect(link.getAttribute('href') ?? '').not.toMatch(/^\/admin(?:\/|$)/)
    }
    expectNoForbiddenViewerActions()
  })

  it('does not query canonical Home readers for a whitespace-only active run', () => {
    setViewerActiveRunId('   ')
    api.listRuns.mockResolvedValue({ runs: [] })
    renderHome()

    expect(screen.getByText(/No active Viewer run selected/)).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows a safe unavailable state when a canonical reader fails', async () => {
    setViewerActiveRunId('run alpha')
    api.getViewerTournamentHistory.mockRejectedValueOnce(new Error('canonical outage'))

    renderHome()

    expect(await screen.findByText(/Active run summary is temporarily unavailable/)).toBeInTheDocument()
    expect(screen.queryByText(/canonical outage/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Diamond Open' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps hub links available while canonical previews stay empty', async () => {
    setViewerActiveRunId('run alpha')
    api.getViewerTournamentHistory.mockResolvedValueOnce({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 0,
      published_result_count: 0,
      tournaments: []
    })
    api.listViewerOfficialRankingHistory.mockResolvedValueOnce({
      schema_version: 'viewer_official_ranking_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      public_head_ordinal: 0,
      publication_count: 0,
      publications: []
    })
    api.getViewerFinalsRace.mockResolvedValueOnce({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      latest_target_season_index: null,
      publications: []
    })

    renderHome()

    expect(await screen.findByText(/No completed canonical Tournament Result is published/i)).toBeInTheDocument()
    expect(screen.getByText(/No canonical Official Ranking publication is available/i)).toBeInTheDocument()
    expect(screen.getByText(/No canonical World Tour Finals Race publication is available/i)).toBeInTheDocument()
    const hubs = within(screen.getByRole('list', { name: 'Viewer Home top-level hub links' }))
    expect(hubs.getByRole('link', { name: 'Run Browser' })).toHaveAttribute('href', '/viewer/runs')
    expectNoForbiddenViewerActions()
  })
})
