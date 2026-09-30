import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import {
  ViewerRunFinalsPage,
  ViewerRunFinalsQualificationPage,
  ViewerRunFinalsResultPage,
  ViewerRunHistoryPage
} from './ViewerRunHistoryFinalsPage'

const api = vi.hoisted(() => ({
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  getViewerTournamentResult: vi.fn()
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    ...api
  }
})

function renderViewerRoute(route: string): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/history" element={<ViewerRunHistoryPage />} />
      <Route path="/viewer/runs/:runId/finals" element={<ViewerRunFinalsPage />} />
      <Route path="/viewer/runs/:runId/finals/qualification" element={<ViewerRunFinalsQualificationPage />} />
      <Route path="/viewer/runs/:runId/finals/result" element={<ViewerRunFinalsResultPage />} />
    </Routes>,
    { route }
  )
}

function mockApi(): void {
  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'viewer-run-2e',
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
    product_run_id: 'viewer-run-2e',
    viewer_branch_id: 'branch-viewer',
    public_head_ordinal: 1931,
    publication_count: 1,
    publications: [
      {
        season_index: 31,
        week: 40,
        week_ordinal: 1931,
        snapshot_fingerprint: 'hidden-ranking-fingerprint',
        policy_id: 'best-n-9',
        best_n: 9,
        row_count: 48
      }
    ]
  })
  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'viewer-run-2e',
    viewer_branch_id: 'branch-viewer',
    latest_target_season_index: 31,
    publications: [{
      schema_version: 'viewer_finals_race_publication.v1',
      product_run_id: 'viewer-run-2e',
      viewer_branch_id: 'branch-viewer',
      target_season_index: 31,
      cutoff_season_index: 31,
      cutoff_week: 40,
      best_n: 2,
      selection_published: true,
      finals_event_id: 'WTF-2031',
      rows: [
        { rank: 1, player_id: 'P1', race_points: 125, tournaments_counted: 2, finals_selected: true, finals_seed: 1, qualification_source: 'direct_entry', counted_results: [] },
        { rank: 2, player_id: 'P2', race_points: 90, tournaments_counted: 1, finals_selected: false, finals_seed: null, qualification_source: null, counted_results: [] },
        { rank: 3, player_id: 'P3', race_points: 80, tournaments_counted: 1, finals_selected: true, finals_seed: 2, qualification_source: 'race', counted_results: [] }
      ]
    }]
  })
  api.getViewerTournamentResult.mockResolvedValue({
    schema_version: 'viewer_tournament_result.v1',
    product_run_id: 'viewer-run-2e',
    viewer_branch_id: 'branch-viewer',
    event_id: 'WTF-2031',
    completed_season_index: 31,
    completed_week: 41,
    champion_player_id: 'P3',
    finalist_player_id: 'P1',
    qualification_winner_ids: ['Q1'],
    players: [
      {
        player_id: 'P3',
        draw_type: 'main',
        seed_number: 2,
        qualifier: false,
        main_entry_status: 'direct',
        reached_stage: 'champion',
        final_round_number: 3,
        eliminated_by_player_id: null,
        last_match_id: 'F',
        wins: 3,
        losses: 0,
        byes_received: 0,
        walkovers_received: 0,
        retired_or_walkover_loss: false,
        group_index: null,
        group_position: null,
        played_group_wins: null,
        group_walkovers_received: null,
        knockout_reached_stage: null
      },
      {
        player_id: 'P1',
        draw_type: 'main',
        seed_number: 1,
        qualifier: false,
        main_entry_status: 'direct',
        reached_stage: 'final',
        final_round_number: 3,
        eliminated_by_player_id: 'P3',
        last_match_id: 'F',
        wins: 2,
        losses: 1,
        byes_received: 0,
        walkovers_received: 0,
        retired_or_walkover_loss: false,
        group_index: null,
        group_position: null,
        played_group_wins: null,
        group_walkovers_received: null,
        knockout_reached_stage: null
      }
    ],
    matches: [
      {
        match_id: 'F',
        draw_type: 'main',
        round_number: 3,
        bracket_position: 1,
        winner_player_id: 'P3',
        loser_player_id: 'P1',
        scoreline: '11-8 11-9 11-7'
      }
    ]
  })
}

function expectNoForbiddenViewerActions(): void {
  const forbiddenLabels = [
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

  forbiddenLabels.forEach((label) => {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  })
}

function expectNoDuplicateRunNav(): void {
  expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  expect(screen.queryByRole('navigation', { name: /Viewer active run quick links/i })).not.toBeInTheDocument()
}

function expectNoUnsafeOutput(): void {
  expect(document.body).not.toHaveTextContent('[object Object]')
  expect(document.body).not.toHaveTextContent(/Fake Champion|Fake Winner|Invented Champion|Invented Winner|Fake Finalist|Invented Finalist|Fake History Entry|Invented History Entry|Fake Standing|Invented Standing|Fake Record|Invented Record|Qualification Standing #1|Champion Player Name/i)
  expectNoForbiddenViewerActions()
}

describe('ViewerRunHistoryFinalsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockApi()
  })

  it('renders canonical Saved-Revision history without legacy activity data', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('viewer-run-2e')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('viewer-run-2e')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-2e')

    expect(screen.getByRole('list', { name: 'Canonical completed tournament history' })).toHaveTextContent('Diamond Open')
    expect(screen.getByRole('list', { name: 'Canonical completed tournament history' })).not.toHaveTextContent('Future Open')
    expect(screen.getByRole('list', { name: 'Canonical Official Ranking publication history' })).toHaveTextContent('ordinal 1931')
    expect(screen.getByRole('list', { name: 'Canonical Finals Race publication history' })).toHaveTextContent('Target season 31')
    expect(screen.queryByText(/hidden-ranking-fingerprint/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical history data')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expectNoUnsafeOutput()
    expectNoDuplicateRunNav()
  })

  it('renders canonical History empty states without inventing publications', async () => {
    api.getViewerTournamentHistory.mockResolvedValueOnce({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'viewer-run-1',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 0,
      published_result_count: 0,
      tournaments: []
    })
    api.listViewerOfficialRankingHistory.mockResolvedValueOnce({
      schema_version: 'viewer_official_ranking_history.v1',
      product_run_id: 'viewer-run-1',
      viewer_branch_id: 'branch-viewer',
      public_head_ordinal: 0,
      publication_count: 0,
      publications: []
    })
    api.getViewerFinalsRace.mockResolvedValueOnce({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'viewer-run-1',
      viewer_branch_id: 'branch-viewer',
      latest_target_season_index: null,
      publications: []
    })

    renderViewerRoute('/viewer/runs/viewer-run-1/history')

    expect(await screen.findByText('No canonical sporting publications are available for this run yet.')).toBeInTheDocument()
    expect(screen.getByText('No completed canonical Tournament Results are published yet.')).toBeInTheDocument()
    expect(screen.getByText('No canonical Official Ranking publications are available yet.')).toBeInTheDocument()
    expect(screen.getByText('No canonical World Tour Finals Race publications are available yet.')).toBeInTheDocument()
    expectNoUnsafeOutput()
  })

  it('passes decoded Product Run ID to every canonical History reader', async () => {
    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('run/alpha #1')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('run/alpha #1')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run/alpha #1')
    expect(screen.getAllByText('run/alpha #1').length).toBeGreaterThan(0)
    expectNoUnsafeOutput()
  })

  it('renders canonical History reader errors without legacy fallback', async () => {
    api.getViewerTournamentHistory.mockRejectedValueOnce(new Error('tournament history outage'))
    api.listViewerOfficialRankingHistory.mockRejectedValueOnce(new Error('ranking history outage'))
    api.getViewerFinalsRace.mockRejectedValueOnce(new Error('race history outage'))

    renderViewerRoute('/viewer/runs/viewer-run-1/history')

    expect(await screen.findByText(/Failed to load canonical tournament history: tournament history outage/i)).toBeInTheDocument()
    expect(screen.getByText(/Failed to load canonical ranking history: ranking history outage/i)).toBeInTheDocument()
    expect(screen.getByText(/Failed to load canonical Finals Race history: race history outage/i)).toBeInTheDocument()
    expect(screen.queryByText('Show technical history data')).not.toBeInTheDocument()
    expectNoUnsafeOutput()
  })

  it('renders canonical confirmed Finals field including effective replacement', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-2e')
    expect((await screen.findAllByText('Published')).length).toBeGreaterThan(0)
    expect(screen.getByText('WTF-2031')).toBeInTheDocument()

    const table = screen.getByRole('table', { name: 'Canonical World Tour Finals participants' })
    expect(within(table).getByRole('link', { name: 'P1' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2e/players/P1/career')
    expect(within(table).getByRole('link', { name: 'P3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2e/players/P3/career')
    expect(within(table).queryByText('P2')).not.toBeInTheDocument()
    expect(within(table).getByText('Direct entry')).toBeInTheDocument()
    expect(within(table).getByText('Race')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expectNoDuplicateRunNav()
  })

  it('renders canonical Finals empty publication without inventing qualification', async () => {
    api.getViewerFinalsRace.mockResolvedValueOnce({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'viewer-run-1',
      viewer_branch_id: 'branch-viewer',
      latest_target_season_index: null,
      publications: []
    })
    renderViewerRoute('/viewer/runs/viewer-run-1/finals')

    expect(screen.getByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.getByText('Loading canonical Finals publication…')).toBeInTheDocument()
    expect(await screen.findByText('No canonical World Tour Finals Race publication exists yet.')).toBeInTheDocument()
    expect(screen.getByText('Confirmed World Tour Finals participants are not published yet.')).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-1')
  })

  it('passes decoded Product Run ID to canonical Finals publication API', async () => {
    api.getViewerFinalsRace.mockResolvedValueOnce({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      latest_target_season_index: null,
      publications: []
    })
    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run/alpha #1')
    expect(screen.getAllByText('run/alpha #1').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Open Finals qualification' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/finals/qualification'
    )
  })

  it('renders canonical Finals API errors without legacy fallback', async () => {
    api.getViewerFinalsRace.mockRejectedValueOnce(new Error('finals publication outage'))
    renderViewerRoute('/viewer/runs/viewer-run-1/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load canonical Finals publication: finals publication outage/i)).toBeInTheDocument()
    expect(screen.queryByText('Show technical finals data')).not.toBeInTheDocument()
  })

  it('renders Finals Qualification from canonical confirmed participant publication', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals Qualification' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-2e')
    expect((await screen.findAllByText('W40')).length).toBeGreaterThan(0)
    expect(screen.getByText('WTF-2031')).toBeInTheDocument()

    const table = screen.getByRole('table', { name: 'Canonical World Tour Finals participants' })
    expect(within(table).getByRole('link', { name: 'P1' })).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'P3' })).toBeInTheDocument()
    expect(within(table).queryByText('P2')).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical finals qualification data')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expectNoDuplicateRunNav()
  })

  it('renders Finals Result from canonical Tournament Result publication', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals/result')

    expect(await screen.findByRole('heading', { name: 'Finals Result' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-2e')
    expect(await screen.findByRole('list', { name: 'Canonical Finals match results' })).toHaveTextContent('11-8 11-9 11-7')
    expect(api.getViewerTournamentResult).toHaveBeenCalledWith('viewer-run-2e', 'WTF-2031')

    expect((await screen.findAllByText('W41')).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'WTF-2031' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2e/tournaments/WTF-2031'
    )
    expect(screen.getAllByRole('link', { name: 'P3' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: 'P1' }).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Q1' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2e/players/Q1/career'
    )
    expect(screen.getByRole('list', { name: 'Canonical Finals player results' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Canonical Finals match results' })).toBeInTheDocument()
    expect(screen.queryByText('Show technical finals result data')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expectNoDuplicateRunNav()
  })

  it('keeps Finals Result unpublished until canonical Tournament Result exists', async () => {
    api.getViewerTournamentResult.mockRejectedValueOnce({ status: 404 })
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals/result')

    expect(await screen.findByText('Canonical Finals Tournament Result is not published yet.')).toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledWith('viewer-run-2e', 'WTF-2031')
    expect(screen.queryByRole('list', { name: 'Canonical Finals match results' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not query a Tournament Result before the canonical Finals event identity is published', async () => {
    api.getViewerFinalsRace.mockResolvedValueOnce({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'viewer-run-2e',
      viewer_branch_id: 'branch-viewer',
      latest_target_season_index: 31,
      publications: [{
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'viewer-run-2e',
        viewer_branch_id: 'branch-viewer',
        target_season_index: 31,
        cutoff_season_index: 31,
        cutoff_week: 40,
        best_n: 2,
        selection_published: false,
        finals_event_id: null,
        rows: []
      }]
    })
    renderViewerRoute('/viewer/runs/viewer-run-2e/finals/result')

    expect(await screen.findByText('The canonical Finals event identity is not published yet.')).toBeInTheDocument()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expect(screen.getByText('Finals source links become available after the event identity is published.')).toBeInTheDocument()
  })

})
