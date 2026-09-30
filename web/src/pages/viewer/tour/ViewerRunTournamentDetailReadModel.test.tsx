import { Routes, Route } from 'react-router-dom'
import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerRunTournamentDetailPage } from '../../ViewerRunTournamentsPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
  getEvent: vi.fn(),
  getRun: vi.fn(),
  getViewerTournamentEntryField: vi.fn(),
  getViewerTournamentDraw: vi.fn(),
  getViewerRunCalendar: vi.fn(),
  getViewerCompletedTournaments: vi.fn(),
  getViewerTournamentResult: vi.fn(),
  getViewerTournamentWildCards: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)

function renderDetail(route = '/viewer/runs/run%20alpha/tournaments/EVENT%2F1'): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/tournaments/:eventId" element={<ViewerRunTournamentDetailPage />} />
    </Routes>,
    { route }
  )
}

describe('ViewerRunTournamentDetailPage read model', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: 'run alpha', season: 2028, seed: 42 },
      season_state: {
        season: 2028,
        next_event_index: 1,
        completed_event_ids: ['EVENT/1'],
        ordered_events: [
          { event_id: 'EVENT/1', season: 2028, week: 5, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' }
        ]
      }
    })
    api.getEvent.mockResolvedValue({
      event_sequence: 7,
      event_id: 'EVENT/1',
      season: 2028,
      week: 5,
      template_id: 'WT-PLAT',
      tournament_result: { opaque_payload_marker: 'hidden until technical details open' }
    })
    api.getViewerTournamentEntryField.mockResolvedValue({
      schema_version: 'viewer_tournament_entry_field.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      event_id: 'EVENT/1',
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
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      event_id: 'EVENT/1',
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
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      event_id: 'EVENT/1',
      assignment_count: 2,
      assignments: [
        { wildcard_index: 1, player_id: 'P-WC', source: 'original_wc', reserve_ordinal: null },
        { wildcard_index: 2, player_id: 'P-RWC', source: 'reserve_wc', reserve_ordinal: 3 }
      ]
    })
    api.getViewerTournamentResult.mockRejectedValue(new api.ApiError('canonical result missing', 404))
  })

  it('renders safe persisted tournament metadata and generic publication navigation only', async () => {
    renderDetail()

    expect(await screen.findByText('EVENT/1')).toBeInTheDocument()
    expect(screen.getByText('Platinum')).toBeInTheDocument()
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()

    const sourceLinks = screen.getByRole('heading', { name: 'Source context links' }).closest('article') as HTMLElement
    expect(sourceLinks).not.toBeNull()
    expect(within(sourceLinks).getByRole('link', { name: 'Run browser' })).toHaveAttribute('href', '/viewer/runs')
    expect(within(sourceLinks).getByRole('link', { name: 'Tournament list' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/tournaments'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Planned calendar event' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar/EVENT%2F1'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Week W5' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/weeks/5'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Ranking snapshots' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/rankings'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Race snapshots' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/race'
    )
    expect(screen.getByText(/does not infer event-specific Ranking or Race publications/i)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /publication #/i })).not.toBeInTheDocument()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })





  it('never calls legacy Ranking or Race snapshot APIs from canonical Tournament Detail', async () => {
    api.listRankingSnapshots.mockRejectedValue(new Error('must not be called'))
    api.listRaceSnapshots.mockRejectedValue(new Error('must not be called'))

    renderDetail()

    expect(await screen.findByText('EVENT/1')).toBeInTheDocument()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(screen.queryByText(/snapshot outage/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /publication #/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders conservative source links when persisted event has no planned calendar match', async () => {
    api.getRun.mockResolvedValue({
      run: { run_id: 'run alpha', season: 2028, seed: 42 },
      season_state: {
        season: 2028,
        next_event_index: 1,
        completed_event_ids: [],
        ordered_events: [
          { event_id: 'OTHER', season: 2028, week: 4, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
        ]
      }
    })

    renderDetail()

    expect(await screen.findByText('No ordered-calendar tour')).toBeInTheDocument()
    expect(screen.getByText('No ordered-calendar category')).toBeInTheDocument()
    const sourceLinks = screen.getByRole('heading', { name: 'Source context links' }).closest('article') as HTMLElement
    expect(within(sourceLinks).getByRole('link', { name: 'Run browser' })).toHaveAttribute('href', '/viewer/runs')
    expect(within(sourceLinks).getByRole('link', { name: 'Tournament list' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/tournaments'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Tournament detail' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/tournaments/EVENT%2F1'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Ranking snapshots' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/rankings'
    )
    expect(within(sourceLinks).getByRole('link', { name: 'Race snapshots' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/race'
    )
    expect(within(sourceLinks).queryByRole('link', { name: 'Planned calendar event' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps the persisted week link when an event has week context but no planned calendar match', async () => {
    api.getRun.mockResolvedValue({
      run: { run_id: 'run alpha', season: 2028, seed: 42 },
      season_state: { season: 2028, next_event_index: 1, completed_event_ids: [], ordered_events: [] }
    })

    renderDetail()

    expect(await screen.findByRole('heading', { name: 'Source context links' })).toBeInTheDocument()
    const sourceLinks = screen.getByRole('heading', { name: 'Source context links' }).closest('article') as HTMLElement
    expect(within(sourceLinks).getByRole('link', { name: 'Week W5' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/weeks/5'
    )
    expect(within(sourceLinks).queryByRole('link', { name: 'Planned calendar event' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('omits week and planned-event links when neither persisted nor planned week context exists', async () => {
    api.getRun.mockResolvedValue({
      run: { run_id: 'run alpha', season: 2028, seed: 42 },
      season_state: { season: 2028, next_event_index: 1, completed_event_ids: [], ordered_events: [] }
    })
    api.getEvent.mockResolvedValue({
      event_sequence: 7,
      event_id: 'EVENT/1',
      season: null,
      week: null,
      template_id: null,
      tournament_result: null
    })

    renderDetail()

    expect(await screen.findByText('No ordered-calendar tour')).toBeInTheDocument()
    expect(screen.getByText('No ordered-calendar category')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    const sourceLinks = screen.getByRole('heading', { name: 'Source context links' }).closest('article') as HTMLElement
    expect(within(sourceLinks).queryByRole('link', { name: /^Week W/ })).not.toBeInTheDocument()
    expect(within(sourceLinks).queryByRole('link', { name: 'Planned calendar event' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders a no-data state for a missing persisted event', async () => {
    api.getEvent.mockRejectedValue({ status: 404 })

    renderDetail()

    expect(await screen.findByText('Event EVENT/1 was not found for this run.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Source context links' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders a temporarily unavailable state for API errors', async () => {
    api.getEvent.mockRejectedValue(new Error('network unavailable'))

    renderDetail()

    expect(await screen.findByText('Failed to load tournament detail: network unavailable')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not call APIs when route params are missing', () => {
    renderWithViewerProviders(
      <Routes>
        <Route path="/viewer/runs/:runId/tournaments/" element={<ViewerRunTournamentDetailPage />} />
      </Routes>,
      { route: '/viewer/runs/run%20alpha/tournaments/' }
    )

    expect(screen.getByText('No event ID was provided in the URL.')).toBeInTheDocument()
    expect(api.getEvent).not.toHaveBeenCalled()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
