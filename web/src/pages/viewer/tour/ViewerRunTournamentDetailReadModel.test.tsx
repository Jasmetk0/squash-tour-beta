import { Routes, Route } from 'react-router-dom'
import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { calendarEvent, historyEvent, savedCalendar, savedHistory, savedRankings, savedRace, rankingPublication, racePublication } from '../../../test/viewerCalendarFixtures'
import { ViewerRunTournamentDetailPage } from '../../ViewerRunTournamentsPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  getViewerTournamentResult: vi.fn(),
  getEvent: vi.fn(),
  getRun: vi.fn(),
  getViewerTournamentEntryField: vi.fn(),
  getViewerTournamentDraw: vi.fn(),
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
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar())
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent()]))
    api.listViewerOfficialRankingHistory.mockResolvedValue(savedRankings([rankingPublication()]))
    api.getViewerFinalsRace.mockResolvedValue(savedRace([racePublication()]))
    api.getViewerTournamentResult.mockRejectedValue(new api.ApiError('Not published', 404))
    api.getViewerTournamentEntryField.mockResolvedValue({
      schema_version: 'viewer_tournament_entry_field.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'viewer-branch',
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
      viewer_branch_id: 'viewer-branch',
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
      viewer_branch_id: 'viewer-branch',
      event_id: 'EVENT/1',
      assignment_count: 2,
      assignments: [
        { wildcard_index: 1, player_id: 'P-WC', source: 'original_wc', reserve_ordinal: null },
        { wildcard_index: 2, player_id: 'P-RWC', source: 'reserve_wc', reserve_ordinal: 3 }
      ]
    })
    api.getViewerTournamentResult.mockRejectedValue(new api.ApiError('canonical result missing', 404))
  })

  it('renders canonical metadata, Field, Draw and WC with encoded source links', async () => {
    renderDetail()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run alpha')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('run alpha')
    expect(api.getEvent).not.toHaveBeenCalled()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: 'Open calendar event' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVENT%2F1')
    expect(screen.getByRole('link', { name: 'Open week detail' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/weeks/5')
    expect(await screen.findByRole('list', { name: 'Canonical Main draw slots' })).toHaveTextContent('P-001')
    expect(screen.getByRole('heading', { name: 'Canonical Entry Field' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Definitive Wild Cards' })).toBeInTheDocument()
    expect(await screen.findByText('Canonical Tournament Result is not available for this tournament yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps detail and Race source links when Ranking publications fail', async () => {
    api.listViewerOfficialRankingHistory.mockRejectedValue(new Error('ranking outage'))
    renderDetail()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(await screen.findByText('Failed to load Official Ranking history: ranking outage')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Finals Race' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
  })

  it('keeps Ranking publications available when Race history fails', async () => {
    api.getViewerFinalsRace.mockRejectedValue(new Error('race outage'))
    renderDetail()
    expect(await screen.findByRole('link', { name: 'Ranking publication #1712' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/1712')
    expect(await screen.findByText('Failed to load Finals Race history: race outage')).toBeInTheDocument()
  })

  it('keeps canonical metadata visible when both publication queries fail', async () => {
    api.listViewerOfficialRankingHistory.mockRejectedValue(new Error('ranking outage'))
    api.getViewerFinalsRace.mockRejectedValue(new Error('race outage'))
    renderDetail()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(await screen.findByText('Failed to load Official Ranking history: ranking outage')).toBeInTheDocument()
    expect(await screen.findByText('Failed to load Finals Race history: race outage')).toBeInTheDocument()
  })

  it('uses exact canonical History metadata when the Calendar has no occurrence', async () => {
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([]))
    renderDetail()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open calendar event' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open week detail' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/weeks/5')
  })

  it('does not partially match a different History event ID', async () => {
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([]))
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent(calendarEvent({ event_id: 'EVENT/10' }))]))
    renderDetail()
    expect(await screen.findByText('Event EVENT/1 is not present in the canonical Saved Calendar or Tournament History.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open calendar event' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open week detail' })).not.toBeInTheDocument()
  })

  it('omits week and event links when neither canonical source has this event', async () => {
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([]))
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory())
    renderDetail()
    expect(await screen.findByText('Event EVENT/1 is not present in the canonical Saved Calendar or Tournament History.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open calendar event' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open week detail' })).not.toBeInTheDocument()
  })

  it('does not infer a published result merely from completed Calendar status', async () => {
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([calendarEvent({ status: 'completed' })]))
    renderDetail()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(await screen.findByText('Canonical Tournament Result is not available for this tournament yet.')).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Canonical Tournament match results' })).not.toBeInTheDocument()
  })

  it('reports canonical metadata read errors without fabricating event links', async () => {
    api.getViewerRunCalendar.mockRejectedValue(new Error('network unavailable'))
    api.getViewerTournamentHistory.mockRejectedValue(new Error('network unavailable'))
    renderDetail()
    expect(await screen.findByText('Failed to load canonical tournament metadata: network unavailable')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open week detail' })).not.toBeInTheDocument()
    expect(api.getEvent).not.toHaveBeenCalled()
  })

  it('does not call APIs when the event parameter is missing', () => {
    renderWithViewerProviders(<Routes><Route path="/viewer/runs/:runId/missing-event" element={<ViewerRunTournamentDetailPage />} /></Routes>, { route: '/viewer/runs/run%20alpha/missing-event' })
    expect(screen.getByText('No event ID was provided in the URL.')).toBeInTheDocument()
    for (const reader of [api.getViewerRunCalendar, api.getViewerTournamentHistory, api.getViewerTournamentEntryField, api.getViewerTournamentDraw, api.getViewerTournamentResult]) expect(reader).not.toHaveBeenCalled()
  })
})
