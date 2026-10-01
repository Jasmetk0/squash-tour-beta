import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunTournamentDetailPage, ViewerRunTournamentsPage } from './ViewerRunTournamentsPage'

const api = vi.hoisted(() => ({
  getViewerFinalsRace: vi.fn(),
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentDraw: vi.fn(),
  getViewerTournamentEntryField: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  getViewerTournamentResult: vi.fn(),
  getViewerTournamentWildCards: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

function renderViewerTournamentRoute(route: string): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/tournaments" element={<ViewerRunTournamentsPage />} />
      <Route path="/viewer/runs/:runId/tournaments/:eventId" element={<ViewerRunTournamentDetailPage />} />
    </Routes>,
    { route }
  )
}

function mockCanonicalTournamentData(): void {
  api.getViewerRunCalendar.mockResolvedValue({
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    season_count: 1,
    event_count: 1,
    seasons: [{
      season: '2027/2028',
      event_count: 1,
      events: [{
        event_id: 'EVENT-1',
        season: '2027/2028',
        season_week: 3,
        calendar_year: 2027,
        year_week: 40,
        template_id: 'WT-PLAT',
        event_name: 'Canonical Open',
        category: 'PLATINUM',
        tour_level: 'WORLD_TOUR',
        host_country: 'EGY',
        host_city: 'Cairo',
        region: 'AFRICA',
        duration_in_season_weeks: 1,
        start_season_week: 3,
        end_season_week: 3,
        status: 'completed',
        main_draw_size: 32,
        qualification_draw_size: 16,
        seeds_count: 8,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        prestige: 9
      }]
    }]
  })

  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    tournament_count: 2,
    published_result_count: 1,
    tournaments: [
      {
        event_id: 'EVENT-OLD',
        season: '2000/2001',
        season_week: 5,
        event_name: 'Old Open',
        template_id: 'WT-GOLD',
        category: 'GOLD',
        tour_level: 'WORLD_TOUR',
        host_country: 'CZE',
        host_city: 'Prague',
        region: 'EUROPE',
        main_draw_size: 16,
        qualification_draw_size: 8,
        seeds_count: 4,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: false,
        champion_player_id: null,
        finalist_player_id: null
      },
      {
        event_id: 'EVENT-1',
        season: '2027/2028',
        season_week: 3,
        event_name: 'Canonical Open',
        template_id: 'WT-PLAT',
        category: 'PLATINUM',
        tour_level: 'WORLD_TOUR',
        host_country: 'EGY',
        host_city: 'Cairo',
        region: 'AFRICA',
        main_draw_size: 32,
        qualification_draw_size: 16,
        seeds_count: 8,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: true,
        champion_player_id: 'P-001',
        finalist_player_id: 'P-002'
      }
    ]
  })

  api.listViewerOfficialRankingHistory.mockResolvedValue({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    public_head_ordinal: 8,
    publication_count: 1,
    publications: [{
      season_index: 27,
      week: 3,
      week_ordinal: 8,
      snapshot_fingerprint: 'a'.repeat(64),
      policy_id: 'best-15',
      best_n: 15,
      row_count: 48
    }]
  })

  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    latest_target_season_index: 27,
    publications: [{
      schema_version: 'viewer_finals_race_publication.v1',
      product_run_id: 'viewer-run-1',
      viewer_branch_id: 'branch-viewer',
      target_season_index: 27,
      cutoff_season_index: 27,
      cutoff_week: 3,
      best_n: 8,
      selection_published: false,
      finals_event_id: null,
      rows: []
    }]
  })

  api.getViewerTournamentEntryField.mockResolvedValue({
    schema_version: 'viewer_tournament_entry_field.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    event_id: 'EVENT-1',
    field_sequence: 2,
    mode: 'pre_draw_repair',
    main_draw_capacity: 32,
    active_main_entrant_count: 30,
    effective_main_bye_count: 2,
    direct_main_player_ids: ['P-001', 'P-002'],
    qualification_player_ids: ['P-003'],
    alternate_player_ids: ['P-004'],
    withdrawn_player_ids: ['P-099']
  })

  api.getViewerTournamentDraw.mockResolvedValue({
    schema_version: 'viewer_tournament_draw.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    event_id: 'EVENT-1',
    revision_count: 1,
    main: {
      draw_type: 'main',
      section_id: null,
      bracket_size: 4,
      slots: [
        { slot_index: 1, entrant_kind: 'player', player_id: 'P-001', placeholder_id: null, seed_number: 1, entry_status: null },
        { slot_index: 2, entrant_kind: 'bye', player_id: null, placeholder_id: null, seed_number: null, entry_status: null }
      ]
    },
    qualification_sections: []
  })

  api.getViewerTournamentWildCards.mockResolvedValue({
    schema_version: 'viewer_tournament_wild_cards.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    event_id: 'EVENT-1',
    assignment_count: 1,
    assignments: [
      { wildcard_index: 1, player_id: 'P-WC', source: 'original_wc', reserve_ordinal: null }
    ]
  })

  api.getViewerTournamentResult.mockResolvedValue({
    schema_version: 'viewer_tournament_result.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    event_id: 'EVENT-1',
    completed_season_index: 27,
    completed_week: 3,
    champion_player_id: 'P-001',
    finalist_player_id: 'P-002',
    qualification_winner_ids: ['P-003'],
    players: [
      {
        player_id: 'P-001', draw_type: 'main', seed_number: 1, qualifier: false,
        main_entry_status: 'direct', reached_stage: 'champion', final_round_number: 2,
        eliminated_by_player_id: null, last_match_id: 'final', wins: 2, losses: 0,
        byes_received: 0, walkovers_received: 0, retired_or_walkover_loss: false,
        group_index: null, group_position: null, played_group_wins: null,
        group_walkovers_received: null, knockout_reached_stage: null
      },
      {
        player_id: 'P-002', draw_type: 'main', seed_number: 2, qualifier: false,
        main_entry_status: null, reached_stage: 'finalist', final_round_number: 2,
        eliminated_by_player_id: 'P-001', last_match_id: 'final', wins: 1, losses: 1,
        byes_received: 0, walkovers_received: 0, retired_or_walkover_loss: false,
        group_index: null, group_position: null, played_group_wins: null,
        group_walkovers_received: null, knockout_reached_stage: null
      }
    ],
    matches: [
      { match_id: 'final', draw_type: 'main', round_number: 2, bracket_position: 1, winner_player_id: 'P-001', loser_player_id: 'P-002', scoreline: '3-2' }
    ]
  })
}

function expectNoForbiddenViewerActions(): void {
  const forbidden = /^(Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)$/i
  for (const element of [...screen.queryAllByRole('button'), ...screen.queryAllByRole('link')]) {
    expect(forbidden.test(element.textContent?.trim() ?? '')).toBe(false)
  }
}

describe('ViewerRunTournamentsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockCanonicalTournamentData()
  })

  it('renders canonical multi-season tournament history', async () => {
    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments')

    expect(await screen.findByRole('heading', { name: 'Canonical Tournament History' })).toBeInTheDocument()
    const list = screen.getByRole('list', { name: 'Canonical tournament history list' })
    expect(within(list).getByText('Old Open')).toBeInTheDocument()
    expect(within(list).getByText('Canonical Open')).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: 'W5' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/5')
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunTournamentDetailPage canonical authorities', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockCanonicalTournamentData()
  })

  it('renders tournament metadata, result and canonical publication context without legacy readers', async () => {
    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-1')

    expect(await screen.findByRole('heading', { name: 'Tournament Detail' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-1')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('viewer-run-1')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('viewer-run-1')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('viewer-run-1')

    expect(await screen.findByText('Canonical Open')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(screen.getByText('PLATINUM')).toBeInTheDocument()
    expect(screen.getByText('WORLD TOUR')).toBeInTheDocument()
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ranking publication #8' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/rankings/8'
    )
    expect(screen.getByRole('link', { name: 'Finals Race' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/race'
    )

    expect(await screen.findByRole('list', { name: 'Canonical Tournament player results' })).toHaveTextContent('P-001 · champion · 2W–0L')
    expect(screen.getByRole('list', { name: 'Canonical Tournament match results' })).toHaveTextContent('P-001 def. P-002 · 3-2')

    const technicalSection = screen.getByText('Show canonical source data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    await userEvent.click(screen.getByText('Show canonical source data'))
    expect(within(technicalSection as HTMLElement).getByText(/Canonical Open/i)).toBeVisible()

    expectNoForbiddenViewerActions()
  })

  it('fails closed when event is absent from canonical calendar and history', async () => {
    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/UNKNOWN')

    expect(await screen.findByText(/Event UNKNOWN is not present in the canonical Saved Calendar or Tournament History/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Canonical Entry Field' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps encoded Product Run and event identities in canonical links', async () => {
    api.getViewerRunCalendar.mockResolvedValue({
      schema_version: 'viewer_run_calendar.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      season_count: 1,
      event_count: 1,
      seasons: [{
        season: '2030/2031',
        event_count: 1,
        events: [{
          event_id: 'EVT/1 #A',
          season: '2030/2031',
          season_week: 4,
          calendar_year: 2030,
          year_week: 40,
          template_id: 'WT-GOLD',
          event_name: 'Encoded Open',
          category: 'GOLD',
          tour_level: 'WORLD_TOUR',
          host_country: 'CZE',
          host_city: 'Prague',
          region: 'EUROPE',
          duration_in_season_weeks: 1,
          start_season_week: 4,
          end_season_week: 4,
          status: 'planned',
          main_draw_size: 16,
          qualification_draw_size: 8,
          seeds_count: 4,
          qualifier_spots: 4,
          wild_cards: 2,
          byes: 0,
          prestige: 7
        }]
      }]
    })
    api.getViewerTournamentHistory.mockResolvedValue({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 1,
      published_result_count: 0,
      tournaments: []
    })

    renderViewerTournamentRoute('/viewer/runs/run%2Falpha%20%231/tournaments/EVT%2F1%20%23A')

    expect(await screen.findByText('Encoded Open')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to tournaments' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/tournaments'
    )
    expect(screen.getByRole('link', { name: 'Open calendar event' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/calendar/EVT%2F1%20%23A'
    )
    expectNoForbiddenViewerActions()
  })
})
