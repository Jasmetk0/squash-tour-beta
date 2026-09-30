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
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentEntryField: vi.fn(),
  getViewerTournamentDraw: vi.fn(),
  getViewerTournamentResult: vi.fn(),
  getViewerTournamentWildCards: vi.fn(),
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

function canonicalCalendar() {
  return {
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-viewer',
    calendar_count: 1,
    event_count: 1,
    events: [{
      event_id: 'EVENT/1',
      season: '2028/29',
      season_index: 28,
      season_week: 5,
      calendar_year: 2028,
      year_week: 41,
      template_id: 'WT-PLAT',
      event_name: 'Canonical Event',
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
      result: null
    }]
  }
}

describe('ViewerRunTournamentDetailPage canonical read model', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getViewerRunCalendar.mockResolvedValue(canonicalCalendar())
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'run alpha',
      snapshots: [
        { snapshot_sequence: 10, snapshot_kind: 'ranking', source_event_id: 'EVENT/1', payload: {} },
        { snapshot_sequence: 11, snapshot_kind: 'ranking', source_event_id: 'OTHER', payload: {} }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'run alpha',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'race', source_event_id: 'EVENT/1', payload: {} }]
    })
    api.getViewerTournamentEntryField.mockRejectedValue(new api.ApiError('missing field', 404))
    api.getViewerTournamentDraw.mockRejectedValue(new api.ApiError('missing draw', 404))
    api.getViewerTournamentWildCards.mockResolvedValue({
      schema_version: 'viewer_tournament_wild_cards.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      event_id: 'EVENT/1',
      assignment_count: 0,
      assignments: []
    })
    api.getViewerTournamentResult.mockRejectedValue(new api.ApiError('missing result', 404))
  })

  it('renders Saved Calendar metadata and encoded source links', async () => {
    renderDetail()

    expect(await screen.findByRole('heading', { name: 'Tournament Detail' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run alpha')
    expect(api.listRankingSnapshots).toHaveBeenCalledWith('run alpha')
    expect(api.listRaceSnapshots).toHaveBeenCalledWith('run alpha')
    expect(screen.getByText('Canonical Event')).toBeInTheDocument()
    expect(screen.getByText('2028/29')).toBeInTheDocument()
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()
    expect(screen.getByText('WORLD_TOUR')).toBeInTheDocument()
    expect(screen.getByText('Platinum')).toBeInTheDocument()

    const links = screen.getByRole('heading', { name: 'Source context links' }).closest('article') as HTMLElement
    expect(within(links).getByRole('link', { name: 'Tournament list' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/tournaments'
    )
    expect(within(links).getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar'
    )
    expect(within(links).getByRole('link', { name: 'Planned calendar event' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar/EVENT%2F1'
    )
    expect(within(links).getByRole('link', { name: 'Week W5' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/weeks/5'
    )
    expect(within(links).getByRole('link', { name: 'Ranking publication #10' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/rankings/10'
    )
    expect(within(links).getByRole('link', { name: 'Race publication #12' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/race/12'
    )
    expect(await screen.findByText('Canonical Tournament Result is not available for this tournament yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps canonical tournament metadata visible when ranking publications fail', async () => {
    api.listRankingSnapshots.mockRejectedValue(new Error('ranking snapshot outage'))
    renderDetail()
    expect(await screen.findByText('Canonical Event')).toBeInTheDocument()
    expect(await screen.findByText('Failed to load ranking publications: ranking snapshot outage')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Race publication #12' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps canonical tournament metadata visible when race publications fail', async () => {
    api.listRaceSnapshots.mockRejectedValue(new Error('race snapshot outage'))
    renderDetail()
    expect(await screen.findByText('Canonical Event')).toBeInTheDocument()
    expect(await screen.findByText('Failed to load race publications: race snapshot outage')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ranking publication #10' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('fails closed when the Saved Calendar is unavailable', async () => {
    api.getViewerRunCalendar.mockRejectedValue(new api.ApiError('missing calendar', 404))
    renderDetail()
    expect(await screen.findByText('No saved Calendar Package is available for this run yet.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Source context links' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not query Viewer tournament authorities without an event route param', () => {
    renderWithViewerProviders(
      <Routes>
        <Route path="/viewer/runs/:runId/tournaments/" element={<ViewerRunTournamentDetailPage />} />
      </Routes>,
      { route: '/viewer/runs/run%20alpha/tournaments/' }
    )

    expect(screen.getByText('No event ID was provided in the URL.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentEntryField).not.toHaveBeenCalled()
    expect(api.getViewerTournamentDraw).not.toHaveBeenCalled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
