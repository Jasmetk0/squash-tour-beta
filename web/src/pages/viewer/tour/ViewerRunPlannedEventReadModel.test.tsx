import { Route, Routes } from 'react-router-dom'
import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerRunPlannedEventPage } from '../../ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
  getRun: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)

function renderPlanned(route = '/viewer/runs/run%20alpha/calendar/EVENT%2F1'): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/calendar/:eventId" element={<ViewerRunPlannedEventPage />} />
      <Route path="/viewer/planned-missing" element={<ViewerRunPlannedEventPage />} />
    </Routes>,
    { route }
  )
}

describe('ViewerRunPlannedEventPage read model', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: 'run alpha', season: 2028, seed: 42 },
      season_state: {
        season: 2028,
        next_event_index: 1,
        completed_event_ids: ['EVENT/1'],
        ordered_events: [
          { event_id: 'EVENT/1', season: 2028, week: 5, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
          { event_id: 'EVENT 2', season: 2028, week: 6, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({
      run_id: 'run alpha',
      events: [
        {
          event_sequence: 7,
          event_id: 'EVENT/1',
          season: 2028,
          week: 5,
          template_id: 'WT-PLAT',
          tournament_result: { champion: { player_name: 'Should Not Render' } }
        }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run alpha', snapshots: [] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run alpha', snapshots: [] })
  })

  it('renders planned event metadata and safe source links without result content', async () => {
    renderPlanned()

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(api.getRun).toHaveBeenCalledWith('run alpha')
    expect(api.listEvents).toHaveBeenCalledWith('run alpha')
    expect(screen.getAllByText('run alpha').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT/1').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('2028')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('W5').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('WT-PLAT').length).toBeGreaterThan(0)
    expect(screen.getByText('Plan index')).toBeInTheDocument()
    expect(screen.getAllByText('Plan position').length).toBeGreaterThan(0)
    expect(screen.getAllByText('1 of 2').length).toBeGreaterThan(0)
    expect(screen.getByText('Current next event index')).toBeInTheDocument()
    expect(screen.getByText('Planned event status')).toBeInTheDocument()
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0)
    expect(screen.getByText('Persisted event record')).toBeInTheDocument()
    expect(screen.getByText('Persisted event sequence')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()

    const sourceLinks = screen.getByRole('heading', { name: 'Source context links' }).closest('article')
    expect(sourceLinks).not.toBeNull()
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Run browser' })).toHaveAttribute('href', '/viewer/runs')
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar'
    )
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Planned calendar event' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/calendar/EVENT%2F1'
    )
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Tournament detail' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/tournaments/EVENT%2F1'
    )
    expect(within(sourceLinks as HTMLElement).getByRole('link', { name: 'Week W5' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/weeks/5'
    )
    expect(screen.queryByText('Should Not Render')).not.toBeInTheDocument()
    expect(screen.queryByText('Tournament Result Preview')).not.toBeInTheDocument()
    expect(screen.queryByText(/winner/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/draw/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not render a tournament detail link when no persisted event matches', async () => {
    api.listEvents.mockResolvedValue({ run_id: 'run alpha', events: [] })
    renderPlanned()

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(await screen.findByText('No persisted tournament record is available for this planned event yet.')).toBeInTheDocument()
    expect(screen.getByText('Persisted event record')).toBeInTheDocument()
    expect(screen.getByText('Not available')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tournament detail' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders a no-data state for a missing planned event', async () => {
    renderPlanned('/viewer/runs/run%20alpha/calendar/MISSING')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(await screen.findByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tournament detail' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders a safe error state when season state fails', async () => {
    api.getRun.mockRejectedValue(new Error('season state outage'))
    renderPlanned()

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(await screen.findByText('Failed to load run season state: season state outage')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not call APIs when route params are missing', async () => {
    renderPlanned('/viewer/planned-missing')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(screen.getByText('No planned event route context was provided.')).toBeInTheDocument()
    expect(screen.getByText('No planned event ID was provided in the URL.')).toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
