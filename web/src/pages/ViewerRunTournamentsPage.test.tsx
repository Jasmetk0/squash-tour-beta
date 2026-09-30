import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunTournamentDetailPage, ViewerRunTournamentsPage } from './ViewerRunTournamentsPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentEntryField: vi.fn(),
  getViewerTournamentDraw: vi.fn(),
  getViewerTournamentResult: vi.fn(),
  getViewerTournamentWildCards: vi.fn(),
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

function renderRoute(route: string): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/tournaments" element={<ViewerRunTournamentsPage />} />
      <Route path="/viewer/runs/:runId/tournaments/:eventId" element={<ViewerRunTournamentDetailPage />} />
    </Routes>,
    { route }
  )
}

function event(overrides: Record<string, unknown> = {}) {
  return {
    event_id: 'EVENT-1',
    season: '2027/28',
    season_index: 27,
    season_week: 3,
    calendar_year: 2027,
    year_week: 39,
    template_id: 'WT-PLAT',
    event_name: 'Brno Platinum',
    category: 'Platinum',
    tour_level: 'WORLD_TOUR',
    host_country: 'CZE',
    host_city: 'Brno',
    region: 'Europe',
    main_draw_size: 32,
    qualification_draw_size: 16,
    qualifier_spots: 4,
    wild_card_slots: 2,
    bye_slots: 0,
    ranking_status: 'ranked',
    source_status: 'planned',
    result: {
      champion_player_id: 'P-001',
      finalist_player_id: 'P-002',
      match_count: 31
    },
    ...overrides
  }
}

function calendar(events = [event(), event({
  event_id: 'EVENT-2',
  season_week: 4,
  template_id: 'ET-GOLD',
  event_name: 'Prague Gold',
  category: 'Gold',
  tour_level: 'ELITE_TOUR',
  host_city: 'Prague',
  result: null
})]) {
  return {
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'viewer-run-1',
    viewer_branch_id: 'branch-viewer',
    calendar_count: 1,
    event_count: events.length,
    events
  }
}

function setupDetailAuthorities(): void {
  api.listRankingSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })
  api.listRaceSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })
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
}

function expectNoForbiddenViewerActions(): void {
  for (const label of ['Simulate', 'Generate', 'Persist', 'Apply', 'Execute', 'Delete', 'Edit', 'Import', 'Rollover', 'Rebuild', 'Override', 'Save changes', 'Commit', 'Regenerate', 'Repair', 'Merge', 'Overwrite']) {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  }
}

describe('ViewerRunTournamentsPage canonical calendar', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getViewerRunCalendar.mockResolvedValue(calendar())
  })

  it('renders canonical Saved Calendar metadata and result summaries', async () => {
    renderRoute('/viewer/runs/viewer-run-1/tournaments')

    expect(await screen.findByRole('heading', { name: 'Tournaments' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-1')
    const first = (await screen.findByText('Brno Platinum')).closest('li') as HTMLElement
    expect(within(first).getByText('EVENT-1')).toBeInTheDocument()
    expect(within(first).getByText('WT-PLAT')).toBeInTheDocument()
    expect(within(first).getByText('Platinum')).toBeInTheDocument()
    expect(within(first).getByText('WORLD_TOUR')).toBeInTheDocument()
    expect(within(first).getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(within(first).getByText('Champion')).toBeInTheDocument()
    expect(within(first).getByText('P-001')).toBeInTheDocument()
    expect(within(first).getByText('31')).toBeInTheDocument()
    expect(screen.getByText('Prague Gold')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Open tournament detail/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments/EVENT-1'
    )
    expectNoForbiddenViewerActions()
  })

  it('shows a Saved Calendar missing state without legacy fallback', async () => {
    api.getViewerRunCalendar.mockRejectedValueOnce(new api.ApiError('missing calendar', 404))
    renderRoute('/viewer/runs/viewer-run-1/tournaments')
    expect(await screen.findByText('No saved Calendar Package is available for this run yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders an empty canonical calendar without invented tournament data', async () => {
    api.getViewerRunCalendar.mockResolvedValueOnce(calendar([]))
    renderRoute('/viewer/runs/viewer-run-1/tournaments')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.queryByText(/champion|winner|final score/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunTournamentDetailPage canonical calendar', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getViewerRunCalendar.mockResolvedValue(calendar([event({ result: null })]))
    setupDetailAuthorities()
  })

  it('renders canonical Calendar metadata with Entry, WC and Draw authorities', async () => {
    renderRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-1')

    expect(await screen.findByRole('heading', { name: 'Tournament Detail' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-1')
    expect(screen.getByText('Brno Platinum')).toBeInTheDocument()
    expect(screen.getByText('2027/28')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()
    expect(screen.getByText('Platinum')).toBeInTheDocument()
    expect(screen.getByText('WORLD_TOUR')).toBeInTheDocument()
    expect(screen.getByText('CZE')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Canonical Entry Field' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Definitive Wild Cards' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Canonical Draw' })).toBeInTheDocument()
    expect(screen.getByText('#1 · P-001 · seed 1')).toBeInTheDocument()
    expect(screen.getByText('#4 · P-002 · seed 2 · wild card')).toBeInTheDocument()
    expect(await screen.findByText('Canonical Tournament Result is not available for this tournament yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders detailed canonical Tournament Result independently from calendar summary', async () => {
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
        }
      ],
      matches: [
        { match_id: 'final', draw_type: 'main', round_number: 2, bracket_position: 1, winner_player_id: 'P-001', loser_player_id: 'P-002', scoreline: '3-2' }
      ]
    })

    renderRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-1')

    expect(await screen.findByRole('list', { name: 'Canonical Tournament player results' })).toHaveTextContent('P-001 · champion · 2W–0L · seed 1')
    expect(screen.getByRole('list', { name: 'Canonical Tournament match results' })).toHaveTextContent('final · main R2 · P-001 def. P-002 · 3-2')
    expectNoForbiddenViewerActions()
  })

  it('keeps source publication links encoded while metadata comes from canonical calendar', async () => {
    api.getViewerRunCalendar.mockResolvedValueOnce({
      ...calendar([]),
      product_run_id: 'run/alpha #1',
      events: [event({ event_id: 'EVT/1 #A', season_week: 5, result: null })],
      event_count: 1
    })
    api.listRankingSnapshots.mockResolvedValueOnce({
      run_id: 'legacy',
      snapshots: [{ snapshot_sequence: 10, source_event_id: 'EVT/1 #A', payload: {} }]
    })
    api.listRaceSnapshots.mockResolvedValueOnce({
      run_id: 'legacy',
      snapshots: [{ snapshot_sequence: 12, source_event_id: 'EVT/1 #A', payload: {} }]
    })

    renderRoute('/viewer/runs/run%2Falpha%20%231/tournaments/EVT%2F1%20%23A')

    expect(await screen.findByText('EVT/1 #A')).toBeInTheDocument()
    const links = screen.getByRole('heading', { name: 'Source context links' }).closest('article') as HTMLElement
    expect(within(links).getByRole('link', { name: 'Planned calendar event' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/calendar/EVT%2F1%20%23A'
    )
    expect(within(links).getByRole('link', { name: 'Week W5' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/weeks/5'
    )
    expectNoForbiddenViewerActions()
  })

  it('fails closed when the event is absent from the Saved Calendar', async () => {
    api.getViewerRunCalendar.mockResolvedValueOnce(calendar([]))
    renderRoute('/viewer/runs/viewer-run-1/tournaments/MISSING')
    expect(await screen.findByText('Event MISSING was not found in the saved Viewer calendar.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Canonical Entry Field' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not call canonical tournament APIs without an event route param', () => {
    renderWithViewerProviders(
      <Routes>
        <Route path="/viewer/runs/:runId/tournaments/" element={<ViewerRunTournamentDetailPage />} />
      </Routes>,
      { route: '/viewer/runs/viewer-run-1/tournaments/' }
    )

    expect(screen.getByText('No event ID was provided in the URL.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentEntryField).not.toHaveBeenCalled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
