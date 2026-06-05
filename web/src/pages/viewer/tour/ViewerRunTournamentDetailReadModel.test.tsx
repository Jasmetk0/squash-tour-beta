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
  })

  it('renders safe persisted tournament metadata and encoded source links', async () => {
    renderDetail()

    expect(await screen.findByRole('heading', { name: 'Tournament Detail' })).toBeInTheDocument()
    expect(api.getEvent).toHaveBeenCalledWith('run alpha', 'EVENT/1')
    expect(screen.getAllByText('run alpha').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT/1').length).toBeGreaterThan(0)
    expect(await screen.findByText('Sequence')).toBeInTheDocument()
    expect(screen.getByText('W5')).toBeInTheDocument()
    expect(screen.getByText('World Tour')).toBeInTheDocument()
    expect(screen.getByText('Platinum')).toBeInTheDocument()
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()

    const sourceLinks = screen.getByRole('heading', { name: 'Source context links' }).closest('article') ?? screen.getByText('Safe links').closest('dl')
    expect(sourceLinks).not.toBeNull()
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Run browser' })).toHaveAttribute('href', '/viewer/runs')
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Tournament list' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/tournaments'
    )
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar'
    )
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Planned calendar event' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar/EVENT%2F1'
    )
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Week W5' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/weeks/5'
    )
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Ranking publication #10' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/rankings/10'
    )
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Race publication #12' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/race/12'
    )
    expect(screen.getByText('Ranking publications from event')).toBeInTheDocument()
    expect(screen.getByText('Race publications from event')).toBeInTheDocument()
    expect(screen.queryByText(/winner/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/champion/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/draw/i)).not.toBeInTheDocument()
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
