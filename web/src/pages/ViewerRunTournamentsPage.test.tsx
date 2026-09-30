import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunTournamentDetailPage, ViewerRunTournamentsPage } from './ViewerRunTournamentsPage'

const api = vi.hoisted(() => ({
  getEvent: vi.fn(),
  getRun: vi.fn(),
  getViewerTournamentEntryField: vi.fn(),
  getViewerTournamentDraw: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  getViewerTournamentResult: vi.fn(),
  getViewerTournamentWildCards: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
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

function mockRunMetadata(): void {
  api.getRun.mockResolvedValue({
    run: {
      run_id: 'viewer-run-1',
      season: 2027,
      seed: 42,
      config_version: 'v1',
      config_fingerprint: 'fp',
      next_event_index: 1,
      total_events: 2,
      completed_event_ids: ['EVENT-1']
    },
    season_state: {
      season: 2027,
      next_event_index: 1,
      completed_event_ids: ['EVENT-1'],
      ordered_events: [
        { event_id: 'EVENT-1', season: 2027, week: 3, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
        { event_id: 'EVENT-2', season: 2027, week: 4, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
      ]
    }
  })
}

function mockEvents(): void {
  api.listEvents.mockResolvedValue({
    run_id: 'viewer-run-1',
    events: [
      {
        event_sequence: 8,
        event_id: 'EVENT-1',
        season: 2027,
        week: 3,
        template_id: 'WT-PLAT',
        tournament_result: {
          summary: {
            champion: { player_id: 'P-001', name: 'Ali Farag', country: 'EGY' },
            match_count: 31,
            status: 'completed',
            secret_debug_marker: 'event-list-payload-should-not-render',
            matches: [{ label: 'Match 1 should not render from raw payload' }]
          }
        }
      },
      { event_sequence: 9, event_id: 'EVENT-2', season: 2027, week: 4, template_id: 'ET-GOLD', tournament_result: null }
    ]
  })
}

function mockViewerTournamentHistory(): void {
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
        season: '2002/2003',
        season_week: 17,
        event_name: 'Current Open',
        template_id: 'WT-PLAT',
        category: 'DIAMOND',
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

describe('ViewerRunTournamentsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockViewerTournamentHistory()
  })

  it('renders canonical multi-season tournament history without legacy event reads', async () => {
    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments')

    expect(await screen.findByRole('heading', { name: 'Tournaments' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Canonical Tournament History' })).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('viewer-run-1')
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.getRun).not.toHaveBeenCalled()

    const list = screen.getByRole('list', { name: 'Canonical tournament history list' })
    expect(within(list).getByText('Old Open')).toBeInTheDocument()
    expect(within(list).getByText('Current Open')).toBeInTheDocument()

    const old = within(list).getByText('Old Open').closest('li') as HTMLElement
    expect(within(old).getByText('2000/2001')).toBeInTheDocument()
    expect(within(old).getByRole('link', { name: 'W5' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/weeks/5'
    )
    expect(within(old).getByText('Not published')).toBeInTheDocument()

    const current = within(list).getByText('Current Open').closest('li') as HTMLElement
    expect(within(current).getByText('2002/2003')).toBeInTheDocument()
    expect(within(current).getByText('DIAMOND')).toBeInTheDocument()
    expect(within(current).getByText('WORLD TOUR')).toBeInTheDocument()
    expect(within(current).getByText('Cairo, EGY')).toBeInTheDocument()
    expect(within(current).getByText('Published')).toBeInTheDocument()
    expect(within(current).getByText('P-001')).toBeInTheDocument()
    expect(within(current).getByText('P-002')).toBeInTheDocument()
    expect(within(current).getByRole('link', { name: 'Open tournament detail' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments/EVENT-1'
    )

    expectNoForbiddenViewerActions()
  })

  it('shows a safe empty state when the Viewer Branch has no saved Calendar Package', async () => {
    api.getViewerTournamentHistory.mockRejectedValueOnce(
      new api.ApiError('Viewer Saved Revision has no applied Calendar Package', 404)
    )

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments')

    expect(
      await screen.findByText('No saved Calendar Package is available for this Viewer Branch yet.')
    ).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Canonical tournament history list' })).not.toBeInTheDocument()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.getRun).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders an empty canonical list without inventing sporting data', async () => {
    api.getViewerTournamentHistory.mockResolvedValueOnce({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'viewer-run-1',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 0,
      published_result_count: 0,
      tournaments: []
    })

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments')

    expect(
      await screen.findByText('No tournaments are present in the saved Calendar Packages.')
    ).toBeInTheDocument()
    expect(screen.queryByText(/fake champion|invented winner|legacy champion/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunTournamentDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })
    api.getEvent.mockResolvedValue({
      event_sequence: 8,
      event_id: 'EVENT-1',
      season: 2027,
      week: 3,
      template_id: 'WT-PLAT',
      tournament_result: { secret_debug_marker: 'event-detail-hidden-payload' }
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
          { slot_index: 2, entrant_kind: 'bye', player_id: null, placeholder_id: null, seed_number: null, entry_status: null },
          { slot_index: 3, entrant_kind: 'qualifier_placeholder', player_id: null, placeholder_id: 'Q1', seed_number: null, entry_status: null },
          { slot_index: 4, entrant_kind: 'player', player_id: 'P-002', placeholder_id: null, seed_number: 2, entry_status: 'wild_card' }
        ]
      },
      qualification_sections: []
    })
    api.getViewerTournamentWildCards.mockResolvedValue({
      schema_version: 'viewer_tournament_wild_cards.v1',
      product_run_id: 'viewer-run-1',
      viewer_branch_id: 'branch-viewer',
      event_id: 'EVENT-1',
      assignment_count: 2,
      assignments: [
        { wildcard_index: 1, player_id: 'P-WC', source: 'original_wc', reserve_ordinal: null },
        { wildcard_index: 2, player_id: 'P-RWC', source: 'reserve_wc', reserve_ordinal: 3 }
      ]
    })
    api.getViewerTournamentResult.mockRejectedValue(new api.ApiError('canonical result missing', 404))
  })

  it('renders canonical saved tournament result instead of legacy result payload', async () => {
    api.getEvent.mockResolvedValueOnce({
      event_sequence: 8,
      event_id: 'EVENT-1',
      season: 2027,
      week: 3,
      template_id: 'WT-PLAT',
      tournament_result: {
        summary: {
          champion: { player_id: 'LEGACY', name: 'Legacy Champion', country: 'OLD' },
          secret_debug_marker: 'parseable-hidden-payload'
        }
      }
    })
    api.getViewerTournamentResult.mockResolvedValueOnce({
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
        },
        {
          player_id: 'P-003', draw_type: 'both', seed_number: null, qualifier: true,
          main_entry_status: null, reached_stage: 'semifinal', final_round_number: 1,
          eliminated_by_player_id: 'P-001', last_match_id: 'semi', wins: 1, losses: 1,
          byes_received: 0, walkovers_received: 1, retired_or_walkover_loss: false,
          group_index: null, group_position: null, played_group_wins: null,
          group_walkovers_received: null, knockout_reached_stage: null
        }
      ],
      matches: [
        { match_id: 'semi', draw_type: 'main', round_number: 1, bracket_position: 1, winner_player_id: 'P-001', loser_player_id: 'P-003', scoreline: '3-0' },
        { match_id: 'final', draw_type: 'main', round_number: 2, bracket_position: 1, winner_player_id: 'P-001', loser_player_id: 'P-002', scoreline: '3-2' }
      ]
    })

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-1')

    expect(await screen.findByRole('heading', { name: 'Canonical Tournament Result' })).toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledWith('viewer-run-1', 'EVENT-1')
    expect(await screen.findByRole('list', { name: 'Canonical Tournament player results' })).toHaveTextContent('P-001 · champion · 2W–0L · seed 1')
    expect(screen.getByRole('list', { name: 'Canonical Tournament player results' })).toHaveTextContent('P-003 · semifinal · 1W–1L · qualifier')
    expect(await screen.findByRole('list', { name: 'Canonical Tournament match results' })).toHaveTextContent('final · main R2 · P-001 def. P-002 · 3-2')
    expect(screen.queryByText('Legacy Champion')).not.toBeInTheDocument()
    expect(screen.queryByText(/parseable-hidden-payload/i)).not.toBeVisible()
    const technicalSection = screen.getByText('Show technical event data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expectNoForbiddenViewerActions()
  })


  it('renders sports-facing tournament detail with deferred preview for unknown result shapes', async () => {
    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-1')

    expect(await screen.findByRole('heading', { name: 'Tournament Detail' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-1').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('2027')).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour').length).toBeGreaterThan(0)
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()
    expect(await screen.findByText('Canonical Tournament Result is not available for this tournament yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to tournaments/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments'
    )
    expect(screen.getByRole('link', { name: /Open calendar event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/calendar/EVENT-1'
    )
    expect(screen.getByRole('link', { name: /Open week detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    const technicalSection = screen.getByText('Show technical event data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/event-detail-hidden-payload/i)).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical event data'))
    expect(within(technicalSection as HTMLElement).getByText(/event-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })

  it('keeps missing tournament detail weeks as plain text without a broken week link', async () => {
    api.getEvent.mockResolvedValueOnce({
      event_sequence: 10,
      event_id: 'EVENT-NO-WEEK',
      season: 2027,
      week: null,
      template_id: 'WT-GOLD',
      tournament_result: {
        summary: {
          champion: { player_id: 'P-001', name: 'Ali Farag', country: 'EGY' },
          status: 'completed'
        }
      }
    })

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-NO-WEEK')

    expect(await screen.findByText('WT-GOLD')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Canonical Tournament Result' })).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.queryByRole('link', { name: /^W/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('handles encoded tournament detail route params and malformed snapshots safely', async () => {
    api.getEvent.mockResolvedValueOnce({ event_sequence: 1, event_id: 'EVT/1 #A', season: 2030, week: null, template_id: { bad: true }, tournament_result: { fake_winner: 'Fake Winner' } })
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run/alpha #1', season: 2030, seed: 1, config_version: 'v', config_fingerprint: 'fp', next_event_index: 0, total_events: 0, completed_event_ids: [] },
      season_state: { season: 2030, next_event_index: 0, completed_event_ids: [], ordered_events: [{ event_id: { bad: true }, week: { bad: true } }] }
    })
    api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'run/alpha #1', snapshots: [null, {}, { snapshot_sequence: { bad: true }, source_event_id: { bad: true } }] })
    api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'run/alpha #1', snapshots: [null, 7] })

    renderViewerTournamentRoute('/viewer/runs/run%2Falpha%20%231/tournaments/EVT%2F1%20%23A')

    expect(await screen.findByRole('heading', { name: 'Tournament Detail' })).toBeInTheDocument()
    expect(api.getEvent).toHaveBeenCalledWith('run/alpha #1', 'EVT/1 #A')
    expect(api.getRun).toHaveBeenCalledWith('run/alpha #1')
    expect(screen.getAllByText('run/alpha #1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVT/1 #A').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Back to tournaments/i })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/tournaments')
    expect(await screen.findByText('Canonical Tournament Result is not available for this tournament yet.')).toBeInTheDocument()
    expect(screen.queryByText('Fake Winner')).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('[object Object]')
    expectNoForbiddenViewerActions()
  })

})
